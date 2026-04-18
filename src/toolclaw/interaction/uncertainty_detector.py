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
        error_category = str(repair.metadata.get("mapped_from_error_category") or "unknown")
        missing_input_keys = self._infer_missing_input_keys(step)
        missing_assets = self._collect_missing_assets(
            workflow=workflow,
            step=step,
            state_values=state_values,
            missing_input_keys=missing_input_keys,
        )
        for source in (repair.metadata.get("missing_assets", []),):
            if not isinstance(source, list):
                continue
            for item in source:
                asset = str(item)
                if asset and asset not in missing_assets:
                    missing_assets.append(asset)
        failed_tool_id = str(repair.metadata.get("failed_tool_id") or (step.tool_id if step else "") or "")
        backup_tool_id = str(repair.metadata.get("backup_tool_id") or "")
        available_tool_ids = [tool.tool_id for tool in workflow.context.candidate_tools]
        alternative_tool_ids = [
            tool_id for tool_id in available_tool_ids if tool_id and tool_id != failed_tool_id
        ]
        branch_options = self._collect_branch_options(step=step, repair=repair)
        stale_assets = [
            str(item)
            for item in state_values.get("__stale_state_slots__", [])
            if str(item)
        ]
        for item in repair.metadata.get("stale_assets", []):
            asset = str(item)
            if asset and asset not in stale_assets:
                stale_assets.append(asset)

        if repair.repair_type == RepairType.REQUEST_APPROVAL:
            return UncertaintyReport(
                primary_label="policy_approval",
                confidence=0.95,
                conflicts=[ConstraintConflict(conflict_type="approval", rationale="policy requires confirmation")],
                metadata={
                    "state_keys": sorted(state_values.keys()),
                    "step_id": step_id,
                    "patch_targets": {"approved": "policy.approved"},
                    "constraint_source": "policy",
                },
            )
        if repair.repair_type == RepairType.ASK_USER:
            if missing_assets:
                return UncertaintyReport(
                    primary_label="missing_asset",
                    confidence=0.9,
                    information_gaps=[
                        InformationGap(gap_type="missing_asset", target=asset, rationale="blocked step is missing a required asset")
                        for asset in missing_assets
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "missing_input_keys": missing_input_keys,
                        "missing_assets": missing_assets,
                        "failed_tool_id": failed_tool_id or None,
                        "backup_tool_id": backup_tool_id or None,
                        "error_category": error_category,
                    },
                )
            if error_category == "state_failure" and stale_assets:
                return UncertaintyReport(
                    primary_label="stale_state",
                    confidence=0.86,
                    information_gaps=[
                        InformationGap(gap_type="stale_state", target=asset, rationale="blocked step needs refreshed state before retry")
                        for asset in stale_assets
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "stale_assets": stale_assets,
                        "missing_assets": stale_assets,
                        "failed_tool_id": failed_tool_id or None,
                        "backup_tool_id": backup_tool_id or None,
                        "error_category": error_category,
                    },
                )
            if self._is_constraint_conflict(workflow=workflow, repair=repair, error_category=error_category):
                return UncertaintyReport(
                    primary_label="constraint_conflict",
                    confidence=0.84,
                    conflicts=[
                        ConstraintConflict(
                            conflict_type="hard_or_policy_constraint",
                            rationale="execution is blocked by a constraint or permission requirement",
                        )
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "error_category": error_category,
                        "failed_tool_id": failed_tool_id or None,
                        "constraint_requires_approval": bool(workflow.task.constraints.requires_user_approval),
                        "forbidden_actions": list(workflow.task.constraints.forbidden_actions),
                    },
                )
            if branch_options:
                return UncertaintyReport(
                    primary_label="branch_disambiguation",
                    confidence=0.8,
                    information_gaps=[
                        InformationGap(
                            gap_type="branch_choice",
                            rationale="multiple viable execution branches remain available",
                        )
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "branch_options": branch_options,
                        "failed_tool_id": failed_tool_id or None,
                        "backup_tool_id": backup_tool_id or None,
                        "error_category": error_category,
                    },
                )
            if self._is_tool_mismatch(
                error_category=error_category,
                failed_tool_id=failed_tool_id,
                backup_tool_id=backup_tool_id,
                alternative_tool_ids=alternative_tool_ids,
            ):
                return UncertaintyReport(
                    primary_label="tool_mismatch",
                    confidence=0.78,
                    conflicts=[
                        ConstraintConflict(
                            conflict_type="tool_binding",
                            rationale="the blocked step likely needs a different tool binding",
                        )
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "failed_tool_id": failed_tool_id or None,
                        "backup_tool_id": backup_tool_id or None,
                        "available_tool_ids": available_tool_ids,
                        "alternative_tool_ids": alternative_tool_ids,
                        "error_category": error_category,
                    },
                )
            if error_category == "environment_failure":
                return UncertaintyReport(
                    primary_label="environment_unavailable",
                    confidence=0.76,
                    conflicts=[
                        ConstraintConflict(
                            conflict_type="environment",
                            rationale="the active environment or route is unavailable",
                        )
                    ],
                    metadata={
                        "state_keys": sorted(state_values.keys()),
                        "step_id": step_id,
                        "failed_tool_id": failed_tool_id or None,
                        "backup_tool_id": backup_tool_id or None,
                        "available_tool_ids": available_tool_ids,
                        "error_category": error_category,
                    },
                )
            return UncertaintyReport(
                primary_label="execution_guidance",
                confidence=0.85,
                information_gaps=[InformationGap(gap_type="user_guidance", rationale="repair requires a direct tool, asset, or path hint")],
                metadata={
                    "state_keys": sorted(state_values.keys()),
                    "step_id": step_id,
                    "missing_input_keys": missing_input_keys,
                    "missing_assets": missing_assets,
                    "failed_tool_id": failed_tool_id or None,
                    "backup_tool_id": backup_tool_id or None,
                    "available_tool_ids": available_tool_ids,
                    "alternative_tool_ids": alternative_tool_ids,
                    "branch_options": branch_options,
                    "error_category": error_category,
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

    @staticmethod
    def _collect_missing_assets(
        *,
        workflow: Workflow,
        step: Any,
        state_values: Dict[str, Any],
        missing_input_keys: List[str],
    ) -> List[str]:
        missing_assets: List[str] = []
        if step is not None:
            for key in missing_input_keys:
                scoped_key = f"{step.step_id}.{key}"
                if scoped_key not in missing_assets and key not in missing_assets:
                    missing_assets.append(key)
        for source in (
            workflow.context.environment.missing_assets,
            state_values.get("__missing_assets__", []),
        ):
            if not isinstance(source, list):
                continue
            for item in source:
                asset = str(item)
                if asset and asset not in missing_assets:
                    missing_assets.append(asset)
        return missing_assets

    @staticmethod
    def _collect_branch_options(step: Any, repair: Repair) -> List[str]:
        branch_options: List[str] = []
        for source in (
            repair.metadata.get("branch_options"),
            step.metadata.get("branch_options") if step is not None else None,
        ):
            if not isinstance(source, list):
                continue
            for item in source:
                option = str(item)
                if option and option not in branch_options:
                    branch_options.append(option)
        return branch_options

    @staticmethod
    def _is_constraint_conflict(
        *,
        workflow: Workflow,
        repair: Repair,
        error_category: str,
    ) -> bool:
        if error_category in {"constraint_failure", "permission_failure", "policy_failure"}:
            return True
        if workflow.task.constraints.requires_user_approval:
            return True
        if workflow.task.constraints.forbidden_actions:
            return True
        question = (repair.interaction.question or "").lower()
        return "constraint" in question or "permission" in question or "approve" in question

    @staticmethod
    def _is_tool_mismatch(
        *,
        error_category: str,
        failed_tool_id: str,
        backup_tool_id: str,
        alternative_tool_ids: List[str],
    ) -> bool:
        if error_category not in {"selection_failure", "binding_failure", "environment_failure"}:
            return False
        if not failed_tool_id:
            return False
        if error_category == "environment_failure":
            return bool(backup_tool_id)
        return bool(backup_tool_id or alternative_tool_ids)
