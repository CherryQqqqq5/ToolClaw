from toolclaw.execution.recovery import RecoveryEngine
from toolclaw.schemas.error import (
    ErrorCategory,
    ErrorEvidence,
    ErrorSeverity,
    ErrorStage,
    Recoverability,
    StateContext,
    ToolClawError,
)
from toolclaw.schemas.repair import RepairType


def make_error(category: ErrorCategory, error_id: str = "err_test_001") -> ToolClawError:
    return ToolClawError(
        error_id=error_id,
        run_id="run_test_001",
        workflow_id="wf_test_001",
        step_id="step_01",
        category=category,
        subtype="test_subtype",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=["synthetic test error"],
        evidence=ErrorEvidence(
            tool_id="tool_a",
            raw_message="synthetic failure",
            related_events=["evt_01"],
        ),
        root_cause_hypothesis=["synthetic root cause"],
        state_context=StateContext(
            active_capability="cap_test",
            active_step_id="step_01",
            missing_assets=["target_path"],
            state_values={"foo": "bar"},
            policy_flags={"approval_pending": False},
        ),
        recoverability=Recoverability(
            recoverable=True,
            requires_user_input=False,
            requires_tool_switch=False,
            requires_rollback=False,
            requires_approval=False,
        ),
        failtax_label=category.value,
    )


def test_binding_failure_maps_to_rebind_args() -> None:
    engine = RecoveryEngine()
    error = make_error(ErrorCategory.BINDING_FAILURE, error_id="err_binding_001")

    repair = engine.plan_repair(error)

    assert repair.repair_type == RepairType.REBIND_ARGS


def test_environment_failure_maps_to_switch_tool_when_backup_exists() -> None:
    engine = RecoveryEngine()
    error = make_error(ErrorCategory.ENVIRONMENT_FAILURE, error_id="err_env_001")

    repair = engine.plan_repair(error, backup_tool_id="tool_backup")

    assert repair.repair_type == RepairType.SWITCH_TOOL


def test_environment_failure_maps_to_ask_user_when_no_backup() -> None:
    engine = RecoveryEngine()
    error = make_error(ErrorCategory.ENVIRONMENT_FAILURE, error_id="err_env_002")

    repair = engine.plan_repair(error, backup_tool_id=None)

    assert repair.repair_type == RepairType.ASK_USER


def test_binding_failure_sanitizes_invalid_search_contact_filters_before_retry() -> None:
    engine = RecoveryEngine()
    error = make_error(ErrorCategory.BINDING_FAILURE, error_id="err_binding_contacts_001")
    error.evidence.tool_id = "search_contacts"
    error.evidence.raw_message = "NumberParseException: The string supplied did not seem to be a phone number."
    error.evidence.inputs = {
        "name": "Fredrik Thordendal",
        "phone_number": "0000000000",
        "person_id": "",
        "relationship": "",
        "is_self": False,
    }

    repair = engine.plan_repair(error)

    assert repair.repair_type == RepairType.REBIND_ARGS
    assert repair.actions[0].target == "step_01.inputs"
    assert repair.actions[0].value == {"name": "Fredrik Thordendal"}


def test_state_failure_with_preflight_policy_patches_required_state_before_retry() -> None:
    engine = RecoveryEngine()
    error = make_error(ErrorCategory.STATE_FAILURE, error_id="err_state_preflight_001")
    error.evidence.tool_id = "send_message_with_phone_number"
    error.evidence.raw_message = "Cellular service is not enabled"
    error.evidence.metadata["preflight_state_policy"] = {
        "state_slot": "cellular_service_status",
        "required_value": True,
        "repair_target": "cellular_service_status",
        "repair_value": True,
        "auto_repair": True,
    }
    error.state_context.missing_assets = ["cellular_service_status"]

    repair = engine.plan_repair(error)

    assert repair.repair_type == RepairType.ACQUIRE_MISSING_ASSET
    assert repair.interaction.ask_user is False
    assert repair.actions[0].target == "state.cellular_service_status"
    assert repair.actions[0].value is True
