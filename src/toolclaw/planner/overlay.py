"""Non-destructive planner overlays for strict-superset system variants."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, List

from toolclaw.schemas.workflow import Workflow

_OVERLAY_METADATA_PREFIXES = ("planner_overlay_", "reuse_overlay_")
_OVERLAY_METADATA_KEYS = {
    "planner_observability",
    "planner_candidate_metadata",
    "planner_candidate_step_count",
    "planner_candidate_tool_count",
    "planner_candidate_binding_count",
}


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


def _execution_relevant_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Keep all metadata except explicitly overlay-only observability fields."""

    relevant: Dict[str, Any] = {}
    for key, value in sorted((metadata or {}).items()):
        if key in _OVERLAY_METADATA_KEYS:
            continue
        if any(str(key).startswith(prefix) for prefix in _OVERLAY_METADATA_PREFIXES):
            continue
        relevant[str(key)] = value
    return relevant


def workflow_execution_fingerprint(workflow: Workflow) -> Dict[str, Any]:
    """Return the score/runtime-relevant execution shape of a workflow.

    Overlay metadata is intentionally ignored, while step order, selected tools,
    inputs, policy, graph nodes, bindings, task constraints, candidate tools, and
    non-overlay metadata are included.
    """

    return _normalize(
        {
            "task": {
                "task_id": workflow.task.task_id,
                "user_goal": workflow.task.user_goal,
                "success_criteria": list(workflow.task.success_criteria),
                "constraints": workflow.task.constraints,
            },
            "context": workflow.context,
            "capability_graph": workflow.capability_graph,
            "tool_bindings": workflow.tool_bindings,
            "execution_plan": workflow.execution_plan,
            "workflow_graph": workflow.workflow_graph,
            "policy": workflow.policy,
            "reusable_targets": workflow.reusable_targets,
            "metadata": _execution_relevant_metadata(workflow.metadata),
        }
    )


def _planner_diff_summary(base_workflow: Workflow, planner_workflow: Workflow) -> List[Dict[str, Any]]:
    rejected: List[Dict[str, Any]] = []
    base_steps = list(base_workflow.execution_plan or [])
    planner_steps = list(planner_workflow.execution_plan or [])
    if len(base_steps) != len(planner_steps):
        rejected.append(
            {
                "type": "step_count_change",
                "base_step_count": len(base_steps),
                "planner_step_count": len(planner_steps),
            }
        )
    for index, (base_step, planner_step) in enumerate(zip(base_steps, planner_steps)):
        diffs: Dict[str, Any] = {}
        for field in (
            "step_id",
            "capability_id",
            "tool_id",
            "action_type",
            "inputs",
            "expected_output",
            "checkpoint",
            "rollback_to",
            "requires_user_confirmation",
            "metadata",
        ):
            base_value = getattr(base_step, field)
            planner_value = getattr(planner_step, field)
            if _normalize(base_value) != _normalize(planner_value):
                diffs[field] = {
                    "base": _normalize(base_value),
                    "planner": _normalize(planner_value),
                }
        if diffs:
            rejected.append({"type": "step_mutation", "index": index, "diffs": diffs})
    if _normalize(base_workflow.tool_bindings) != _normalize(planner_workflow.tool_bindings):
        rejected.append({"type": "tool_binding_change"})
    if _normalize(base_workflow.workflow_graph) != _normalize(planner_workflow.workflow_graph):
        rejected.append({"type": "workflow_graph_change"})
    if _normalize(base_workflow.policy) != _normalize(planner_workflow.policy):
        rejected.append({"type": "policy_change"})
    if _normalize(base_workflow.task.constraints) != _normalize(planner_workflow.task.constraints):
        rejected.append({"type": "task_constraint_change"})
    if _normalize(_execution_relevant_metadata(base_workflow.metadata)) != _normalize(
        _execution_relevant_metadata(planner_workflow.metadata)
    ):
        rejected.append({"type": "execution_relevant_metadata_change"})
    return rejected


def apply_planner_overlay(
    base_workflow: Workflow,
    planner_workflow: Workflow,
    metadata: Dict[str, Any] | None = None,
) -> Workflow:
    """Attach planner observability to the base workflow without changing execution.

    V1 deliberately rejects all planner execution-path differences. This is not
    fallback-after-failure; it preserves the lower-layer workflow by construction.
    """

    workflow = deepcopy(base_workflow)
    before = workflow_execution_fingerprint(workflow)
    planner_metadata = dict(metadata or {})
    rejected_changes = _planner_diff_summary(base_workflow, planner_workflow)
    if workflow_execution_fingerprint(base_workflow) != workflow_execution_fingerprint(planner_workflow):
        if not any(change.get("type") == "execution_fingerprint_change" for change in rejected_changes):
            rejected_changes.append({"type": "execution_fingerprint_change"})

    workflow.metadata["planner_overlay_applied"] = True
    workflow.metadata["planner_overlay_mode"] = "observability_only_v1"
    workflow.metadata["planner_overlay_policy_version"] = "strict_superset_v1"
    workflow.metadata["planner_overlay_rejected_changes"] = rejected_changes
    workflow.metadata["planner_candidate_step_count"] = len(planner_workflow.execution_plan or [])
    workflow.metadata["planner_candidate_tool_count"] = len(planner_workflow.context.candidate_tools or [])
    workflow.metadata["planner_candidate_binding_count"] = len(planner_workflow.tool_bindings or [])
    workflow.metadata["planner_observability"] = {
        "candidate_workflow_id": planner_workflow.workflow_id,
        "candidate_task_id": planner_workflow.task.task_id,
        "metadata": planner_metadata,
    }

    after = workflow_execution_fingerprint(workflow)
    if after != before:
        raise AssertionError("planner overlay changed base execution fingerprint")
    return workflow


def apply_reuse_overlay_noop(workflow: Workflow, metadata: Dict[str, Any] | None = None) -> Workflow:
    """V1 exact-reuse overlay placeholder: observability-only and no-op by design."""

    overlaid = deepcopy(workflow)
    before = workflow_execution_fingerprint(overlaid)
    overlaid.metadata["reuse_overlay_applied"] = True
    overlaid.metadata["reuse_overlay_mode"] = "observability_only_noop_v1"
    overlaid.metadata["reuse_overlay_policy_version"] = "strict_superset_v1"
    overlaid.metadata["reuse_overlay_metadata"] = dict(metadata or {})
    after = workflow_execution_fingerprint(overlaid)
    if after != before:
        raise AssertionError("reuse overlay changed base execution fingerprint")
    return overlaid
