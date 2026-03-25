import json

from toolclaw.schemas.workflow import Workflow, Phase as WorkflowPhase, ActionType
from toolclaw.schemas.trace import Trace, RunMode, EventType
from toolclaw.schemas.error import ToolClawError, ErrorCategory, ErrorSeverity
from toolclaw.schemas.repair import Repair, RepairType, RepairStrategy, RepairStatus


def test_schema_demo_instantiation_smoke() -> None:
    workflow = Workflow.demo()
    trace = Trace.demo()
    error = ToolClawError.demo()
    repair = Repair.demo()

    assert isinstance(workflow, Workflow)
    assert isinstance(trace, Trace)
    assert isinstance(error, ToolClawError)
    assert isinstance(repair, Repair)


def test_schema_to_dict_json_serializable_smoke() -> None:
    workflow_dict = Workflow.demo().to_dict()
    trace_dict = Trace.demo().to_dict()
    error_dict = ToolClawError.demo().to_dict()
    repair_dict = Repair.demo().to_dict()

    # smoke check: should be JSON-serializable
    json.dumps(workflow_dict)
    json.dumps(trace_dict)
    json.dumps(error_dict)
    json.dumps(repair_dict)


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
    assert len(workflow.execution_plan) > 0
    assert workflow.phase.value == "phase1_training_free"

    assert trace.run_id
    assert trace.workflow_id
    assert len(trace.events) > 0
    assert trace.metadata.mode.value in {"baseline", "toolclaw"}

    assert error.error_id
    assert error.run_id
    assert error.category.value
    assert len(error.symptoms) > 0

    assert repair.repair_id
    assert repair.run_id
    assert repair.repair_type.value
    assert repair.decision.rationale