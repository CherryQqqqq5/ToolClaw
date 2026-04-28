from copy import deepcopy

from toolclaw.planner.admission import admit_planner_workflow
from toolclaw.planner.overlay import apply_admitted_planner_overlay, workflow_execution_fingerprint
from toolclaw.schemas.workflow import ToolSpec, Workflow, WorkflowStep


def _with_missing_required(workflow: Workflow) -> Workflow:
    workflow = deepcopy(workflow)
    workflow.execution_plan[0].metadata["required_input_keys"] = ["query"]
    workflow.execution_plan[0].inputs.pop("query", None)
    return workflow


def test_admission_rejects_primary_tool_override_when_base_valid() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.execution_plan[0].tool_id = "different_tool"

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert "deleted_or_mutated_base_step:step_search" in decision.rejected_reasons or decision.admission_mode != "execution_takeover"


def test_admission_rejects_budget_increase_and_disallowed_tool() -> None:
    base = Workflow.demo()
    base.task.constraints.max_tool_calls = 2
    planner = deepcopy(base)
    planner.context.candidate_tools = list(base.context.candidate_tools)
    planner.execution_plan.append(WorkflowStep(step_id="extra", capability_id="cap_extra", tool_id="not_allowed"))

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert "budget_increase" in decision.rejected_reasons or "planner_static_invalid" in decision.rejected_reasons
    assert decision.safety_checks["candidate_tool_constraints_preserved"] is False


def test_admission_rejects_gold_field_visibility() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.metadata["reference_result_summary"] = "gold"

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert "gold_field_visible" in decision.rejected_reasons


def test_admission_rejects_disallowed_base_seed_without_semantic_preservation() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    allowed_tool = ToolSpec(tool_id="allowed_tool", description="Allowed tool")
    base.context.candidate_tools = [allowed_tool]
    planner.context.candidate_tools = [allowed_tool]
    planner.execution_plan = [
        WorkflowStep(
            step_id="planner_step",
            capability_id="cap_update",
            tool_id="allowed_tool",
            inputs={"query": "different execution path"},
        )
    ]

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"candidate_tool_ids": ["allowed_tool"]},
    )

    assert decision.admitted is False
    assert decision.admission_mode != "execution_takeover"
    assert decision.reason == "no_admissible_execution_takeover"
    assert decision.safety_checks["base_static_valid"] is False
    assert decision.safety_checks["planner_static_valid"] is True
    assert decision.safety_checks["grounded_values_preserved"] is False


def test_admission_allows_base_invalid_planner_valid_when_semantics_preserved() -> None:
    base = _with_missing_required(Workflow.demo())
    planner = deepcopy(base)
    planner.execution_plan[0].inputs["query"] = "Retrieve a file summary."

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is True
    assert decision.admission_mode == "execution_takeover"
    assert decision.reason in {"base_invalid_planner_valid", "planner_resolves_static_requirements"}


def test_admission_allows_strict_refinement_with_read_only_inserted_step() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    lookup_tool = ToolSpec(tool_id="lookup_tool", description="Read-only lookup", metadata={"read_only": True})
    base.context.candidate_tools.append(lookup_tool)
    planner.context.candidate_tools.append(lookup_tool)
    planner.execution_plan.insert(
        0,
        WorkflowStep(
            step_id="precheck",
            capability_id="cap_lookup",
            tool_id="lookup_tool",
            metadata={"read_only": True, "precondition_acquisition": True},
        ),
    )

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is True
    assert decision.reason == "strict_refinement"


def test_apply_admitted_planner_overlay_preserves_base_when_rejected() -> None:
    base = Workflow.demo()
    planner = deepcopy(base)
    planner.execution_plan[0].inputs["query"] = "mutated"

    overlaid = apply_admitted_planner_overlay(base, planner, {})

    assert overlaid.metadata["planner_overlay_admitted"] is False
    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(base)


def test_apply_admitted_planner_overlay_returns_planner_for_takeover() -> None:
    base = _with_missing_required(Workflow.demo())
    planner = deepcopy(base)
    planner.execution_plan[0].inputs["query"] = "Retrieve a file summary."

    overlaid = apply_admitted_planner_overlay(base, planner, {})

    assert overlaid.metadata["planner_overlay_admitted"] is True
    assert overlaid.metadata["planner_admission_decision"]["admission_mode"] == "execution_takeover"
    assert workflow_execution_fingerprint(overlaid) == workflow_execution_fingerprint(planner)
