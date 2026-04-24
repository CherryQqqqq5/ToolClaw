import json
from pathlib import Path

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.planner.htgp import HTGPPlanner, PlanningHints, PlanningRequest, PolicyInjector, RuleBasedCapabilitySelector
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.workflow import TaskConstraints, TaskSpec, ToolSpec, WorkflowContext


def _planner() -> HTGPPlanner:
    return HTGPPlanner(
        capability_selector=RuleBasedCapabilitySelector(),
        graph_builder=RuleBasedCapabilityGraphBuilder(CapabilityTemplateRegistry()),
        binder=ToolBinder(),
        policy_injector=PolicyInjector(),
    )


def test_htgp_bypass_observability_uses_enum_reason() -> None:
    request = PlanningRequest(
        task=TaskSpec(task_id="obs_bypass", user_goal="write the report", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="report_writer", description="write report")]),
        hints=PlanningHints(user_style={"categories": ["single_tool"], "tool_allow_list": ["report_writer"]}),
    )

    result = _planner().plan(request)
    observability = result.workflow.metadata["planner_observability"]

    assert observability["planner_bypass_applied"] is True
    assert observability["minimal_path_reason"] == "single_tool_category"
    assert observability["graph_builder_used"] is False
    assert observability["candidate_capability_count"] >= 1
    assert observability["selected_capability_order_initial"]
    assert observability["selected_capability_order_final"]


def test_htgp_non_bypass_observability_is_structured() -> None:
    request = PlanningRequest(
        task=TaskSpec(task_id="obs_non_bypass", user_goal="retrieve the notes and write the report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="source_lookup", description="retrieve source"),
                ToolSpec(tool_id="report_writer", description="write report"),
            ]
        ),
    )

    result = _planner().plan(request)
    observability = result.workflow.metadata["planner_observability"]

    assert observability["planner_bypass_applied"] is False
    assert observability["minimal_path_reason"] == "not_applied"
    assert observability["graph_builder_used"] is True
    assert "cap_retrieve" in observability["selected_capability_order_final"]
    assert "cap_write" in observability["selected_capability_order_final"]
    assert observability["selected_capability_instance_order_final"]
    assert observability["graph_edge_order"]


def test_executor_copies_planner_observability_to_trace_metadata(tmp_path: Path) -> None:
    request = PlanningRequest(
        task=TaskSpec(
            task_id="obs_trace",
            user_goal="retrieve the note and write the report",
            constraints=TaskConstraints(max_tool_calls=4, max_user_turns=1, max_repair_attempts=0),
        ),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="source_lookup", description="retrieve source", metadata={"execution_backend": "semantic_mock"}),
                ToolSpec(tool_id="report_writer", description="write report", metadata={"execution_backend": "semantic_mock"}),
            ]
        ),
        hints=PlanningHints(user_style={"tool_execution_backend": "semantic_mock"}),
    )
    workflow = _planner().plan(request).workflow
    trace_path = tmp_path / "trace.json"

    SequentialExecutor().run(workflow=workflow, run_id="obs_trace_run", output_path=str(trace_path))
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    annotations = payload["metadata"]["task_annotations"]

    assert "planner_observability" in annotations
    assert annotations["planner_observability"]["planner_bypass_applied"] is False
    assert annotations["planner_observability"]["minimal_path_reason"] == "not_applied"
