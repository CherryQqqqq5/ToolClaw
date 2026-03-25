import json

from toolclaw.schemas.error import ErrorCategory, ErrorSeverity, ToolClawError
from toolclaw.schemas.repair import Repair, RepairStatus, RepairStrategy, RepairType
from toolclaw.schemas.trace import EventType, RunMode, Trace
from toolclaw.schemas.workflow import ActionType, Phase as WorkflowPhase, Workflow


def test_schema_demo_instantiation_smoke() -> None:
    workflow = Workflow.demo()
    trace = Trace.demo()
    error = ToolClawError.demo()
    repair = Repair.demo()

    assert isinstance(workflow, Workflow)
    assert isinstance(trace, Trace)
    assert isinstance(error, ToolClawError)
    assert isinstance(repair, Repair)


def test_schema_to_dict_json_serializable_and_key_consistency() -> None:
    workflow = Workflow.demo()
    trace = Trace.demo()
    error = ToolClawError.demo()
    repair = Repair.demo()

    workflow_dict = workflow.to_dict()
    trace_dict = trace.to_dict()
    error_dict = error.to_dict()
    repair_dict = repair.to_dict()

    json.dumps(workflow_dict)
    json.dumps(trace_dict)
    json.dumps(error_dict)
    json.dumps(repair_dict)

    assert workflow_dict["workflow_id"] == trace_dict["workflow_id"] == error_dict["workflow_id"] == repair_dict["workflow_id"]
    assert trace_dict["run_id"] == error_dict["run_id"] == repair_dict["run_id"]
    assert workflow_dict["task"]["task_id"] == trace_dict["task_id"]


def test_schema_enum_values_smoke() -> None:
    assert WorkflowPhase.PHASE1_TRAINING_FREE.value == "phase1_training_free"
    assert ActionType.TOOL_CALL.value == "tool_call"

    assert RunMode.TOOLCLAW.value == "toolclaw"
    assert EventType.TOOL_RESULT.value == "tool_result"

    assert ErrorCategory.BINDING_FAILURE.value == "binding_failure"
    assert ErrorSeverity.MEDIUM.value == "medium"

    assert RepairType.REBIND_ARGS.value == "rebind_args"
    assert RepairStrategy.DIRECT_PATCH.value == "direct_patch"
    assert RepairStatus.PENDING.value == "pending"


def test_schema_key_fields_non_empty_smoke() -> None:
    workflow = Workflow.demo()
    trace = Trace.demo()
    error = ToolClawError.demo()
    repair = Repair.demo()

    assert workflow.workflow_id
    assert workflow.task.task_id
    assert workflow.execution_plan[0].step_id == "step_01"
    assert workflow.execution_plan[1].step_id == "step_02"

    assert trace.run_id
    assert trace.events[0].event_type.value == "plan_generated"
    assert trace.events[-1].event_type.value == "tool_result"

    assert error.error_id
    assert error.state_context.active_step_id == "step_02"
    assert error.evidence.tool_id == "write_tool"

    assert repair.repair_id
    assert repair.triggered_error_ids[0] == "err_demo_001"
    assert repair.actions[0].target == "step_02.inputs.target_path"
