from toolclaw.planner.htgp import (
    HTGPPlanner,
    PlanningHints,
    PlanningRequest,
    PolicyInjector,
    RuleBasedCapabilitySelector,
)
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.workflow import TaskConstraints, TaskSpec, ToolSpec, WorkflowContext


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
