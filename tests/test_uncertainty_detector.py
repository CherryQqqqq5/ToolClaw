from toolclaw.interaction.uncertainty_detector import UncertaintyDetector
from toolclaw.schemas.repair import Repair, RepairType
from toolclaw.schemas.workflow import Workflow


def test_uncertainty_detector_marks_approval_needed() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.REQUEST_APPROVAL
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "approval_needed"


def test_uncertainty_detector_marks_missing_info_for_ask_user() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "missing_info"
