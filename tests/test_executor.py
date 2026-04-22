import json
from pathlib import Path
from types import MethodType

import toolclaw.execution.executor as executor_module
from toolclaw.execution.executor import SequentialExecutor, StepExecutionResult
from toolclaw.execution.state_tracker import StateTracker
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.planner.htgp import HTGPPlanner, PlanningHints, PlanningRequest, PolicyInjector, RuleBasedCapabilitySelector
from toolclaw.schemas.error import ErrorCategory, ErrorEvidence, ErrorSeverity, ErrorStage, Recoverability, StateContext, ToolClawError
from toolclaw.schemas.trace import EventType, Trace
from toolclaw.schemas.workflow import ActionType, ToolSpec, Workflow, WorkflowStep
from toolclaw.tools.mock_tools import ToolExecutionError


class _NeverRepairEngine:
    def plan_repair(self, *args, **kwargs):  # pragma: no cover - deterministic test double
        return None


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


def test_switch_tool_repair_clears_environment_failure_flag_for_backup_tool(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.metadata["tool_execution_backend"] = "semantic_mock"
    workflow.context.candidate_tools = [
        ToolSpec(tool_id="search_tool", description="Search information."),
        ToolSpec(tool_id="write_tool", description="Write report to disk."),
        ToolSpec(tool_id="backup_write_tool", description="Backup write report to disk."),
    ]
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_switch_clears_flag_001",
        output_path=str(tmp_path / "run_switch_clears_flag.json"),
        backup_tool_map={"write_tool": "backup_write_tool"},
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].tool_id == "backup_write_tool"
    assert "force_environment_failure" not in workflow.execution_plan[1].inputs


def test_binding_repair_restores_default_target_path_for_write_step(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.metadata["tool_execution_backend"] = "semantic_mock"
    workflow.context.candidate_tools = [
        ToolSpec(tool_id="search_tool", description="Search information."),
        ToolSpec(tool_id="write_tool", description="Write report to disk."),
    ]
    workflow.execution_plan[1].inputs.pop("target_path", None)
    workflow.execution_plan[1].metadata["repair_default_inputs"] = {"target_path": "outputs/reports/restored.txt"}

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_binding_restore_001",
        output_path=str(tmp_path / "run_binding_restore.json"),
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].inputs["target_path"] == "outputs/reports/restored.txt"
    assert workflow.execution_plan[1].metadata["repair_default_inputs"]["target_path"] == "outputs/reports/restored.txt"


def test_binding_repair_refreshes_grounding_metadata_after_patch(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.metadata["tool_execution_backend"] = "semantic_mock"
    workflow.context.candidate_tools = [
        ToolSpec(tool_id="search_tool", description="Search information."),
        ToolSpec(tool_id="write_tool", description="Write report to disk."),
    ]
    workflow.execution_plan[1].inputs.pop("target_path", None)
    workflow.execution_plan[1].metadata.update(
        {
            "required_input_keys": ["target_path"],
            "unresolved_required_inputs": ["target_path"],
            "grounding_sources": {"target_path": {"source": "unresolved", "confidence": 0.0}},
            "grounding_confidence": {"target_path": 0.0},
            "repair_default_inputs": {"target_path": "outputs/reports/restored.txt"},
        }
    )
    write_binding = next(binding for binding in workflow.tool_bindings if binding.capability_id == "cap_write")
    write_binding.unresolved_required_inputs = ["target_path"]
    write_binding.grounding_sources = {"target_path": {"source": "unresolved", "confidence": 0.0}}
    write_binding.grounding_confidence = {"target_path": 0.0}

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_binding_refresh_001",
        output_path=str(tmp_path / "run_binding_refresh.json"),
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].metadata["unresolved_required_inputs"] == []
    assert workflow.execution_plan[1].metadata["grounding_sources"]["target_path"]["source"] == "repair_patch"
    assert workflow.execution_plan[1].metadata["grounding_confidence"]["target_path"] >= 0.7
    assert write_binding.unresolved_required_inputs == []
    assert write_binding.grounding_sources["target_path"]["source"] == "repair_patch"


def test_state_failure_repair_overrides_wrong_write_target_for_retry(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.metadata["tool_execution_backend"] = "semantic_mock"
    workflow.context.candidate_tools = [
        ToolSpec(tool_id="search_tool", description="Search information."),
        ToolSpec(tool_id="write_tool", description="Write report to disk."),
    ]
    workflow.execution_plan[1].inputs["target_path"] = "outputs/reports/demo_report.shadow.txt"
    workflow.execution_plan[1].inputs["expected_target_path"] = "outputs/reports/demo_report.txt"
    workflow.execution_plan[1].metadata["simulated_missing_arg_values"] = {
        "target_path": "outputs/reports/demo_report.txt"
    }

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_state_wrong_target_001",
        output_path=str(tmp_path / "run_state_wrong_target.json"),
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].inputs["target_path"] == "outputs/reports/demo_report.txt"


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


def test_executor_suffix_replan_falls_back_to_previous_step_when_rollback_target_missing(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.context.candidate_tools.append(type(workflow.context.candidate_tools[1])(tool_id="ordering_write_tool", description="write with wrong order"))
    workflow.execution_plan[1].tool_id = "ordering_write_tool"
    workflow.execution_plan[1].rollback_to = None
    write_binding = [b for b in workflow.tool_bindings if b.capability_id == "cap_write"][0]
    write_binding.primary_tool = "ordering_write_tool"

    trace = SequentialExecutor(planner=build_planner()).run(
        workflow=workflow,
        run_id="run_replan_fallback_001",
        output_path=str(tmp_path / "run_replan_fallback.json"),
    )

    assert trace.metrics.success is True
    payload = json.loads((tmp_path / "run_replan_fallback.json").read_text(encoding="utf-8"))
    rollback_event = next(event for event in payload["events"] if event["event_type"] == EventType.ROLLBACK.value)
    assert rollback_event["output"]["rollback_to"] == "step_01"
    event_types = [evt["event_type"] for evt in payload["events"]]
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


def test_materialize_tool_args_sanitizes_overfilled_search_contacts_inputs() -> None:
    step = WorkflowStep(
        step_id="step_01",
        capability_id="cap_retrieve",
        tool_id="search_contacts",
        action_type=ActionType.TOOL_CALL,
        inputs={
            "name": " Fredrik Thordendal ",
            "person_id": "",
            "phone_number": "unknown",
            "relationship": " ",
            "is_self": False,
        },
    )

    tool_args = SequentialExecutor._materialize_tool_args(step=step, state_values={})

    assert tool_args == {"name": "Fredrik Thordendal"}


def test_check_state_failure_enforces_cellular_preflight_for_outbound_message() -> None:
    step = WorkflowStep(
        step_id="step_02",
        capability_id="cap_write",
        tool_id="send_message_with_phone_number",
        action_type=ActionType.TOOL_CALL,
        inputs={"phone_number": "+12453344098", "content": "hello"},
        metadata={"allowed_tools": ["get_cellular_service_status", "set_cellular_service_status"]},
    )
    trace = Trace(run_id="run_preflight_001", workflow_id="wf_preflight_001", task_id="task_preflight_001")

    result = SequentialExecutor()._check_state_failure(step=step, trace=trace, state_values={})

    assert result is not None
    assert result.ok is False
    assert result.error is not None
    assert result.error.category == ErrorCategory.STATE_FAILURE
    assert result.error.subtype == "preflight_state_unsatisfied"
    assert result.error.evidence.metadata["preflight_state_policy"]["state_slot"] == "cellular_service_status"


def test_check_state_failure_accepts_dict_state_slot_values() -> None:
    step = WorkflowStep(
        step_id="step_03",
        capability_id="cap_write",
        tool_id="bfcl_followup_tool",
        action_type=ActionType.TOOL_CALL,
        inputs={"query": "continue the workflow"},
        metadata={"required_state_slots": ["prior_tool_result"]},
    )
    trace = Trace(run_id="run_bfcl_state_001", workflow_id="wf_bfcl_state_001", task_id="task_bfcl_state_001")

    result = SequentialExecutor()._check_state_failure(
        step=step,
        trace=trace,
        state_values={"prior_tool_result": {"tool_id": "lookup_customer", "arguments": {"customer_id": "42"}}},
    )

    assert result is None


def test_materialize_tool_args_uses_input_bindings_from_state() -> None:
    step = WorkflowStep(
        step_id="step_ground_01",
        capability_id="cap_weather",
        tool_id="weather_lookup",
        action_type=ActionType.TOOL_CALL,
        inputs={},
        metadata={
            "required_input_keys": ["loc"],
            "input_bindings": {"loc": "user_location"},
        },
    )

    tool_args = SequentialExecutor._materialize_tool_args(
        step=step,
        state_values={"user_location": "Ha Noi, Vietnam"},
    )

    assert tool_args["loc"] == "Ha Noi, Vietnam"


def test_run_preflight_reports_missing_required_inputs() -> None:
    workflow = Workflow.demo()
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_ground_02",
            capability_id="cap_weather",
            tool_id="weather_lookup",
            action_type=ActionType.TOOL_CALL,
            inputs={},
            metadata={"required_input_keys": ["loc", "unit"]},
        )
    ]

    report = SequentialExecutor.run_preflight(workflow)

    assert report.ok is False
    assert report.missing_required_inputs == ["step_ground_02.loc", "step_ground_02.unit"]


def test_executor_fails_fast_on_missing_required_inputs_before_tool_execution(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_ground_03",
            capability_id="cap_weather",
            tool_id="weather_lookup",
            action_type=ActionType.TOOL_CALL,
            expected_output="weather_payload",
            inputs={},
            metadata={"required_input_keys": ["loc"]},
        )
    ]
    workflow.metadata["enable_schema_preflight"] = True

    original_run_tool = executor_module.run_tool

    def _forbidden_run_tool(*args, **kwargs):
        raise AssertionError("run_tool should not be called when schema preflight fails")

    executor_module.run_tool = _forbidden_run_tool
    try:
        outcome = SequentialExecutor(
            config=executor_module.ExecutorConfig(allow_repair=False, enable_schema_preflight=True)
        ).run_until_blocked(
            workflow=workflow,
            run_id="run_grounding_preflight_001",
            output_path=str(tmp_path / "grounding_preflight_trace.json"),
        )
    finally:
        executor_module.run_tool = original_run_tool

    assert outcome.success is False
    payload = json.loads((tmp_path / "grounding_preflight_trace.json").read_text(encoding="utf-8"))
    preflight_events = [
        event
        for event in payload["events"]
        if event["event_type"] == EventType.PREFLIGHT_CHECK.value
        and event.get("output", {}).get("reason") == "missing_required_input"
    ]
    assert len(preflight_events) == 1
    assert preflight_events[0]["output"]["missing_required_inputs"] == ["loc"]
    stop_event = next(event for event in payload["events"] if event["event_type"] == EventType.STOP.value)
    assert stop_event["output"]["reason"] == "repair_disabled"


def test_executor_supports_semantic_mock_backend_for_non_toy_tools(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan = workflow.execution_plan[:1]
    workflow.execution_plan[0].tool_id = "set_wifi_status"
    workflow.execution_plan[0].inputs = {"enabled": False}
    workflow.execution_plan[0].expected_output = "wifi_status_update"
    workflow.context.candidate_tools = [
        ToolSpec(
            tool_id="set_wifi_status",
            description="Toggle device WiFi state.",
            metadata={"execution_backend": "semantic_mock", "affordances": ["set", "state", "status"]},
        )
    ]
    workflow.metadata["tool_execution_backend"] = "semantic_mock"

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_semantic_mock_001",
        output_path=str(tmp_path / "semantic_mock_trace.json"),
    )

    assert trace.metrics.success is True
    payload = json.loads((tmp_path / "semantic_mock_trace.json").read_text(encoding="utf-8"))
    result_event = next(event for event in payload["events"] if event["event_type"] == EventType.TOOL_RESULT.value)
    assert result_event["tool_id"] == "set_wifi_status"
    assert "updated state" in result_event["output"]["payload"]


def test_executor_auto_approves_from_simulated_policy_and_continues(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.requires_user_approval = True
    workflow.metadata["simulated_policy"] = {"mode": "cooperative"}

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_auto_approval_001",
        output_path=str(tmp_path / "auto_approval_trace.json"),
    )

    assert trace.metrics.success is True
    payload = json.loads((tmp_path / "auto_approval_trace.json").read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in payload["events"]]
    assert EventType.APPROVAL_RESPONSE.value in event_types


def test_executor_stops_on_repeat_failure_limit_instead_of_spinning(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    failing_step = workflow.execution_plan[1]
    failing_step.rollback_to = "step_01"

    executor = SequentialExecutor()
    executor.config.max_repeat_failures_per_signature = 2
    executor.recovery_engine = _NeverRepairEngine()
    original_execute_step = executor._execute_step

    def _always_fail_second_step(self, workflow, step, trace, state_values):
        if step.step_id != failing_step.step_id:
            return original_execute_step(workflow, step, trace, state_values)
        return StepExecutionResult(
            ok=False,
            step_id=step.step_id,
            tool_id=step.tool_id,
            error=self._build_error(
                workflow=workflow,
                trace=trace,
                step=step,
                exc=ToolExecutionError("synthetic repeat failure"),
                tool_args={"retrieved_info": "cached", "target_path": "outputs/reports/demo_report.txt"},
            ),
        )

    executor._execute_step = MethodType(_always_fail_second_step, executor)

    outcome = executor.run_until_blocked(
        workflow=workflow,
        run_id="run_repeat_failure_guard_001",
        output_path=str(tmp_path / "repeat_failure_guard.json"),
    )

    assert outcome.success is False
    assert outcome.metadata["stopped_reason"] == "repeat_failure_limit_reached"
    payload = json.loads((tmp_path / "repeat_failure_guard.json").read_text(encoding="utf-8"))
    stop_event = next(event for event in payload["events"] if event["event_type"] == EventType.STOP.value)
    assert stop_event["output"]["reason"] == "repeat_failure_limit_reached"


def test_executor_materialize_tool_args_supports_explicit_implicit_fallback_slots() -> None:
    step = WorkflowStep(
        step_id="step_custom_01",
        capability_id="cap_retrieve",
        tool_id="custom_tool",
        inputs={},
        metadata={"implicit_state_fallback_slots": ["query"]},
    )

    tool_args = SequentialExecutor._materialize_tool_args(step, {"query": "hello world"})

    assert tool_args["query"] == "hello world"


def test_executor_materialize_tool_args_allows_explicit_opt_out_for_write_steps() -> None:
    step = WorkflowStep(
        step_id="step_write_01",
        capability_id="cap_write",
        tool_id="write_tool",
        inputs={"target_path": "outputs/reports/demo.txt"},
        metadata={"implicit_state_fallback_slots": []},
    )

    tool_args = SequentialExecutor._materialize_tool_args(
        step,
        {"query": "should not leak", "retrieved_info": "should not leak"},
    )

    assert tool_args == {"target_path": "outputs/reports/demo.txt"}
