import json
from pathlib import Path

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.execution.state_tracker import StateTracker
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.planner.htgp import HTGPPlanner, PlanningHints, PlanningRequest, PolicyInjector, RuleBasedCapabilitySelector
from toolclaw.schemas.error import ErrorCategory, ErrorEvidence, ErrorSeverity, ErrorStage, Recoverability, StateContext, ToolClawError
from toolclaw.schemas.trace import EventType, Trace
from toolclaw.schemas.workflow import Workflow


def build_planner() -> HTGPPlanner:
    return HTGPPlanner(
        capability_selector=RuleBasedCapabilitySelector(),
        graph_builder=RuleBasedCapabilityGraphBuilder(CapabilityTemplateRegistry()),
        binder=ToolBinder(),
        policy_injector=PolicyInjector(),
    )


def test_executor_runs_demo_workflow_and_writes_trace(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    output_file = tmp_path / "traces" / "run_success.json"

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_success_001",
        output_path=str(output_file),
    )

    assert trace.metrics.success is True
    assert output_file.exists()

    trace_payload = json.loads(output_file.read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in trace_payload["events"]]
    assert EventType.TOOL_CALL.value in event_types
    assert EventType.TOOL_RESULT.value in event_types
    assert EventType.STOP.value in event_types


def test_executor_triggers_repair_and_applies_backup_tool(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True
    output_file = tmp_path / "traces" / "run_repair.json"

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_repair_001",
        output_path=str(output_file),
        backup_tool_map={"write_tool": "backup_write_tool"},
    )

    assert trace.metrics.success is True

    trace_payload = json.loads(output_file.read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in trace_payload["events"]]
    assert EventType.REPAIR_TRIGGERED.value in event_types
    assert EventType.REPAIR_APPLIED.value in event_types
    assert EventType.STOP.value in event_types


def test_switch_tool_repair_updates_workflow_state(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_switch_update_001",
        output_path=str(tmp_path / "run_switch_update.json"),
        backup_tool_map={"write_tool": "backup_write_tool"},
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].tool_id == "backup_write_tool"
    write_binding = [b for b in workflow.tool_bindings if b.capability_id == "cap_write"][0]
    assert write_binding.primary_tool == "backup_write_tool"
    assert "write_tool" in write_binding.backup_tools


def test_executor_rolls_back_and_replans_suffix_when_ordering_failure_occurs(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.context.candidate_tools.append(type(workflow.context.candidate_tools[1])(tool_id="ordering_write_tool", description="write with wrong order"))
    workflow.execution_plan[1].tool_id = "ordering_write_tool"
    write_binding = [b for b in workflow.tool_bindings if b.capability_id == "cap_write"][0]
    write_binding.primary_tool = "ordering_write_tool"

    trace = SequentialExecutor(planner=build_planner()).run(
        workflow=workflow,
        run_id="run_replan_001",
        output_path=str(tmp_path / "run_replan.json"),
    )

    assert trace.metrics.success is True
    payload = json.loads((tmp_path / "run_replan.json").read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in payload["events"]]
    assert EventType.ROLLBACK.value in event_types
    assert EventType.REPLAN_TRIGGERED.value in event_types
    assert EventType.REPLAN_APPLIED.value in event_types


def test_executor_suffix_replan_preserves_request_hints_from_workflow_metadata() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=Workflow.demo().task,
        context=Workflow.demo().context,
        policy=Workflow.demo().policy,
        hints=PlanningHints(
                reusable_asset_ids=["asset_003"],
                prior_failures=["binding_failure"],
                user_style={
                    "benchmark": "toolsandbox",
                    "categories": ["multiple_user_turn"],
                    "tool_allow_list": ["search_tool", "write_tool"],
                    "ideal_tool_calls": 2,
                    "milestones": ["retrieve info", "write artifact"],
                },
        ),
    )
    workflow = planner.plan(request).workflow
    step = workflow.execution_plan[1]
    step.rollback_to = "step_01"
    tracker = StateTracker(
        completed_steps=["step_01"],
        state_values={"retrieved_info": "summary"},
    )
    tracker.save_checkpoint("cp_step_01")
    trace = Trace(run_id="run_replan_ctx_002", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    error = ToolClawError(
        error_id="err_replan_ctx_002",
        run_id="run_replan_ctx_002",
        workflow_id=workflow.workflow_id,
        step_id=step.step_id,
        category=ErrorCategory.ORDERING_FAILURE,
        subtype="ordering_error",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=["ordering failed"],
        evidence=ErrorEvidence(tool_id=None, raw_message="ordering failed"),
        root_cause_hypothesis=["synthetic test"],
        state_context=StateContext(active_capability=step.capability_id, active_step_id=step.step_id),
        recoverability=Recoverability(recoverable=True, requires_rollback=True),
        failtax_label="ordering_failure",
    )

    replanned = SequentialExecutor(planner=planner)._attempt_rollback_and_suffix_replan(
        workflow=workflow,
        step=step,
        error=error,
        trace=trace,
        tracker=tracker,
    )

    assert replanned is not None
    replanned_workflow, _ = replanned
    assert replanned_workflow.metadata["planning_request"]["hints"]["user_style"]["benchmark"] == "toolsandbox"
    assert replanned_workflow.metadata["replan_context"]["reusable_asset_ids"] == ["asset_003"]
    assert "ordering_failure" in replanned_workflow.metadata["replan_context"]["prior_failures"]
