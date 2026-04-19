"""Task-level diagnostics for A3 vs A4 reuse regressions on ToolSandbox outputs."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


METRIC_PRIORITY: Tuple[str, ...] = (
    "execution_verified_success",
    "success",
    "milestone_similarity",
    "hallucination_avoidance",
    "state_dependency_score",
    "interaction_efficiency",
    "tool_efficiency",
    "turn_efficiency",
)

INTERACTION_CATEGORIES = {"insufficient_information", "multiple_user_turn"}
ORDERING_CATEGORIES = {"canonicalization", "state_dependency"}
RECOVERY_HINT_TOKENS = ("clarify", "ask", "approval", "patch", "retry")


@dataclass
class TraceSummary:
    path: str
    preflight_missing_assets: List[str] = field(default_factory=list)
    user_queries: int = 0
    repair_count: int = 0
    repair_types: List[str] = field(default_factory=list)
    mapped_error_categories: List[str] = field(default_factory=list)
    tool_sequence: List[str] = field(default_factory=list)
    stop_reason: str = ""


@dataclass
class RegressionCase:
    run_index: int
    task_id: str
    cause: str
    degradation_metrics: List[Dict[str, float]]
    categories: List[str]
    expected_recovery_path: str
    reused_artifact: bool
    evidence: List[str]
    a3_trace_path: str
    a4_trace_path: str


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze_outdir(
    outdir: Path,
    *,
    left_system: str = "a3_interaction",
    right_system: str = "a4_reuse",
) -> Dict[str, Any]:
    scored_path = _discover_comparison_path(outdir)

    rows = load_csv_rows(scored_path)
    raw_path = outdir / "comparison.raw.csv"
    if raw_path.exists():
        rows = _merge_raw_fields(scored_rows=rows, raw_rows=load_csv_rows(raw_path))
    paired_cases = _paired_rows(rows, left_system=left_system, right_system=right_system)
    regressions: List[RegressionCase] = []
    for _, left_row, right_row in paired_cases:
        degradation_metrics = metric_degradation(left_row, right_row)
        if not degradation_metrics:
            continue
        regressions.append(classify_regression_case(outdir=outdir, left_row=left_row, right_row=right_row, degradation_metrics=degradation_metrics))

    unique_tasks = sorted({case.task_id for case in regressions})
    cause_counts: Dict[str, int] = {}
    for case in regressions:
        cause_counts[case.cause] = cause_counts.get(case.cause, 0) + 1

    unique_task_causes: Dict[str, List[str]] = {}
    for task_id in unique_tasks:
        unique_task_causes[task_id] = sorted({case.cause for case in regressions if case.task_id == task_id})

    return {
        "outdir": str(outdir),
        "left_system": left_system,
        "right_system": right_system,
        "metric_priority": list(METRIC_PRIORITY),
        "paired_case_count": len(paired_cases),
        "regression_case_count": len(regressions),
        "regressed_task_count": len(unique_tasks),
        "cause_counts": cause_counts,
        "regressed_tasks": [
            {
                "task_id": task_id,
                "causes": unique_task_causes[task_id],
                "num_runs": sum(1 for case in regressions if case.task_id == task_id),
            }
            for task_id in unique_tasks
        ],
        "cases": [
            {
                "run_index": case.run_index,
                "task_id": case.task_id,
                "cause": case.cause,
                "degradation_metrics": case.degradation_metrics,
                "categories": case.categories,
                "expected_recovery_path": case.expected_recovery_path,
                "reused_artifact": case.reused_artifact,
                "evidence": case.evidence,
                "a3_trace_path": case.a3_trace_path,
                "a4_trace_path": case.a4_trace_path,
            }
            for case in regressions
        ],
        "recommendations": build_recommendations(cause_counts),
    }


def metric_degradation(left_row: Dict[str, str], right_row: Dict[str, str]) -> List[Dict[str, float]]:
    degradations: List[Dict[str, float]] = []
    for metric in METRIC_PRIORITY:
        left_value = _float_value(left_row.get(metric))
        right_value = _float_value(right_row.get(metric))
        if right_value < left_value - 1e-9:
            degradations.append(
                {
                    "metric": metric,
                    "a3": left_value,
                    "a4": right_value,
                    "delta": right_value - left_value,
                }
            )
    return degradations


def classify_regression_case(
    *,
    outdir: Path,
    left_row: Dict[str, str],
    right_row: Dict[str, str],
    degradation_metrics: List[Dict[str, float]],
) -> RegressionCase:
    categories = _json_list(right_row.get("categories") or left_row.get("categories"))
    expected_recovery_path = str(right_row.get("expected_recovery_path") or left_row.get("expected_recovery_path") or "")
    left_trace = summarize_trace(_resolve_trace_path(outdir, left_row.get("trace_path", "")))
    right_trace = summarize_trace(_resolve_trace_path(outdir, right_row.get("trace_path", "")))
    reused_artifact = _bool_value(right_row.get("reused_artifact"))
    evidence: List[str] = []

    if right_trace.preflight_missing_assets != left_trace.preflight_missing_assets:
        evidence.append(
            "preflight missing assets differ: "
            f"a3={left_trace.preflight_missing_assets or []}, a4={right_trace.preflight_missing_assets or []}"
        )
    if right_trace.user_queries != left_trace.user_queries:
        evidence.append(f"user query count differs: a3={left_trace.user_queries}, a4={right_trace.user_queries}")
    if right_trace.repair_count != left_trace.repair_count:
        evidence.append(f"repair count differs: a3={left_trace.repair_count}, a4={right_trace.repair_count}")
    if right_trace.tool_sequence != left_trace.tool_sequence:
        evidence.append(f"tool sequence differs: a3={left_trace.tool_sequence}, a4={right_trace.tool_sequence}")
    if degradation_metrics:
        evidence.append(
            "metric deltas: "
            + ", ".join(
                f"{item['metric']} {item['a3']:.3f}->{item['a4']:.3f}"
                for item in degradation_metrics
            )
        )

    interaction_sensitive = bool(set(categories) & INTERACTION_CATEGORIES) or any(token in expected_recovery_path for token in RECOVERY_HINT_TOKENS)
    selected_wrong = _selected_wrong(left_row=left_row, right_row=right_row, left_trace=left_trace, right_trace=right_trace)
    binding_or_ordering = _binding_or_ordering_regression(left_row=left_row, right_row=right_row, left_trace=left_trace, right_trace=right_trace, categories=categories)
    interaction_overridden = (
        reused_artifact
        and interaction_sensitive
        and right_trace.user_queries < left_trace.user_queries
        and (
            len(right_trace.preflight_missing_assets) < len(left_trace.preflight_missing_assets)
            or right_trace.repair_count < left_trace.repair_count
        )
    )
    used_too_early = (
        reused_artifact
        and not selected_wrong
        and not binding_or_ordering
        and not interaction_overridden
        and (
            len(right_trace.preflight_missing_assets) < len(left_trace.preflight_missing_assets)
            or right_trace.repair_count < left_trace.repair_count
        )
    )

    if selected_wrong:
        cause = "artifact_selected_wrong"
    elif binding_or_ordering:
        cause = "artifact_caused_binding_or_ordering"
    elif interaction_overridden:
        cause = "artifact_overrode_interaction_repair"
    elif used_too_early:
        cause = "artifact_used_too_early"
    else:
        cause = "unclassified_reuse_regression"
        if reused_artifact:
            evidence.append("reuse was active, but current heuristics could not assign a tighter cause")
        else:
            evidence.append("A4 underperformed without an explicit reused artifact signal")

    return RegressionCase(
        run_index=int(left_row.get("run_index", 0) or 0),
        task_id=str(left_row.get("task_id") or right_row.get("task_id") or ""),
        cause=cause,
        degradation_metrics=degradation_metrics,
        categories=categories,
        expected_recovery_path=expected_recovery_path,
        reused_artifact=reused_artifact,
        evidence=evidence,
        a3_trace_path=left_trace.path,
        a4_trace_path=right_trace.path,
    )


def summarize_trace(path: Path) -> TraceSummary:
    if not path.exists():
        return TraceSummary(path=str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    preflight_missing_assets: List[str] = []
    repair_types: List[str] = []
    mapped_error_categories: List[str] = []
    tool_sequence: List[str] = []
    stop_reason = ""
    for event in events:
        event_type = str(event.get("event_type") or "")
        output = event.get("output") or {}
        if event_type == "preflight_check" and not preflight_missing_assets:
            preflight_missing_assets = [str(item) for item in output.get("missing_assets", []) if str(item)]
        elif event_type == "repair_triggered":
            repair_type = str(output.get("repair_type") or "")
            if repair_type:
                repair_types.append(repair_type)
            metadata = output.get("metadata") or {}
            mapped = str(metadata.get("mapped_from_error_category") or "")
            if mapped:
                mapped_error_categories.append(mapped)
        elif event_type == "tool_call":
            tool_id = str(event.get("tool_id") or "")
            if tool_id:
                tool_sequence.append(tool_id)
        elif event_type == "stop":
            stop_reason = str(output.get("reason") or stop_reason)
    return TraceSummary(
        path=str(path),
        preflight_missing_assets=preflight_missing_assets,
        user_queries=sum(1 for event in events if event.get("event_type") == "user_query"),
        repair_count=sum(1 for event in events if event.get("event_type") == "repair_triggered"),
        repair_types=repair_types,
        mapped_error_categories=mapped_error_categories,
        tool_sequence=tool_sequence,
        stop_reason=stop_reason,
    )


def build_recommendations(cause_counts: Dict[str, int]) -> List[str]:
    recommendations: List[str] = []
    if cause_counts.get("artifact_used_too_early", 0):
        recommendations.append(
            "Tighten reuse admission on tasks whose expected_recovery_path still needs local failure materialization; do not prefill repair-sensitive slots before the task actually blocks."
        )
    if cause_counts.get("artifact_overrode_interaction_repair", 0):
        recommendations.append(
            "Blacklist clarification-owned slots from reuse injection when the task category or recovery path says the user should supply them interactively."
        )
    if cause_counts.get("artifact_selected_wrong", 0):
        recommendations.append(
            "Split exact-vs-transfer binding confidence and require a stronger tool-match threshold before reuse can override planner-selected bindings."
        )
    if cause_counts.get("artifact_caused_binding_or_ordering", 0):
        recommendations.append(
            "Gate reuse on dependency_edges / required_state_slots compatibility and add early rollback when reused inputs trigger binding or ordering regressions."
        )
    if not recommendations:
        recommendations.append("No reuse-specific regression pattern was detected in the selected output.")
    return recommendations


def render_markdown(analysis: Dict[str, Any]) -> str:
    lines = [
        "# A3 vs A4 Core Reuse Failure Analysis",
        "",
        f"- outdir: `{analysis['outdir']}`",
        f"- paired cases: `{analysis['paired_case_count']}`",
        f"- regressed cases: `{analysis['regression_case_count']}`",
        f"- regressed tasks: `{analysis['regressed_task_count']}`",
        "",
        "## Cause Counts",
        "",
    ]
    if analysis["cause_counts"]:
        for cause, count in sorted(analysis["cause_counts"].items()):
            lines.append(f"- `{cause}`: `{count}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Recommendations", ""])
    for recommendation in analysis["recommendations"]:
        lines.append(f"- {recommendation}")
    lines.extend(["", "## Cases", ""])
    if not analysis["cases"]:
        lines.append("- none")
        return "\n".join(lines) + "\n"
    for case in analysis["cases"]:
        lines.extend(
            [
                f"### {case['task_id']} (run {case['run_index']})",
                f"- cause: `{case['cause']}`",
                f"- categories: `{', '.join(case['categories'])}`",
                f"- expected_recovery_path: `{case['expected_recovery_path']}`",
                f"- reused_artifact: `{case['reused_artifact']}`",
                f"- a3 trace: `{case['a3_trace_path']}`",
                f"- a4 trace: `{case['a4_trace_path']}`",
                "- evidence:",
            ]
        )
        for item in case["evidence"]:
            lines.append(f"  - {item}")
    return "\n".join(lines) + "\n"


def _discover_comparison_path(outdir: Path) -> Path:
    for candidate in ("comparison.scored.csv", "comparison.raw.csv", "comparison.csv"):
        path = outdir / candidate
        if path.exists():
            return path
    manifest_path = outdir / "experiment_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in (
            "comparison_scored_path",
            "comparison_raw_path",
            "comparison_path",
            "latest_comparison_scored_path",
            "latest_comparison_raw_path",
        ):
            candidate = str(payload.get(key) or "").strip()
            if not candidate:
                continue
            path = Path(candidate)
            if not path.is_absolute():
                path = (outdir / candidate).resolve()
            if path.exists():
                return path
    runs_dir = outdir / "runs"
    if runs_dir.exists():
        run_candidates = sorted(runs_dir.glob("run_*/comparison.csv"))
        if run_candidates:
            return run_candidates[-1]
    raise FileNotFoundError(f"no comparison csv found under {outdir}")


def _paired_rows(
    rows: Iterable[Dict[str, str]],
    *,
    left_system: str,
    right_system: str,
) -> List[Tuple[Tuple[str, str], Dict[str, str], Dict[str, str]]]:
    paired: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = {}
    for row in rows:
        key = (str(row.get("run_index", "")), str(row.get("task_id", "")))
        paired.setdefault(key, {})[str(row.get("system", ""))] = row
    result: List[Tuple[Tuple[str, str], Dict[str, str], Dict[str, str]]] = []
    for key, systems in sorted(paired.items()):
        if left_system in systems and right_system in systems:
            result.append((key, systems[left_system], systems[right_system]))
    return result


def _merge_raw_fields(
    *,
    scored_rows: List[Dict[str, str]],
    raw_rows: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    raw_by_key = {
        (str(row.get("run_index", "")), str(row.get("task_id", "")), str(row.get("system", ""))): row
        for row in raw_rows
    }
    merged: List[Dict[str, str]] = []
    for row in scored_rows:
        key = (str(row.get("run_index", "")), str(row.get("task_id", "")), str(row.get("system", "")))
        raw_row = raw_by_key.get(key, {})
        enriched = dict(raw_row)
        enriched.update({k: v for k, v in row.items() if v not in ("", None)})
        merged.append(enriched)
    return merged


def _selected_wrong(
    *,
    left_row: Dict[str, str],
    right_row: Dict[str, str],
    left_trace: TraceSummary,
    right_trace: TraceSummary,
) -> bool:
    left_chosen = str(left_row.get("chosen_tool") or "")
    right_chosen = str(right_row.get("chosen_tool") or "")
    gold_tool = str(right_row.get("gold_tool") or left_row.get("gold_tool") or "")
    if right_chosen and gold_tool and right_chosen != gold_tool:
        return True
    if left_chosen and right_chosen and left_chosen != right_chosen and right_chosen != gold_tool:
        return True
    if left_trace.tool_sequence and right_trace.tool_sequence:
        left_final = left_trace.tool_sequence[-1]
        right_final = right_trace.tool_sequence[-1]
        if gold_tool and right_final and right_final != gold_tool and right_final != left_final:
            return True
    return False


def _binding_or_ordering_regression(
    *,
    left_row: Dict[str, str],
    right_row: Dict[str, str],
    left_trace: TraceSummary,
    right_trace: TraceSummary,
    categories: List[str],
) -> bool:
    right_observed = str(right_row.get("observed_error_type") or "")
    left_observed = str(left_row.get("observed_error_type") or "")
    if right_observed in {"binding_failure", "ordering_failure"} and right_observed != left_observed:
        return True
    if any(item in {"binding_failure", "ordering_failure"} for item in right_trace.mapped_error_categories):
        return True
    if any(item in {"rebind_args", "replan_suffix"} for item in right_trace.repair_types) and right_trace.repair_count > left_trace.repair_count:
        return True
    return bool(set(categories) & ORDERING_CATEGORIES and right_trace.tool_sequence and left_trace.tool_sequence and right_trace.tool_sequence != left_trace.tool_sequence)


def _resolve_trace_path(outdir: Path, trace_path: str) -> Path:
    trace = Path(trace_path)
    if trace.is_absolute():
        return trace
    candidate = outdir / trace
    if candidate.exists():
        return candidate
    root_candidate = outdir.parent.parent / trace
    if root_candidate.exists():
        return root_candidate
    return (Path.cwd() / trace).resolve()


def _json_list(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [item.strip() for item in text.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def _float_value(raw: Any) -> float:
    text = str(raw or "").strip()
    if not text:
        return 0.0
    if text.lower() == "true":
        return 1.0
    if text.lower() == "false":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _bool_value(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes"}
