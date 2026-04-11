from pathlib import Path

from toolclaw.compiler.swpc import SWPCCompiler, build_task_signature_candidates
from toolclaw.execution.executor import ExecutionOutcome, SequentialExecutor
from toolclaw.main import ToolClawRuntime
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
from toolclaw.interaction.repair_updater import RepairUpdater
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
    assert artifacts.workflow_snippets[0].metadata["promotion_status"] == "promoted"
    assert artifacts.workflow_snippets[0].metadata["promotion_mode"] == "heuristic_only"
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


def test_compiler_rejects_artifact_when_workflow_violates_overplanning_objective() -> None:
    workflow = Workflow.demo()
    workflow.metadata["benchmark_hints"] = {
        "ideal_tool_calls": 1,
        "ideal_turn_count": 0,
        "overplanning_objective": {
            "active": True,
            "max_steps": 1,
            "preferred_capabilities": ["cap_write"],
            "allowed_tools": ["write_tool"],
        },
    }
    trace = Trace.demo()

    artifacts = SWPCCompiler().compile_from_trace(workflow=workflow, trace=trace, final_state={})

    assert artifacts.workflow_snippets == []
    assert artifacts.skill_hints == []
    assert artifacts.policy_snippets == []
    assert artifacts.metadata["compile_gate"]["allow_compile"] is False
    assert artifacts.metadata["compile_gate"]["objective_consistent"] is False
    assert artifacts.metadata["compile_gate"]["promotion_status"] == "rejected"


def test_runtime_compile_gate_uses_real_trace_metrics_before_upserting(tmp_path: Path) -> None:
    registry = InMemoryAssetRegistry()
    planner = build_planner(registry)
    runtime = ToolClawRuntime(
        planner=planner,
        executor=SequentialExecutor(planner=planner),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    workflow = Workflow.demo()
    workflow.metadata["benchmark_hints"] = {
        "ideal_tool_calls": 1,
        "ideal_turn_count": 0,
        "overplanning_objective": {
            "active": True,
            "max_steps": 1,
            "preferred_capabilities": ["cap_write"],
            "allowed_tools": ["write_tool"],
        },
    }
    trace_path = tmp_path / "compile_gate_trace.json"
    trace_path.write_text(__import__("json").dumps(Trace.demo().to_dict()), encoding="utf-8")
    outcome = ExecutionOutcome(
        run_id="run_compile_gate_001",
        workflow=workflow,
        success=True,
        trace_path=str(trace_path),
    )
    runtime._compile_and_store_if_success(outcome, enabled=True)

    assert registry._assets == {}
    trace_payload = __import__("json").loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["metrics"]["tool_calls"] >= 1


def test_compiler_indexes_signature_aliases_for_structural_reuse() -> None:
    workflow = Workflow.demo()
    workflow.task.user_goal = "Retrieve the customer handoff summary and save the support report."
    workflow.metadata["task_family"] = "toolsandbox_reuse_transfer_001"
    workflow.metadata["failure_type"] = "binding_failure"

    artifacts = SWPCCompiler().compile_from_trace(workflow=workflow, trace=Trace.demo(), final_state={})
    snippet = artifacts.workflow_snippets[0]

    assert snippet.task_signature.endswith("goal=retrieve_the_customer_handoff_summary_and_save_the_support_report")
    assert "task_signature_aliases" in snippet.metadata
    aliases = snippet.metadata["task_signature_aliases"]
    assert any(alias.endswith("::family=toolsandbox_reuse_transfer_001::caps=cap_retrieve+cap_write::fail=binding_failure") for alias in aliases)


def test_structural_signature_candidates_support_query_variation() -> None:
    registry = InMemoryAssetRegistry()
    workflow = Workflow.demo()
    workflow.task.user_goal = "Retrieve the customer handoff summary and save the support report."
    workflow.metadata["task_family"] = "toolsandbox_reuse_transfer_001"
    workflow.metadata["failure_type"] = "binding_failure"
    snippet = SWPCCompiler().compile_from_trace(workflow=workflow, trace=Trace.demo(), final_state={}).workflow_snippets[0]
    registry.upsert(snippet)

    variant_signatures = build_task_signature_candidates(
        user_goal="Fetch the customer transition notes and write the support brief.",
        task_family="toolsandbox_reuse_transfer_001",
        capability_skeleton=["cap_retrieve", "cap_write"],
        failure_context="binding_failure",
    )
    matches = []
    for signature in variant_signatures:
        matches.extend(registry.query(signature))

    assert matches


def test_registry_query_supports_structural_similarity_without_exact_signature() -> None:
    registry = InMemoryAssetRegistry()
    workflow = Workflow.demo()
    workflow.task.user_goal = "Retrieve the customer handoff summary and save the support report."
    workflow.metadata["task_family"] = "toolsandbox_reuse_transfer_001"
    workflow.metadata["failure_type"] = "binding_failure"
    snippet = SWPCCompiler().compile_from_trace(workflow=workflow, trace=Trace.demo(), final_state={}).workflow_snippets[0]
    registry.upsert(snippet)

    matches = registry.query(
        "phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=fetch_transition_notes_and_write_support_brief"
    )

    assert matches
    assert matches[0].metadata["match_type"] in {"structural_similarity", "lexical_similarity", "exact"}


def test_compiler_blocks_promotion_on_heldout_eval_split() -> None:
    workflow = Workflow.demo()
    workflow.metadata["reuse_split"] = "eval"

    artifacts = SWPCCompiler().compile_from_trace(workflow=workflow, trace=Trace.demo(), final_state={})

    assert artifacts.workflow_snippets == []
    assert artifacts.metadata["compile_gate"]["allow_compile"] is False
    assert artifacts.metadata["compile_gate"]["promotion_status"] == "rejected"
    assert "heldout_split:eval" in artifacts.metadata["compile_gate"]["rejection_reasons"]
