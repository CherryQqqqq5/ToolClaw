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