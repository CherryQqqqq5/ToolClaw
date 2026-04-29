#!/usr/bin/env python3
"""Audit strict/proxy shape gaps from existing ToolSandbox traces.

Diagnostic-only: reads comparison rows and traces, writes aggregate JSON/MD,
and does not affect runtime, planner, admission, or scoring behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STRICT_SHAPE_AUDIT_VERSION = "toolsandbox_strict_proxy_shape_audit_v1"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_trace(path: str, *, root: Path) -> Tuple[Dict[str, Any], str]:
    if not path:
        return {"events": []}, ""
    trace_path = Path(path)
    if not trace_path.is_absolute():
        trace_path = root / trace_path
    try:
        with trace_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        return {"events": [], "_trace_load_error": str(exc)}, str(trace_path)
    return payload if isinstance(payload, dict) else {"events": []}, str(trace_path)


def _iter_dicts(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _planner_admission(trace: Dict[str, Any]) -> Dict[str, Any]:
    for obj in _iter_dicts(trace):
        decision = obj.get("planner_admission_decision")
        if isinstance(decision, dict):
            return decision
    return {}


def _proxy_result(trace: Dict[str, Any]) -> Dict[str, Any]:
    metadata = trace.get("metadata") if isinstance(trace.get("metadata"), dict) else {}
    for key in ("toolsandbox_result", "toolsandbox_proxy_result"):
        value = metadata.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _tool_events(trace: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    calls: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    events = trace.get("events") if isinstance(trace.get("events"), list) else []
    for event in events:
        if not isinstance(event, dict):
            continue
        output = event.get("output") if isinstance(event.get("output"), dict) else {}
        if event.get("event_type") == "tool_call":
            calls.append({"tool_id": event.get("tool_id") or output.get("tool_id"), "args": event.get("tool_args") or output.get("tool_args") or {}})
        if event.get("event_type") == "tool_result":
            results.append({"tool_id": event.get("tool_id") or output.get("tool_id"), "output": output})
    return calls, results


def _completion_verification(trace: Dict[str, Any]) -> Dict[str, Any]:
    events = trace.get("events") if isinstance(trace.get("events"), list) else []
    for event in events:
        if isinstance(event, dict) and event.get("event_type") == "completion_verification":
            output = event.get("output")
            return output if isinstance(output, dict) else {}
    return {}


def _final_response(trace: Dict[str, Any]) -> str:
    events = trace.get("events") if isinstance(trace.get("events"), list) else []
    response = ""
    for event in events:
        if not isinstance(event, dict):
            continue
        output = event.get("output") if isinstance(event.get("output"), dict) else {}
        if event.get("event_type") == "final_response_synthesized" and output.get("content"):
            response = str(output.get("content"))
        if event.get("event_type") == "stop" and output.get("final_response"):
            response = str(output.get("final_response"))
    return response


def _payload_has_required_slots(payload: Any) -> Dict[str, bool]:
    if not isinstance(payload, dict):
        return {"content": False, "reminder_timestamp": False}
    return {
        "content": bool(str(payload.get("content") or "").strip()),
        "reminder_timestamp": payload.get("reminder_timestamp") not in {None, ""},
    }


def _action_state_summary(calls: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    action_results: List[Dict[str, Any]] = []
    for result in results:
        tool_id = str(result.get("tool_id") or "")
        if not (tool_id.startswith(("add_", "create_", "modify_", "remove_", "send_", "set_", "update_", "delete_"))):
            continue
        output = result.get("output") if isinstance(result.get("output"), dict) else {}
        payload = output.get("payload")
        state_patch = output.get("state_patch")
        slot_presence = _payload_has_required_slots(payload) if tool_id == "add_reminder" else {}
        action_results.append(
            {
                "tool_id": tool_id,
                "status": output.get("status"),
                "payload_type": type(payload).__name__,
                "state_diff_exists": isinstance(state_patch, dict) and bool(state_patch),
                "required_slots_bound": all(slot_presence.values()) if slot_presence else None,
                "slot_presence": slot_presence,
                "payload_preview": _json_preview(payload),
            }
        )
    return {
        "action_executed": bool(action_results),
        "action_results": action_results,
        "all_action_state_diff_exists": bool(action_results) and all(item["state_diff_exists"] for item in action_results),
        "all_required_slots_bound": bool(action_results) and all(item["required_slots_bound"] is not False for item in action_results),
    }


def _json_preview(value: Any, limit: int = 260) -> str:
    try:
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    except Exception:
        text = str(value)
    return text[:limit]


def classify_shape_gap(*, row: Dict[str, str], trace: Dict[str, Any], action_summary: Dict[str, Any]) -> str:
    if not action_summary["action_executed"]:
        return "missing_action"
    if not action_summary["all_action_state_diff_exists"]:
        return "missing_state_diff"
    if not action_summary["all_required_slots_bound"]:
        return "missing_required_slot"
    proxy = _proxy_result(trace)
    mapping = proxy.get("milestone_mapping")
    if isinstance(mapping, list) and any(item is None for item in mapping):
        return "proxy_milestone_cardinality_or_wrapper_gap"
    if proxy.get("value_level_answer_verified") is False:
        return "proxy_value_level_shape_gap"
    final_response = _final_response(trace)
    if final_response and not _truthy(row.get("strict_scored_success") or row.get("success")):
        return "final_render_or_proxy_contract_gap"
    return "manual_review"


def build_audit(rows: List[Dict[str, str]], *, repo_root: Path, target_system: str) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.get("system") or "") != target_system:
            continue
        trace, trace_path = _load_trace(str(row.get("trace_path") or ""), root=repo_root)
        calls, results = _tool_events(trace)
        action_summary = _action_state_summary(calls, results)
        strict_success = _truthy(row.get("strict_scored_success") or row.get("success"))
        proxy = _proxy_result(trace)
        completion = _completion_verification(trace)
        shape_gap = "" if strict_success else classify_shape_gap(row=row, trace=trace, action_summary=action_summary)
        record = {
            "task_id": row.get("task_id", ""),
            "system": target_system,
            "strict_success": strict_success,
            "shape_gap": shape_gap,
            "action_executed": action_summary["action_executed"],
            "all_required_slots_bound": action_summary["all_required_slots_bound"],
            "all_action_state_diff_exists": action_summary["all_action_state_diff_exists"],
            "action_results": action_summary["action_results"],
            "proxy_similarity": proxy.get("similarity"),
            "proxy_matched_milestones": proxy.get("matched_milestones"),
            "proxy_milestone_mapping": proxy.get("milestone_mapping"),
            "proxy_value_level_answer_verified": proxy.get("value_level_answer_verified"),
            "completion_recommended_action": completion.get("recommended_action"),
            "completion_verified": completion.get("completion_verified"),
            "planner_admission_reason": _planner_admission(trace).get("reason", ""),
            "planner_admitted": _planner_admission(trace).get("admitted"),
            "final_response_present": bool(_final_response(trace)),
            "trace_path": trace_path,
        }
        records.append(record)
    failed = [record for record in records if not record["strict_success"]]
    one_of_two = [
        record
        for record in failed
        if record.get("proxy_similarity") == 0.5 or record.get("proxy_matched_milestones") == 1
    ]
    slot_complete_failed = [
        record
        for record in failed
        if record["action_executed"] and record["all_required_slots_bound"] and record["all_action_state_diff_exists"]
    ]
    return {
        "analysis_version": STRICT_SHAPE_AUDIT_VERSION,
        "target_system": target_system,
        "row_count": len(records),
        "strict_success_count": sum(1 for record in records if record["strict_success"]),
        "strict_failure_count": len(failed),
        "shape_gap_counts": dict(sorted(Counter(record["shape_gap"] for record in failed).items())),
        "strict_1_of_2_failure_count": len(one_of_two),
        "slot_complete_state_diff_strict_failure_count": len(slot_complete_failed),
        "slot_complete_state_diff_strict_failure_shape_counts": dict(sorted(Counter(record["shape_gap"] for record in slot_complete_failed).items())),
        "records": records,
    }


def write_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Strict Proxy Shape Audit",
        "",
        f"- analysis_version: `{summary['analysis_version']}`",
        f"- target_system: `{summary['target_system']}`",
        f"- row_count: `{summary['row_count']}`",
        f"- strict_success_count: `{summary['strict_success_count']}`",
        f"- strict_failure_count: `{summary['strict_failure_count']}`",
        f"- strict_1_of_2_failure_count: `{summary['strict_1_of_2_failure_count']}`",
        f"- slot_complete_state_diff_strict_failure_count: `{summary['slot_complete_state_diff_strict_failure_count']}`",
        "",
        "## Shape Gaps",
        "",
        "| shape_gap | count |",
        "|---|---:|",
    ]
    for gap, count in summary.get("shape_gap_counts", {}).items():
        lines.append(f"| {gap} | {count} |")
    lines.extend(["", "## Representative Failures", "", "| task_id | shape_gap | action | slots | state_diff | proxy_similarity | mapping | trace |", "|---|---|---|---|---|---:|---|---|"])
    for record in [item for item in summary["records"] if not item["strict_success"]][:25]:
        lines.append(
            "| "
            + " | ".join(
                str(cell).replace("|", "\\|")
                for cell in [
                    record["task_id"],
                    record["shape_gap"],
                    record["action_executed"],
                    record["all_required_slots_bound"],
                    record["all_action_state_diff_exists"],
                    record["proxy_similarity"],
                    record["proxy_milestone_mapping"],
                    record["trace_path"],
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", required=True)
    parser.add_argument("--target-system", default="s4_reuse_overlay")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = Path(args.comparison)
    rows = _read_rows(comparison)
    summary = build_audit(rows, repo_root=Path.cwd(), target_system=args.target_system)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(summary, out_md)
    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")


if __name__ == "__main__":
    main()
