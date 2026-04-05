from toolclaw.planner.htgp import (
    HTGPPlanner,
    PlanningHints,
    PlanningRequest,
    PolicyInjector,
    RuleBasedCapabilitySelector,
)
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.error import ErrorCategory, ErrorEvidence, ErrorSeverity, ErrorStage, Recoverability, StateContext, ToolClawError
from toolclaw.schemas.workflow import PolicyRule, RiskLevel, TaskConstraints, TaskSpec, ToolSpec, WorkflowContext, WorkflowPolicy


def build_planner() -> HTGPPlanner:
    return HTGPPlanner(
        capability_selector=RuleBasedCapabilitySelector(),
        graph_builder=RuleBasedCapabilityGraphBuilder(CapabilityTemplateRegistry()),
        binder=ToolBinder(),
        policy_injector=PolicyInjector(),
    )


def test_planner_builds_linear_plan_for_simple_task() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) >= 2
    assert result.workflow.execution_plan[0].capability_id == "cap_retrieve"
    assert result.workflow.execution_plan[1].capability_id == "cap_write"


def test_planner_emits_unresolved_capability_when_no_tool_matches() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_002", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[ToolSpec(tool_id="unknown_tool", description="unknown")]
        ),
        hints=PlanningHints(forbidden_tools=["unknown_tool"]),
    )

    result = planner.plan(request)

    assert len(result.diagnostics.unresolved_capabilities) > 0


def test_planner_injects_checkpoint_and_policy_gates() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_003", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    result = planner.plan(request)

    assert all(step.checkpoint for step in result.workflow.execution_plan)
    assert all("policy_gate" in step.metadata for step in result.workflow.execution_plan)


def test_planner_injects_approval_gate_from_policy_expression() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(
            task_id="task_004",
            user_goal="retrieve and write report",
            constraints=TaskConstraints(risk_level=RiskLevel.HIGH),
        ),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        policy=WorkflowPolicy(
            approval_rules=[PolicyRule(rule_id="apr_high_risk", trigger="risk_level == high", action="ask_user")]
        ),
    )

    result = planner.plan(request)

    assert all(step.requires_user_confirmation for step in result.workflow.execution_plan)
    assert all(step.metadata["requires_approval"] is True for step in result.workflow.execution_plan)


def test_planner_applies_bypass_for_single_tool_benchmark_hints() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_005", user_goal="save the final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "ideal_turn_count": 1,
                "milestones": ["save artifact"],
            }
        ),
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) == 1
    assert result.workflow.execution_plan[0].tool_id == "write_tool"
    assert result.diagnostics.overplanning_risk["bypass_applied"] is True
    assert "tool_allow_list" in result.diagnostics.benchmark_hints_used


def test_planner_records_overplanning_risk_when_steps_exceed_ideal() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_006", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["multiple_user_turn"],
                "tool_allow_list": ["search_tool", "write_tool"],
                "ideal_tool_calls": 1,
            }
        ),
    )

    result = planner.plan(request)

    assert result.diagnostics.overplanning_risk["steps_exceed_ideal"] is True
    assert "overplanning_risk:steps_exceed_ideal_tool_calls" in result.diagnostics.warnings


def test_planner_can_round_trip_request_context_from_workflow_metadata() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_007", user_goal="save final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            preferred_capabilities=["cap_write"],
            forbidden_tools=["deprecated_tool"],
            reusable_asset_ids=["asset_001"],
            prior_failures=["binding_failure"],
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "milestones": ["save answer"],
            },
        ),
        planner_mode="benchmark_aware",
        workflow_overrides={"steps": {"step_01": {"inputs": {"target_path": "outputs/custom.txt"}}}},
    )

    result = planner.plan(request)
    restored = planner.request_from_workflow(result.workflow)

    assert restored.planner_mode == "benchmark_aware"
    assert restored.hints.reusable_asset_ids == ["asset_001"]
    assert restored.hints.prior_failures == ["binding_failure"]
    assert restored.hints.user_style["tool_allow_list"] == ["write_tool"]
    assert restored.workflow_overrides["steps"]["step_01"]["inputs"]["target_path"] == "outputs/custom.txt"


def test_replan_from_error_inherits_workflow_request_context_when_request_is_sparse() -> None:
    planner = build_planner()
    original_request = PlanningRequest(
        task=TaskSpec(task_id="task_008", user_goal="save final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            reusable_asset_ids=["asset_002"],
            prior_failures=["environment_failure"],
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "ideal_turn_count": 1,
            },
        ),
    )
    planned = planner.plan(original_request).workflow
    sparse_request = PlanningRequest(task=planned.task, context=planned.context, policy=planned.policy)
    error = ToolClawError(
        error_id="err_replan_ctx_001",
        run_id="run_replan_ctx_001",
        workflow_id=planned.workflow_id,
        step_id="step_01",
        category=ErrorCategory.ORDERING_FAILURE,
        subtype="dependency_error",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=["ordering failed"],
        evidence=ErrorEvidence(tool_id=None, raw_message="ordering failed"),
        root_cause_hypothesis=["synthetic test"],
        state_context=StateContext(active_step_id="step_01"),
        recoverability=Recoverability(recoverable=True, requires_rollback=True),
        failtax_label="ordering_failure",
    )

    replanned = planner.replan_from_error(
        request=sparse_request,
        failed_workflow=planned,
        error=error,
        state_values={"retrieved_info": "cached"},
    )

    assert replanned.diagnostics.overplanning_risk["bypass_applied"] is True
    assert "tool_allow_list" in replanned.diagnostics.benchmark_hints_used
    assert replanned.workflow.metadata["replan_context"]["reusable_asset_ids"] == ["asset_002"]
    assert "ordering_failure" in replanned.workflow.metadata["replan_context"]["prior_failures"]
