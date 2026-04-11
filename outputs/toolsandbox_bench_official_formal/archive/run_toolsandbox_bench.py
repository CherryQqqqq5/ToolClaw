"""Prepare ToolSandbox-style samples, execute repeated runs, and aggregate benchmark outputs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import ToolSandboxAdapter
from toolclaw.benchmarks.runner_utils import (
    AggregateMetric,
    BenchmarkScriptConfig,
    aggregate_records,
    finalize_outputs,
    invoke_run_eval,
    load_run_rows,
    mean_or_zero,
    normalize_systems,
    score_to_payload,
    update_experiment_manifest,
    write_csv_rows,
    write_group_markdown,
)


def _default_source() -> Path:
    candidates = [
        ROOT_DIR / "data" / "toolsandbox.formal.official.json",
        ROOT_DIR / "data" / "toolsandbox.formal.json",
        ROOT_DIR / "data" / "toolsandbox.sample.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


DEFAULT_SOURCE = _default_source()
DEFAULT_OFFICIAL_DATA_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox" / "data"


def _bool_from_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _query_is_natural_language(query: Any, sample_id: str) -> bool:
    normalized_query = str(query or "").strip()
    normalized_sample_id = str(sample_id).strip()
    if not normalized_query:
        return False
    if normalized_query == normalized_sample_id:
        return False
    return (" " in normalized_query) or any(char in normalized_query for char in "?!.:,;'\"")


def _reference_result_summary(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = raw_payload.get("metadata", {})
    for container in (raw_payload, metadata if isinstance(metadata, dict) else {}):
        if isinstance(container, dict):
            summary = (
                container.get("reference_result_summary")
                or container.get("toolsandbox_reference_result")
                or container.get("result_summary")
                or container.get("toolsandbox_result")
            )
            if isinstance(summary, dict):
                return summary
    return {}


def _summary_exception_type(summary: Dict[str, Any]) -> str:
    exception_type = summary.get("exception_type") or summary.get("error_type")
    if exception_type:
        return str(exception_type)
    traceback = str(summary.get("traceback") or "")
    if "APIConnectionError" in traceback:
        return "APIConnectionError"
    return ""


def _has_alternative_verification_signal(raw_payload: Dict[str, Any]) -> bool:
    summary = _reference_result_summary(raw_payload)
    mapping = summary.get("milestone_mapping")
    if isinstance(mapping, dict) and mapping:
        return True
    if isinstance(mapping, list) and mapping:
        return True
    matched = summary.get("matched_milestones")
    total = summary.get("total_milestones")
    try:
        if int(matched or 0) > 0 or int(total or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _ground_truth_present(raw_payload: Dict[str, Any], sample_id: str) -> bool:
    return (
        bool(raw_payload.get("messages"))
        or bool(raw_payload.get("candidate_tools"))
        or bool(raw_payload.get("tool_allow_list"))
        or bool(raw_payload.get("milestones"))
        or _query_is_natural_language(raw_payload.get("query"), sample_id)
    )


def _validate_toolsandbox_sample(sample: Any) -> List[str]:
    raw_payload = sample.raw_payload
    issues: List[str] = []
    if not raw_payload.get("messages") and not _query_is_natural_language(raw_payload.get("query"), sample.sample_id):
        issues.append("missing_messages_or_natural_language_query")
    if not raw_payload.get("candidate_tools") and not raw_payload.get("tool_allow_list"):
        issues.append("missing_candidate_tools_and_tool_allow_list")
    if not raw_payload.get("milestones") and not _has_alternative_verification_signal(raw_payload):
        issues.append("missing_milestones_and_execution_verified_signal")
    return issues


def _filter_and_validate_samples(samples: List[Any], *, smoke: bool) -> List[Any]:
    valid_samples: List[Any] = []
    invalid_rows: List[str] = []
    for sample in samples:
        issues = _validate_toolsandbox_sample(sample)
        if not issues:
            valid_samples.append(sample)
            continue
        exception_type = _summary_exception_type(_reference_result_summary(sample.raw_payload))
        if exception_type == "APIConnectionError" and not _ground_truth_present(sample.raw_payload, sample.sample_id):
            print(
                f"skipping ToolSandbox sample without recoverable ground truth: {sample.sample_id} ({', '.join(issues)})",
                file=sys.stderr,
            )
            continue
        invalid_rows.append(f"{sample.sample_id}: {', '.join(issues)}")
    if invalid_rows:
        raise ValueError("invalid ToolSandbox samples detected before benchmark execution:\n- " + "\n- ".join(invalid_rows))
    if not valid_samples:
        raise ValueError("No valid ToolSandbox samples remain after source validation")
    if smoke:
        _validate_smoke_profile(valid_samples)
    return valid_samples


def _validate_smoke_profile(samples: List[Any]) -> None:
    categories = {
        category
        for sample in samples
        for category in sample.metadata.get("toolsandbox_categories", [])
    }
    has_state = any(str(sample.raw_payload.get("execution_scenario") or "") == "state_failure" for sample in samples)
    has_interaction = any(
        str(sample.raw_payload.get("execution_scenario") or "") == "approval_required"
        or bool(sample.raw_payload.get("constraints", {}).get("requires_user_approval"))
        or any(category in sample.metadata.get("toolsandbox_categories", []) for category in ("multiple_user_turn", "insufficient_information"))
        for sample in samples
    )
    has_recovery = any(
        str(sample.raw_payload.get("execution_scenario") or "") == "binding_failure"
        or (
            str(sample.raw_payload.get("execution_scenario") or "") == "environment_failure"
            and bool(sample.raw_payload.get("backup_tool_map"))
        )
        for sample in samples
    )
    family_passes: Dict[str, set[int]] = {}
    family_queries: Dict[str, set[str]] = {}
    for sample in samples:
        family_id = str(sample.raw_payload.get("reuse_family_id") or "").strip()
        pass_index = sample.raw_payload.get("reuse_pass_index")
        if not family_id:
            continue
        try:
            resolved_pass_index = int(pass_index)
        except (TypeError, ValueError):
            continue
        family_passes.setdefault(family_id, set()).add(resolved_pass_index)
        query = str(sample.raw_payload.get("query") or "").strip().lower()
        if query:
            family_queries.setdefault(family_id, set()).add(query)
    has_reuse_pair = any(len(pass_indices) >= 2 and 1 in pass_indices and 2 in pass_indices for pass_indices in family_passes.values())
    has_transfer_reuse_pair = any(
        len(family_queries.get(family_id, set())) >= 2 and len(pass_indices) >= 2 and 1 in pass_indices and 2 in pass_indices
        for family_id, pass_indices in family_passes.items()
    )
    has_planner_distractor = any(
        len(sample.raw_payload.get("candidate_tools", [])) >= 3
        and any(
            str(item.get("tool_id") or item.get("name") or "") == "ordering_write_tool"
            for item in sample.raw_payload.get("candidate_tools", [])
            if isinstance(item, dict)
        )
        for sample in samples
    )
    if (
        len(samples) < 8
        or not has_state
        or not has_interaction
        or not has_recovery
        or not has_reuse_pair
        or not has_transfer_reuse_pair
        or not has_planner_distractor
    ):
        raise ValueError(
            "ToolSandbox smoke requires at least 8 validated samples covering explicit state_failure, interaction, recovery, planner-distractor, exact reuse-pair, and transfer-style reuse slices."
        )


def _build_scored_row(*, run_index: int, raw_row: Dict[str, str], score_payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = dict(score_payload.get("metrics", {}))
    diagnostics = dict(score_payload.get("diagnostics", {}))
    categories = diagnostics.get("categories", [])
    if not isinstance(categories, list):
        categories = []
    return {
        "run_index": run_index,
        "task_id": raw_row["task_id"],
        "system": raw_row["system"],
        "scenario": raw_row.get("scenario", "toolsandbox"),
        "task_family": raw_row.get("task_family", ""),
        "failure_type": raw_row.get("failure_type", ""),
        "primary_failtax": raw_row.get("primary_failtax", "recovery"),
        "failtaxes": raw_row.get("failtaxes", "[]"),
        "failure_step": raw_row.get("failure_step", ""),
        "expected_recovery_path": raw_row.get("expected_recovery_path", ""),
        "gold_tool": raw_row.get("gold_tool", ""),
        "chosen_tool": raw_row.get("chosen_tool", ""),
        "state_slots": raw_row.get("state_slots", "[]"),
        "dependency_edges": raw_row.get("dependency_edges", "[]"),
        "success": bool(score_payload.get("success")),
        "execution_verified_success": bool(metrics.get("execution_verified_success", 0.0)),
        "proxy_summary_success": bool(metrics.get("proxy_summary_success", 0.0)),
        "raw_trace_success": _bool_from_value(raw_row.get("success", "False")),
        "raw_success": _bool_from_value(raw_row.get("success", "False")),
        "stop_reason": raw_row.get("stop_reason", "unknown"),
        "trace_path": raw_row.get("trace_path", ""),
        "tool_calls": int(diagnostics.get("tool_calls", raw_row.get("tool_calls", 0) or 0)),
        "user_queries": int(diagnostics.get("user_queries", raw_row.get("user_turns", 0) or 0)),
        "turn_count": int(diagnostics.get("turn_count", 0) or 0),
        "expected_turn_count": int(diagnostics.get("expected_turn_count", 0) or 0),
        "expected_tool_calls": int(diagnostics.get("expected_tool_calls", 0) or 0),
        "matched_milestones": int(diagnostics.get("matched_milestones", 0) or 0),
        "total_milestones": int(diagnostics.get("total_milestones", 0) or 0),
        "milestone_similarity": float(metrics.get("milestone_similarity", 0.0) or 0.0),
        "milestone_coverage": float(metrics.get("milestone_coverage", 0.0) or 0.0),
        "execution_verified_success_rate": float(metrics.get("execution_verified_success", 0.0) or 0.0),
        "proxy_summary_success_rate": float(metrics.get("proxy_summary_success", 0.0) or 0.0),
        "interaction_efficiency": float(metrics.get("interaction_efficiency", 0.0) or 0.0),
        "tool_efficiency": float(metrics.get("tool_efficiency", 0.0) or 0.0),
        "turn_efficiency": float(metrics.get("turn_efficiency", 0.0) or 0.0),
        "hallucination_avoidance": float(metrics.get("hallucination_avoidance", 0.0) or 0.0),
        "state_dependency_score": float(metrics.get("state_dependency_score", 0.0) or 0.0),
        "result_summary_coverage": 1.0 if diagnostics.get("used_result_summary") else 0.0,
        "reference_summary_coverage": 1.0 if diagnostics.get("reference_result_summary_available") else 0.0,
        "primary_category": str(diagnostics.get("primary_category", raw_row.get("scenario", "toolsandbox"))),
        "categories": json.dumps(categories, ensure_ascii=True),
        "result_summary_source": str(diagnostics.get("result_summary_source", "toolclaw_proxy")),
        "raw_repair_actions": int(raw_row.get("repair_actions", 0) or 0),
        "raw_repair_triggered": int(raw_row.get("repair_triggered", 0) or 0),
        "raw_total_steps": int(raw_row.get("total_steps", 0) or 0),
        "raw_token_cost": float(raw_row.get("token_cost", 0.0) or 0.0),
        "raw_wall_clock_ms": int(raw_row.get("wall_clock_ms", 0) or 0),
        "observed_error_type": str(raw_row.get("observed_error_type", raw_row.get("failure_type", "none"))),
        "first_failure_recovered": _bool_from_value(raw_row.get("first_failure_recovered", "False")),
        "repair_extra_tool_calls": int(raw_row.get("repair_extra_tool_calls", 0) or 0),
        "repair_extra_user_turns": int(raw_row.get("repair_extra_user_turns", 0) or 0),
        "repair_user_clarification": _bool_from_value(raw_row.get("repair_user_clarification", "False")),
        "clarification_precision": float(raw_row.get("clarification_precision", 0.0) or 0.0),
        "clarification_recall": float(raw_row.get("clarification_recall", 0.0) or 0.0),
        "unnecessary_question_rate": float(raw_row.get("unnecessary_question_rate", 0.0) or 0.0),
        "patch_success_rate": float(raw_row.get("patch_success_rate", 0.0) or 0.0),
        "post_answer_retry_count": int(raw_row.get("post_answer_retry_count", 0) or 0),
        "reuse_pass_index": int(raw_row.get("reuse_pass_index", 0) or 0),
        "reused_artifact": _bool_from_value(raw_row.get("reused_artifact", "False")),
        "second_run_improvement": float(raw_row.get("second_run_improvement", 0.0) or 0.0),
        "budget_violation": _bool_from_value(raw_row.get("budget_violation", "False")),
        "budget_violation_reason": str(raw_row.get("budget_violation_reason", "")),
        "recovery_budget_used": float(raw_row.get("recovery_budget_used", 0.0) or 0.0),
    }


def _category_breakdown(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        categories = json.loads(record["row"].get("categories", "[]"))
        if not categories:
            categories = [record["row"].get("scenario", "toolsandbox")]
        for category in categories:
            grouped.setdefault(str(category), []).append(record)

    summary: Dict[str, Dict[str, float]] = {}
    for category, category_records in grouped.items():
        summary[category] = {
            "num_rows": float(len(category_records)),
            "success_rate": mean_or_zero([1.0 if _bool_from_value(record["row"].get("success")) else 0.0 for record in category_records]),
            "execution_verified_success": mean_or_zero([float(record["row"].get("execution_verified_success_rate", 0.0)) for record in category_records]),
            "proxy_summary_success": mean_or_zero([float(record["row"].get("proxy_summary_success_rate", 0.0)) for record in category_records]),
            "milestone_similarity": mean_or_zero([float(record["row"].get("milestone_similarity", 0.0)) for record in category_records]),
            "milestone_coverage": mean_or_zero([float(record["row"].get("milestone_coverage", 0.0)) for record in category_records]),
            "interaction_efficiency": mean_or_zero([float(record["row"].get("interaction_efficiency", 0.0)) for record in category_records]),
            "tool_efficiency": mean_or_zero([float(record["row"].get("tool_efficiency", 0.0)) for record in category_records]),
            "turn_efficiency": mean_or_zero([float(record["row"].get("turn_efficiency", 0.0)) for record in category_records]),
            "hallucination_avoidance": mean_or_zero([float(record["row"].get("hallucination_avoidance", 0.0)) for record in category_records]),
            "state_dependency_score": mean_or_zero([float(record["row"].get("state_dependency_score", 0.0)) for record in category_records]),
            "result_summary_coverage": mean_or_zero([float(record["row"].get("result_summary_coverage", 0.0)) for record in category_records]),
            "reference_summary_coverage": mean_or_zero([float(record["row"].get("reference_summary_coverage", 0.0)) for record in category_records]),
            "dominant_result_summary_source": _dominant_result_summary_source(category_records),
        }
    return summary


def _dominant_result_summary_source(records: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = {}
    for record in records:
        source = str(record["row"].get("result_summary_source", "unknown"))
        counts[source] = counts.get(source, 0) + 1
    if not counts:
        return "unknown"
    return max(sorted(counts), key=lambda key: counts[key])


def _result_summary_source_breakdown(records: List[Dict[str, Any]]) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    for record in records:
        source = str(record["row"].get("result_summary_source", "unknown"))
        counts[source] = counts.get(source, 0.0) + 1.0
    return counts


TOOLSANDBOX_GROUP_METRICS = [
    AggregateMetric("execution_verified_success"),
    AggregateMetric("proxy_summary_success"),
    AggregateMetric("milestone_similarity"),
    AggregateMetric("milestone_coverage"),
    AggregateMetric("interaction_efficiency"),
    AggregateMetric("tool_efficiency"),
    AggregateMetric("turn_efficiency"),
    AggregateMetric("hallucination_avoidance"),
    AggregateMetric("state_dependency_score"),
    AggregateMetric("used_result_summary", source="diagnostics", label="result_summary_coverage"),
    AggregateMetric("reference_result_summary_available", source="diagnostics", label="reference_summary_coverage"),
]

FOCUSED_SLICE_CATEGORIES = (
    "insufficient_information",
    "multiple_user_turn",
    "single_tool",
)


TOOLSANDBOX_CONFIG = BenchmarkScriptConfig(
    benchmark_name="toolsandbox",
    normalized_filename="toolsandbox.normalized.json",
    system_summary_title="ToolSandbox Per-System Summary",
    aggregate_metrics=[
        AggregateMetric("execution_verified_success"),
        AggregateMetric("proxy_summary_success"),
        AggregateMetric("milestone_similarity"),
        AggregateMetric("milestone_coverage"),
        AggregateMetric("interaction_efficiency"),
        AggregateMetric("tool_efficiency"),
        AggregateMetric("turn_efficiency"),
        AggregateMetric("hallucination_avoidance"),
        AggregateMetric("state_dependency_score"),
        AggregateMetric("used_result_summary", source="diagnostics", label="result_summary_coverage"),
        AggregateMetric("reference_result_summary_available", source="diagnostics", label="reference_summary_coverage"),
    ],
    signature_builder=lambda score, row: json.dumps(
        {
            "success": bool(score.get("success")),
            "stop_reason": row.get("stop_reason", "unknown"),
            "tool_calls": row.get("tool_calls", "0"),
            "milestone_similarity": round(float(score.get("metrics", {}).get("milestone_similarity", 0.0)), 4),
            "hallucination_avoidance": round(float(score.get("metrics", {}).get("hallucination_avoidance", 0.0)), 4),
            "primary_category": score.get("diagnostics", {}).get("primary_category", row.get("scenario", "unknown")),
        },
        sort_keys=True,
    ),
    sample_extra_builder=lambda sample: {
        "categories": list(sample.metadata.get("toolsandbox_categories", [])),
    },
    system_extra_builder=lambda records: {
        "per_category": _category_breakdown(records),
        "result_summary_source_breakdown": _result_summary_source_breakdown(records),
        "dominant_result_summary_source": _dominant_result_summary_source(records),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and run ToolSandbox-style benchmark slices through ToolClaw")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Path to ToolSandbox-style JSON or JSONL source (defaults to formal ToolSandbox data when available)",
    )
    parser.add_argument(
        "--official-run-dir",
        default=None,
        help="Official ToolSandbox run directory, or 'latest' to auto-discover under data/external/ToolSandbox/data",
    )
    parser.add_argument(
        "--official-data-root",
        default=str(DEFAULT_OFFICIAL_DATA_ROOT),
        help="Root directory containing official ToolSandbox run directories for --official-run-dir auto-discovery",
    )
    parser.add_argument(
        "--result-source",
        default=None,
        help="Optional JSON/JSONL file or directory containing official ToolSandbox result summaries to merge before scoring",
    )
    parser.add_argument("--outdir", default="outputs/toolsandbox_bench", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    parser.add_argument(
        "--systems",
        default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
        help="Comma-separated systems to run: a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke slice (min(limit, 10))")
    parser.add_argument("--num-runs", type=int, default=1, help="Repeat runs to estimate pass@k and consistency")
    parser.add_argument(
        "--asset-registry-root",
        default=None,
        help="Optional root for file-backed reusable assets. Each benchmark repetition uses a separate subdirectory under this root.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Recorded experiment seed for archive manifest")
    parser.add_argument("--model-version", default="phase1_executor", help="Recorded model/runtime version for archive manifest")
    parser.add_argument("--budget-note", default="default phase1 budget", help="Recorded budget note for archive manifest")
    parser.add_argument("--config-file", default=str(ROOT_DIR / "configs" / "benchmark_toolsandbox.yaml"), help="Primary benchmark config file to archive")
    parser.add_argument("--phase-config", default=str(ROOT_DIR / "configs" / "phase1.yaml"), help="Phase config file to archive")
    parser.add_argument(
        "--require-result-summary",
        action="store_true",
        help="Fail if the prepared ToolSandbox source does not include any merged result_summary / toolsandbox_result signal",
    )
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep the normalized taskset JSON file")
    return parser.parse_args()


def _write_toolsandbox_artifacts(summary: Dict[str, Any], outdir: Path) -> None:
    write_group_markdown(
        summary,
        outdir / "per_category_summary.md",
        title="ToolSandbox Category Summary",
        group_key="per_category",
        metrics=TOOLSANDBOX_GROUP_METRICS,
    )
    per_category_summary = {
        system: dict(system_summary.get("per_category", {}))
        for system, system_summary in summary.items()
    }
    (outdir / "per_category_summary.json").write_text(json.dumps(per_category_summary, indent=2), encoding="utf-8")
    per_failtax_summary = {
        system: dict(system_summary.get("per_failtax", {}))
        for system, system_summary in summary.items()
    }
    (outdir / "per_failtax_summary.json").write_text(json.dumps(per_failtax_summary, indent=2), encoding="utf-8")
    focused_summary = _focused_slice_summary(summary)
    (outdir / "focused_slice_summary.json").write_text(json.dumps(focused_summary, indent=2), encoding="utf-8")
    _write_focused_slice_markdown(focused_summary, outdir / "focused_slice_summary.md")


def _focused_slice_summary(per_system_summary: Dict[str, Any]) -> Dict[str, Any]:
    per_category: Dict[str, Dict[str, Any]] = {}
    for system, system_summary in per_system_summary.items():
        category_stats = dict(system_summary.get("per_category", {}))
        per_category[system] = {
            category: dict(category_stats.get(category, {}))
            for category in FOCUSED_SLICE_CATEGORIES
            if category in category_stats
        }
    deltas: Dict[str, Dict[str, Dict[str, float]]] = {}
    delta_pairs = [
        ("a3_interaction_minus_a0_baseline", "a3_interaction", "a0_baseline"),
        ("a3_interaction_minus_a1_recovery", "a3_interaction", "a1_recovery"),
        ("a3_interaction_minus_a2_planner", "a3_interaction", "a2_planner"),
        ("a4_reuse_minus_a3_interaction", "a4_reuse", "a3_interaction"),
    ]
    metric_keys = (
        "success_rate",
        "milestone_similarity",
        "interaction_efficiency",
        "tool_efficiency",
        "turn_efficiency",
    )
    for delta_name, right_system, left_system in delta_pairs:
        right_summary = per_category.get(right_system, {})
        left_summary = per_category.get(left_system, {})
        category_delta: Dict[str, Dict[str, float]] = {}
        for category in FOCUSED_SLICE_CATEGORIES:
            if category not in right_summary or category not in left_summary:
                continue
            category_delta[category] = {
                metric_key: float(right_summary[category].get(metric_key, 0.0)) - float(left_summary[category].get(metric_key, 0.0))
                for metric_key in metric_keys
            }
        deltas[delta_name] = category_delta
    return {
        "focus_categories": list(FOCUSED_SLICE_CATEGORIES),
        "per_system": per_category,
        "deltas": deltas,
    }


def _write_focused_slice_markdown(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolSandbox Focused Slice Summary",
        "",
        "Focused categories:",
        f"- {', '.join(summary.get('focus_categories', []))}",
        "",
        "| system | category | success_rate | milestone_similarity | interaction_efficiency | tool_efficiency | turn_efficiency |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for system, category_map in sorted(summary.get("per_system", {}).items()):
        for category in summary.get("focus_categories", []):
            stats = category_map.get(category)
            if not isinstance(stats, dict):
                continue
            lines.append(
                f"| {system} | {category} | {float(stats.get('success_rate', 0.0)):.3f} | {float(stats.get('milestone_similarity', 0.0)):.3f} | {float(stats.get('interaction_efficiency', 0.0)):.3f} | {float(stats.get('tool_efficiency', 0.0)):.3f} | {float(stats.get('turn_efficiency', 0.0)):.3f} |"
            )

    delta_map = summary.get("deltas", {})
    if isinstance(delta_map, dict) and delta_map:
        lines.extend(
            [
                "",
                "## Focused Deltas",
                "",
                "| delta | category | success_rate | milestone_similarity | interaction_efficiency | tool_efficiency | turn_efficiency |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for delta_name, category_map in sorted(delta_map.items()):
            if not isinstance(category_map, dict):
                continue
            for category in summary.get("focus_categories", []):
                stats = category_map.get(category)
                if not isinstance(stats, dict):
                    continue
                lines.append(
                    f"| {delta_name} | {category} | {float(stats.get('success_rate', 0.0)):+.3f} | {float(stats.get('milestone_similarity', 0.0)):+.3f} | {float(stats.get('interaction_efficiency', 0.0)):+.3f} | {float(stats.get('tool_efficiency', 0.0)):+.3f} | {float(stats.get('turn_efficiency', 0.0)):+.3f} |"
                )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_toolsandbox_report(scoreboard: Dict[str, Any], outdir: Path) -> None:
    lines = [
        "# ToolSandbox Benchmark Report",
        "",
        f"- source: `{scoreboard['source']}`",
        f"- normalized_taskset: `{scoreboard['normalized_taskset']}`",
        f"- samples: `{scoreboard['num_samples']}`",
        f"- runs: `{scoreboard['num_runs']}`",
        f"- systems: `{', '.join(scoreboard['systems'])}`",
        f"- raw_execution_report: `{outdir / 'latest_run_raw_report.md'}`",
        f"- raw_comparison: `{outdir / 'comparison.raw.csv'}`",
        f"- scored_comparison: `{outdir / 'comparison.scored.csv'}`",
        f"- focused_slice_summary: `{outdir / 'focused_slice_summary.md'}`",
        f"- failtax_summary: `{outdir / 'per_failtax_summary.json'}`",
        "",
        "## Aggregate",
        "",
        "| system | mean_success_rate | execution_verified_success | proxy_summary_success | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    per_system = scoreboard["per_system_summary"]
    for system, stats in per_system.items():
        lines.append(
            f"| {system} | {float(stats.get('mean_success_rate', 0.0)):.3f} | {float(stats.get('execution_verified_success', 0.0)):.3f} | {float(stats.get('proxy_summary_success', 0.0)):.3f} | {float(stats.get('consistency', 0.0)):.3f} | {float(stats.get('milestone_similarity', 0.0)):.3f} | {float(stats.get('milestone_coverage', 0.0)):.3f} | {float(stats.get('state_dependency_score', 0.0)):.3f} | {float(stats.get('hallucination_avoidance', 0.0)):.3f} | {float(stats.get('tool_efficiency', 0.0)):.3f} | {float(stats.get('turn_efficiency', 0.0)):.3f} | {float(stats.get('budget_violation_rate', 0.0)):.3f} | {float(stats.get('used_result_summary', 0.0)):.3f} | {float(stats.get('reference_result_summary_available', 0.0)):.3f} | {stats.get('dominant_result_summary_source', 'unknown')} |"
        )

    lines.extend(
        [
            "",
            "## FailTax Breakdown",
            "",
            "| system | primary_failtax | rows | success_rate | pass@k | consistency |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for system, stats in per_system.items():
        for failtax, failtax_stats in sorted(stats.get("per_failtax", {}).items()):
            lines.append(
                f"| {system} | {failtax} | {int(failtax_stats.get('num_rows', 0))} | {float(failtax_stats.get('success_rate', 0.0)):.3f} | {float(failtax_stats.get('pass_at_k', 0.0)):.3f} | {float(failtax_stats.get('consistency', 0.0)):.3f} |"
            )

    lines.extend(
        [
            "",
            "## Category Breakdown",
            "",
            "| system | category | rows | success_rate | execution_verified_success | proxy_summary_success | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for system, stats in per_system.items():
        for category, category_stats in sorted(stats.get("per_category", {}).items()):
            lines.append(
                f"| {system} | {category} | {int(category_stats.get('num_rows', 0))} | {float(category_stats.get('success_rate', 0.0)):.3f} | {float(category_stats.get('execution_verified_success', 0.0)):.3f} | {float(category_stats.get('proxy_summary_success', 0.0)):.3f} | {float(category_stats.get('milestone_similarity', 0.0)):.3f} | {float(category_stats.get('milestone_coverage', 0.0)):.3f} | {float(category_stats.get('state_dependency_score', 0.0)):.3f} | {float(category_stats.get('hallucination_avoidance', 0.0)):.3f} | {float(category_stats.get('tool_efficiency', 0.0)):.3f} | {float(category_stats.get('turn_efficiency', 0.0)):.3f} | {float(category_stats.get('result_summary_coverage', 0.0)):.3f} | {float(category_stats.get('reference_summary_coverage', 0.0)):.3f} | {category_stats.get('dominant_result_summary_source', 'unknown')} |"
            )

    lines.extend(
        [
            "",
            "## Result Summary Sources",
            "",
            "| system | result_summary_source | rows |",
            "|---|---|---:|",
        ]
    )
    for system, stats in per_system.items():
        for source, count in sorted(dict(stats.get("result_summary_source_breakdown", {})).items()):
            lines.append(f"| {system} | {source} | {int(count)} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `mean_success_rate` is computed from `execution_verified_success`, not from proxy summaries alone.",
            "- `proxy_summary_success` tracks runs that looked successful under the attached ToolClaw proxy summary path.",
            "- `result_summary_source` is reported explicitly so proxy-derived runs are visible in the main report.",
            "- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.",
            "- FailTax is the default slicing axis for phase-2 style failure studies; category tables remain useful but secondary.",
            "- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.",
            "- `latest_run_raw_report.md` preserves the raw `run_eval.py` report so it is not confused with this scored benchmark report.",
            "- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.",
            "- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.",
            "- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.",
            "- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.",
            "- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.",
            "- `budget_violation_rate` and `recovery_budget_used` are the budget-side controls for phase-2 evaluation.",
        ]
    )
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _attach_current_result_summary(
    adapter: ToolSandboxAdapter,
    sample: Any,
    trace_path: Path,
    trace_payload: Dict[str, Any],
) -> Dict[str, Any]:
    metadata = trace_payload.setdefault("metadata", {})
    metadata["toolsandbox_result"] = adapter.build_proxy_result_summary(sample, trace_payload)
    metadata["toolsandbox_result_source"] = "toolclaw_proxy"
    reference_summary = adapter._extract_reference_result_summary(sample.raw_payload)
    if reference_summary:
        metadata["toolsandbox_reference_result"] = reference_summary
    trace_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
    return trace_payload


def _prepare_source_if_needed(source: str, result_source: str | None, prepared_dir: Path) -> Path:
    source_path = Path(source)
    if result_source is None and source_path.is_file():
        return source_path

    aligned_path = prepared_dir / "toolsandbox.aligned.jsonl"
    cmd: List[str] = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "prepare_toolsandbox_source.py"),
        "--source",
        str(source_path),
        "--out",
        str(aligned_path),
    ]
    if result_source is not None:
        cmd.extend(["--result-source", result_source])
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return aligned_path


def _prepare_source_from_official_run(official_run_dir: str, official_data_root: str, prepared_dir: Path) -> Path:
    aligned_path = prepared_dir / "toolsandbox.official.aligned.jsonl"
    cmd: List[str] = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "prepare_toolsandbox_official_run.py"),
        "--run-dir",
        official_run_dir,
        "--data-root",
        official_data_root,
        "--out",
        str(aligned_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return aligned_path


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    if args.official_run_dir is not None:
        source_for_adapter = _prepare_source_from_official_run(args.official_run_dir, args.official_data_root, prepared_dir)
    else:
        source_for_adapter = _prepare_source_if_needed(args.source, args.result_source, prepared_dir)

    adapter = ToolSandboxAdapter()
    samples = adapter.load_samples(str(source_for_adapter))
    samples = _filter_and_validate_samples(samples, smoke=False)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
        _validate_smoke_profile(samples)
    if not samples:
        raise ValueError("No ToolSandbox samples loaded from source after validation")
    if args.require_result_summary and not any(sample.raw_payload.get("result_summary") for sample in samples):
        raise ValueError("require-result-summary was set, but no ToolSandbox result_summary / toolsandbox_result was found")
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / TOOLSANDBOX_CONFIG.normalized_filename
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    raw_run_rows: List[Dict[str, Any]] = []
    scored_run_rows: List[Dict[str, Any]] = []
    run_records: List[Dict[str, Any]] = []
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        asset_registry_root = None
        if args.asset_registry_root:
            asset_registry_root = Path(args.asset_registry_root) / f"run_{run_index:02d}"
        invoke_run_eval(normalized_path, run_outdir, args.mode, systems, asset_registry_root=asset_registry_root)
        raw_report_path = run_outdir / "report.md"
        if raw_report_path.exists():
            raw_report_path.replace(run_outdir / "raw_report.md")
        raw_rows = load_run_rows(run_outdir / "comparison.csv")
        write_csv_rows(raw_rows, run_outdir / "comparison.raw.csv")
        scored_rows_for_run: List[Dict[str, Any]] = []
        for raw_row in raw_rows:
            trace_path = Path(raw_row["trace_path"])
            trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
            sample = next(sample for sample in samples if sample.sample_id == raw_row["task_id"])
            trace_payload = _attach_current_result_summary(adapter, sample, trace_path, trace_payload)
            score_payload = score_to_payload(adapter.score_trace(sample, trace_payload))
            scored_row = _build_scored_row(run_index=run_index, raw_row=raw_row, score_payload=score_payload)
            raw_run_rows.append({"run_index": run_index, **raw_row})
            scored_rows_for_run.append(scored_row)
            scored_run_rows.append(scored_row)
            run_records.append(
                {
                    "run_index": run_index,
                    "system": raw_row["system"],
                    "task_id": raw_row["task_id"],
                    "row": scored_row,
                    "score": score_payload,
                }
            )
        write_csv_rows(scored_rows_for_run, run_outdir / "comparison.scored.csv")

    scoreboard = aggregate_records(
        config=TOOLSANDBOX_CONFIG,
        adapter=adapter,
        samples=samples,
        systems=systems,
        run_records=run_records,
        source=str(source_for_adapter),
        mode=args.mode,
        normalized_path=normalized_path,
        num_runs=args.num_runs,
        smoke=args.smoke,
    )
    finalize_outputs(
        outdir=outdir,
        prepared_dir=prepared_dir,
        benchmark_name=TOOLSANDBOX_CONFIG.benchmark_name,
        source=args.source,
        normalized_path=normalized_path,
        mode=args.mode,
        systems=systems,
        num_runs=args.num_runs,
        scoreboard=scoreboard,
        config=TOOLSANDBOX_CONFIG,
        keep_normalized_taskset=args.keep_normalized_taskset,
        comparison_filename=None,
        latest_comparison_filename=None,
        extra_output_writers=_write_toolsandbox_artifacts,
        experiment_metadata={
            "seed": args.seed,
            "model_version": args.model_version,
            "budget_note": args.budget_note,
            "runner_script": str(Path(__file__).resolve()),
            "config_file": str(Path(args.config_file).resolve()),
            "phase_config": str(Path(args.phase_config).resolve()),
            "official_run_dir": args.official_run_dir,
            "official_data_root": str(Path(args.official_data_root).resolve()),
        },
        archive_files=[
            Path(__file__).resolve(),
            Path(args.config_file),
            Path(args.phase_config),
        ],
    )
    write_csv_rows(raw_run_rows, outdir / "comparison.raw.csv")
    write_csv_rows(scored_run_rows, outdir / "comparison.scored.csv")
    latest_run_index = args.num_runs
    write_csv_rows([row for row in raw_run_rows if int(row["run_index"]) == latest_run_index], outdir / "latest_run_comparison.raw.csv")
    write_csv_rows([row for row in scored_run_rows if int(row["run_index"]) == latest_run_index], outdir / "latest_run_comparison.scored.csv")
    latest_run_raw_report = outdir / "runs" / f"run_{latest_run_index:02d}" / "raw_report.md"
    if latest_run_raw_report.exists():
        (outdir / "latest_run_raw_report.md").write_text(latest_run_raw_report.read_text(encoding="utf-8"), encoding="utf-8")
    update_experiment_manifest(
        outdir,
        updates={
            "comparison_path": str((outdir / "comparison.scored.csv").resolve()),
            "comparison_raw_path": str((outdir / "comparison.raw.csv").resolve()),
            "comparison_scored_path": str((outdir / "comparison.scored.csv").resolve()),
            "latest_comparison_raw_path": str((outdir / "latest_run_comparison.raw.csv").resolve()),
            "latest_comparison_scored_path": str((outdir / "latest_run_comparison.scored.csv").resolve()),
            "latest_raw_report_path": str((outdir / "latest_run_raw_report.md").resolve()) if (outdir / "latest_run_raw_report.md").exists() else None,
        },
    )
    for obsolete_name in ("comparison.csv", "latest_run_comparison.csv"):
        obsolete_path = outdir / obsolete_name
        if obsolete_path.exists():
            obsolete_path.unlink()
    _write_toolsandbox_report(scoreboard, outdir)
    update_experiment_manifest(
        outdir,
        updates={
            "report_path": str((outdir / "report.md").resolve()),
        },
    )

    print(f"prepared toolsandbox taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"raw execution: {outdir / 'runs' / f'run_{latest_run_index:02d}' / 'comparison.csv'}")
    print(f"raw report: {outdir / 'latest_run_raw_report.md'}")
    print(f"scored evaluation: {outdir / 'comparison.scored.csv'}")
    print(f"final benchmark verdict: {outdir / 'scoreboard.json'}")
    print(f"per-system summary: {outdir / 'per_system_summary.json'}")


if __name__ == "__main__":
    main()
