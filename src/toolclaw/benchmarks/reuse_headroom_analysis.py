"""Focused analysis for high-headroom exact/near-match reuse cases."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from toolclaw.benchmarks.reuse_stratified_analysis import (
    _discover_comparison_path,
    _discover_taskset_path,
    _enrich_row,
    _load_task_lookup,
    _metric_value,
    _paired_rows,
    load_csv_rows,
)


DEFAULT_FOCUS_TIERS: Tuple[str, ...] = ("exact_match_reuse", "same_family_transfer_reuse")


def analyze_outdir(
    outdir: Path,
    *,
    left_system: str = "a3_interaction",
    right_system: str = "a4_reuse",
    taskset_path: Optional[Path] = None,
    focus_tiers: Sequence[str] = DEFAULT_FOCUS_TIERS,
) -> Dict[str, Any]:
    comparison_path = _discover_comparison_path(outdir)
    resolved_taskset = taskset_path or _discover_taskset_path(outdir)
    task_lookup = _load_task_lookup(resolved_taskset) if resolved_taskset else {}
    rows = [_enrich_row(row, outdir=outdir, task_lookup=task_lookup) for row in load_csv_rows(comparison_path)]
    paired = _paired_rows(rows, left_system=left_system, right_system=right_system)

    focus_tier_set = {str(tier) for tier in focus_tiers}
    candidate_cases: List[Dict[str, Any]] = []
    shape_summary: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for left_row, right_row in paired:
        if not right_row.get("_reused_artifact_bool"):
            continue
        tier = str(right_row.get("_reuse_tier") or "none")
        if tier not in focus_tier_set:
            continue
        headroom = _headroom_profile(left_row)
        if headroom["headroom_score"] <= 0:
            continue
        case = _build_case(outdir, left_row, right_row, headroom=headroom)
        candidate_cases.append(case)
        key = (
            case["tier"],
            case["failure_type"],
            case["expected_recovery_path"],
        )
        bucket = shape_summary.setdefault(
            key,
            {
                "tier": case["tier"],
                "failure_type": case["failure_type"],
                "expected_recovery_path": case["expected_recovery_path"],
                "cases": 0,
                "tasks": set(),
                "avg_a3_tool_calls": [],
                "avg_a3_repair_actions": [],
                "avg_a3_user_turns": [],
                "delta_success": [],
                "delta_tool_calls": [],
                "delta_repair_actions": [],
                "delta_user_turns": [],
            },
        )
        bucket["cases"] += 1
        bucket["tasks"].add(case["task_id"])
        bucket["avg_a3_tool_calls"].append(case["a3"]["tool_calls"])
        bucket["avg_a3_repair_actions"].append(case["a3"]["repair_actions"])
        bucket["avg_a3_user_turns"].append(case["a3"]["user_turns"])
        bucket["delta_success"].append(case["deltas"]["success"])
        bucket["delta_tool_calls"].append(case["deltas"]["tool_calls"])
        bucket["delta_repair_actions"].append(case["deltas"]["repair_actions"])
        bucket["delta_user_turns"].append(case["deltas"]["user_turns"])

    summarized_shapes = [
        {
            "tier": stats["tier"],
            "failure_type": stats["failure_type"],
            "expected_recovery_path": stats["expected_recovery_path"],
            "cases": int(stats["cases"]),
            "unique_tasks": len(stats["tasks"]),
            "avg_a3_tool_calls": _mean_or_zero(stats["avg_a3_tool_calls"]),
            "avg_a3_repair_actions": _mean_or_zero(stats["avg_a3_repair_actions"]),
            "avg_a3_user_turns": _mean_or_zero(stats["avg_a3_user_turns"]),
            "delta_success": _mean_or_zero(stats["delta_success"]),
            "delta_tool_calls": _mean_or_zero(stats["delta_tool_calls"]),
            "delta_repair_actions": _mean_or_zero(stats["delta_repair_actions"]),
            "delta_user_turns": _mean_or_zero(stats["delta_user_turns"]),
        }
        for _, stats in sorted(shape_summary.items())
    ]

    recommendation = _recommendation(candidate_cases, summarized_shapes)
    return {
        "outdir": str(outdir),
        "comparison_path": str(comparison_path),
        "taskset_path": str(resolved_taskset) if resolved_taskset else "",
        "left_system": left_system,
        "right_system": right_system,
        "focus_tiers": list(focus_tiers),
        "candidate_case_count": len(candidate_cases),
        "candidate_task_count": len({case["task_id"] for case in candidate_cases}),
        "shape_summary": summarized_shapes,
        "candidate_cases": candidate_cases,
        "recommendation": recommendation,
    }


def render_markdown(analysis: Dict[str, Any]) -> str:
    lines = [
        "# Reuse Headroom Analysis",
        "",
        f"- outdir: `{analysis['outdir']}`",
        f"- comparison: `{analysis['comparison_path']}`",
        f"- focus tiers: `{', '.join(analysis['focus_tiers'])}`",
        f"- candidate cases: `{analysis['candidate_case_count']}`",
        f"- candidate tasks: `{analysis['candidate_task_count']}`",
        "",
        "## Shape Summary",
        "",
        "| tier | failure_type | expected_recovery_path | cases | unique_tasks | avg_a3_tool_calls | avg_a3_repair_actions | avg_a3_user_turns | delta_success | delta_tool_calls | delta_repair_actions | delta_user_turns |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in analysis.get("shape_summary", []):
        lines.append(
            f"| {row['tier']} | {row['failure_type'] or '-'} | {row['expected_recovery_path'] or '-'} | {row['cases']} | {row['unique_tasks']} | {row['avg_a3_tool_calls']:.2f} | {row['avg_a3_repair_actions']:.2f} | {row['avg_a3_user_turns']:.2f} | {row['delta_success']:+.3f} | {row['delta_tool_calls']:+.3f} | {row['delta_repair_actions']:+.3f} | {row['delta_user_turns']:+.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- headline: **{analysis['recommendation']['headline']}**",
            f"- framing: {analysis['recommendation']['paper_framing']}",
            f"- evidence: {analysis['recommendation']['rationale']}",
        ]
    )
    return "\n".join(lines)


def _headroom_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    tool_calls = _metric_value(row, "tool_calls") or 0.0
    repair_actions = _metric_value(row, "repair_actions") or 0.0
    user_turns = _metric_value(row, "user_turns") or 0.0
    signals: List[str] = []
    if repair_actions > 0:
        signals.append("repair")
    if user_turns > 0:
        signals.append("interaction")
    if tool_calls > 2 and repair_actions <= 0 and user_turns <= 0:
        signals.append("long_execution")
    return {
        "headroom_score": len(signals),
        "signals": signals,
    }


def _build_case(
    outdir: Path,
    left_row: Dict[str, Any],
    right_row: Dict[str, Any],
    *,
    headroom: Dict[str, Any],
) -> Dict[str, Any]:
    a3_trace = _load_trace_summary(outdir, left_row.get("trace_path", ""))
    a4_trace = _load_trace_summary(outdir, right_row.get("trace_path", ""))
    return {
        "run_index": int(right_row.get("_run_index", 1) or 1),
        "task_id": str(right_row.get("task_id") or ""),
        "tier": str(right_row.get("_reuse_tier") or "none"),
        "reuse_mode": str(right_row.get("_reuse_mode") or "none"),
        "source_task_id": str(right_row.get("reuse_source_task_id") or ""),
        "source_family": str(right_row.get("_reuse_source_family") or ""),
        "target_family": str(right_row.get("_reuse_target_family") or ""),
        "failure_type": str(right_row.get("failure_type") or ""),
        "primary_failtax": str(right_row.get("primary_failtax") or ""),
        "expected_recovery_path": str(right_row.get("expected_recovery_path") or ""),
        "headroom_signals": list(headroom["signals"]),
        "a3": {
            "success": bool(_metric_value(left_row, "success")),
            "tool_calls": _metric_value(left_row, "tool_calls") or 0.0,
            "repair_actions": _metric_value(left_row, "repair_actions") or 0.0,
            "user_turns": _metric_value(left_row, "user_turns") or 0.0,
            "query_types": a3_trace["query_types"],
            "repair_types": a3_trace["repair_types"],
            "stop_reason": str(left_row.get("stop_reason") or ""),
            "trace_path": str(left_row.get("trace_path") or ""),
        },
        "a4": {
            "success": bool(_metric_value(right_row, "success")),
            "tool_calls": _metric_value(right_row, "tool_calls") or 0.0,
            "repair_actions": _metric_value(right_row, "repair_actions") or 0.0,
            "user_turns": _metric_value(right_row, "user_turns") or 0.0,
            "query_types": a4_trace["query_types"],
            "repair_types": a4_trace["repair_types"],
            "reuse_application": a4_trace["reuse_application"],
            "continuation_hint_kinds": a4_trace["continuation_hint_kinds"],
            "stop_reason": str(right_row.get("stop_reason") or ""),
            "trace_path": str(right_row.get("trace_path") or ""),
        },
        "deltas": {
            "success": (_metric_value(right_row, "success") or 0.0) - (_metric_value(left_row, "success") or 0.0),
            "tool_calls": (_metric_value(right_row, "tool_calls") or 0.0) - (_metric_value(left_row, "tool_calls") or 0.0),
            "repair_actions": (_metric_value(right_row, "repair_actions") or 0.0)
            - (_metric_value(left_row, "repair_actions") or 0.0),
            "user_turns": (_metric_value(right_row, "user_turns") or 0.0) - (_metric_value(left_row, "user_turns") or 0.0),
        },
    }


def _load_trace_summary(outdir: Path, raw_path: str) -> Dict[str, Any]:
    raw = str(raw_path or "").strip()
    if not raw:
        return {"query_types": [], "repair_types": [], "reuse_application": "", "continuation_hint_kinds": []}
    path = Path(raw)
    if not path.is_absolute():
        path = outdir / path
    if not path.exists() or path.is_dir():
        return {"query_types": [], "repair_types": [], "reuse_application": "", "continuation_hint_kinds": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    query_types: List[str] = []
    repair_types: List[str] = []
    for event in payload.get("events", []):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if event_type == "user_query":
            metadata = event.get("metadata", {})
            if isinstance(metadata, dict):
                decision = metadata.get("query_policy_decision", {})
                if isinstance(decision, dict):
                    question_type = str(decision.get("question_type") or "").strip()
                    if question_type:
                        query_types.append(question_type)
        elif event_type == "repair_triggered":
            output = event.get("output", {})
            if isinstance(output, dict):
                repair_type = str(output.get("repair_type") or "").strip()
                if repair_type:
                    repair_types.append(repair_type)
    metadata = payload.get("metadata", {})
    reusable_context = metadata.get("reusable_context", {}) if isinstance(metadata, dict) else {}
    continuation_hints = reusable_context.get("continuation_hints", []) if isinstance(reusable_context, dict) else []
    return {
        "query_types": query_types,
        "repair_types": repair_types,
        "reuse_application": str(reusable_context.get("reuse_application") or ""),
        "continuation_hint_kinds": [
            str(item.get("kind") or "").strip()
            for item in continuation_hints
            if isinstance(item, dict) and str(item.get("kind") or "").strip()
        ],
    }


def _mean_or_zero(values: Iterable[float]) -> float:
    values = list(values)
    return mean(values) if values else 0.0


def _recommendation(candidate_cases: List[Dict[str, Any]], shape_summary: List[Dict[str, Any]]) -> Dict[str, str]:
    if not candidate_cases:
        return {
            "headline": "no reusable headroom cases found",
            "paper_framing": "The current slice does not contain exact or near-match reused cases with observable repair or interaction cost to compress.",
            "rationale": "Exact and same-family reuse mostly land on already-cheap executions, so lack of gain is inconclusive about the reuse mechanism itself.",
        }
    improvements = [
        case for case in candidate_cases
        if case["deltas"]["success"] > 0
        or case["deltas"]["tool_calls"] < 0
        or case["deltas"]["repair_actions"] < 0
        or case["deltas"]["user_turns"] < 0
    ]
    if improvements:
        return {
            "headline": "headroom-sensitive reuse gains present",
            "paper_framing": "Reuse is showing value on the subset of exact or near-match cases that still have repair or interaction cost to compress.",
            "rationale": "At least one high-headroom exact or near-match reused case improves over A3 on success or downstream execution cost.",
        }
    shapes = [row for row in shape_summary if row["avg_a3_repair_actions"] > 0 or row["avg_a3_user_turns"] > 0]
    if shapes:
        return {
            "headline": "reuse remains safe but not yet headroom-seeking",
            "paper_framing": "Frame the current reuse mechanism as safe prior selection, not yet as a cost-reducing continuation policy.",
            "rationale": "Even on exact or near-match cases with observable repair or interaction headroom, A4 matches A3 instead of reducing turns, repairs, or tool calls.",
        }
    return {
        "headline": "reuse mainly lands on low-headroom executions",
        "paper_framing": "The current benchmark slice under-tests reuse utility because the surviving exact or near-match reused cases already sit near the execution floor.",
        "rationale": "Observed exact and near-match reused cases do not carry meaningful repair or interaction cost, so zero gain is expected rather than diagnostic.",
    }
