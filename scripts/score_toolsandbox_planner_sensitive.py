#!/usr/bin/env python3
"""Score ToolSandbox planner-sensitive protocol bundles.

This scorer is intentionally separate from the generic ToolSandbox scorer. The
generic benchmark result says whether a run satisfied the task contract; this
script checks whether HTGP's structural path is actually better than the A1
execution/recovery proxy without leaking scorer-only gold hints to the planner.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


GOLD_KEYS = {
    "expected_capability_order",
    "expected_dependency_edges",
    "expected_tool_sequence",
    "required_state_slots_by_step",
    "forbidden_shortcuts",
}
PRIMARY_SYSTEM = "a2_planner"
BASELINE_SYSTEM = "a1_recovery"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any) -> float:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return 1.0
        if normalized == "false":
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def task_id(row: Dict[str, Any], idx: int) -> str:
    return str(row.get("task_id") or row.get("sample_id") or row.get("name") or f"planner_sensitive_{idx:03d}")


def trace_path(row: Dict[str, str], root: Path) -> Path:
    raw_path = Path(str(row.get("trace_path") or ""))
    if raw_path.is_absolute():
        return raw_path
    return root / raw_path


def load_trace(row: Dict[str, str], root: Path) -> Tuple[Dict[str, Any], str]:
    path = trace_path(row, root)
    if not path.exists():
        return {}, "trace_missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), "ok"
    except json.JSONDecodeError:
        return {}, "trace_unreadable"


def walk_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def extract_tool_sequence(trace: Dict[str, Any], row: Dict[str, str]) -> List[str]:
    tools: List[str] = []
    for event in trace.get("events", []) if isinstance(trace.get("events"), list) else []:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if event_type not in {"tool_call", "tool_result", "step_completed"}:
            continue
        tool_id = event.get("tool_id")
        if not tool_id and isinstance(event.get("output"), dict):
            tool_id = event["output"].get("tool_id")
        if tool_id:
            tool = str(tool_id)
            if not tools or tools[-1] != tool:
                tools.append(tool)
    if not tools:
        chosen = str(row.get("chosen_tool") or "").strip()
        if chosen:
            tools.append(chosen)
    return tools


def infer_capability(tool_id: str, tool_specs: Dict[str, Dict[str, Any]]) -> str:
    spec = tool_specs.get(tool_id, {})
    normalized_tool_id = tool_id.lower()
    id_rules = [
        ("cap_write", ("writer", "write", "publish", "report")),
        ("cap_summarize", ("summary", "summarize", "brief")),
        ("cap_merge", ("merge", "merger", "synth")),
        ("cap_select", ("branch", "select", "route")),
        ("cap_verify", ("verify", "verifier", "confirm")),
        ("cap_modify", ("modify", "modifier", "patch", "update", "execute")),
        ("cap_check", ("check", "checker", "inspect", "audit")),
        ("cap_retrieve", ("retrieve", "retriever", "lookup", "fetch", "source")),
    ]
    for capability, needles in id_rules:
        if any(needle in normalized_tool_id for needle in needles):
            return capability
    text = " ".join(
        [
            tool_id,
            str(spec.get("description") or ""),
            " ".join(str(item) for item in spec.get("semantic_tags", []) or []),
            " ".join(str(item) for item in spec.get("affordances", []) or []),
        ]
    ).lower()
    rules = [
        ("cap_summarize", ("summarize", "summary", "digest", "abstract", "brief")),
        ("cap_write", ("write", "writer", "publish", "compose", "draft", "store", "save", "report")),
        ("cap_check", ("check", "inspect", "validate", "verify", "audit", "scan")),
        ("cap_modify", ("modify", "update", "patch", "edit", "change", "toggle")),
        ("cap_verify", ("verify", "confirm", "test", "validate", "assert")),
        ("cap_select", ("branch", "select", "route", "choose", "classify")),
        ("cap_merge", ("merge", "join", "combine", "aggregate", "synthesize")),
        ("cap_retrieve", ("retrieve", "search", "lookup", "fetch", "read", "collect", "source")),
    ]
    for capability, needles in rules:
        if any(needle in text for needle in needles):
            return capability
    return "cap_unknown"


def capability_sequence_from_tools(tools: List[str], tool_specs: Dict[str, Dict[str, Any]]) -> List[str]:
    sequence: List[str] = []
    for tool in tools:
        capability = infer_capability(tool, tool_specs)
        if capability == "cap_unknown":
            continue
        if not sequence or sequence[-1] != capability:
            sequence.append(capability)
    return sequence


def extract_planner_capability_sequence(trace: Dict[str, Any]) -> List[str]:
    metadata = trace.get("metadata", {}) if isinstance(trace.get("metadata"), dict) else {}
    for dict_value in walk_dicts(metadata):
        for key in ("capability_order", "planned_capability_order", "capability_sequence"):
            value = dict_value.get(key)
            if isinstance(value, list) and value:
                return [str(item) for item in value]
    return []


def edges_from_order(order: List[str]) -> List[List[str]]:
    return [[left, right] for left, right in zip(order, order[1:])]


def edge_match_rate(actual_edges: List[List[str]], expected_edges: List[List[str]]) -> float:
    if not expected_edges:
        return 1.0
    actual = {tuple(edge) for edge in actual_edges}
    expected = {tuple(edge) for edge in expected_edges}
    return len(actual & expected) / len(expected)


def order_correct(actual_order: List[str], expected_order: List[str]) -> float:
    if not expected_order:
        return 1.0
    return 1.0 if actual_order[: len(expected_order)] == expected_order else 0.0


def sequence_match(actual_tools: List[str], expected_tools: List[str]) -> float:
    if not expected_tools:
        return 1.0
    return 1.0 if actual_tools[: len(expected_tools)] == expected_tools else 0.0


def required_state_rate(actual_order: List[str], required_by_step: Dict[str, Any]) -> float:
    if not required_by_step:
        return 1.0
    satisfied = 0
    total = 0
    positions = {cap: idx for idx, cap in enumerate(actual_order)}
    for step_capability, requirements in required_by_step.items():
        if not isinstance(requirements, list):
            continue
        total += len(requirements)
        step_position = positions.get(str(step_capability), 10_000)
        for required_capability in requirements:
            if positions.get(str(required_capability), 10_000) < step_position:
                satisfied += 1
    return satisfied / total if total else 1.0


def detect_bypass(trace: Dict[str, Any]) -> str:
    if not trace:
        return "unknown"
    text = json.dumps(trace, sort_keys=True)
    if "planner_bypass_applied:minimal_path" in text or '"low_branching_fast_path": true' in text:
        return "true"
    if "planner_bypass_applied" in text or "low_branching_fast_path" in text:
        return "true"
    if "planner_mode" in text or "htgp" in text.lower() or "capability" in text.lower():
        return "false"
    return "unknown"


def detect_hint_leakage(trace: Dict[str, Any], row: Dict[str, str], source_row: Dict[str, Any]) -> Dict[str, Any]:
    visible = source_row.get("planner_visible", {}) if isinstance(source_row.get("planner_visible"), dict) else {}
    gold = source_row.get("scorer_gold", {}) if isinstance(source_row.get("scorer_gold"), dict) else {}
    metadata = trace.get("metadata", {}) if isinstance(trace.get("metadata"), dict) else {}
    metadata_text = json.dumps(metadata, sort_keys=True)
    row_text = json.dumps(row, sort_keys=True)
    gold_fields_in_trace_metadata = sorted(key for key in GOLD_KEYS if key in metadata_text)
    gold_fields_in_request_hints = []
    gold_fields_in_workflow_benchmark_hints = []
    for container in walk_dicts(metadata):
        if "user_style" in container:
            text = json.dumps(container.get("user_style"), sort_keys=True)
            gold_fields_in_request_hints.extend(key for key in GOLD_KEYS if key in text)
        if "benchmark_hints" in container:
            text = json.dumps(container.get("benchmark_hints"), sort_keys=True)
            gold_fields_in_workflow_benchmark_hints.extend(key for key in GOLD_KEYS if key in text)
    overlap_keys = sorted(set(visible.keys()) & set(gold.keys()))
    row_gold_fields = sorted(key for key in GOLD_KEYS if key in row_text)
    leakage_detected = bool(
        overlap_keys
        or gold_fields_in_trace_metadata
        or gold_fields_in_request_hints
        or gold_fields_in_workflow_benchmark_hints
        or row_gold_fields
    )
    return {
        "planner_visible_keys": sorted(visible.keys()),
        "scorer_only_keys": sorted(gold.keys()),
        "overlap_keys": overlap_keys,
        "gold_fields_in_trace_metadata": sorted(set(gold_fields_in_trace_metadata)),
        "gold_fields_in_request_hints": sorted(set(gold_fields_in_request_hints)),
        "gold_fields_in_workflow_benchmark_hints": sorted(set(gold_fields_in_workflow_benchmark_hints)),
        "gold_fields_in_scored_row": row_gold_fields,
        "leakage_detected": leakage_detected,
    }


def score_row(row: Dict[str, str], source_row: Dict[str, Any], root: Path) -> Dict[str, Any]:
    visible = source_row.get("planner_visible", {}) if isinstance(source_row.get("planner_visible"), dict) else {}
    gold = source_row.get("scorer_gold", {}) if isinstance(source_row.get("scorer_gold"), dict) else {}
    tool_specs = {
        str(tool.get("tool_id") or tool.get("name")): tool
        for tool in visible.get("candidate_tools", [])
        if isinstance(tool, dict)
    }
    trace, trace_status = load_trace(row, root)
    actual_tools = extract_tool_sequence(trace, row)
    proxy_order = capability_sequence_from_tools(actual_tools, tool_specs)
    planner_order = extract_planner_capability_sequence(trace)
    actual_order = planner_order if row.get("system") == PRIMARY_SYSTEM and planner_order else proxy_order
    expected_order = [str(item) for item in gold.get("expected_capability_order", []) or []]
    expected_edges = [[str(item[0]), str(item[1])] for item in gold.get("expected_dependency_edges", []) or [] if isinstance(item, list) and len(item) == 2]
    expected_tools = [str(item) for item in gold.get("expected_tool_sequence", []) or []]
    actual_edges = edges_from_order(actual_order)
    order_score = order_correct(actual_order, expected_order)
    edge_score = edge_match_rate(actual_edges, expected_edges)
    tool_score = sequence_match(actual_tools, expected_tools)
    state_rate = required_state_rate(actual_order, gold.get("required_state_slots_by_step", {}) if isinstance(gold.get("required_state_slots_by_step"), dict) else {})
    raw_success = max(
        safe_float(row.get("raw_execution_success")),
        safe_float(row.get("raw_success")),
        safe_float(row.get("raw_trace_success")),
        safe_float(row.get("success")),
    )
    forbidden_shortcuts = [str(item) for item in gold.get("forbidden_shortcuts", []) or []]
    trace_text = json.dumps(trace, sort_keys=True) if trace else ""
    shortcut_seen = any(shortcut and shortcut in trace_text for shortcut in forbidden_shortcuts)
    strict = 1.0 if raw_success >= 1.0 and order_score >= 1.0 and edge_score >= 1.0 and tool_score >= 1.0 and state_rate >= 1.0 and not shortcut_seen else 0.0
    fail_stop = 1.0 if str(row.get("stop_reason") or "").strip() not in {"", "success_criteria_satisfied"} and strict < 1.0 else 0.0
    ordering_failure = 1.0 - order_score
    state_rate = required_state_rate(actual_order, gold.get("required_state_slots_by_step", {}) if isinstance(gold.get("required_state_slots_by_step"), dict) else {})
    bypass = detect_bypass(trace)
    ideal_steps = max(len(expected_tools), len(expected_order), 1)
    steps_exceed_ideal = 1.0 if safe_int(row.get("tool_calls")) > ideal_steps else 0.0
    unresolved_capability = 1.0 if "cap_unknown" in capability_sequence_from_tools(actual_tools, tool_specs) else 0.0
    return {
        "task_id": str(row.get("task_id") or source_row.get("task_id") or ""),
        "run_index": safe_int(row.get("run_index")),
        "system": str(row.get("system") or ""),
        "family": str(source_row.get("family") or source_row.get("task_family") or ""),
        "strict_scored_success": strict,
        "fail_stop_rate": fail_stop,
        "ordering_failure_rate": ordering_failure,
        "state_dependency_failure_rate": 1.0 - state_rate,
        "capability_order_correct": order_score,
        "dependency_edge_correct": edge_score,
        "required_state_satisfaction_rate": state_rate,
        "tool_sequence_match": tool_score,
        "planner_bypass": bypass,
        "steps_exceed_ideal_rate": steps_exceed_ideal,
        "unresolved_capability_rate": unresolved_capability,
        "tool_calls": safe_int(row.get("tool_calls")),
        "user_queries": safe_int(row.get("user_queries")),
        "actual_tool_sequence": actual_tools,
        "actual_capability_order": actual_order,
        "trace_status": trace_status,
        "trace_path": str(row.get("trace_path") or ""),
        "hint_leakage": detect_hint_leakage(trace, row, source_row),
    }


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate(scored: List[Dict[str, Any]], *, source_count: int) -> Dict[str, Any]:
    by_system: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_family_system: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in scored:
        by_system[row["system"]].append(row)
        by_family_system[row["family"]][row["system"]].append(row)

    metrics = [
        "strict_scored_success",
        "fail_stop_rate",
        "ordering_failure_rate",
        "state_dependency_failure_rate",
        "capability_order_correct",
        "dependency_edge_correct",
        "required_state_satisfaction_rate",
        "tool_sequence_match",
        "steps_exceed_ideal_rate",
        "unresolved_capability_rate",
        "tool_calls",
        "user_queries",
    ]
    per_system = {
        system: {
            "n": len(rows),
            **{metric: mean([float(row[metric]) for row in rows]) for metric in metrics},
            "planner_bypass_rate": mean([1.0 if row["planner_bypass"] == "true" else 0.0 for row in rows if row["planner_bypass"] != "unknown"])
            if any(row["planner_bypass"] != "unknown" for row in rows)
            else "unknown",
            "planner_bypass_unknown_count": sum(1 for row in rows if row["planner_bypass"] == "unknown"),
            "trace_missing_count": sum(1 for row in rows if row["trace_status"] != "ok"),
        }
        for system, rows in sorted(by_system.items())
    }
    per_family = {
        family: {
            system: {
                "n": len(rows),
                "strict_scored_success": mean([float(row["strict_scored_success"]) for row in rows]),
                "capability_order_correct": mean([float(row["capability_order_correct"]) for row in rows]),
                "dependency_edge_correct": mean([float(row["dependency_edge_correct"]) for row in rows]),
            }
            for system, rows in sorted(system_rows.items())
        }
        for family, system_rows in sorted(by_family_system.items())
    }
    pair_outcomes = {"wins": 0, "losses": 0, "ties": 0, "pairs": 0}
    paired_index: Dict[Tuple[str, int], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in scored:
        paired_index[(row["task_id"], row["run_index"])][row["system"]] = row
    for system_rows in paired_index.values():
        if PRIMARY_SYSTEM not in system_rows or BASELINE_SYSTEM not in system_rows:
            continue
        delta = float(system_rows[PRIMARY_SYSTEM]["strict_scored_success"]) - float(system_rows[BASELINE_SYSTEM]["strict_scored_success"])
        pair_outcomes["pairs"] += 1
        if delta > 0:
            pair_outcomes["wins"] += 1
        elif delta < 0:
            pair_outcomes["losses"] += 1
        else:
            pair_outcomes["ties"] += 1

    a2 = per_system.get(PRIMARY_SYSTEM, {})
    a1 = per_system.get(BASELINE_SYSTEM, {})
    def delta(metric: str) -> Any:
        left = a2.get(metric)
        right = a1.get(metric)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return float(left) - float(right)
        return "unknown"

    leakage_rows = [row for row in scored if row["hint_leakage"]["leakage_detected"]]
    acceptance = {
        "a2_success_delta_ge_20pp": isinstance(delta("strict_scored_success"), float) and delta("strict_scored_success") >= 0.20,
        "paired_wins_exceed_losses": pair_outcomes["wins"] > pair_outcomes["losses"],
        "capability_order_delta_ge_20pp": isinstance(delta("capability_order_correct"), float) and delta("capability_order_correct") >= 0.20,
        "dependency_edge_delta_ge_20pp": isinstance(delta("dependency_edge_correct"), float) and delta("dependency_edge_correct") >= 0.20,
        "no_hint_leakage_detected": not leakage_rows,
        "a2_not_cost_explosion": float(a2.get("tool_calls", 0.0) or 0.0) <= max(float(a1.get("tool_calls", 0.0) or 0.0) * 1.5, float(a1.get("tool_calls", 0.0) or 0.0) + 2.0),
    }
    a2_bypass_rate = a2.get("planner_bypass_rate", "unknown")
    acceptance["planner_bypass_rate_controlled"] = a2_bypass_rate == "unknown" or float(a2_bypass_rate) <= 0.25
    effect_size_evidence_ready = all(bool(value) for value in acceptance.values())
    strong_claim_allowed = effect_size_evidence_ready and source_count >= 40
    return {
        "protocol": "planner_sensitive_v1",
        "source_task_count": source_count,
        "primary_comparison": f"{PRIMARY_SYSTEM}_vs_{BASELINE_SYSTEM}",
        "per_system": per_system,
        "per_family": per_family,
        "paired_wins_losses_ties": pair_outcomes,
        "deltas": {
            "a2_minus_a1_success_delta": delta("strict_scored_success"),
            "a2_minus_a1_capability_order_correct": delta("capability_order_correct"),
            "a2_minus_a1_dependency_edge_correct": delta("dependency_edge_correct"),
            "a2_minus_a1_tool_sequence_match": delta("tool_sequence_match"),
        },
        "acceptance_checks": acceptance,
        "effect_size_evidence_ready": effect_size_evidence_ready,
        "strong_claim_allowed": strong_claim_allowed,
        "paper_safe_for_planner_claim": strong_claim_allowed,
        "paper_safe_reason": "passes effect-size gates but requires >=40 tasks before strong planner claim"
        if effect_size_evidence_ready and source_count < 40
        else "all gates and size threshold passed"
        if strong_claim_allowed
        else "one or more effect-size, leakage, bypass, or cost gates failed",
        "leakage_task_count": len(leakage_rows),
    }


def leakage_report(scored: List[Dict[str, Any]], source_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    task_reports = {
        row["task_id"]: row["hint_leakage"]
        for row in scored
        if row["system"] == PRIMARY_SYSTEM or row["system"] == BASELINE_SYSTEM
    }
    any_leakage = any(report.get("leakage_detected") for report in task_reports.values())
    return {
        "protocol": "planner_sensitive_v1",
        "sample_count": len(source_rows),
        "task_reports": task_reports,
        "leakage_detected": any_leakage,
    }


def write_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Planner-Sensitive Summary",
        "",
        f"- Protocol: `{summary['protocol']}`",
        f"- Primary comparison: `{summary['primary_comparison']}`",
        f"- Source task count: `{summary['source_task_count']}`",
        f"- Effect-size evidence ready: `{summary['effect_size_evidence_ready']}`",
        f"- Strong claim allowed: `{summary['strong_claim_allowed']}`",
        f"- Paper-safe planner claim: `{summary['paper_safe_for_planner_claim']}`",
        f"- Reason: {summary['paper_safe_reason']}",
        "",
        "## Deltas",
        "",
    ]
    for key, value in summary["deltas"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Paired Wins/Losses/Ties", ""])
    for key, value in summary["paired_wins_losses_ties"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Acceptance Checks", ""])
    for key, value in summary["acceptance_checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Per-System Metrics", ""])
    for system, metrics in summary["per_system"].items():
        lines.append(f"- `{system}`: success={metrics.get('strict_scored_success')}, capability_order={metrics.get('capability_order_correct')}, dependency_edges={metrics.get('dependency_edge_correct')}, tool_calls={metrics.get('tool_calls')}, bypass={metrics.get('planner_bypass_rate')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_leakage_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Planner-Sensitive Hint Leakage Report",
        "",
        f"- Protocol: `{report['protocol']}`",
        f"- Sample count: `{report['sample_count']}`",
        f"- Leakage detected: `{report['leakage_detected']}`",
        "",
        "## Task Reports",
        "",
    ]
    for task_id, task_report in sorted(report["task_reports"].items()):
        lines.append(f"- `{task_id}`: leakage={task_report.get('leakage_detected')}, overlap={task_report.get('overlap_keys')}, trace_gold={task_report.get('gold_fields_in_trace_metadata')}, request_hints={task_report.get('gold_fields_in_request_hints')}, benchmark_hints={task_report.get('gold_fields_in_workflow_benchmark_hints')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score ToolSandbox planner-sensitive protocol outputs")
    parser.add_argument("--source", required=True)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    root = Path.cwd()
    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = root / source_path
    comparison_path = Path(args.comparison)
    if not comparison_path.is_absolute():
        comparison_path = root / comparison_path
    outdir = Path(args.outdir)
    if not outdir.is_absolute():
        outdir = root / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    source_rows = load_jsonl(source_path)
    source_by_id = {task_id(row, idx): row for idx, row in enumerate(source_rows, start=1)}
    scored_rows: List[Dict[str, Any]] = []
    for row in load_csv(comparison_path):
        source_row = source_by_id.get(str(row.get("task_id") or ""))
        if source_row is None:
            continue
        scored_rows.append(score_row(row, source_row, root))

    summary = aggregate(scored_rows, source_count=len(source_rows))
    leakage = leakage_report(scored_rows, source_rows)
    (outdir / "planner_sensitive_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (outdir / "hint_leakage_report.json").write_text(json.dumps(leakage, indent=2), encoding="utf-8")
    write_markdown(summary, outdir / "planner_sensitive_summary.md")
    write_leakage_markdown(leakage, outdir / "hint_leakage_report.md")
    print(f"planner-sensitive summary: {outdir / 'planner_sensitive_summary.json'}")
    print(f"hint leakage report: {outdir / 'hint_leakage_report.json'}")


if __name__ == "__main__":
    main()
