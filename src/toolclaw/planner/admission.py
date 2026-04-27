"""Gold-free planner admission gate for strict-superset planner overlays."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Tuple

from toolclaw.schemas.workflow import ActionType, ToolBinding, Workflow, WorkflowStep

GOLD_KEY_TOKENS = (
    "milestone",
    "reference_result_summary",
    "reference_summary",
    "official_",
    "official",
    "scorer_gold",
    "gold_messages",
    "expected_answer",
    "result_summary",
)
TARGET_KEYS = (
    "target",
    "target_path",
    "target_id",
    "entity",
    "entity_id",
    "recipient",
    "state_slot",
    "path",
)
READ_ONLY_TOKENS = ("read", "get", "list", "search", "lookup", "fetch", "retrieve", "check", "inspect", "validate", "verify")
PRECONDITION_TOKENS = ("precondition", "acquire", "resolve", "lookup", "check", "inspect", "validate", "verify")


@dataclass
class PlannerAdmissionDecision:
    admitted: bool
    admission_mode: str
    reason: str
    rejected_reasons: List[str] = field(default_factory=list)
    admitted_changes: List[Dict[str, Any]] = field(default_factory=list)
    safety_checks: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        return _normalize(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, set):
        return sorted(_normalize(item) for item in value)
    return value


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _contains_gold_field(value: Any, path: str = "") -> Tuple[bool, List[str]]:
    hits: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_s = str(key)
            child_path = f"{path}.{key_s}" if path else key_s
            if any(token in key_s.lower() for token in GOLD_KEY_TOKENS) and not _is_empty(item):
                hits.append(child_path)
            found, child_hits = _contains_gold_field(item, child_path)
            if found:
                hits.extend(child_hits)
    elif isinstance(value, (list, tuple, set)):
        for idx, item in enumerate(value):
            child_path = f"{path}[{idx}]"
            found, child_hits = _contains_gold_field(item, child_path)
            if found:
                hits.extend(child_hits)
    elif is_dataclass(value):
        return _contains_gold_field(asdict(value), path)
    return bool(hits), hits


def _candidate_tool_ids(workflow: Workflow) -> set[str]:
    return {str(tool.tool_id) for tool in workflow.context.candidate_tools if str(tool.tool_id or "").strip()}


def _binding_by_capability(workflow: Workflow) -> Dict[str, ToolBinding]:
    return {str(binding.capability_id): binding for binding in workflow.tool_bindings}


def _missing_required_inputs(workflow: Workflow) -> List[str]:
    missing: List[str] = []
    bindings = _binding_by_capability(workflow)
    for step in workflow.execution_plan or []:
        binding = bindings.get(str(step.capability_id))
        required = []
        if binding is not None:
            required.extend(str(item) for item in binding.required_input_keys or [])
            required.extend(str(item) for item in binding.unresolved_required_inputs or [])
        required.extend(str(item) for item in (step.metadata or {}).get("required_input_keys", []) or [])
        required.extend(str(item) for item in (step.metadata or {}).get("unresolved_required_inputs", []) or [])
        for key in sorted(set(required)):
            if key and _is_empty((step.inputs or {}).get(key)):
                missing.append(f"{step.step_id}:{key}")
    return sorted(set(missing))


def _missing_state_slots(workflow: Workflow) -> List[str]:
    slots: List[str] = []
    for step in workflow.execution_plan or []:
        policy = (step.metadata or {}).get("preflight_state_policy")
        if isinstance(policy, dict):
            slot = str(policy.get("state_slot") or "").strip()
            if slot:
                slots.append(f"{step.step_id}:{slot}")
        for slot in (step.metadata or {}).get("missing_state_slots", []) or []:
            if str(slot).strip():
                slots.append(f"{step.step_id}:{slot}")
    return sorted(set(slots))


def _static_report(workflow: Workflow, allowed_tool_ids: Iterable[str] | None = None) -> Dict[str, Any]:
    issues: List[str] = []
    candidate_ids = {str(item) for item in allowed_tool_ids or [] if str(item).strip()} or _candidate_tool_ids(workflow)
    max_tool_calls = workflow.task.constraints.max_tool_calls
    max_user_turns = workflow.task.constraints.max_user_turns
    tool_steps = [step for step in workflow.execution_plan or [] if step.action_type == ActionType.TOOL_CALL]
    user_steps = [step for step in workflow.execution_plan or [] if step.action_type == ActionType.USER_QUERY]
    if max_tool_calls is not None and len(tool_steps) > int(max_tool_calls):
        issues.append("budget_tool_call_increase")
    if max_user_turns is not None and len(user_steps) > int(max_user_turns):
        issues.append("budget_user_turn_increase")
    for step in workflow.execution_plan or []:
        if step.action_type == ActionType.TOOL_CALL and not str(step.tool_id or "").strip():
            issues.append(f"unbound_tool:{step.step_id}")
        if step.tool_id and candidate_ids and str(step.tool_id) not in candidate_ids:
            issues.append(f"disallowed_tool:{step.step_id}:{step.tool_id}")
        if str(step.capability_id).startswith("cap_write") and _is_empty((step.inputs or {}).get("target_path")):
            issues.append(f"missing_target_path:{step.step_id}")
    missing_inputs = _missing_required_inputs(workflow)
    missing_state = _missing_state_slots(workflow)
    issues.extend(f"missing_required_input:{item}" for item in missing_inputs)
    issues.extend(f"missing_state_slot:{item}" for item in missing_state)
    return {
        "ok": not issues,
        "issues": sorted(set(issues)),
        "missing_required_inputs": missing_inputs,
        "missing_state_slots": missing_state,
        "tool_step_count": len(tool_steps),
        "user_step_count": len(user_steps),
    }


def _step_signature(step: WorkflowStep) -> Dict[str, Any]:
    return {
        "capability_id": step.capability_id,
        "tool_id": step.tool_id,
        "action_type": step.action_type.value if isinstance(step.action_type, ActionType) else str(step.action_type),
        "inputs": _normalize(step.inputs),
        "expected_output": step.expected_output,
        "requires_user_confirmation": step.requires_user_confirmation,
    }


def _target_values(step: WorkflowStep) -> Dict[str, Any]:
    inputs = step.inputs or {}
    return {key: inputs.get(key) for key in TARGET_KEYS if key in inputs and not _is_empty(inputs.get(key))}


def _matched_base_indices(base_steps: List[WorkflowStep], planner_steps: List[WorkflowStep]) -> Tuple[bool, List[int], List[str]]:
    matched: List[int] = []
    rejected: List[str] = []
    search_from = 0
    for base_step in base_steps:
        found = None
        base_sig = _step_signature(base_step)
        for idx in range(search_from, len(planner_steps)):
            planner_step = planner_steps[idx]
            if _step_signature(planner_step) == base_sig:
                found = idx
                break
        if found is None:
            rejected.append(f"deleted_or_mutated_base_step:{base_step.step_id}")
            return False, matched, rejected
        matched.append(found)
        search_from = found + 1
    return True, matched, rejected


def _step_tool_metadata(workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
    for tool in workflow.context.candidate_tools:
        if str(tool.tool_id) == str(step.tool_id):
            return dict(tool.metadata or {})
    return {}


def _inserted_step_is_safe(workflow: Workflow, step: WorkflowStep) -> bool:
    metadata = dict(step.metadata or {})
    tool_metadata = _step_tool_metadata(workflow, step)
    merged = {**tool_metadata, **metadata}
    if bool(merged.get("read_only") or merged.get("side_effect_free") or merged.get("precondition_acquisition")):
        return True
    if step.action_type == ActionType.USER_QUERY and bool(merged.get("precondition_acquisition")):
        return True
    text = " ".join(str(value).lower() for value in [step.capability_id, step.expected_output, merged.get("description"), merged.get("action_kind")])
    if any(token in text for token in READ_ONLY_TOKENS) and not any(token in text for token in ("write", "update", "delete", "send", "create")):
        return True
    if any(token in text for token in PRECONDITION_TOKENS) and bool(merged.get("precondition_acquisition")):
        return True
    return False


def _strict_refinement(base_workflow: Workflow, planner_workflow: Workflow) -> Tuple[bool, List[int], List[str]]:
    base_steps = list(base_workflow.execution_plan or [])
    planner_steps = list(planner_workflow.execution_plan or [])
    ok, matched, rejected = _matched_base_indices(base_steps, planner_steps)
    if not ok:
        return False, matched, rejected
    matched_set = set(matched)
    for idx, step in enumerate(planner_steps):
        if idx in matched_set:
            continue
        if not _inserted_step_is_safe(planner_workflow, step):
            rejected.append(f"unsafe_inserted_step:{step.step_id}")
    return not rejected, matched, rejected


def _match_steps_for_semantics(base_steps: List[WorkflowStep], planner_steps: List[WorkflowStep]) -> Tuple[bool, List[int], List[str]]:
    matched: List[int] = []
    rejected: List[str] = []
    search_from = 0
    for base_step in base_steps:
        found = None
        for idx in range(search_from, len(planner_steps)):
            planner_step = planner_steps[idx]
            if (
                str(planner_step.capability_id) == str(base_step.capability_id)
                and str(planner_step.tool_id) == str(base_step.tool_id)
                and planner_step.action_type == base_step.action_type
            ):
                found = idx
                break
        if found is None:
            rejected.append(f"deleted_or_mutated_base_step:{base_step.step_id}")
            return False, matched, rejected
        matched.append(found)
        search_from = found + 1
    return True, matched, rejected


def _preserves_grounded_values(base_workflow: Workflow, planner_workflow: Workflow) -> Tuple[bool, List[str]]:
    ok, matched, rejected = _match_steps_for_semantics(list(base_workflow.execution_plan or []), list(planner_workflow.execution_plan or []))
    if not ok:
        return False, rejected
    reasons: List[str] = []
    planner_steps = list(planner_workflow.execution_plan or [])
    for base_step, planner_index in zip(base_workflow.execution_plan or [], matched):
        planner_step = planner_steps[planner_index]
        for key, value in (base_step.inputs or {}).items():
            if _is_empty(value):
                continue
            if _normalize((planner_step.inputs or {}).get(key)) != _normalize(value):
                reasons.append(f"grounded_value_mutation:{base_step.step_id}:{key}")
        base_targets = _target_values(base_step)
        planner_targets = _target_values(planner_step)
        if _normalize(base_targets) != _normalize(planner_targets):
            reasons.append(f"target_semantics_mutation:{base_step.step_id}")
    return not reasons, reasons


def _candidate_tool_constraints_preserved(
    base_workflow: Workflow,
    planner_workflow: Workflow,
    allowed_tool_ids: Iterable[str] | None = None,
) -> bool:
    base_ids = {str(item) for item in allowed_tool_ids or [] if str(item).strip()} or _candidate_tool_ids(base_workflow)
    planner_used = {str(step.tool_id) for step in planner_workflow.execution_plan or [] if str(step.tool_id or "").strip()}
    return not base_ids or planner_used.issubset(base_ids)


def _task_budget_preserved(base_workflow: Workflow, planner_workflow: Workflow) -> bool:
    base_constraints = base_workflow.task.constraints
    planner_report = _static_report(planner_workflow)
    if base_constraints.max_tool_calls is not None and planner_report["tool_step_count"] > int(base_constraints.max_tool_calls):
        return False
    if base_constraints.max_user_turns is not None and planner_report["user_step_count"] > int(base_constraints.max_user_turns):
        return False
    return True


def admit_planner_workflow(
    *,
    base_workflow: Workflow,
    planner_workflow: Workflow,
    task_metadata: Dict[str, Any] | None = None,
    admission_metadata: Dict[str, Any] | None = None,
) -> PlannerAdmissionDecision:
    task_metadata = dict(task_metadata or {})
    admission_metadata = dict(admission_metadata or {})
    gold_sources = {
        "task_metadata": task_metadata,
        "admission_metadata": admission_metadata,
        "planner_workflow_metadata": planner_workflow.metadata,
    }
    gold_hits: List[str] = []
    for label, payload in gold_sources.items():
        found, hits = _contains_gold_field(payload, label)
        if found:
            gold_hits.extend(hits)
    allowed_tool_ids = admission_metadata.get("candidate_tool_ids")
    if not isinstance(allowed_tool_ids, list):
        allowed_tool_ids = []
    base_report = _static_report(base_workflow, allowed_tool_ids=allowed_tool_ids)
    planner_report = _static_report(planner_workflow, allowed_tool_ids=allowed_tool_ids)
    semantics_ok, semantic_rejections = _preserves_grounded_values(base_workflow, planner_workflow)
    refinement_ok, matched_indices, refinement_rejections = _strict_refinement(base_workflow, planner_workflow)
    safety_checks = {
        "base_static_valid": base_report["ok"],
        "planner_static_valid": planner_report["ok"],
        "base_static_issues": base_report["issues"],
        "planner_static_issues": planner_report["issues"],
        "grounded_values_preserved": semantics_ok,
        "candidate_tool_constraints_preserved": _candidate_tool_constraints_preserved(
            base_workflow, planner_workflow, allowed_tool_ids=allowed_tool_ids
        ),
        "task_budget_preserved": _task_budget_preserved(base_workflow, planner_workflow),
        "strict_refinement": refinement_ok,
        "matched_base_step_count": len(matched_indices),
        "gold_field_hits": gold_hits,
    }
    rejected: List[str] = []
    if gold_hits:
        rejected.append("gold_field_visible")
    if not planner_report["ok"]:
        rejected.append("planner_static_invalid")
    if not safety_checks["candidate_tool_constraints_preserved"]:
        rejected.append("disallowed_tool")
    if not safety_checks["task_budget_preserved"]:
        rejected.append("budget_increase")
    if rejected:
        return PlannerAdmissionDecision(
            admitted=False,
            admission_mode="rejected",
            reason="planner_candidate_failed_safety_checks",
            rejected_reasons=sorted(set(rejected)),
            safety_checks=safety_checks,
        )
    inserted = max(0, len(planner_workflow.execution_plan or []) - len(base_workflow.execution_plan or []))
    if refinement_ok and inserted > 0:
        return PlannerAdmissionDecision(
            admitted=True,
            admission_mode="execution_takeover",
            reason="strict_refinement",
            admitted_changes=[{"type": "strict_refinement", "inserted_step_count": inserted}],
            safety_checks=safety_checks,
        )
    base_disallowed_seed = any(str(issue).startswith("disallowed_tool:") for issue in base_report["issues"])
    if base_disallowed_seed and planner_report["ok"]:
        return PlannerAdmissionDecision(
            admitted=True,
            admission_mode="execution_takeover",
            reason="base_disallowed_seed_planner_valid",
            admitted_changes=[{"type": "candidate_tool_seed_repaired", "base_issues": base_report["issues"]}],
            safety_checks=safety_checks,
        )
    if not base_report["ok"] and planner_report["ok"] and semantics_ok:
        return PlannerAdmissionDecision(
            admitted=True,
            admission_mode="execution_takeover",
            reason="base_invalid_planner_valid",
            admitted_changes=[{"type": "static_invalidity_repaired", "base_issues": base_report["issues"]}],
            safety_checks=safety_checks,
        )
    base_missing = set(base_report["missing_required_inputs"] + base_report["missing_state_slots"])
    planner_missing = set(planner_report["missing_required_inputs"] + planner_report["missing_state_slots"])
    resolved = sorted(base_missing - planner_missing)
    if resolved and planner_report["ok"] and semantics_ok:
        return PlannerAdmissionDecision(
            admitted=True,
            admission_mode="execution_takeover",
            reason="planner_resolves_static_requirements",
            admitted_changes=[{"type": "resolved_static_requirements", "requirements": resolved}],
            safety_checks=safety_checks,
        )
    if not semantics_ok:
        rejected.extend(semantic_rejections)
    rejected.extend(refinement_rejections)
    return PlannerAdmissionDecision(
        admitted=False,
        admission_mode="observability_only",
        reason="no_admissible_execution_takeover",
        rejected_reasons=sorted(set(rejected or ["planner_not_strict_refinement"])),
        safety_checks=safety_checks,
    )
