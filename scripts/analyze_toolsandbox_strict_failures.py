#!/usr/bin/env python3
"""Analyze strict ToolSandbox core failures without mutating runtime behavior."""

from __future__ import annotations

import argparse
import csv
import json
import re
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

SUBCAUSE_FIXES = {
    "final_response_milestone_gap": "Try a generic final response synthesizer that summarizes completed tool results and state updates without reading milestones.",
    "state_milestone_gap": "Inspect generic state/precondition verification and state patch persistence.",
    "tool_trace_milestone_gap": "Inspect whether runtime tool traces provide task-relevant evidence before finalization.",
    "missing_interaction_gap": "Expand generic interaction triggers for unresolved or ambiguous user-provided information.",
    "interaction_decoder_gap": "Expand generic semantic decoding for typed replies and state/input patches.",
    "post_execution_verifier_gap": "Use completion verifier diagnostics to decide whether to ask, repair, or synthesize final response before stop.",
    "raw_success_overclaim": "Tighten executor-side completion criteria only through gold-free runtime evidence.",
    "scorer_contract_gap": "Audit adapter/scorer contract interpretation without changing runtime behavior.",
    "final_response_absent": "Add gold-free final-response synthesis before successful stop events.",
    "final_response_present_but_contract_fail": "Inspect whether finalization evidence is insufficient or benchmark-facing scorer contract remains stricter than runtime completion.",
    "interaction_contract_still_blocked": "Expand generic interaction triggers only if final response is present but an explicit interaction contract remains unsatisfied.",
    "unknown_raw_strict_gap": "Manually inspect representative traces and add generic diagnostic features.",
}

WORKFLOW_RESIDUAL_FIXES = {
    "missing_action_step": "Add a gold-free workflow obligation check: tasks that require mutation must not finalize after read-only evidence only.",
    "summary_not_field_evidence": "Replace placeholder search summaries with typed runtime-visible records before downstream binding or finalization.",
    "missing_state_diff": "Require mutating tools to return or persist a structured state delta before the trace can satisfy stateful strict contracts.",
    "placeholder_tool_result_contract_gap": "Treat generic placeholder tool outputs as insufficient benchmark evidence and route to recovery or contract runtime.",
    "final_response_without_field_evidence": "Restrict finalization to concrete tool payloads or state values; do not use generic summaries as evidence.",
    "interaction_contract_missing": "Route unresolved user-dependent contracts through the interaction policy instead of finalizing.",
    "pure_final_rendering": "Limit fixes to benchmark-facing rendering only after typed tool evidence and state obligations are already present.",
    "manual_review": "Inspect representative traces and add only generic workflow-contract diagnostics.",
}

READ_ONLY_TOOL_PREFIXES = ("get_", "search_", "find_", "lookup_", "list_", "query_", "retrieve_")
MUTATING_TOOL_PREFIXES = (
    "add_",
    "create_",
    "delete_",
    "modify_",
    "remove_",
    "send_",
    "set_",
    "update_",
    "turn_",
)

MUTATION_GOAL_TOKENS = (
    "add",
    "book",
    "call",
    "cancel",
    "create",
    "delete",
    "modify",
    "remind",
    "remove",
    "reply",
    "reserve",
    "reschedule",
    "schedule",
    "send",
    "set",
    "text",
    "turn",
    "update",
)
OBLIGATION_CLASSIFIER_VERSION = "toolsandbox_workflow_obligation_shadow_v1"




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


def _stringify_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(payload)


def _payload_has_domain_fields(payload: Any) -> bool:
    if isinstance(payload, dict):
        keys = {str(key).lower() for key in payload}
        if keys & {
            "content",
            "message_id",
            "person_id",
            "phone_number",
            "reminder_id",
            "reminder_timestamp",
            "state_delta",
            "state_patch",
            "timestamp",
        }:
            return True
        return any(_payload_has_domain_fields(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_payload_has_domain_fields(item) for item in payload)
    return False


def _is_placeholder_payload(tool_id: str, payload: Any) -> bool:
    text = _stringify_payload(payload).strip().lower()
    if not text:
        return True
    if text.startswith("summary for:"):
        return True
    if text.startswith("tool ") and " executed successfully" in text:
        return True
    if text in {"updated", "retrieved_info", "auto_filled_value"}:
        return True
    if text == "current timestamp" and tool_id != "get_current_timestamp":
        return True
    return False


def _is_read_only_tool(tool_id: str) -> bool:
    return tool_id.startswith(READ_ONLY_TOOL_PREFIXES)


def _is_mutating_tool(tool_id: str) -> bool:
    return tool_id.startswith(MUTATING_TOOL_PREFIXES)


def _task_goal_text(trace_payload: Dict[str, Any], trace_evidence: Dict[str, Any]) -> str:
    for container in (trace_payload, trace_payload.get("metadata"), trace_payload.get("workflow")):
        if not isinstance(container, dict):
            continue
        for key in ("query", "task_goal", "goal", "instruction", "user_instruction"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for tool_call in trace_evidence.get("tool_calls", []) if isinstance(trace_evidence, dict) else []:
        args = tool_call.get("args") if isinstance(tool_call, dict) else {}
        if isinstance(args, dict):
            query = args.get("query") or args.get("instruction") or args.get("content")
            if isinstance(query, str) and query.strip():
                return query.strip()
    return ""


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
    completion_verifier: Dict[str, Any] = {}
    final_response: Dict[str, Any] = {"present": False, "source": "", "length": 0}
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []
    placeholder_tool_ids: List[str] = []
    domain_state_evidence_present = False

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
        if event_type == "tool_call":
            tool_id = str(event.get("tool_id") or output.get("tool_id") or "")
            args = event.get("tool_args") if isinstance(event.get("tool_args"), dict) else {}
            if not args:
                args = output.get("tool_args") if isinstance(output.get("tool_args"), dict) else {}
            tool_calls.append({"tool_id": tool_id, "args": args})
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
        if event_type == "tool_result":
            tool_id = str(event.get("tool_id") or output.get("tool_id") or "")
            payload = output.get("payload") if isinstance(output, dict) else None
            placeholder = _is_placeholder_payload(tool_id, payload)
            if placeholder:
                _append_unique(placeholder_tool_ids, tool_id)
            if _payload_has_domain_fields(payload):
                domain_state_evidence_present = True
            tool_results.append(
                {
                    "tool_id": tool_id,
                    "status": output.get("status", "") if isinstance(output, dict) else "",
                    "placeholder": placeholder,
                    "domain_fields_present": _payload_has_domain_fields(payload),
                    "payload_preview": _stringify_payload(payload)[:180],
                }
            )
        if event_type == "stop":
            final_stop_reason = str(output.get("reason") or final_stop_reason or "")
            _append_unique(raw_message_patterns, metadata.get("failtax_label"))
            _append_unique(raw_message_patterns, metadata.get("root_cause"))
        if event_type == "completion_verification":
            completion_verifier = dict(output)
        if event_type == "final_response_synthesized":
            content = str(output.get("content") or "").strip()
            if content:
                final_response = {"present": True, "source": "final_response_synthesized", "length": len(content)}
        if event_type == "stop" and not final_response.get("present"):
            content = str(output.get("final_response") or "").strip()
            if content:
                final_response = {"present": True, "source": "stop_output", "length": len(content)}

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
        "completion_verifier": completion_verifier,
        "final_response": final_response,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "placeholder_tool_ids": placeholder_tool_ids,
        "semantic_payload_placeholder": bool(placeholder_tool_ids),
        "domain_state_evidence_present": domain_state_evidence_present,
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


def classify_subcause(row: Dict[str, str], trace_evidence: Dict[str, Any]) -> str:
    raw_success = _truthy(row.get("raw_execution_success") or row.get("raw_success"))
    execution_verified = _truthy(row.get("execution_verified_success"))
    strict_success = _truthy(row.get("strict_scored_success") or row.get("success"))
    final_response = trace_evidence.get("final_response") if isinstance(trace_evidence, dict) else {}
    final_response_present = bool(final_response.get("present")) if isinstance(final_response, dict) else False
    interaction_blocked = _truthy(row.get("interaction_contract_satisfied")) is False and (
        str(row.get("failure_type") or "") in {"multiple_user_turn", "insufficient_information"}
    )
    verifier = trace_evidence.get("completion_verifier")
    if isinstance(verifier, dict) and verifier:
        missing = {str(item) for item in verifier.get("missing_evidence", []) if str(item)}
        action = str(verifier.get("recommended_action") or "")
        if "user_clarification_for_ambiguous_goal" in missing and not final_response_present:
            return "missing_interaction_gap"
        if "unresolved_required_inputs" in missing and not final_response_present:
            return "state_milestone_gap"
        if "successful_tool_result" in missing and not final_response_present:
            return "tool_trace_milestone_gap"
        if "task_relevant_final_evidence" in missing and action == "synthesize_final_response" and not final_response_present:
            return "final_response_milestone_gap"
        if missing and not final_response_present:
            return "post_execution_verifier_gap"
    if raw_success and not execution_verified:
        return "raw_success_overclaim"
    if execution_verified and not strict_success and final_response_present and interaction_blocked:
        return "interaction_contract_still_blocked"
    if execution_verified and not strict_success and final_response_present:
        return "final_response_present_but_contract_fail"
    if raw_success and not strict_success and final_response_present and interaction_blocked:
        return "interaction_contract_still_blocked"
    if raw_success and not strict_success and final_response_present:
        return "final_response_present_but_contract_fail"
    if raw_success and not strict_success and not final_response_present:
        return "final_response_absent"
    if execution_verified and not strict_success:
        return "scorer_contract_gap"
    return "unknown_raw_strict_gap"


def classify_workflow_obligation_audit(
    row: Dict[str, str],
    trace_evidence: Dict[str, Any],
    trace_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Shadow-only classifier for missing workflow action obligations.

    The classifier uses visible task text plus the executed tool trace. It does
    not read milestones, result summaries, reference answers, or task IDs, and
    it only emits audit diagnostics for downstream analysis.
    """

    tool_calls = trace_evidence.get("tool_calls", []) if isinstance(trace_evidence, dict) else []
    executed_tools = [str(call.get("tool_id") or "") for call in tool_calls if isinstance(call, dict)]
    executed_mutating_tools = [tool_id for tool_id in executed_tools if _is_mutating_tool(tool_id)]
    executed_read_only_tools = [tool_id for tool_id in executed_tools if _is_read_only_tool(tool_id)]
    goal_text = _task_goal_text(trace_payload, trace_evidence).lower()
    goal_tokens = set(re.findall(r"[a-z0-9]+", goal_text))
    expected_action_tools: List[str] = []

    if {"remind", "reminder", "reminders", "todo"} & goal_tokens:
        expected_action_tools.append("add_reminder")
    if ({"send", "text", "message"} & goal_tokens) and not ({"search", "find", "latest", "oldest"} & goal_tokens):
        expected_action_tools.append("send_message_with_phone_number")
    if ({"update", "modify", "change"} & goal_tokens) and ({"contact", "phone", "number", "relationship"} & goal_tokens):
        expected_action_tools.append("modify_contact")
    if ({"add", "create"} & goal_tokens) and "contact" in goal_tokens:
        expected_action_tools.append("add_contact")

    goal_requires_mutation = bool(expected_action_tools) or bool(goal_tokens & set(MUTATION_GOAL_TOKENS))
    missing_required_action = bool(goal_requires_mutation and not executed_mutating_tools)
    if missing_required_action:
        status = "missing_required_action"
    elif goal_requires_mutation:
        status = "satisfied"
    else:
        status = "not_required"
    return {
        "classifier_version": OBLIGATION_CLASSIFIER_VERSION,
        "audit_only": True,
        "repair_enabled": False,
        "goal_requires_mutation": goal_requires_mutation,
        "expected_action_tools": sorted(set(expected_action_tools)),
        "executed_tools": executed_tools,
        "executed_read_only_tools": executed_read_only_tools,
        "executed_mutating_tools": executed_mutating_tools,
        "missing_required_action": missing_required_action,
        "status": status,
        "evidence_sources": ["visible_goal_text", "tool_trace"],
    }


def classify_workflow_residual(row: Dict[str, str], trace_evidence: Dict[str, Any], trace_payload: Dict[str, Any]) -> str:
    raw_success = _truthy(row.get("raw_execution_success") or row.get("raw_success"))
    strict_success = _truthy(row.get("strict_scored_success") or row.get("success"))
    execution_verified = _truthy(row.get("execution_verified_success"))
    interaction_blocked = _truthy(row.get("interaction_contract_satisfied")) is False and (
        str(row.get("failure_type") or "") in {"multiple_user_turn", "insufficient_information"}
    )
    if strict_success:
        return ""

    tool_calls = trace_evidence.get("tool_calls", []) if isinstance(trace_evidence, dict) else []
    tool_results = trace_evidence.get("tool_results", []) if isinstance(trace_evidence, dict) else []
    tool_ids = [str(call.get("tool_id") or "") for call in tool_calls if isinstance(call, dict)]
    result_tool_ids = [str(result.get("tool_id") or "") for result in tool_results if isinstance(result, dict)]
    mutating_calls = [tool_id for tool_id in tool_ids if _is_mutating_tool(tool_id)]
    read_only_calls = [tool_id for tool_id in tool_ids if _is_read_only_tool(tool_id)]
    placeholder_ids = trace_evidence.get("placeholder_tool_ids", [])
    has_placeholder = bool(placeholder_ids)
    has_domain_evidence = bool(trace_evidence.get("domain_state_evidence_present"))
    final_response = trace_evidence.get("final_response") if isinstance(trace_evidence, dict) else {}
    final_response_present = bool(final_response.get("present")) if isinstance(final_response, dict) else False

    obligation_audit = classify_workflow_obligation_audit(row, trace_evidence, trace_payload)

    if interaction_blocked:
        return "interaction_contract_missing"
    if obligation_audit.get("missing_required_action") and read_only_calls:
        return "missing_action_step"
    if has_placeholder and any(tool_id.startswith("search_") or tool_id.startswith("find_") for tool_id in result_tool_ids):
        return "summary_not_field_evidence"
    if mutating_calls and not has_domain_evidence:
        return "missing_state_diff"
    if has_placeholder and final_response_present and not has_domain_evidence:
        return "final_response_without_field_evidence"
    if has_placeholder:
        return "placeholder_tool_result_contract_gap"
    if raw_success and execution_verified and final_response_present and has_domain_evidence:
        return "pure_final_rendering"
    if raw_success and final_response_present and has_domain_evidence:
        return "pure_final_rendering"
    return "manual_review"


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
        subcause = classify_subcause(row, evidence)
        workflow_residual = classify_workflow_residual(row, evidence, trace)
        obligation_audit = classify_workflow_obligation_audit(row, evidence, trace)
        run_task = (str(row.get("run_index") or ""), str(row.get("task_id") or ""))
        record = {
            "run_index": row.get("run_index", ""),
            "task_id": row.get("task_id", ""),
            "system": target_system,
            "failure_category": category,
            "failure_subcause": subcause,
            "workflow_residual": workflow_residual,
            "workflow_obligation_audit": obligation_audit,
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
            "recommended_subcause_fix": SUBCAUSE_FIXES[subcause],
            "recommended_workflow_fix": WORKFLOW_RESIDUAL_FIXES[workflow_residual],
            "completion_verifier": evidence.get("completion_verifier", {}),
            "final_response": evidence.get("final_response", {"present": False, "source": "", "length": 0}),
            "tool_calls": evidence.get("tool_calls", []),
            "tool_results": evidence.get("tool_results", []),
            "semantic_payload_placeholder": evidence.get("semantic_payload_placeholder", False),
            "placeholder_tool_ids": evidence.get("placeholder_tool_ids", []),
            "domain_state_evidence_present": evidence.get("domain_state_evidence_present", False),
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
    subcause_counts = Counter(record["failure_subcause"] for record in records)
    workflow_residual_counts = Counter(record["workflow_residual"] for record in records)
    workflow_obligation_audit_counts = Counter(
        record.get("workflow_obligation_audit", {}).get("status", "unknown") for record in records
    )
    owner_counts = Counter(record["candidate_owning_layer"] for record in records)
    first_layer_counts = Counter(record["first_failed_layer"] for record in records)
    raw_success_strict_fail = sum(1 for record in records if record["raw_success_but_strict_fail"])
    final_response_present = sum(1 for record in records if record.get("final_response", {}).get("present"))
    placeholder_count = sum(1 for record in records if record.get("semantic_payload_placeholder"))
    domain_evidence_count = sum(1 for record in records if record.get("domain_state_evidence_present"))
    return {
        "analysis_version": "toolsandbox_strict_failure_taxonomy_v2_workflow_residuals",
        "target_system": target_system,
        "failure_row_count": len(records),
        "unique_failed_task_count": len({record["task_id"] for record in records}),
        "raw_success_but_strict_fail_count": raw_success_strict_fail,
        "runtime_execution_failure_count": len(records) - raw_success_strict_fail,
        "final_response_present_count": final_response_present,
        "final_response_absent_count": len(records) - final_response_present,
        "semantic_payload_placeholder_count": placeholder_count,
        "domain_state_evidence_present_count": domain_evidence_count,
        "failure_category_counts": dict(sorted(category_counts.items())),
        "error_subtype_counts": dict(subtype_counts.most_common()),
        "failure_subcause_counts": dict(sorted(subcause_counts.items())),
        "workflow_residual_counts": dict(sorted(workflow_residual_counts.items())),
        "workflow_obligation_audit_counts": dict(sorted(workflow_obligation_audit_counts.items())),
        "workflow_obligation_missing_required_action_count": workflow_obligation_audit_counts.get("missing_required_action", 0),
        "workflow_obligation_classifier_version": OBLIGATION_CLASSIFIER_VERSION,
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
        f"- final_response_present_count: `{summary.get('final_response_present_count', 0)}`",
        f"- final_response_absent_count: `{summary.get('final_response_absent_count', 0)}`",
        f"- semantic_payload_placeholder_count: `{summary.get('semantic_payload_placeholder_count', 0)}`",
        f"- domain_state_evidence_present_count: `{summary.get('domain_state_evidence_present_count', 0)}`",
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
    lines.extend(["", "## Failure Subcauses", "", "| subcause | count |", "|---|---:|"])
    for subcause, count in sorted(summary.get("failure_subcause_counts", {}).items()):
        lines.append(f"| {subcause} | {count} |")
    lines.extend(["", "## Workflow Residuals", "", "| residual | count |", "|---|---:|"])
    for residual, count in sorted(summary.get("workflow_residual_counts", {}).items()):
        lines.append(f"| {residual} | {count} |")
    lines.extend(["", "## Workflow Obligation Audit", "", "| status | count |", "|---|---:|"])
    for status, count in sorted(summary.get("workflow_obligation_audit_counts", {}).items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            "## Example Diagnostics",
            "",
            "| run | task_id | category | subcause | workflow_residual | subtype | first_failed_layer | owner | stop_reason | trace_path |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for record in summary["records"][:25]:
        cells = [
            record["run_index"],
            record["task_id"],
            record["failure_category"],
            record.get("failure_subcause", ""),
            record.get("workflow_residual", ""),
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
