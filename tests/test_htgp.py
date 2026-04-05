from toolclaw.planner.htgp import (
    HTGPPlanner,
    PlanningHints,
    PlanningRequest,
    PolicyInjector,
    RuleBasedCapabilitySelector,
)
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
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
