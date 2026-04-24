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
from typing import Any, Dict, Iterable, List, Optional, Tuple


GOLD_KEYS = {
    "expected_capability_order",
    "expected_dependency_edges",
    "expected_tool_sequence",
    "required_state_slots_by_step",
    "forbidden_shortcuts",
}
PRIMARY_SYSTEM = "a2_planner"
BASELINE_SYSTEM = "a1_recovery"
V2_PROTOCOL = "planner_sensitive_v2"


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


def planner_observability(trace: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    metadata = trace.get("metadata", {}) if isinstance(trace.get("metadata"), dict) else {}
    task_annotations = metadata.get("task_annotations", {}) if isinstance(metadata.get("task_annotations"), dict) else {}
    for value in (
        task_annotations.get("planner_observability"),
        metadata.get("planner_observability"),
    ):
        if isinstance(value, dict):
            return value, "structured"
    return {}, "missing"


def extract_planner_capability_sequence(trace: Dict[str, Any]) -> List[str]:
    observability, _source = planner_observability(trace)
    for key in ("selected_capability_order_final", "selected_capability_order_initial"):
        value = observability.get(key)
        if isinstance(value, list) and value:
            return [str(item) for item in value]
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


def detect_bypass(trace: Dict[str, Any]) -> Dict[str, Any]:
    if not trace:
        return {
            "value": "unknown",
            "known": False,
            "source": "trace_missing",
            "observability": {},
        }
    observability, source = planner_observability(trace)
    if source == "structured" and isinstance(observability.get("planner_bypass_applied"), bool):
        return {
            "value": "true" if observability["planner_bypass_applied"] else "false",
            "known": True,
            "source": "structured",
            "observability": observability,
        }
    text = json.dumps(trace, sort_keys=True)
    if "planner_bypass_applied:minimal_path" in text or '"low_branching_fast_path": true' in text:
        return {"value": "true", "known": True, "source": "legacy_inferred", "observability": observability}
    if "planner_bypass_applied" in text or "low_branching_fast_path" in text:
        return {"value": "true", "known": True, "source": "legacy_inferred", "observability": observability}
    if "planner_mode" in text or "htgp" in text.lower() or "capability" in text.lower():
        return {"value": "false", "known": True, "source": "legacy_inferred", "observability": observability}
    return {"value": "unknown", "known": False, "source": "unknown", "observability": observability}


def _compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _structure_leaks(container: Any, gold: Dict[str, Any]) -> List[str]:
    text = _compact_json(container)
    leaks: List[str] = []
    for key in ("expected_capability_order", "expected_dependency_edges", "expected_tool_sequence"):
        value = gold.get(key)
        if isinstance(value, list) and value:
            serialized = _compact_json(value)
            if serialized in text:
                leaks.append(key)
    return sorted(set(leaks))


def _without_observability(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_observability(child)
            for key, child in value.items()
            if key != "planner_observability"
        }
    if isinstance(value, list):
        return [_without_observability(child) for child in value]
    return value


def detect_hint_leakage(trace: Dict[str, Any], row: Dict[str, str], source_row: Dict[str, Any]) -> Dict[str, Any]:
    visible = source_row.get("planner_visible", {}) if isinstance(source_row.get("planner_visible"), dict) else {}
    gold = source_row.get("scorer_gold", {}) if isinstance(source_row.get("scorer_gold"), dict) else {}
    metadata = trace.get("metadata", {}) if isinstance(trace.get("metadata"), dict) else {}
    metadata_for_leakage = _without_observability(metadata)
    metadata_text = json.dumps(metadata_for_leakage, sort_keys=True)
    row_text = json.dumps(row, sort_keys=True)
    gold_fields_in_trace_metadata = sorted(key for key in GOLD_KEYS if key in metadata_text)
    gold_fields_in_request_hints = []
    gold_fields_in_workflow_benchmark_hints = []
    ordered_gold_structures_in_trace_metadata = _structure_leaks(metadata_for_leakage, gold)
    ordered_gold_structures_in_request_hints: List[str] = []
    ordered_gold_structures_in_workflow_benchmark_hints: List[str] = []
    ordered_gold_structures_in_scored_row = _structure_leaks(row, gold)
    for container in walk_dicts(metadata_for_leakage):
        if "user_style" in container:
            user_style = container.get("user_style")
            text = json.dumps(user_style, sort_keys=True)
            gold_fields_in_request_hints.extend(key for key in GOLD_KEYS if key in text)
            ordered_gold_structures_in_request_hints.extend(_structure_leaks(user_style, gold))
        if "benchmark_hints" in container:
            benchmark_hints = container.get("benchmark_hints")
            text = json.dumps(benchmark_hints, sort_keys=True)
            gold_fields_in_workflow_benchmark_hints.extend(key for key in GOLD_KEYS if key in text)
            ordered_gold_structures_in_workflow_benchmark_hints.extend(_structure_leaks(benchmark_hints, gold))
    overlap_keys = sorted(set(visible.keys()) & set(gold.keys()))
    row_gold_fields = sorted(key for key in GOLD_KEYS if key in row_text)
    ordered_gold_structure_leakage_detected = bool(
        ordered_gold_structures_in_trace_metadata
        or ordered_gold_structures_in_request_hints
        or ordered_gold_structures_in_workflow_benchmark_hints
        or ordered_gold_structures_in_scored_row
    )
    leakage_detected = bool(
        overlap_keys
        or gold_fields_in_trace_metadata
        or gold_fields_in_request_hints
        or gold_fields_in_workflow_benchmark_hints
        or row_gold_fields
        or ordered_gold_structure_leakage_detected
    )
    return {
        "planner_visible_keys": sorted(visible.keys()),
        "scorer_only_keys": sorted(gold.keys()),
        "overlap_keys": overlap_keys,
        "gold_fields_in_trace_metadata": sorted(set(gold_fields_in_trace_metadata)),
        "gold_fields_in_request_hints": sorted(set(gold_fields_in_request_hints)),
        "gold_fields_in_workflow_benchmark_hints": sorted(set(gold_fields_in_workflow_benchmark_hints)),
        "gold_fields_in_scored_row": row_gold_fields,
        "ordered_gold_structures_in_trace_metadata": ordered_gold_structures_in_trace_metadata,
        "ordered_gold_structures_in_request_hints": sorted(set(ordered_gold_structures_in_request_hints)),
        "ordered_gold_structures_in_workflow_benchmark_hints": sorted(set(ordered_gold_structures_in_workflow_benchmark_hints)),
        "ordered_gold_structures_in_scored_row": ordered_gold_structures_in_scored_row,
        "leakage_detected": leakage_detected,
        "ordered_gold_structure_leakage_detected": ordered_gold_structure_leakage_detected,
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
        "protocol": str(source_row.get("planner_sensitive_protocol") or source_row.get("protocol") or "planner_sensitive_v1"),
        "strict_scored_success": strict,
        "fail_stop_rate": fail_stop,
        "ordering_failure_rate": ordering_failure,
        "state_dependency_failure_rate": 1.0 - state_rate,
        "capability_order_correct": order_score,
        "dependency_edge_correct": edge_score,
        "required_state_satisfaction_rate": state_rate,
        "tool_sequence_match": tool_score,
        "planner_bypass": bypass["value"],
        "planner_bypass_known": bool(bypass["known"]),
        "planner_bypass_source": bypass["source"],
        "planner_observability": bypass["observability"],
        "steps_exceed_ideal_rate": steps_exceed_ideal,
        "unresolved_capability_rate": unresolved_capability,
        "tool_calls": safe_int(row.get("tool_calls")),
        "user_queries": safe_int(row.get("user_queries")),
        "actual_tool_sequence": actual_tools,
        "actual_capability_order": actual_order,
        "expected_tool_sequence": expected_tools,
        "expected_capability_order": expected_order,
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
    protocols = sorted({str(row.get("protocol") or "planner_sensitive_v1") for row in scored}) or ["planner_sensitive_v1"]
    protocol = V2_PROTOCOL if V2_PROTOCOL in protocols else protocols[0]
    per_system = {}
    for system, rows in sorted(by_system.items()):
        known_rows = [row for row in rows if row.get("planner_bypass_known")]
        structured_rows = [row for row in rows if row.get("planner_bypass_source") == "structured"]
        per_system[system] = {
            "n": len(rows),
            **{metric: mean([float(row[metric]) for row in rows]) for metric in metrics},
            "planner_bypass_rate": mean([1.0 if row["planner_bypass"] == "true" else 0.0 for row in known_rows])
            if known_rows
            else "unknown",
            "planner_bypass_known_rate": len(known_rows) / len(rows) if rows else 0.0,
            "planner_bypass_structured_rate": len(structured_rows) / len(rows) if rows else 0.0,
            "planner_bypass_unknown_count": sum(1 for row in rows if row["planner_bypass"] == "unknown"),
            "planner_bypass_legacy_inferred_count": sum(1 for row in rows if row["planner_bypass_source"] == "legacy_inferred"),
            "trace_missing_count": sum(1 for row in rows if row["trace_status"] != "ok"),
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

    claim_rows = [row for row in scored if row["system"] in {PRIMARY_SYSTEM, BASELINE_SYSTEM}]
    leakage_rows = [row for row in claim_rows if row["hint_leakage"]["leakage_detected"]]
    ordered_leakage_rows = [
        row for row in claim_rows if row["hint_leakage"].get("ordered_gold_structure_leakage_detected")
    ]
    family_deltas: Dict[str, float] = {}
    family_positive_count = 0
    for family, system_rows in by_family_system.items():
        a2_rows = system_rows.get(PRIMARY_SYSTEM, [])
        a1_rows = system_rows.get(BASELINE_SYSTEM, [])
        family_delta = mean([float(row["strict_scored_success"]) for row in a2_rows]) - mean(
            [float(row["strict_scored_success"]) for row in a1_rows]
        )
        family_deltas[family] = family_delta
        if family_delta > 0:
            family_positive_count += 1
    acceptance = {
        "a2_success_delta_ge_20pp": isinstance(delta("strict_scored_success"), float) and delta("strict_scored_success") >= 0.20,
        "paired_wins_exceed_losses": pair_outcomes["wins"] > pair_outcomes["losses"],
        "capability_order_delta_ge_20pp": isinstance(delta("capability_order_correct"), float) and delta("capability_order_correct") >= 0.20,
        "dependency_edge_delta_ge_20pp": isinstance(delta("dependency_edge_correct"), float) and delta("dependency_edge_correct") >= 0.20,
        "no_hint_leakage_detected": not leakage_rows,
        "no_ordered_gold_structure_leakage_detected": not ordered_leakage_rows,
        "a2_not_cost_explosion": float(a2.get("tool_calls", 0.0) or 0.0) <= max(float(a1.get("tool_calls", 0.0) or 0.0) * 1.5, float(a1.get("tool_calls", 0.0) or 0.0) + 2.0),
    }
    a2_bypass_rate = a2.get("planner_bypass_rate", "unknown")
    a2_bypass_known_rate = float(a2.get("planner_bypass_known_rate", 0.0) or 0.0)
    acceptance["source_task_count_ge_40"] = source_count >= 40
    acceptance["family_positive_count_ge_3"] = family_positive_count >= 3
    acceptance["planner_bypass_known_rate_ge_90pp"] = a2_bypass_known_rate >= 0.90 if protocol == V2_PROTOCOL else True
    acceptance["planner_bypass_rate_controlled"] = (
        isinstance(a2_bypass_rate, (int, float)) and float(a2_bypass_rate) <= 0.25
    ) if protocol == V2_PROTOCOL else (a2_bypass_rate == "unknown" or float(a2_bypass_rate) <= 0.25)
    effect_size_evidence_ready = all(
        bool(value)
        for key, value in acceptance.items()
        if key not in {"source_task_count_ge_40", "family_positive_count_ge_3", "planner_bypass_known_rate_ge_90pp"}
    )
    v2_promotion_ready = protocol == V2_PROTOCOL and all(bool(value) for value in acceptance.values())
    strong_claim_allowed = v2_promotion_ready
    return {
        "protocol": protocol,
        "source_task_count": source_count,
        "primary_comparison": f"{PRIMARY_SYSTEM}_vs_{BASELINE_SYSTEM}",
        "per_system": per_system,
        "per_family": per_family,
        "family_deltas": family_deltas,
        "family_positive_count": family_positive_count,
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
        "v2_promotion_ready": v2_promotion_ready,
        "paper_safe_reason": "passes effect-size gates but requires >=40 tasks before strong planner claim"
        if effect_size_evidence_ready and source_count < 40
        else "all gates and size threshold passed"
        if strong_claim_allowed
        else "one or more effect-size, leakage, bypass, or cost gates failed",
        "leakage_task_count": len(leakage_rows),
        "ordered_gold_structure_leakage_task_count": len(ordered_leakage_rows),
    }


def leakage_report(scored: List[Dict[str, Any]], source_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    task_reports = {
        row["task_id"]: row["hint_leakage"]
        for row in scored
        if row["system"] == PRIMARY_SYSTEM or row["system"] == BASELINE_SYSTEM
    }
    any_leakage = any(report.get("leakage_detected") for report in task_reports.values())
    any_ordered_leakage = any(report.get("ordered_gold_structure_leakage_detected") for report in task_reports.values())
    protocols = sorted({str(row.get("planner_sensitive_protocol") or row.get("protocol") or "planner_sensitive_v1") for row in source_rows})
    return {
        "protocol": V2_PROTOCOL if V2_PROTOCOL in protocols else (protocols[0] if protocols else "planner_sensitive_v1"),
        "sample_count": len(source_rows),
        "task_reports": task_reports,
        "leakage_detected": any_leakage,
        "ordered_gold_structure_leakage_detected": any_ordered_leakage,
    }


def classify_failure(row: Dict[str, Any]) -> Tuple[str, str]:
    if row.get("trace_status") != "ok":
        return "runtime_execution_gap", "runtime_semantic_mock"
    expected_order = row.get("expected_capability_order") or []
    actual_order = row.get("actual_capability_order") or []
    expected_tools = row.get("expected_tool_sequence") or []
    actual_tools = row.get("actual_tool_sequence") or []
    observability = row.get("planner_observability") if isinstance(row.get("planner_observability"), dict) else {}
    unresolved = observability.get("unresolved_capabilities") if isinstance(observability.get("unresolved_capabilities"), list) else []
    if unresolved:
        return "capability_intent_gap", "capability_intent_rules"
    if expected_order and actual_order and actual_order[: len(expected_order)] != expected_order:
        return "capability_intent_gap", "capability_intent_rules"
    if expected_tools and actual_tools and actual_tools[: len(expected_tools)] != expected_tools:
        return "binder_selection_gap", "binder_rules"
    if not actual_tools:
        return "runtime_execution_gap", "runtime_semantic_mock"
    if float(row.get("tool_sequence_match", 0.0) or 0.0) < 1.0:
        return "tool_semantic_tag_gap", "dataset_prompt_or_tool_tags"
    return "scorer_expectation_mismatch", "scorer_expectation"


def family_diagnostics(scored: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_family_system: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in scored:
        by_family_system[row["family"]][row["system"]].append(row)
    families: Dict[str, Any] = {}
    for family, system_rows in sorted(by_family_system.items()):
        families[family] = {}
        for system, rows in sorted(system_rows.items()):
            classifications: Dict[str, int] = defaultdict(int)
            fix_scopes: Dict[str, int] = defaultdict(int)
            examples: List[Dict[str, Any]] = []
            for row in rows:
                if float(row.get("strict_scored_success", 0.0) or 0.0) >= 1.0:
                    continue
                classification, fix_scope = classify_failure(row)
                classifications[classification] += 1
                fix_scopes[fix_scope] += 1
                if len(examples) < 5:
                    observability = row.get("planner_observability") if isinstance(row.get("planner_observability"), dict) else {}
                    examples.append(
                        {
                            "task_id": row.get("task_id"),
                            "run_index": row.get("run_index"),
                            "expected_capability_order": row.get("expected_capability_order"),
                            "actual_capability_order": row.get("actual_capability_order"),
                            "expected_tool_sequence": row.get("expected_tool_sequence"),
                            "actual_tool_sequence": row.get("actual_tool_sequence"),
                            "selected_capability_order_initial": observability.get("selected_capability_order_initial", "unavailable"),
                            "selected_capability_order_final": observability.get("selected_capability_order_final", "unavailable"),
                            "bound_tool_order": observability.get("bound_tool_order", "unavailable"),
                            "unresolved_capabilities": observability.get("unresolved_capabilities", "unavailable"),
                            "planner_bypass": row.get("planner_bypass"),
                            "planner_bypass_source": row.get("planner_bypass_source"),
                            "trace_status": row.get("trace_status"),
                            "failure_classification": classification,
                            "recommended_fix_scope": fix_scope,
                        }
                    )
            families[family][system] = {
                "n": len(rows),
                "strict_scored_success": mean([float(row["strict_scored_success"]) for row in rows]),
                "classification_counts": dict(sorted(classifications.items())),
                "recommended_fix_scope_counts": dict(sorted(fix_scopes.items())),
                "examples": examples,
            }
    return {"families": families}


def write_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Planner-Sensitive Summary",
        "",
        f"- Protocol: `{summary['protocol']}`",
        f"- Primary comparison: `{summary['primary_comparison']}`",
        f"- Source task count: `{summary['source_task_count']}`",
        f"- Effect-size evidence ready: `{summary['effect_size_evidence_ready']}`",
        f"- Strong claim allowed: `{summary['strong_claim_allowed']}`",
        f"- V2 promotion ready: `{summary.get('v2_promotion_ready')}`",
        f"- Paper-safe planner claim: `{summary['paper_safe_for_planner_claim']}`",
        f"- Family positive count: `{summary.get('family_positive_count')}`",
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
        lines.append(f"- `{system}`: success={metrics.get('strict_scored_success')}, capability_order={metrics.get('capability_order_correct')}, dependency_edges={metrics.get('dependency_edge_correct')}, tool_calls={metrics.get('tool_calls')}, bypass={metrics.get('planner_bypass_rate')}, bypass_known={metrics.get('planner_bypass_known_rate')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_leakage_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Planner-Sensitive Hint Leakage Report",
        "",
        f"- Protocol: `{report['protocol']}`",
        f"- Sample count: `{report['sample_count']}`",
        f"- Leakage detected: `{report['leakage_detected']}`",
        f"- Ordered gold structure leakage detected: `{report.get('ordered_gold_structure_leakage_detected')}`",
        "",
        "## Task Reports",
        "",
    ]
    for task_id, task_report in sorted(report["task_reports"].items()):
        lines.append(f"- `{task_id}`: leakage={task_report.get('leakage_detected')}, overlap={task_report.get('overlap_keys')}, trace_gold={task_report.get('gold_fields_in_trace_metadata')}, request_hints={task_report.get('gold_fields_in_request_hints')}, benchmark_hints={task_report.get('gold_fields_in_workflow_benchmark_hints')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_family_diagnostics_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = ["# Planner-Sensitive Family Diagnostics", ""]
    for family, systems in sorted(report.get("families", {}).items()):
        lines.extend([f"## `{family}`", ""])
        for system, payload in sorted(systems.items()):
            lines.append(
                f"- `{system}`: success={payload.get('strict_scored_success')}, "
                f"classifications={payload.get('classification_counts')}, "
                f"recommended_fix_scope={payload.get('recommended_fix_scope_counts')}"
            )
            for example in payload.get("examples", [])[:3]:
                lines.append(
                    f"- example `{example.get('task_id')}` run={example.get('run_index')}: "
                    f"classification={example.get('failure_classification')}, "
                    f"fix={example.get('recommended_fix_scope')}, "
                    f"expected_caps={example.get('expected_capability_order')}, "
                    f"actual_caps={example.get('actual_capability_order')}, "
                    f"expected_tools={example.get('expected_tool_sequence')}, "
                    f"actual_tools={example.get('actual_tool_sequence')}"
                )
        lines.append("")
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
    diagnostics = family_diagnostics(scored_rows)
    (outdir / "planner_sensitive_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (outdir / "hint_leakage_report.json").write_text(json.dumps(leakage, indent=2), encoding="utf-8")
    (outdir / "planner_sensitive_family_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    write_markdown(summary, outdir / "planner_sensitive_summary.md")
    write_leakage_markdown(leakage, outdir / "hint_leakage_report.md")
    write_family_diagnostics_markdown(diagnostics, outdir / "planner_sensitive_family_diagnostics.md")
    print(f"planner-sensitive summary: {outdir / 'planner_sensitive_summary.json'}")
    print(f"hint leakage report: {outdir / 'hint_leakage_report.json'}")
    print(f"family diagnostics: {outdir / 'planner_sensitive_family_diagnostics.json'}")


if __name__ == "__main__":
    main()
