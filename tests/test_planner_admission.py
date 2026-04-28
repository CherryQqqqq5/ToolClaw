from copy import deepcopy

from toolclaw.planner.admission import admit_planner_workflow
from toolclaw.planner.overlay import apply_admitted_planner_overlay, workflow_execution_fingerprint
from toolclaw.schemas.workflow import ActionType, ToolSpec, Workflow, WorkflowStep


def _with_missing_required(workflow: Workflow) -> Workflow:
    workflow = deepcopy(workflow)
    workflow.execution_plan[0].metadata["required_input_keys"] = ["query"]
    workflow.execution_plan[0].inputs.pop("query", None)
    return workflow


def _single_step(workflow: Workflow) -> Workflow:
    workflow = deepcopy(workflow)
    workflow.execution_plan = [workflow.execution_plan[0]]
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


def test_admission_allows_base_invalid_same_shape_tool_correction() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    allowed_tool = ToolSpec(tool_id="allowed_tool", description="Allowed replacement")
    base.context.candidate_tools = [allowed_tool]
    planner.context.candidate_tools = [allowed_tool]
    base.execution_plan[0].tool_id = "not_allowed"
    planner.execution_plan[0].tool_id = "allowed_tool"

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"candidate_tool_ids": ["allowed_tool"]},
    )

    assert decision.admitted is True
    assert decision.admission_mode == "execution_takeover"
    assert decision.reason == "base_invalid_safe_tool_correction"
    assert decision.safety_checks["base_static_valid"] is False
    assert decision.safety_checks["planner_static_valid"] is True
    assert decision.safety_checks["safe_tool_correction"] is True


def test_admission_rejects_valid_base_tool_correction_without_opt_in() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    replacement = ToolSpec(tool_id="replacement_search", description="Replacement search")
    base.context.candidate_tools.append(replacement)
    planner.context.candidate_tools.append(replacement)
    planner.execution_plan[0].tool_id = "replacement_search"

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert decision.reason == "no_admissible_execution_takeover"
    assert decision.safety_checks["base_static_valid"] is True
    assert decision.safety_checks["safe_tool_correction"] is True
    assert decision.safety_checks["allow_relaxed_planner_takeover"] is False


def test_admission_allows_valid_base_tool_correction_with_explicit_opt_in() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    replacement = ToolSpec(tool_id="replacement_search", description="Replacement search")
    base.context.candidate_tools.append(replacement)
    planner.context.candidate_tools.append(replacement)
    planner.execution_plan[0].tool_id = "replacement_search"

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"allow_relaxed_planner_takeover": True},
    )

    assert decision.admitted is True
    assert decision.reason == "relaxed_safe_tool_correction_opt_in"
    assert any(change["type"] == "tool_correction" for change in decision.admitted_changes)


def test_admission_rejects_tool_correction_that_drops_grounded_input() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    replacement = ToolSpec(tool_id="replacement_search", description="Replacement search")
    base.context.candidate_tools.append(replacement)
    planner.context.candidate_tools.append(replacement)
    planner.execution_plan[0].tool_id = "replacement_search"
    planner.execution_plan[0].inputs.pop("query", None)

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"allow_relaxed_planner_takeover": True},
    )

    assert decision.admitted is False
    assert f"grounded_value_mutation:{base.execution_plan[0].step_id}:query" in decision.rejected_reasons


def test_admission_rejects_target_mutation_even_with_relaxed_opt_in() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    base.execution_plan[0].inputs["target_path"] = "outputs/reports/base.txt"
    planner.execution_plan[0].inputs["target_path"] = "outputs/reports/planner.txt"

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"allow_relaxed_planner_takeover": True},
    )

    assert decision.admitted is False
    assert f"grounded_value_mutation:{base.execution_plan[0].step_id}:target_path" in decision.rejected_reasons


def test_admission_rejects_state_slot_mutation_even_with_relaxed_opt_in() -> None:
    base = _single_step(Workflow.demo())
    planner = deepcopy(base)
    base.execution_plan[0].metadata["preflight_state_policy"] = {"state_slot": "contact_id"}
    planner.execution_plan[0].metadata["preflight_state_policy"] = {"state_slot": "reminder_id"}

    decision = admit_planner_workflow(
        base_workflow=base,
        planner_workflow=planner,
        admission_metadata={"allow_relaxed_planner_takeover": True},
    )

    assert decision.admitted is False
    assert (
        f"state_slot_semantics_mutation:{base.execution_plan[0].step_id}"
        in decision.safety_checks["safe_tool_correction_rejections"]
    )


def test_admission_rejects_user_turn_budget_increase() -> None:
    base = Workflow.demo()
    base.task.constraints.max_user_turns = 0
    planner = deepcopy(base)
    planner.execution_plan.append(
        WorkflowStep(
            step_id="ask_user",
            capability_id="cap_query_user",
            tool_id=None,
            action_type=ActionType.USER_QUERY,
            inputs={"question": "Need clarification"},
        )
    )

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert "budget_increase" in decision.rejected_reasons or "planner_static_invalid" in decision.rejected_reasons
    assert decision.safety_checks["task_budget_preserved"] is False


def test_admission_allows_base_invalid_planner_valid_when_semantics_preserved() -> None:
    base = _with_missing_required(Workflow.demo())
    planner = deepcopy(base)
    planner.execution_plan[0].inputs["query"] = "Retrieve a file summary."

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is True
    assert decision.admission_mode == "execution_takeover"
    assert decision.reason in {"base_invalid_planner_valid", "planner_resolves_static_requirements"}


def test_admission_allows_generic_seed_read_domain_takeover() -> None:
    base = Workflow.demo()
    search_holiday = ToolSpec(tool_id="search_holiday", description="Search holiday calendar")
    base.context.candidate_tools.append(search_holiday)
    planner = deepcopy(base)
    planner.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_retrieve",
            tool_id="search_holiday",
            inputs={"query": "How many days is it till Christmas Day"},
        )
    ]

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is True
    assert decision.reason == "generic_seed_read_domain_takeover"
    assert decision.safety_checks["generic_seed_read_domain_takeover"] is True


def test_admission_rejects_generic_seed_mutating_domain_takeover() -> None:
    base = Workflow.demo()
    modify_reminder = ToolSpec(tool_id="modify_reminder", description="Modify reminders")
    base.context.candidate_tools.append(modify_reminder)
    planner = deepcopy(base)
    planner.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_modify",
            tool_id="modify_reminder",
            inputs={"state_key": "state_checked"},
        )
    ]

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert any("unsafe_domain_tools:modify_reminder" == reason for reason in decision.rejected_reasons)


def test_admission_rejects_generic_seed_read_takeover_with_placeholder_inputs() -> None:
    base = Workflow.demo()
    search_contact = ToolSpec(tool_id="search_contacts", description="Search contacts")
    base.context.candidate_tools.append(search_contact)
    planner = deepcopy(base)
    planner.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_retrieve",
            tool_id="search_contacts",
            inputs={"query": "retrieved_info"},
        )
    ]

    decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

    assert decision.admitted is False
    assert any(reason.startswith("placeholder_inputs:") for reason in decision.rejected_reasons)


def test_admission_rejects_generic_seed_mutating_prefixes_by_default() -> None:
    for tool_id in [
        "add_contact",
        "create_reminder",
        "delete_contact",
        "remove_contact",
        "send_message",
        "set_wifi_status",
        "update_contact",
    ]:
        base = Workflow.demo()
        base.context.candidate_tools.append(ToolSpec(tool_id=tool_id, description="Mutating domain tool"))
        planner = deepcopy(base)
        planner.execution_plan = [
            WorkflowStep(
                step_id="step_01",
                capability_id="cap_modify",
                tool_id=tool_id,
                inputs={"query": "safe-looking query"},
            )
        ]

        decision = admit_planner_workflow(base_workflow=base, planner_workflow=planner)

        assert decision.admitted is False, tool_id
        assert any(reason == f"unsafe_domain_tools:{tool_id}" for reason in decision.rejected_reasons)


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
