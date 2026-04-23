"""Prepare ToolSandbox-style samples, execute repeated runs, and aggregate benchmark outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
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
        ROOT_DIR / "data" / "toolsandbox.formal.json",
        ROOT_DIR / "data" / "toolsandbox.formal.official.json",
        ROOT_DIR / "data" / "toolsandbox.sample.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


DEFAULT_SOURCE = _default_source()
DEFAULT_OFFICIAL_DATA_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox" / "data"
CAUSAL_SLICE_POLICY_VERSION = "toolsandbox_causality_v1"
CAUSAL_CLAIM_IDS = ["interaction_headline", "interaction_semantic_usefulness_mechanism"]
SMOKE_SAMPLE_IDS = [
    "toolsandbox_env_backup_001",
    "toolsandbox_binding_repair_001",
    "toolsandbox_approval_interaction_001",
    "toolsandbox_state_failure_resume_001",
    "toolsandbox_state_failure_target_001",
    "toolsandbox_reuse_family_001__pass1",
    "toolsandbox_reuse_family_001__pass2",
    "toolsandbox_reuse_transfer_001__pass1",
    "toolsandbox_reuse_transfer_001__pass2",
    "toolsandbox_planner_sensitive_001",
]


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
    has_planner_sensitive = any(_is_planner_sensitive_task(sample.sample_id) for sample in samples)
    missing_requirements: List[str] = []
    if len(samples) < 8:
        missing_requirements.append("at least 8 validated samples")
    if not has_state:
        missing_requirements.append("explicit state_failure")
    if not has_interaction:
        missing_requirements.append("interaction")
    if not has_recovery:
        missing_requirements.append("recovery")
    if not has_planner_sensitive:
        missing_requirements.append("planner-sensitive")
    if not has_reuse_pair:
        missing_requirements.append("exact reuse-pair")
    if not has_transfer_reuse_pair:
        missing_requirements.append("transfer-style reuse")
    if missing_requirements:
        raise ValueError(
            "ToolSandbox smoke profile is missing required coverage: "
            + ", ".join(missing_requirements)
        )


def _select_smoke_samples(samples: List[Any], max_count: int = 10) -> List[Any]:
    by_id = {str(sample.sample_id): sample for sample in samples}
    if all(sample_id in by_id for sample_id in SMOKE_SAMPLE_IDS):
        return [by_id[sample_id] for sample_id in SMOKE_SAMPLE_IDS[:max_count]]
    return samples[:max_count]


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
        "strict_scored_success": bool(metrics.get("strict_scored_success", metrics.get("execution_verified_success", 0.0))),
        "repair_scored_success": bool(metrics.get("repair_scored_success", 0.0)),
        "execution_verified_success": bool(metrics.get("execution_verified_success", 0.0)),
        "proxy_summary_success": bool(metrics.get("proxy_summary_success", 0.0)),
        "raw_trace_success": _bool_from_value(raw_row.get("success", "False")),
        "raw_execution_success": _bool_from_value(str(bool(diagnostics.get("raw_execution_success", raw_row.get("success", "False"))))),
        "raw_success": _bool_from_value(raw_row.get("success", "False")),
        "stop_reason": raw_row.get("stop_reason", "unknown"),
        "trace_path": raw_row.get("trace_path", ""),
        "tool_calls": int(diagnostics.get("tool_calls", raw_row.get("tool_calls", 0) or 0)),
        "user_queries": int(diagnostics.get("user_queries", raw_row.get("user_turns", 0) or 0)),
        "mean_user_queries": float(metrics.get("mean_user_queries", diagnostics.get("user_queries", raw_row.get("user_turns", 0)) or 0.0)),
        "probe_user_queries": int(diagnostics.get("probe_user_queries", 0) or 0),
        "repair_user_queries": int(diagnostics.get("repair_user_queries", 0) or 0),
        "probe_user_replies": int(diagnostics.get("probe_user_replies", 0) or 0),
        "repair_user_replies": int(diagnostics.get("repair_user_replies", 0) or 0),
        "interaction_contract_satisfied": bool(metrics.get("interaction_contract_satisfied", 0.0)),
        "repair_interaction_satisfied": bool(metrics.get("repair_interaction_satisfied", 0.0)),
        "reply_usable_rate": float(metrics.get("reply_usable_rate", 0.0) or 0.0),
        "target_aligned_patch_rate": float(metrics.get("target_aligned_patch_rate", 0.0) or 0.0),
        "effective_patch_rate": float(metrics.get("effective_patch_rate", 0.0) or 0.0),
        "post_query_progress_rate": float(metrics.get("post_query_progress_rate", 0.0) or 0.0),
        "useful_interaction_round_rate": float(metrics.get("useful_interaction_round_rate", 0.0) or 0.0),
        "turn_count": int(diagnostics.get("turn_count", 0) or 0),
        "expected_turn_count": int(diagnostics.get("expected_turn_count", 0) or 0),
        "expected_tool_calls": int(diagnostics.get("expected_tool_calls", 0) or 0),
        "matched_milestones": int(diagnostics.get("matched_milestones", 0) or 0),
        "total_milestones": int(diagnostics.get("total_milestones", 0) or 0),
        "milestone_similarity": float(metrics.get("milestone_similarity", 0.0) or 0.0),
        "milestone_coverage": float(metrics.get("milestone_coverage", 0.0) or 0.0),
        "milestone_signal_coverage": 1.0 if diagnostics.get("milestone_signal_available") else 0.0,
        "execution_verified_success_rate": float(metrics.get("execution_verified_success", 0.0) or 0.0),
        "strict_scored_success_rate": float(metrics.get("strict_scored_success", metrics.get("execution_verified_success", 0.0)) or 0.0),
        "repair_scored_success_rate": float(metrics.get("repair_scored_success", 0.0) or 0.0),
        "proxy_summary_success_rate": float(metrics.get("proxy_summary_success", 0.0) or 0.0),
        "raw_trace_success_rate": 1.0 if diagnostics.get("raw_trace_success") else 0.0,
        "raw_execution_success_rate": 1.0 if diagnostics.get("raw_execution_success", diagnostics.get("raw_trace_success")) else 0.0,
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
        "used_result_summary": _bool_from_value(str(bool(diagnostics.get("used_result_summary", False)))),
        "milestone_signal_available": _bool_from_value(str(bool(diagnostics.get("milestone_signal_available", False)))),
        "reference_result_summary_available": _bool_from_value(str(bool(diagnostics.get("reference_result_summary_available", False)))),
        "expected_target_path": str(diagnostics.get("expected_target_path") or ""),
        "observed_target_path": str(diagnostics.get("observed_target_path") or ""),
        "write_target_verified": _bool_from_value(str(bool(metrics.get("write_target_verified", 0.0)))),
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
        "reuse_mode": str(raw_row.get("reuse_mode", "none") or "none"),
        "reuse_tier": str(raw_row.get("reuse_tier", "none") or "none"),
        "reuse_selected_asset_id": str(raw_row.get("reuse_selected_asset_id", "") or ""),
        "reuse_selected_match_signature": str(raw_row.get("reuse_selected_match_signature", "") or ""),
        "reuse_source_task_id": str(raw_row.get("reuse_source_task_id", "") or ""),
        "reuse_target_family": str(raw_row.get("reuse_target_family", "") or ""),
        "reuse_source_family": str(raw_row.get("reuse_source_family", "") or ""),
        "reuse_target_semantic_family": str(raw_row.get("reuse_target_semantic_family", "") or ""),
        "reuse_source_semantic_family": str(raw_row.get("reuse_source_semantic_family", "") or ""),
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
        task_id = str(record["row"].get("task_id", ""))
        if _is_planner_sensitive_task(task_id):
            categories = [*categories, "planner_sensitive"]
        for category in categories:
            grouped.setdefault(str(category), []).append(record)

    summary: Dict[str, Dict[str, float]] = {}
    for category, category_records in grouped.items():
        summary[category] = {
            "num_rows": float(len(category_records)),
            "success_rate": mean_or_zero([float(record["row"].get("execution_verified_success_rate", 0.0)) for record in category_records]),
            "execution_verified_success": mean_or_zero([float(record["row"].get("execution_verified_success_rate", 0.0)) for record in category_records]),
            "strict_scored_success": mean_or_zero([float(record["row"].get("strict_scored_success_rate", 0.0)) for record in category_records]),
            "repair_scored_success": mean_or_zero([float(record["row"].get("repair_scored_success_rate", 0.0)) for record in category_records]),
            "interaction_contract_satisfied": mean_or_zero([_float_cell(record["row"].get("interaction_contract_satisfied", 0.0)) for record in category_records]),
            "mean_user_queries": mean_or_zero([float(record["row"].get("mean_user_queries", 0.0)) for record in category_records]),
            "reply_usable_rate": mean_or_zero([float(record["row"].get("reply_usable_rate", 0.0)) for record in category_records]),
            "target_aligned_patch_rate": mean_or_zero([float(record["row"].get("target_aligned_patch_rate", 0.0)) for record in category_records]),
            "effective_patch_rate": mean_or_zero([float(record["row"].get("effective_patch_rate", 0.0)) for record in category_records]),
            "post_query_progress_rate": mean_or_zero([float(record["row"].get("post_query_progress_rate", 0.0)) for record in category_records]),
            "useful_interaction_round_rate": mean_or_zero([float(record["row"].get("useful_interaction_round_rate", 0.0)) for record in category_records]),
            "repair_interaction_satisfied": mean_or_zero([_float_cell(record["row"].get("repair_interaction_satisfied", 0.0)) for record in category_records]),
            "proxy_summary_success": mean_or_zero([float(record["row"].get("proxy_summary_success_rate", 0.0)) for record in category_records]),
            "raw_trace_success_rate": mean_or_zero([float(record["row"].get("raw_trace_success_rate", 0.0)) for record in category_records]),
            "raw_execution_success_rate": mean_or_zero([float(record["row"].get("raw_execution_success_rate", 0.0)) for record in category_records]),
            "milestone_similarity": mean_or_zero([float(record["row"].get("milestone_similarity", 0.0)) for record in category_records]),
            "milestone_coverage": mean_or_zero([float(record["row"].get("milestone_coverage", 0.0)) for record in category_records]),
            "milestone_signal_coverage": mean_or_zero([float(record["row"].get("milestone_signal_coverage", 0.0)) for record in category_records]),
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


def _toolsandbox_benchmark_caution_flags(scoreboard: Dict[str, Any]) -> List[str]:
    per_system = dict(scoreboard.get("per_system_summary", {}))
    if not per_system:
        return ["missing_per_system_summary"]

    flags: List[str] = []
    if int(scoreboard.get("num_samples", 0) or 0) <= 1:
        flags.append("single_validated_sample")

    if all(float(stats.get("reference_summary_coverage", 0.0) or 0.0) <= 0.0 for stats in per_system.values()):
        flags.append("no_reference_result_summaries")

    if all(str(stats.get("dominant_result_summary_source", "unknown")) == "toolclaw_proxy" for stats in per_system.values()):
        flags.append("proxy_only_result_summaries")

    if all(float(stats.get("milestone_signal_coverage", 0.0) or 0.0) <= 0.0 for stats in per_system.values()):
        flags.append("no_milestone_verification_signal")

    if any(float(stats.get("raw_trace_success_rate", 0.0) or 0.0) > float(stats.get("mean_success_rate", 0.0) or 0.0) for stats in per_system.values()):
        flags.append("raw_vs_benchmark_success_gap")

    return flags


TOOLSANDBOX_GROUP_METRICS = [
    AggregateMetric("execution_verified_success"),
    AggregateMetric("strict_scored_success"),
    AggregateMetric("repair_scored_success"),
    AggregateMetric("interaction_contract_satisfied"),
    AggregateMetric("mean_user_queries"),
    AggregateMetric("reply_usable_rate"),
    AggregateMetric("target_aligned_patch_rate"),
    AggregateMetric("effective_patch_rate"),
    AggregateMetric("post_query_progress_rate"),
    AggregateMetric("useful_interaction_round_rate"),
    AggregateMetric("repair_interaction_satisfied"),
    AggregateMetric("proxy_summary_success"),
    AggregateMetric("raw_trace_success", source="diagnostics", label="raw_trace_success_rate"),
    AggregateMetric("raw_execution_success", source="diagnostics", label="raw_execution_success_rate"),
    AggregateMetric("milestone_similarity"),
    AggregateMetric("milestone_coverage"),
    AggregateMetric("milestone_signal_available", source="diagnostics", label="milestone_signal_coverage"),
    AggregateMetric("interaction_efficiency"),
    AggregateMetric("tool_efficiency"),
    AggregateMetric("turn_efficiency"),
    AggregateMetric("hallucination_avoidance"),
    AggregateMetric("state_dependency_score"),
    AggregateMetric("used_result_summary", source="diagnostics", label="result_summary_coverage"),
    AggregateMetric("reference_result_summary_available", source="diagnostics", label="reference_summary_coverage"),
]

def _is_planner_sensitive_task(task_id: str) -> bool:
    return str(task_id or "").strip().startswith("toolsandbox_planner_sensitive_")


FOCUSED_SLICE_CATEGORIES = (
    "planner_sensitive",
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
        AggregateMetric("strict_scored_success"),
        AggregateMetric("repair_scored_success"),
        AggregateMetric("interaction_contract_satisfied"),
        AggregateMetric("mean_user_queries"),
        AggregateMetric("reply_usable_rate"),
        AggregateMetric("target_aligned_patch_rate"),
        AggregateMetric("effective_patch_rate"),
        AggregateMetric("post_query_progress_rate"),
        AggregateMetric("useful_interaction_round_rate"),
        AggregateMetric("repair_interaction_satisfied"),
        AggregateMetric("proxy_summary_success"),
        AggregateMetric("raw_trace_success", source="diagnostics", label="raw_trace_success_rate"),
        AggregateMetric("raw_execution_success", source="diagnostics", label="raw_execution_success_rate"),
        AggregateMetric("milestone_similarity"),
        AggregateMetric("milestone_coverage"),
        AggregateMetric("milestone_signal_available", source="diagnostics", label="milestone_signal_coverage"),
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
    parser.add_argument(
        "--interaction-target",
        choices=["simulator", "user_cli", "llm_openrouter", "cli_cmd"],
        default="simulator",
        help="Interaction responder for interactive systems: simulator (default), user_cli, llm_openrouter, or cli_cmd.",
    )
    parser.add_argument(
        "--cli-prompt-prefix",
        default="toolclaw",
        help="Prompt prefix when --interaction-target=user_cli.",
    )
    parser.add_argument(
        "--openrouter-model",
        default="openai/gpt-4o-mini",
        help="OpenRouter model slug when --interaction-target=llm_openrouter.",
    )
    parser.add_argument(
        "--openrouter-base-url",
        default="https://openrouter.ai/api/v1/chat/completions",
        help="OpenRouter chat completions URL when --interaction-target=llm_openrouter.",
    )
    parser.add_argument(
        "--openrouter-site-url",
        default="",
        help="Optional HTTP-Referer value sent to OpenRouter.",
    )
    parser.add_argument(
        "--openrouter-site-name",
        default="ToolClaw",
        help="Optional X-Title value sent to OpenRouter.",
    )
    parser.add_argument(
        "--cli-command",
        default="",
        help="Command for --interaction-target=cli_cmd. Receives request JSON via stdin and returns reply via stdout.",
    )
    parser.add_argument(
        "--cli-timeout-s",
        type=float,
        default=30.0,
        help="Timeout in seconds for --interaction-target=cli_cmd.",
    )
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


def _maybe_write_causal_ablation_outputs(outdir: Path, systems: List[str]) -> None:
    causal_systems = {"a2_planner", "a3_full_interaction", "a3_no_query", "a3_noisy_user"}
    if not causal_systems.issubset(set(systems)):
        return
    subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "analyze_toolsandbox_causal_ablation.py"),
            "--comparison",
            str(outdir / "comparison.scored.csv"),
            "--scoreboard",
            str(outdir / "scoreboard.json"),
            "--outdir",
            str(outdir),
        ],
        cwd=ROOT_DIR,
        check=True,
    )


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
        ("a2_planner_minus_a0_baseline", "a2_planner", "a0_baseline"),
        ("a2_planner_minus_a3_interaction", "a2_planner", "a3_interaction"),
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


def _load_scored_rows(outdir: Path) -> List[Dict[str, Any]]:
    scored_path = outdir / "comparison.scored.csv"
    if not scored_path.exists():
        return []
    with scored_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_trace_payload(trace_path: str) -> Dict[str, Any]:
    if not trace_path:
        return {}
    path = Path(trace_path)
    if not path.is_absolute():
        path = ROOT_DIR / path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _trace_repair_loop_flags(trace_payload: Dict[str, Any]) -> Dict[str, float]:
    events = trace_payload.get("events", [])
    patch_compiled_count = 0
    resume_requested_count = 0
    state_patch_count = 0
    policy_patch_count = 0
    binding_patch_count = 0
    for event in events:
        event_type = str(event.get("event_type") or "")
        if event_type == "patch_compiled":
            patch_compiled_count += 1
            output = dict(event.get("output") or {})
            if output.get("state_updates"):
                state_patch_count += 1
            if output.get("policy_updates"):
                policy_patch_count += 1
            if output.get("binding_patch"):
                binding_patch_count += 1
        elif event_type == "resume_requested":
            resume_requested_count += 1
    return {
        "has_patch_compiled": 1.0 if patch_compiled_count > 0 else 0.0,
        "has_resume_requested": 1.0 if resume_requested_count > 0 else 0.0,
        "patch_compiled_count": float(patch_compiled_count),
        "resume_requested_count": float(resume_requested_count),
        "state_patch_count": float(state_patch_count),
        "policy_patch_count": float(policy_patch_count),
        "binding_patch_count": float(binding_patch_count),
    }


def _group_scored_rows(rows: List[Dict[str, Any]], *, group_key: str) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for row in rows:
        system = str(row.get("system") or "unknown")
        group_name = str(row.get(group_key) or "unknown")
        grouped.setdefault(system, {}).setdefault(group_name, []).append(row)
    return grouped


def _summarize_failure_type_rows(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    return {
        "num_rows": float(len(rows)),
        "raw_execution_success": _mean_float(rows, "raw_execution_success"),
        "strict_scored_success": _mean_float(rows, "strict_scored_success"),
        "repair_scored_success": _mean_float(rows, "repair_scored_success"),
        "interaction_contract_satisfied": _mean_float(rows, "interaction_contract_satisfied"),
        "repair_interaction_satisfied": _mean_float(rows, "repair_interaction_satisfied"),
        "probe_user_queries": _mean_float(rows, "probe_user_queries"),
        "repair_user_queries": _mean_float(rows, "repair_user_queries"),
        "patch_success_rate": _mean_float(rows, "patch_success_rate"),
        "tool_calls": _mean_float(rows, "tool_calls"),
        "turn_count": _mean_float(rows, "turn_count"),
    }


def _failure_type_summary(outdir: Path) -> Dict[str, Dict[str, Dict[str, float]]]:
    rows = _load_scored_rows(outdir)
    grouped = _group_scored_rows(rows, group_key="failure_type")
    return {
        system: {
            failure_type: _summarize_failure_type_rows(group_rows)
            for failure_type, group_rows in sorted(system_groups.items())
        }
        for system, system_groups in sorted(grouped.items())
    }


def _write_failure_type_markdown(summary: Dict[str, Dict[str, Dict[str, float]]], out_path: Path) -> None:
    lines = [
        "# ToolSandbox Failure-Type Summary",
        "",
        "| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, failure_types in sorted(summary.items()):
        for failure_type, stats in sorted(failure_types.items()):
            lines.append(
                f"| {system} | {failure_type} | {int(stats.get('num_rows', 0))} | {float(stats.get('raw_execution_success', 0.0)):.3f} | {float(stats.get('strict_scored_success', 0.0)):.3f} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('interaction_contract_satisfied', 0.0)):.3f} | {float(stats.get('repair_interaction_satisfied', 0.0)):.3f} | {float(stats.get('probe_user_queries', 0.0)):.3f} | {float(stats.get('repair_user_queries', 0.0)):.3f} | {float(stats.get('patch_success_rate', 0.0)):.3f} | {float(stats.get('tool_calls', 0.0)):.3f} | {float(stats.get('turn_count', 0.0)):.3f} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _repair_loop_summary(outdir: Path) -> Dict[str, Any]:
    rows = _load_scored_rows(outdir)
    trace_cache: Dict[str, Dict[str, float]] = {}
    for row in rows:
        trace_path = str(row.get("trace_path") or "")
        if trace_path not in trace_cache:
            trace_cache[trace_path] = _trace_repair_loop_flags(_load_trace_payload(trace_path))

    per_system: Dict[str, Dict[str, float]] = {}
    per_failure_type: Dict[str, Dict[str, Dict[str, float]]] = {}
    grouped_by_system = _group_scored_rows(rows, group_key="system")
    for system, system_rows_map in grouped_by_system.items():
        system_rows = system_rows_map.get(system, [])
        per_system[system] = _summarize_repair_loop_rows(system_rows, trace_cache)

    grouped_by_failure_type = _group_scored_rows(rows, group_key="failure_type")
    for system, failure_type_map in sorted(grouped_by_failure_type.items()):
        per_failure_type[system] = {
            failure_type: _summarize_repair_loop_rows(group_rows, trace_cache)
            for failure_type, group_rows in sorted(failure_type_map.items())
        }

    return {
        "per_system": per_system,
        "per_failure_type": per_failure_type,
    }


def _summarize_repair_loop_rows(rows: List[Dict[str, Any]], trace_cache: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    if not rows:
        return {
            "num_rows": 0.0,
            "repair_rows": 0.0,
            "repair_scored_success": 0.0,
            "repair_user_queries": 0.0,
            "probe_user_queries": 0.0,
            "patch_success_rate": 0.0,
            "has_patch_compiled": 0.0,
            "has_resume_requested": 0.0,
            "patch_compiled_count": 0.0,
            "resume_requested_count": 0.0,
            "state_patch_count": 0.0,
            "policy_patch_count": 0.0,
            "binding_patch_count": 0.0,
        }
    overlays = [trace_cache.get(str(row.get("trace_path") or ""), {}) for row in rows]
    repair_rows = [
        row for row in rows
        if _float_cell(row.get("repair_user_queries", 0.0)) > 0.0
        or _float_cell(row.get("repair_user_replies", 0.0)) > 0.0
    ]
    def overlay_mean(key: str) -> float:
        return mean_or_zero([float(overlay.get(key, 0.0)) for overlay in overlays])
    return {
        "num_rows": float(len(rows)),
        "repair_rows": float(len(repair_rows)),
        "repair_scored_success": _mean_float(rows, "repair_scored_success"),
        "repair_user_queries": _mean_float(rows, "repair_user_queries"),
        "probe_user_queries": _mean_float(rows, "probe_user_queries"),
        "patch_success_rate": _mean_float(rows, "patch_success_rate"),
        "has_patch_compiled": overlay_mean("has_patch_compiled"),
        "has_resume_requested": overlay_mean("has_resume_requested"),
        "patch_compiled_count": overlay_mean("patch_compiled_count"),
        "resume_requested_count": overlay_mean("resume_requested_count"),
        "state_patch_count": overlay_mean("state_patch_count"),
        "policy_patch_count": overlay_mean("policy_patch_count"),
        "binding_patch_count": overlay_mean("binding_patch_count"),
    }


def _write_repair_loop_markdown(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolSandbox Repair Loop Summary",
        "",
        "## Per System",
        "",
        "| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, stats in sorted(summary.get("per_system", {}).items()):
        lines.append(
            f"| {system} | {int(stats.get('num_rows', 0))} | {int(stats.get('repair_rows', 0))} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('repair_user_queries', 0.0)):.3f} | {float(stats.get('probe_user_queries', 0.0)):.3f} | {float(stats.get('patch_success_rate', 0.0)):.3f} | {float(stats.get('has_patch_compiled', 0.0)):.3f} | {float(stats.get('has_resume_requested', 0.0)):.3f} | {float(stats.get('patch_compiled_count', 0.0)):.3f} | {float(stats.get('resume_requested_count', 0.0)):.3f} | {float(stats.get('state_patch_count', 0.0)):.3f} | {float(stats.get('policy_patch_count', 0.0)):.3f} | {float(stats.get('binding_patch_count', 0.0)):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Per Failure Type",
            "",
            "| system | failure_type | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | state_patch_count | policy_patch_count | binding_patch_count |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, failure_types in sorted(summary.get("per_failure_type", {}).items()):
        for failure_type, stats in sorted(failure_types.items()):
            lines.append(
                f"| {system} | {failure_type} | {int(stats.get('num_rows', 0))} | {int(stats.get('repair_rows', 0))} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('repair_user_queries', 0.0)):.3f} | {float(stats.get('probe_user_queries', 0.0)):.3f} | {float(stats.get('patch_success_rate', 0.0)):.3f} | {float(stats.get('has_patch_compiled', 0.0)):.3f} | {float(stats.get('has_resume_requested', 0.0)):.3f} | {float(stats.get('state_patch_count', 0.0)):.3f} | {float(stats.get('policy_patch_count', 0.0)):.3f} | {float(stats.get('binding_patch_count', 0.0)):.3f} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _mean_float(rows: List[Dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    values = [_float_cell(row.get(key, 0.0)) for row in rows]
    return sum(values) / len(values)


def _float_cell(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    text = str(value or "").strip().lower()
    if text in {"true", "yes"}:
        return 1.0
    if text in {"false", "no"}:
        return 0.0
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _reuse_focused_summary(outdir: Path, *, reuse_scope: str, asset_registry_root: str | None) -> Dict[str, Any]:
    rows = _load_scored_rows(outdir)
    if not rows:
        return {
            "reuse_scope": reuse_scope,
            "asset_registry_root": asset_registry_root,
            "metrics": [],
            "per_system": {},
            "deltas": {},
        }
    reuse_rows = [row for row in rows if str(row.get("task_id", "")).startswith("toolsandbox_reuse_")]
    if not reuse_rows:
        return {
            "reuse_scope": reuse_scope,
            "asset_registry_root": asset_registry_root,
            "metrics": [],
            "per_system": {},
            "deltas": {},
        }

    metrics = [
        "tool_calls",
        "raw_repair_triggered",
        "raw_repair_actions",
        "repair_extra_tool_calls",
        "repair_extra_user_turns",
        "reused_artifact",
        "second_run_improvement",
        "first_failure_recovered",
    ]
    per_system: Dict[str, Dict[str, float]] = {}
    for system in sorted({str(row.get("system", "")) for row in reuse_rows}):
        system_rows = [row for row in reuse_rows if str(row.get("system", "")) == system]
        per_system[system] = {
            "num_rows": float(len(system_rows)),
            "avg_tool_calls": _mean_float(system_rows, "tool_calls"),
            "repair_trigger_rate": _mean_float(system_rows, "raw_repair_triggered"),
            "avg_repair_actions": _mean_float(system_rows, "raw_repair_actions"),
            "avg_repair_extra_tool_calls": _mean_float(system_rows, "repair_extra_tool_calls"),
            "avg_repair_extra_user_turns": _mean_float(system_rows, "repair_extra_user_turns"),
            "reused_artifact_rate": _mean_float(system_rows, "reused_artifact"),
            "mean_second_run_improvement": _mean_float(system_rows, "second_run_improvement"),
            "first_failure_recovered_rate": _mean_float(system_rows, "first_failure_recovered"),
        }

    delta_pairs = [
        ("a4_reuse_minus_a3_interaction", "a4_reuse", "a3_interaction"),
        ("a4_reuse_minus_a0_baseline", "a4_reuse", "a0_baseline"),
    ]
    deltas: Dict[str, Dict[str, float]] = {}
    for name, right, left in delta_pairs:
        if right not in per_system or left not in per_system:
            continue
        deltas[name] = {
            "avg_tool_calls": per_system[right]["avg_tool_calls"] - per_system[left]["avg_tool_calls"],
            "repair_trigger_rate": per_system[right]["repair_trigger_rate"] - per_system[left]["repair_trigger_rate"],
            "avg_repair_actions": per_system[right]["avg_repair_actions"] - per_system[left]["avg_repair_actions"],
            "avg_repair_extra_tool_calls": per_system[right]["avg_repair_extra_tool_calls"] - per_system[left]["avg_repair_extra_tool_calls"],
            "avg_repair_extra_user_turns": per_system[right]["avg_repair_extra_user_turns"] - per_system[left]["avg_repair_extra_user_turns"],
            "reused_artifact_rate": per_system[right]["reused_artifact_rate"] - per_system[left]["reused_artifact_rate"],
            "mean_second_run_improvement": per_system[right]["mean_second_run_improvement"] - per_system[left]["mean_second_run_improvement"],
            "first_failure_recovered_rate": per_system[right]["first_failure_recovered_rate"] - per_system[left]["first_failure_recovered_rate"],
        }
    return {
        "reuse_scope": reuse_scope,
        "asset_registry_root": asset_registry_root,
        "metrics": metrics,
        "per_system": per_system,
        "deltas": deltas,
    }


def _write_reuse_focused_markdown(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolSandbox Reuse Focused Summary",
        "",
        f"- reuse_scope: `{summary.get('reuse_scope', 'within_invocation')}`",
        f"- asset_registry_root: `{summary.get('asset_registry_root') or 'none'}`",
        "",
        "| system | rows | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, stats in sorted(summary.get("per_system", {}).items()):
        lines.append(
            f"| {system} | {int(stats.get('num_rows', 0))} | {float(stats.get('avg_tool_calls', 0.0)):.3f} | {float(stats.get('repair_trigger_rate', 0.0)):.3f} | {float(stats.get('avg_repair_actions', 0.0)):.3f} | {float(stats.get('avg_repair_extra_tool_calls', 0.0)):.3f} | {float(stats.get('avg_repair_extra_user_turns', 0.0)):.3f} | {float(stats.get('reused_artifact_rate', 0.0)):.3f} | {float(stats.get('mean_second_run_improvement', 0.0)):.3f} | {float(stats.get('first_failure_recovered_rate', 0.0)):.3f} |"
        )
    if summary.get("deltas"):
        lines.extend(
            [
                "",
                "## Reuse Deltas",
                "",
                "| delta | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for delta_name, delta in sorted(summary["deltas"].items()):
            lines.append(
                f"| {delta_name} | {float(delta.get('avg_tool_calls', 0.0)):+.3f} | {float(delta.get('repair_trigger_rate', 0.0)):+.3f} | {float(delta.get('avg_repair_actions', 0.0)):+.3f} | {float(delta.get('avg_repair_extra_tool_calls', 0.0)):+.3f} | {float(delta.get('avg_repair_extra_user_turns', 0.0)):+.3f} | {float(delta.get('reused_artifact_rate', 0.0)):+.3f} | {float(delta.get('mean_second_run_improvement', 0.0)):+.3f} | {float(delta.get('first_failure_recovered_rate', 0.0)):+.3f} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _bootstrap_ci_mean_delta(deltas: List[float], *, rounds: int = 1000, seed: int = 0) -> Dict[str, float]:
    if not deltas:
        return {"mean_delta": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = random.Random(seed)
    n = len(deltas)
    sampled_means: List[float] = []
    for _ in range(rounds):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        sampled_means.append(sum(sample) / n)
    sampled_means.sort()
    low_idx = int(0.025 * (rounds - 1))
    high_idx = int(0.975 * (rounds - 1))
    return {
        "mean_delta": sum(deltas) / n,
        "ci_low": sampled_means[low_idx],
        "ci_high": sampled_means[high_idx],
    }


def _task_level_paired_summary(
    per_system_summary: Dict[str, Any],
    *,
    right_system: str,
    left_system: str,
    task_filter: Any = None,
) -> Dict[str, Any]:
    right = per_system_summary.get(right_system, {}).get("per_sample", {})
    left = per_system_summary.get(left_system, {}).get("per_sample", {})
    common_tasks = sorted(set(right).intersection(left))
    if task_filter is not None:
        common_tasks = [task_id for task_id in common_tasks if task_filter(task_id)]
    deltas: List[float] = []
    wins = 0
    losses = 0
    ties = 0
    for task_id in common_tasks:
        right_success = float(right[task_id].get("success_rate", 0.0))
        left_success = float(left[task_id].get("success_rate", 0.0))
        delta = right_success - left_success
        deltas.append(delta)
        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        else:
            ties += 1
    ci = _bootstrap_ci_mean_delta(deltas)
    return {
        "right_system": right_system,
        "left_system": left_system,
        "num_tasks": len(common_tasks),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_delta": ci["mean_delta"],
        "ci_low": ci["ci_low"],
        "ci_high": ci["ci_high"],
    }


def _focused_slice_filters() -> Dict[str, Any]:
    return {
        "approval": lambda task_id: "approval" in str(task_id),
        "state_repair": lambda task_id: "state_failure" in str(task_id),
        "repeated_reusable": lambda task_id: str(task_id).startswith("toolsandbox_reuse_"),
        "planner_distractor_hard": lambda task_id: (
            str(task_id).startswith("toolsandbox_planner_sensitive_")
            or str(task_id).startswith("toolsandbox_planner_distractor_")
        ),
    }


def _statistical_robustness_summary(scoreboard: Dict[str, Any]) -> Dict[str, Any]:
    per_system_summary = dict(scoreboard.get("per_system_summary", {}))
    paired_overall = [
        _task_level_paired_summary(per_system_summary, right_system="a2_planner", left_system="a3_interaction"),
        _task_level_paired_summary(per_system_summary, right_system="a4_reuse", left_system="a3_interaction"),
        _task_level_paired_summary(per_system_summary, right_system="a4_reuse", left_system="a0_baseline"),
    ]
    focused_filters = _focused_slice_filters()
    paired_focused: Dict[str, List[Dict[str, Any]]] = {}
    for slice_name, task_filter in focused_filters.items():
        paired_focused[slice_name] = [
            _task_level_paired_summary(
                per_system_summary,
                right_system="a2_planner",
                left_system="a3_interaction",
                task_filter=task_filter,
            ),
            _task_level_paired_summary(
                per_system_summary,
                right_system="a4_reuse",
                left_system="a3_interaction",
                task_filter=task_filter,
            ),
            _task_level_paired_summary(
                per_system_summary,
                right_system="a4_reuse",
                left_system="a0_baseline",
                task_filter=task_filter,
            ),
        ]
    return {
        "deterministic_warning": "consistency_is_replication_stability_not_uncertainty_estimation",
        "paired_overall": paired_overall,
        "paired_focused_slices": paired_focused,
    }


def _write_toolsandbox_report(scoreboard: Dict[str, Any], outdir: Path, *, reuse_scope: str, asset_registry_root: str | None) -> None:
    reuse_summary = _reuse_focused_summary(outdir, reuse_scope=reuse_scope, asset_registry_root=asset_registry_root)
    (outdir / "reuse_focused_summary.json").write_text(json.dumps(reuse_summary, indent=2), encoding="utf-8")
    _write_reuse_focused_markdown(reuse_summary, outdir / "reuse_focused_summary.md")
    robustness_summary = _statistical_robustness_summary(scoreboard)
    (outdir / "statistical_robustness_summary.json").write_text(json.dumps(robustness_summary, indent=2), encoding="utf-8")
    caution_flags = list(scoreboard.get("benchmark_caution_flags", []))
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
        f"- reuse_focused_summary: `{outdir / 'reuse_focused_summary.md'}`",
        f"- per_failure_type_summary: `{outdir / 'per_failure_type_summary.md'}`",
        f"- repair_loop_summary: `{outdir / 'repair_loop_summary.md'}`",
        f"- statistical_robustness_summary: `{outdir / 'statistical_robustness_summary.json'}`",
        f"- failtax_summary: `{outdir / 'per_failtax_summary.json'}`",
        "",
        "## Readiness",
        "",
    ]
    lines.extend(
        [
            f"- reuse_scope: `{reuse_scope}`",
            f"- asset_registry_root: `{asset_registry_root or 'none'}`",
            "",
        ]
    )
    if caution_flags:
        lines.extend(
            [
                "- primary_result_ready: `False`",
                "- caution_flags:",
                *[f"  - `{flag}`" for flag in caution_flags],
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- primary_result_ready: `True`",
                "- caution_flags: none",
                "",
            ]
        )

    lines.extend(
        [
        "## Aggregate",
        "",
        "| system | mean_success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | consistency | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    per_system = scoreboard["per_system_summary"]
    for system, stats in per_system.items():
        lines.append(
            f"| {system} | {float(stats.get('mean_success_rate', 0.0)):.3f} | {float(stats.get('strict_scored_success', stats.get('execution_verified_success', 0.0))):.3f} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('interaction_contract_satisfied', 0.0)):.3f} | {float(stats.get('mean_user_queries', 0.0)):.3f} | {float(stats.get('reply_usable_rate', 0.0)):.3f} | {float(stats.get('target_aligned_patch_rate', 0.0)):.3f} | {float(stats.get('effective_patch_rate', 0.0)):.3f} | {float(stats.get('post_query_progress_rate', 0.0)):.3f} | {float(stats.get('useful_interaction_round_rate', 0.0)):.3f} | {float(stats.get('repair_interaction_satisfied', 0.0)):.3f} | {float(stats.get('proxy_summary_success', 0.0)):.3f} | {float(stats.get('raw_trace_success_rate', 0.0)):.3f} | {float(stats.get('raw_execution_success_rate', 0.0)):.3f} | {float(stats.get('consistency', 0.0)):.3f} | {float(stats.get('milestone_similarity', 0.0)):.3f} | {float(stats.get('milestone_coverage', 0.0)):.3f} | {float(stats.get('milestone_signal_coverage', 0.0)):.3f} | {float(stats.get('state_dependency_score', 0.0)):.3f} | {float(stats.get('hallucination_avoidance', 0.0)):.3f} | {float(stats.get('tool_efficiency', 0.0)):.3f} | {float(stats.get('turn_efficiency', 0.0)):.3f} | {float(stats.get('budget_violation_rate', 0.0)):.3f} | {float(stats.get('used_result_summary', 0.0)):.3f} | {float(stats.get('reference_result_summary_available', 0.0)):.3f} | {stats.get('dominant_result_summary_source', 'unknown')} |"
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
            "| system | category | rows | success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for system, stats in per_system.items():
        for category, category_stats in sorted(stats.get("per_category", {}).items()):
            lines.append(
                f"| {system} | {category} | {int(category_stats.get('num_rows', 0))} | {float(category_stats.get('success_rate', 0.0)):.3f} | {float(category_stats.get('strict_scored_success', category_stats.get('execution_verified_success', 0.0))):.3f} | {float(category_stats.get('repair_scored_success', 0.0)):.3f} | {float(category_stats.get('interaction_contract_satisfied', 0.0)):.3f} | {float(category_stats.get('mean_user_queries', 0.0)):.3f} | {float(category_stats.get('reply_usable_rate', 0.0)):.3f} | {float(category_stats.get('target_aligned_patch_rate', 0.0)):.3f} | {float(category_stats.get('effective_patch_rate', 0.0)):.3f} | {float(category_stats.get('post_query_progress_rate', 0.0)):.3f} | {float(category_stats.get('useful_interaction_round_rate', 0.0)):.3f} | {float(category_stats.get('repair_interaction_satisfied', 0.0)):.3f} | {float(category_stats.get('proxy_summary_success', 0.0)):.3f} | {float(category_stats.get('raw_trace_success_rate', 0.0)):.3f} | {float(category_stats.get('raw_execution_success_rate', 0.0)):.3f} | {float(category_stats.get('milestone_similarity', 0.0)):.3f} | {float(category_stats.get('milestone_coverage', 0.0)):.3f} | {float(category_stats.get('milestone_signal_coverage', 0.0)):.3f} | {float(category_stats.get('state_dependency_score', 0.0)):.3f} | {float(category_stats.get('hallucination_avoidance', 0.0)):.3f} | {float(category_stats.get('tool_efficiency', 0.0)):.3f} | {float(category_stats.get('turn_efficiency', 0.0)):.3f} | {float(category_stats.get('result_summary_coverage', 0.0)):.3f} | {float(category_stats.get('reference_summary_coverage', 0.0)):.3f} | {category_stats.get('dominant_result_summary_source', 'unknown')} |"
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

    failure_type_summary = _failure_type_summary(outdir)
    lines.extend(
        [
            "",
            "## Failure Type Summary",
            "",
            "| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, failure_types in sorted(failure_type_summary.items()):
        for failure_type, stats in sorted(failure_types.items()):
            lines.append(
                f"| {system} | {failure_type} | {int(stats.get('num_rows', 0))} | {float(stats.get('raw_execution_success', 0.0)):.3f} | {float(stats.get('strict_scored_success', 0.0)):.3f} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('interaction_contract_satisfied', 0.0)):.3f} | {float(stats.get('repair_interaction_satisfied', 0.0)):.3f} | {float(stats.get('probe_user_queries', 0.0)):.3f} | {float(stats.get('repair_user_queries', 0.0)):.3f} | {float(stats.get('patch_success_rate', 0.0)):.3f} | {float(stats.get('tool_calls', 0.0)):.3f} | {float(stats.get('turn_count', 0.0)):.3f} |"
            )

    repair_loop_summary = _repair_loop_summary(outdir)
    lines.extend(
        [
            "",
            "## Repair Loop Summary",
            "",
            "| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, stats in sorted(repair_loop_summary.get("per_system", {}).items()):
        lines.append(
            f"| {system} | {int(stats.get('num_rows', 0))} | {int(stats.get('repair_rows', 0))} | {float(stats.get('repair_scored_success', 0.0)):.3f} | {float(stats.get('repair_user_queries', 0.0)):.3f} | {float(stats.get('probe_user_queries', 0.0)):.3f} | {float(stats.get('patch_success_rate', 0.0)):.3f} | {float(stats.get('has_patch_compiled', 0.0)):.3f} | {float(stats.get('has_resume_requested', 0.0)):.3f} | {float(stats.get('patch_compiled_count', 0.0)):.3f} | {float(stats.get('resume_requested_count', 0.0)):.3f} | {float(stats.get('state_patch_count', 0.0)):.3f} | {float(stats.get('policy_patch_count', 0.0)):.3f} | {float(stats.get('binding_patch_count', 0.0)):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Reuse Focused",
            "",
            "| system | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, stats in sorted(reuse_summary.get("per_system", {}).items()):
        lines.append(
            f"| {system} | {float(stats.get('avg_tool_calls', 0.0)):.3f} | {float(stats.get('repair_trigger_rate', 0.0)):.3f} | {float(stats.get('avg_repair_actions', 0.0)):.3f} | {float(stats.get('avg_repair_extra_tool_calls', 0.0)):.3f} | {float(stats.get('avg_repair_extra_user_turns', 0.0)):.3f} | {float(stats.get('reused_artifact_rate', 0.0)):.3f} | {float(stats.get('mean_second_run_improvement', 0.0)):.3f} | {float(stats.get('first_failure_recovered_rate', 0.0)):.3f} |"
        )
    if reuse_summary.get("deltas"):
        lines.extend(
            [
                "",
                "| reuse_delta | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for delta_name, delta in sorted(reuse_summary["deltas"].items()):
            lines.append(
                f"| {delta_name} | {float(delta.get('avg_tool_calls', 0.0)):+.3f} | {float(delta.get('repair_trigger_rate', 0.0)):+.3f} | {float(delta.get('avg_repair_actions', 0.0)):+.3f} | {float(delta.get('avg_repair_extra_tool_calls', 0.0)):+.3f} | {float(delta.get('avg_repair_extra_user_turns', 0.0)):+.3f} | {float(delta.get('reused_artifact_rate', 0.0)):+.3f} | {float(delta.get('mean_second_run_improvement', 0.0)):+.3f} | {float(delta.get('first_failure_recovered_rate', 0.0)):+.3f} |"
            )

    lines.extend(
        [
            "",
            "## Statistical Robustness",
            "",
            "- consistency=1.0 here mainly indicates deterministic replication stability across repeats.",
            "- paired comparison is reported at task level (wins/losses/ties) with bootstrap 95% CI on mean success delta.",
            "",
            "| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in robustness_summary.get("paired_overall", []):
        lines.append(
            f"| {row['right_system']} vs {row['left_system']} | {int(row['num_tasks'])} | {int(row['wins'])} | {int(row['losses'])} | {int(row['ties'])} | {float(row['mean_delta']):+.3f} | [{float(row['ci_low']):+.3f}, {float(row['ci_high']):+.3f}] |"
        )

    for slice_name, rows in sorted(dict(robustness_summary.get("paired_focused_slices", {})).items()):
        lines.extend(
            [
                "",
                f"### Focused Slice: {slice_name}",
                "",
                "| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            lines.append(
                f"| {row['right_system']} vs {row['left_system']} | {int(row['num_tasks'])} | {int(row['wins'])} | {int(row['losses'])} | {int(row['ties'])} | {float(row['mean_delta']):+.3f} | [{float(row['ci_low']):+.3f}, {float(row['ci_high']):+.3f}] |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `mean_success_rate` is computed from strict scored success, not from proxy summaries alone.",
            "- `strict_scored_success` is the benchmark-facing success after the must-interact gate is applied.",
            "- `repair_scored_success` is stricter: it only counts runs that both score successfully and include at least one non-probe repair interaction.",
            "- `interaction_contract_satisfied` can be lifted by an interaction probe; `repair_interaction_satisfied` cannot.",
            "- `raw_trace_success_rate` / `raw_execution_success_rate` are reported separately because executor success and benchmark-verified success can diverge.",
            "- `proxy_summary_success` tracks runs that looked successful under the attached ToolClaw proxy summary path.",
            "- `milestone_signal_coverage` shows whether the trace carried an explicit milestone verification signal; low coverage weakens benchmark claims even if proxy summaries exist.",
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
    proxy_summary = adapter.build_proxy_result_summary(sample, trace_payload)
    reference_summary = adapter._extract_reference_result_summary(sample.raw_payload)
    metadata["toolsandbox_proxy_result"] = proxy_summary
    if reference_summary:
        normalized_reference_summary = dict(reference_summary)
        normalized_reference_summary["source"] = "reference_result_summary"
        # Prefer reference summaries for benchmark scoring when available.
        metadata["toolsandbox_result"] = normalized_reference_summary
        metadata["toolsandbox_result_source"] = "reference_result_summary"
        metadata["toolsandbox_reference_result"] = normalized_reference_summary
    else:
        metadata["toolsandbox_result"] = proxy_summary
        metadata["toolsandbox_result_source"] = "toolclaw_proxy"
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
        samples = _select_smoke_samples(samples, max_count=10)
        _validate_smoke_profile(samples)
    if not samples:
        raise ValueError("No ToolSandbox samples loaded from source after validation")
    if args.require_result_summary and not any(sample.raw_payload.get("result_summary") for sample in samples):
        raise ValueError("require-result-summary was set, but no ToolSandbox result_summary / toolsandbox_result was found")
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    if args.interaction_target == "user_cli":
        for task in normalized_tasks:
            task["interaction_backend"] = {
                "type": "human",
                "prompt_prefix": args.cli_prompt_prefix,
            }
    elif args.interaction_target == "llm_openrouter":
        for task in normalized_tasks:
            task["interaction_backend"] = {
                "type": "llm",
                "provider_name": "openrouter",
                "mode": "openrouter",
                "model": args.openrouter_model,
                "base_url": args.openrouter_base_url,
                "site_url": args.openrouter_site_url,
                "site_name": args.openrouter_site_name,
                "status": "accept",
            }
    elif args.interaction_target == "cli_cmd":
        if not str(args.cli_command or "").strip():
            raise ValueError("--cli-command is required when --interaction-target=cli_cmd")
        for task in normalized_tasks:
            task["interaction_backend"] = {
                "type": "cli",
                "provider_name": "cli_cmd",
                "command": args.cli_command,
                "timeout_s": float(args.cli_timeout_s),
            }
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
    scoreboard["benchmark_caution_flags"] = _toolsandbox_benchmark_caution_flags(scoreboard)
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
            "interaction_target": args.interaction_target,
            "cli_prompt_prefix": args.cli_prompt_prefix if args.interaction_target == "user_cli" else None,
            "cli_command": args.cli_command if args.interaction_target == "cli_cmd" else None,
            "cli_timeout_s": args.cli_timeout_s if args.interaction_target == "cli_cmd" else None,
            "openrouter_model": args.openrouter_model if args.interaction_target == "llm_openrouter" else None,
            "openrouter_base_url": args.openrouter_base_url if args.interaction_target == "llm_openrouter" else None,
        },
        archive_files=[
            Path(__file__).resolve(),
            Path(args.config_file),
            Path(args.phase_config),
        ],
    )
    write_csv_rows(raw_run_rows, outdir / "comparison.raw.csv")
    write_csv_rows(scored_run_rows, outdir / "comparison.scored.csv")
    failure_type_summary = _failure_type_summary(outdir)
    (outdir / "per_failure_type_summary.json").write_text(
        json.dumps(failure_type_summary, indent=2),
        encoding="utf-8",
    )
    _write_failure_type_markdown(failure_type_summary, outdir / "per_failure_type_summary.md")
    repair_loop_summary = _repair_loop_summary(outdir)
    (outdir / "repair_loop_summary.json").write_text(
        json.dumps(repair_loop_summary, indent=2),
        encoding="utf-8",
    )
    _write_repair_loop_markdown(repair_loop_summary, outdir / "repair_loop_summary.md")
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
    reuse_scope = "cross_run_persistent" if args.asset_registry_root else "within_invocation"
    _write_toolsandbox_report(
        scoreboard,
        outdir,
        reuse_scope=reuse_scope,
        asset_registry_root=str(Path(args.asset_registry_root).resolve()) if args.asset_registry_root else None,
    )
    _maybe_write_causal_ablation_outputs(outdir, systems)
    update_experiment_manifest(
        outdir,
        updates={
            "report_path": str((outdir / "report.md").resolve()),
            "causal_claim_summary_path": str((outdir / "causal_claim_summary.json").resolve())
            if (outdir / "causal_claim_summary.json").exists()
            else None,
            "causal_claim_report_path": str((outdir / "causal_claim_report.md").resolve())
            if (outdir / "causal_claim_report.md").exists()
            else None,
            "slice_policy_version": CAUSAL_SLICE_POLICY_VERSION
            if (outdir / "causal_claim_summary.json").exists()
            else None,
            "claim_ids": CAUSAL_CLAIM_IDS if (outdir / "causal_claim_summary.json").exists() else None,
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
