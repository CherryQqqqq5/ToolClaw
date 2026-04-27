from copy import deepcopy

from toolclaw.planner.overlay import (
    apply_admitted_planner_overlay,
    apply_planner_overlay,
    apply_reuse_overlay_noop,
    workflow_execution_fingerprint,
)
from toolclaw.schemas.workflow import Workflow, WorkflowStep


def test_planner_overlay_preserves_execution_fingerprint() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.metadata["planner_note"] = "candidate only"

    overlaid = apply_planner_overlay(base, planner, {"test": "preserve"})

    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(base)
    assert overlaid.metadata["planner_overlay_applied"] is True
    assert overlaid.metadata["planner_overlay_mode"] == "observability_only_v1"


def test_planner_overlay_rejects_primary_tool_override() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.execution_plan[0].tool_id = "different_tool"

    overlaid = apply_planner_overlay(base, planner, {})

    assert overlaid.execution_plan[0].tool_id == base.execution_plan[0].tool_id
    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(base)
    rejected = overlaid.metadata["planner_overlay_rejected_changes"]
    assert any(change["type"] == "step_mutation" for change in rejected)


def test_planner_overlay_rejects_step_insertion_reorder_input_and_metadata_changes() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.execution_plan = list(reversed(planner.execution_plan))
    planner.execution_plan[0].inputs["query"] = "mutated"
    planner.execution_plan.append(
        WorkflowStep(
            step_id="extra_step",
            capability_id="cap_extra",
            tool_id="extra_tool",
        )
    )
    planner.metadata["enable_core_grounding"] = False

    overlaid = apply_planner_overlay(base, planner, {})

    assert [step.step_id for step in overlaid.execution_plan] == [step.step_id for step in base.execution_plan]
    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(base)
    rejected_types = {change["type"] for change in overlaid.metadata["planner_overlay_rejected_changes"]}
    assert "step_count_change" in rejected_types
    assert "step_mutation" in rejected_types
    assert "execution_relevant_metadata_change" in rejected_types


def test_reuse_overlay_no_exact_hit_preserves_workflow_fingerprint() -> None:
    workflow = Workflow.demo()

    overlaid = apply_reuse_overlay_noop(workflow, {"exact_hit": False})

    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(workflow)
    assert overlaid.metadata["reuse_overlay_applied"] is True
    assert overlaid.metadata["reuse_overlay_mode"] == "observability_only_noop_v1"


def test_admitted_planner_overlay_rejected_candidate_keeps_base_fingerprint() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.execution_plan[0].tool_id = "different_tool"

    overlaid = apply_admitted_planner_overlay(base, planner, {})

    assert overlaid.metadata["planner_overlay_admitted"] is False
    assert overlaid.metadata["planner_overlay_policy_version"] == "strict_superset_v2_admitted_execution"
    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(base)
