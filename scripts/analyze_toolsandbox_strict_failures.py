#!/usr/bin/env python3
"""Analyze strict ToolSandbox core failures without mutating runtime behavior."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


STRICT_SYSTEMS = [
    "s0_baseline",
    "s1_recovery",
    "s2_planner_overlay",
    "s3_interaction_overlay",
    "s4_reuse_overlay",
]

GENERIC_FIXES = {
    "runtime_execution_failure": "Inspect generic executor/recovery failure handling before changing planner or interaction layers.",
    "raw_success_but_strict_fail": "Compare executor completion with benchmark-facing success checks; improve generic final-response or verification alignment only if the mismatch is systematic.",
    "missing_or_unasked_user_input": "Route unresolved required information into generic interaction query policy and semantic decoding.",
    "state_precondition_gap": "Use generic state/precondition metadata to patch, confirm, or ask for missing state slots before retry.",
    "recovery_trigger_gap": "Improve generic recovery trigger detection and repair eligibility telemetry for recoverable failures.",
    "planner_hint_gap": "Expose failure-activated planner hints for recovery or suffix replan only after a failure or preflight block.",
    "interaction_trigger_or_decoder_gap": "Expand generic interaction triggers and typed reply decoding for missing information, ambiguity, approval, and state confirmation.",
    "benchmark_final_response_mismatch": "Audit generic benchmark-facing final-response and milestone/summary alignment without adding scenario-specific rules.",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value).strip() or "0"))
    except Exception:
        return 0


def _safe_json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(str(value or "[]"))
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_trace(path: str, *, root: Path) -> Dict[str, Any]:
    if not path:
        return {}
    trace_path = Path(path)
    if not trace_path.is_absolute():
        trace_path = root / trace_path
    try:
        with trace_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        return {"_trace_load_error": str(exc), "events": []}
    return payload if isinstance(payload, dict) else {"events": payload if isinstance(payload, list) else []}


def _append_unique(items: List[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def extract_trace_evidence(trace_payload: Dict[str, Any]) -> Dict[str, Any]:
    events = trace_payload.get("events", [])
    if not isinstance(events, list):
        events = []

    repair_types: List[str] = []
    repair_applied = False
    repair_blocked: List[str] = []
    missing_input_keys: List[str] = []
    missing_assets: List[str] = []
    raw_message_patterns: List[str] = []
    user_query_count = 0
    user_reply_count = 0
    tool_error_count = 0
    final_stop_reason = ""

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        output = event.get("output") if isinstance(event.get("output"), dict) else {}
        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}

        if event_type == "user_query":
            user_query_count += 1
        if event_type == "user_reply":
            user_reply_count += 1
        if event_type == "repair_triggered":
            _append_unique(repair_types, output.get("repair_type"))
            for key in output.get("metadata", {}).get("missing_input_keys", []) if isinstance(output.get("metadata"), dict) else []:
                _append_unique(missing_input_keys, key)
            for action in output.get("actions", []) if isinstance(output.get("actions"), list) else []:
                if not isinstance(action, dict):
                    continue
                action_metadata = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
                for key in action_metadata.get("missing_targets", []) if isinstance(action_metadata.get("missing_targets"), list) else []:
                    _append_unique(missing_input_keys, key)
                _append_unique(missing_assets, action_metadata.get("state_slot"))
            interaction = output.get("interaction") if isinstance(output.get("interaction"), dict) else {}
            _append_unique(raw_message_patterns, interaction.get("expected_answer_type"))
        if event_type == "repair_applied":
            repair_applied = True
            _append_unique(repair_types, output.get("repair_type"))
            result = output.get("result") if isinstance(output.get("result"), dict) else {}
            if str(result.get("status") or "").lower() not in {"", "success", "succeeded"}:
                _append_unique(repair_blocked, result.get("message") or result.get("status"))
        if "repair" in event_type and event_type not in {"repair_triggered", "repair_applied"}:
            _append_unique(repair_blocked, output.get("reason") or output.get("message") or event_type)
        if event_type in {"tool_error", "error_detected"}:
            tool_error_count += 1
            _append_unique(raw_message_patterns, output.get("reason") or output.get("message") or metadata.get("root_cause"))
        if event_type == "tool_result" and str(output.get("status") or "").lower() in {"failed", "error"}:
            tool_error_count += 1
            _append_unique(raw_message_patterns, output.get("reason") or output.get("message") or output.get("payload"))
        if event_type == "stop":
            final_stop_reason = str(output.get("reason") or final_stop_reason or "")
            _append_unique(raw_message_patterns, metadata.get("failtax_label"))
            _append_unique(raw_message_patterns, metadata.get("root_cause"))

        for key in ("missing_input_keys", "unresolved_required_inputs", "missing_targets"):
            value = metadata.get(key)
            if isinstance(value, list):
                for item in value:
                    _append_unique(missing_input_keys, item)
        state_context = metadata.get("state_context") if isinstance(metadata.get("state_context"), dict) else {}
        assets = state_context.get("missing_assets") if isinstance(state_context.get("missing_assets"), list) else []
        for item in assets:
            _append_unique(missing_assets, item)

    return {
        "repair_type_chosen": repair_types[0] if repair_types else "",
        "repair_types": repair_types,
        "repair_applied": repair_applied,
        "repair_blocked": repair_blocked,
        "missing_input_keys": missing_input_keys,
        "state_context": {"missing_assets": missing_assets},
        "raw_message_pattern": "; ".join(raw_message_patterns[:4]),
        "user_query_count": user_query_count,
        "user_reply_count": user_reply_count,
        "tool_error_count": tool_error_count,
        "final_stop_reason": final_stop_reason,
    }


def _system_rows_by_run_task(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, Dict[str, str]]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row.get("run_index") or ""), str(row.get("task_id") or ""))][str(row.get("system") or "")] = row
    return grouped


def first_failed_layer(system_rows: Dict[str, Dict[str, str]]) -> str:
    for system in STRICT_SYSTEMS:
        row = system_rows.get(system)
        if row is not None and not _truthy(row.get("strict_scored_success")):
            return system
    return ""


def classify_failure(row: Dict[str, str], trace_evidence: Dict[str, Any]) -> Tuple[str, str, str]:
    raw_success = _truthy(row.get("raw_execution_success") or row.get("raw_success"))
    strict_success = _truthy(row.get("strict_scored_success") or row.get("success"))
    failure_type = str(row.get("failure_type") or "").lower()
    primary_failtax = str(row.get("primary_failtax") or "").lower()
    failtaxes = {str(item).lower() for item in _safe_json_list(row.get("failtaxes"))}
    stop_reason = str(row.get("stop_reason") or trace_evidence.get("final_stop_reason") or "")
    user_queries = _safe_int(row.get("repair_user_queries")) + int(trace_evidence.get("user_query_count") or 0)
    repair_actions = _safe_int(row.get("raw_repair_actions"))
    observed_error = str(row.get("observed_error_type") or "").lower()

    if raw_success and not strict_success:
        if failure_type in {"multiple_user_turn", "insufficient_information"} and user_queries == 0:
            return (
                "interaction_trigger_or_decoder_gap",
                f"{failure_type or 'interaction_required'}_no_user_query",
                "s3_interaction_overlay",
            )
        if "state" in {primary_failtax, observed_error} or "state" in failtaxes or observed_error == "state_failure":
            return ("state_precondition_gap", "state_related_raw_success_strict_fail", "s1_recovery")
        if stop_reason == "success_criteria_satisfied":
            return ("benchmark_final_response_mismatch", "executor_success_benchmark_contract_fail", "scoring_or_adapter")
        return ("raw_success_but_strict_fail", "executor_success_strict_fail", "scoring_or_adapter")

    if not raw_success:
        if repair_actions == 0 and ("recovery" in failtaxes or primary_failtax in {"binding", "state", "selection"}):
            return ("recovery_trigger_gap", "recoverable_failure_without_repair", "s1_recovery")
        if "state" in {primary_failtax, observed_error} or observed_error == "state_failure":
            return ("state_precondition_gap", "state_failure_runtime", "s1_recovery")
        if primary_failtax == "ordering" or "ordering" in failtaxes:
            return ("planner_hint_gap", "ordering_or_suffix_replan_gap", "s2_planner_overlay")
        return ("runtime_execution_failure", stop_reason or "runtime_failure", "s1_recovery")

    return ("raw_success_but_strict_fail", "unclassified_strict_failure", "manual_review")


def build_taxonomy(rows: List[Dict[str, str]], *, repo_root: Path, target_system: str = "s4_reuse_overlay") -> Dict[str, Any]:
    grouped = _system_rows_by_run_task(rows)
    records: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("system") or "") != target_system:
            continue
        if _truthy(row.get("strict_scored_success") or row.get("success")):
            continue
        trace = _load_trace(str(row.get("trace_path") or ""), root=repo_root)
        evidence = extract_trace_evidence(trace)
        category, subtype, owner = classify_failure(row, evidence)
        run_task = (str(row.get("run_index") or ""), str(row.get("task_id") or ""))
        record = {
            "run_index": row.get("run_index", ""),
            "task_id": row.get("task_id", ""),
            "system": target_system,
            "failure_category": category,
            "error_subtype": subtype,
            "raw_message_pattern": evidence.get("raw_message_pattern", ""),
            "missing_input_keys": evidence.get("missing_input_keys", []),
            "state_context": evidence.get("state_context", {"missing_assets": []}),
            "repair_type_chosen": evidence.get("repair_type_chosen", ""),
            "repair_applied": bool(evidence.get("repair_applied")),
            "repair_blocked": evidence.get("repair_blocked", []),
            "stop_reason": row.get("stop_reason") or evidence.get("final_stop_reason", ""),
            "raw_success_but_strict_fail": _truthy(row.get("raw_execution_success") or row.get("raw_success"))
            and not _truthy(row.get("strict_scored_success") or row.get("success")),
            "first_failed_layer": first_failed_layer(grouped.get(run_task, {})),
            "candidate_owning_layer": owner,
            "recommended_generic_fix": GENERIC_FIXES[category],
            "failure_type": row.get("failure_type", ""),
            "primary_failtax": row.get("primary_failtax", ""),
            "failtaxes": _safe_json_list(row.get("failtaxes")),
            "observed_error_type": row.get("observed_error_type", ""),
            "chosen_tool": row.get("chosen_tool", ""),
            "trace_path": row.get("trace_path", ""),
        }
        records.append(record)

    category_counts = Counter(record["failure_category"] for record in records)
    subtype_counts = Counter(record["error_subtype"] for record in records)
    owner_counts = Counter(record["candidate_owning_layer"] for record in records)
    first_layer_counts = Counter(record["first_failed_layer"] for record in records)
    raw_success_strict_fail = sum(1 for record in records if record["raw_success_but_strict_fail"])
    return {
        "analysis_version": "toolsandbox_strict_failure_taxonomy_v1",
        "target_system": target_system,
        "failure_row_count": len(records),
        "unique_failed_task_count": len({record["task_id"] for record in records}),
        "raw_success_but_strict_fail_count": raw_success_strict_fail,
        "runtime_execution_failure_count": len(records) - raw_success_strict_fail,
        "failure_category_counts": dict(sorted(category_counts.items())),
        "error_subtype_counts": dict(subtype_counts.most_common()),
        "candidate_owning_layer_counts": dict(sorted(owner_counts.items())),
        "first_failed_layer_counts": dict(sorted(first_layer_counts.items())),
        "records": records,
    }


def write_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Strict S4 Failure Taxonomy",
        "",
        f"- analysis_version: `{summary['analysis_version']}`",
        f"- target_system: `{summary['target_system']}`",
        f"- failure_row_count: `{summary['failure_row_count']}`",
        f"- unique_failed_task_count: `{summary['unique_failed_task_count']}`",
        f"- raw_success_but_strict_fail_count: `{summary['raw_success_but_strict_fail_count']}`",
        f"- runtime_execution_failure_count: `{summary['runtime_execution_failure_count']}`",
        "",
        "## Failure Categories",
        "",
        "| category | count |",
        "|---|---:|",
    ]
    for category, count in sorted(summary["failure_category_counts"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Candidate Owning Layer", "", "| owner | count |", "|---|---:|"])
    for owner, count in sorted(summary["candidate_owning_layer_counts"].items()):
        lines.append(f"| {owner} | {count} |")
    lines.extend(["", "## First Failed Layer", "", "| layer | count |", "|---|---:|"])
    for layer, count in sorted(summary["first_failed_layer_counts"].items()):
        lines.append(f"| {layer} | {count} |")
    lines.extend(
        [
            "",
            "## Example Diagnostics",
            "",
            "| run | task_id | category | subtype | first_failed_layer | owner | stop_reason | trace_path |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for record in summary["records"][:25]:
        cells = [
            record["run_index"],
            record["task_id"],
            record["failure_category"],
            record["error_subtype"],
            record["first_failed_layer"],
            record["candidate_owning_layer"],
            record["stop_reason"],
            record["trace_path"],
        ]
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This report is diagnostic only. It may cite task IDs and trace paths as examples, but recommended fixes must remain generic and must not introduce scenario-name or tool-name rules.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparison",
        default="outputs/paper_suite/toolsandbox_official_core_reproducible_strict/comparison.scored.csv",
        help="Path to strict ladder comparison.scored.csv.",
    )
    parser.add_argument(
        "--out-json",
        default="outputs/paper_suite/toolsandbox_official_core_reproducible_strict/strict_s4_failure_taxonomy.json",
    )
    parser.add_argument(
        "--out-md",
        default="outputs/paper_suite/toolsandbox_official_core_reproducible_strict/strict_s4_failure_taxonomy.md",
    )
    parser.add_argument("--target-system", default="s4_reuse_overlay")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path.cwd()
    rows = _read_rows(Path(args.comparison))
    summary = build_taxonomy(rows, repo_root=repo_root, target_system=args.target_system)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(summary, out_md)
    print(
        "wrote taxonomy:",
        out_json,
        "failure_rows=",
        summary["failure_row_count"],
        "unique_tasks=",
        summary["unique_failed_task_count"],
    )


if __name__ == "__main__":
    main()
