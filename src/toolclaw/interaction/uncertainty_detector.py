"""Classify blocked states into actionable uncertainty labels for IRC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from toolclaw.schemas.repair import Repair, RepairType
from toolclaw.schemas.workflow import Workflow


@dataclass
class InformationGap:
    gap_type: str
    target: Optional[str] = None
    rationale: str = ""


@dataclass
class ConstraintConflict:
    conflict_type: str
    rationale: str = ""


@dataclass
class UncertaintyReport:
    primary_label: str
    confidence: float
    information_gaps: List[InformationGap] = field(default_factory=list)
    conflicts: List[ConstraintConflict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UncertaintyDetector:
    def analyze_failure(
        self,
        workflow: Workflow,
        repair: Repair,
        state_values: Dict[str, Any],
    ) -> UncertaintyReport:
        step_id = self._resolve_repair_step_id(workflow, repair)
        step = workflow.get_step(step_id)
        missing_input_keys = self._infer_missing_input_keys(step)
        if repair.repair_type == RepairType.REQUEST_APPROVAL:
            return UncertaintyReport(
                primary_label="approval_needed",
                confidence=0.95,
                conflicts=[ConstraintConflict(conflict_type="approval", rationale="policy requires confirmation")],
                metadata={
                    "state_keys": sorted(state_values.keys()),
                    "step_id": step_id,
                    "patch_targets": {"approved": "policy.approved"},
                },
            )
        if repair.repair_type == RepairType.ASK_USER:
            return UncertaintyReport(
                primary_label="missing_info",
                confidence=0.85,
                information_gaps=[InformationGap(gap_type="asset_or_constraint", rationale="repair requires user guidance")],
                metadata={
                    "state_keys": sorted(state_values.keys()),
                    "step_id": step_id,
                    "missing_input_keys": missing_input_keys,
                    "failed_tool_id": repair.metadata.get("failed_tool_id"),
                    "backup_tool_id": repair.metadata.get("backup_tool_id"),
                    "error_category": repair.metadata.get("mapped_from_error_category"),
                },
            )
        return UncertaintyReport(
            primary_label="recoverable_runtime_error",
            confidence=0.6,
            metadata={"state_keys": sorted(state_values.keys()), "step_id": step_id},
        )

    @staticmethod
    def _resolve_repair_step_id(workflow: Workflow, repair: Repair) -> str:
        if repair.workflow_patch.modified_steps:
            return repair.workflow_patch.modified_steps[0]
        for action in repair.actions:
            if action.target and action.target.startswith("step_"):
                return action.target.split(".")[0]
        return workflow.execution_plan[-1].step_id if workflow.execution_plan else "step_01"

    @staticmethod
    def _infer_missing_input_keys(step: Any) -> List[str]:
        if step is None:
            return []
        missing: List[str] = []
        if step.capability_id == "cap_write" and not step.inputs.get("target_path"):
            missing.append("target_path")
        return missing
