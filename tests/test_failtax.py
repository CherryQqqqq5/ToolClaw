from toolclaw.execution.failtax import FailTaxClassifier
from toolclaw.schemas.error import ErrorCategory, ErrorEvidence, ErrorStage, ErrorSeverity, Recoverability, StateContext, ToolClawError
from toolclaw.schemas.workflow import Workflow


def make_error(category: ErrorCategory, message: str) -> ToolClawError:
    return ToolClawError(
        error_id="err_failtax_001",
        run_id="run_failtax_001",
        workflow_id="wf_failtax_001",
        step_id="step_01",
        category=category,
        subtype="test",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=[message],
        evidence=ErrorEvidence(tool_id="write_tool", raw_message=message),
        root_cause_hypothesis=["test"],
        state_context=StateContext(active_step_id="step_01"),
        recoverability=Recoverability(recoverable=True),
    )


def test_failtax_classifier_maps_binding_failure() -> None:
    workflow = Workflow.demo()
    record = FailTaxClassifier().classify_failure(make_error(ErrorCategory.BINDING_FAILURE, "missing required field"), workflow.execution_plan[1], {})
    assert record.failtax_label.value == "binding_failure"


def test_failtax_classifier_maps_policy_failure() -> None:
    workflow = Workflow.demo()
    record = FailTaxClassifier().classify_failure(make_error(ErrorCategory.POLICY_FAILURE, "approval required"), workflow.execution_plan[1], {})
    assert record.failtax_label.value == "policy_failure"
