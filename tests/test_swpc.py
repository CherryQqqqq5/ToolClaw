from pathlib import Path

from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.execution.executor import SequentialExecutor
from toolclaw.planner.htgp import (
    HTGPPlanner,
    PlanningHints,
    PlanningRequest,
    PolicyInjector,
    RuleBasedCapabilitySelector,
)
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.trace import Trace
from toolclaw.schemas.workflow import TaskConstraints, TaskSpec, ToolSpec, Workflow, WorkflowContext


def build_planner(registry: InMemoryAssetRegistry) -> HTGPPlanner:
    return HTGPPlanner(
        capability_selector=RuleBasedCapabilitySelector(),
        graph_builder=RuleBasedCapabilityGraphBuilder(CapabilityTemplateRegistry()),
        binder=ToolBinder(),
        policy_injector=PolicyInjector(),
        asset_registry=registry,
    )


def test_compiler_extracts_workflow_snippet_from_success_trace(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    outcome = SequentialExecutor().run_until_blocked(
        workflow=workflow,
        run_id="run_compile_001",
        output_path=str(tmp_path / "compile_trace.json"),
        backup_tool_map={},
    )
    assert outcome.success is True

    trace_dict = __import__("json").loads((tmp_path / "compile_trace.json").read_text(encoding="utf-8"))
    trace = Trace(run_id=trace_dict["run_id"], workflow_id=trace_dict["workflow_id"], task_id=trace_dict["task_id"])
    trace.metrics.success = trace_dict["metrics"]["success"]

    artifacts = SWPCCompiler().compile_from_trace(workflow=workflow, trace=trace, final_state=outcome.final_state)

    assert len(artifacts.workflow_snippets) == 1
    assert len(artifacts.skill_hints) == 1
    assert len(artifacts.policy_snippets) == 1
    assert "family=" in artifacts.workflow_snippets[0].task_signature
    assert "caps=" in artifacts.workflow_snippets[0].task_signature
    assert "fail=" in artifacts.workflow_snippets[0].task_signature


def test_registry_retrieval_feeds_planner_hints() -> None:
    registry = InMemoryAssetRegistry()
    planner = build_planner(registry)

    compiler = SWPCCompiler()
    snippet = compiler.compile_from_trace(Workflow.demo(), Trace.demo(), final_state={}).workflow_snippets[0]
    asset_id = registry.upsert(snippet)

    matches = registry.query(snippet.task_signature)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_reuse_001", user_goal=Workflow.demo().task.user_goal, constraints=TaskConstraints()),
        context=WorkflowContext(
            environment=Workflow.demo().context.environment,
            candidate_tools=[ToolSpec(tool_id="search_tool", description="search"), ToolSpec(tool_id="write_tool", description="write")],
        ),
        hints=PlanningHints(reusable_asset_ids=[m.asset_id for m in matches]),
    )
    result = planner.plan(request)

    assert asset_id in request.hints.reusable_asset_ids
    assert len(result.workflow.execution_plan) >= 2


def test_second_run_uses_compiled_asset_and_reduces_repairs(tmp_path: Path) -> None:
    failing_workflow = Workflow.demo()
    failing_workflow.execution_plan[1].inputs.pop("target_path", None)

    first = SequentialExecutor().run_until_blocked(
        workflow=failing_workflow,
        run_id="run_fail_then_repair",
        output_path=str(tmp_path / "trace_first.json"),
        backup_tool_map={},
    )
    # First run needs recovery (rebind) but completes.
    assert first.success is True

    registry = InMemoryAssetRegistry()
    compiler = SWPCCompiler()
    snippet = compiler.compile_from_trace(Workflow.demo(), Trace.demo(), final_state={}).workflow_snippets[0]
    registry.upsert(snippet)

    planner = build_planner(registry)
    matches = registry.query(snippet.task_signature)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_reuse_002", user_goal=Workflow.demo().task.user_goal, constraints=TaskConstraints()),
        context=WorkflowContext(
            environment=Workflow.demo().context.environment,
            candidate_tools=[ToolSpec(tool_id="search_tool", description="search"), ToolSpec(tool_id="write_tool", description="write")],
        ),
        hints=PlanningHints(reusable_asset_ids=[m.asset_id for m in matches]),
    )
    planned = planner.plan(request).workflow

    second = SequentialExecutor().run_until_blocked(
        workflow=planned,
        run_id="run_reuse_no_repair",
        output_path=str(tmp_path / "trace_second.json"),
        backup_tool_map={},
    )
    assert second.success is True

    first_trace = __import__("json").loads((tmp_path / "trace_first.json").read_text(encoding="utf-8"))
    second_trace = __import__("json").loads((tmp_path / "trace_second.json").read_text(encoding="utf-8"))
    assert second_trace["metrics"]["repair_actions"] <= first_trace["metrics"]["repair_actions"]
