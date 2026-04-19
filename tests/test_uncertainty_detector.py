from toolclaw.interaction.uncertainty_detector import UncertaintyDetector
from toolclaw.schemas.repair import Repair, RepairInteraction, RepairType
from toolclaw.schemas.workflow import Workflow


def test_uncertainty_detector_marks_approval_needed() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.REQUEST_APPROVAL
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "policy_approval"


def test_uncertainty_detector_exposes_missing_required_state_slots_during_approval() -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.requires_user_approval = True
    workflow.execution_plan[1].metadata["required_state_slots"] = ["approval_note"]
    repair = Repair.demo()
    repair.repair_type = RepairType.REQUEST_APPROVAL

    report = UncertaintyDetector().analyze_failure(workflow, repair, {})

    assert report.primary_label == "policy_approval"
    assert "approval_note" in report.metadata["missing_assets"]
    assert report.metadata["constraint_requires_approval"] is True


def test_uncertainty_detector_exposes_continuation_repair_shape_during_approval() -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.requires_user_approval = True
    workflow.execution_plan[1].metadata["continuation_hints"] = [
        {
            "kind": "patch_then_retry_same_step",
            "patched_input_keys": ["target_path"],
        },
        {
            "kind": "fallback_to_backup_then_resume",
            "backup_tool_id": "backup_write_tool",
        },
    ]
    repair = Repair.demo()
    repair.repair_type = RepairType.REQUEST_APPROVAL

    report = UncertaintyDetector().analyze_failure(workflow, repair, {})

    assert report.primary_label == "policy_approval"
    assert "target_path" in report.metadata["missing_input_keys"]
    assert report.metadata["backup_tool_id"] == "backup_write_tool"
    assert report.metadata["continuation_backup_tool_id"] == "backup_write_tool"


def test_uncertainty_detector_marks_missing_asset_for_ask_user() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    workflow.execution_plan[1].inputs.pop("target_path", None)
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "missing_asset"
    assert report.metadata["missing_input_keys"] == ["target_path"]


def test_uncertainty_detector_marks_constraint_conflict_for_permission_failures() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    repair.metadata["mapped_from_error_category"] = "permission_failure"
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "constraint_conflict"


def test_uncertainty_detector_marks_branch_disambiguation_when_branch_options_exist() -> None:
    workflow = Workflow.demo()
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    repair.metadata["branch_options"] = ["primary_path", "fallback_path"]
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "branch_disambiguation"
    assert report.metadata["branch_options"] == ["primary_path", "fallback_path"]


def test_uncertainty_detector_uses_execution_guidance_when_no_real_branch_options_exist() -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["target_path"] = "outputs/reports/demo_report.txt"
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    repair.metadata["mapped_from_error_category"] = "unknown"
    repair.interaction = RepairInteraction(
        ask_user=True,
        question="The current tool/environment failed at step_02. Do you want to provide an alternative tool, missing asset, or allow a different execution path?",
        expected_answer_type="tool_or_asset_hint",
    )
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "execution_guidance"
    assert report.metadata["branch_options"] == []


def test_uncertainty_detector_marks_tool_mismatch_when_alternative_tool_exists() -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["target_path"] = "outputs/reports/demo_report.txt"
    workflow.context.candidate_tools.append(
        workflow.context.candidate_tools[1].__class__(
            tool_id="backup_write_tool",
            description="Backup writer",
        )
    )
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    repair.metadata["mapped_from_error_category"] = "binding_failure"
    repair.metadata["failed_tool_id"] = "write_tool"
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "tool_mismatch"
    assert "backup_write_tool" in report.metadata["alternative_tool_ids"]


def test_uncertainty_detector_marks_environment_unavailable_without_tool_alternative() -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["target_path"] = "outputs/reports/demo_report.txt"
    workflow.context.candidate_tools = [tool for tool in workflow.context.candidate_tools if tool.tool_id == "write_tool"]
    repair = Repair.demo()
    repair.repair_type = RepairType.ASK_USER
    repair.metadata["mapped_from_error_category"] = "environment_failure"
    repair.metadata["failed_tool_id"] = "write_tool"
    repair.interaction = RepairInteraction(
        ask_user=True,
        question="The environment failed and no alternate route is currently configured.",
        expected_answer_type="tool_or_asset_hint",
    )
    report = UncertaintyDetector().analyze_failure(workflow, repair, {})
    assert report.primary_label == "environment_unavailable"
