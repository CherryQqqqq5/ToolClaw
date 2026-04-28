"""Classify blocked states into actionable uncertainty labels for IRC."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
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
        continuation_missing_input_keys = self._continuation_missing_input_keys(step)
        for input_key in continuation_missing_input_keys:
            if input_key not in missing_input_keys:
                missing_input_keys.append(input_key)
        for input_key in self._repair_missing_targets(repair):
            if input_key not in missing_input_keys:
                missing_input_keys.append(input_key)
        missing_assets = self._collect_missing_assets(
            workflow=workflow,
            step=step,
            state_values=state_values,
            missing_input_keys=missing_input_keys,
        )
        unsatisfied_state_slots = self._collect_unsatisfied_state_slots(step=step, state_values=state_values)
        for slot in unsatisfied_state_slots:
            if slot not in missing_assets:
                missing_assets.append(slot)
        for source in (repair.metadata.get("missing_assets", []),):
            if not isinstance(source, list):
                continue
            for item in source:
                asset = str(item)
                if asset and asset not in missing_assets:
                    missing_assets.append(asset)
        failed_tool_id = str(repair.metadata.get("failed_tool_id") or (step.tool_id if step else "") or "")
        continuation_backup_tool_id = self._continuation_backup_tool_id(step)
        backup_tool_id = str(repair.metadata.get("backup_tool_id") or continuation_backup_tool_id or "")
        available_tool_ids = [tool.tool_id for tool in workflow.context.candidate_tools]
        alternative_tool_ids = [
            tool_id for tool_id in available_tool_ids if tool_id and tool_id != failed_tool_id
        ]
        approval_pending = step_id not in set(state_values.get("__approved_steps__", []))
        constraint_requires_approval = bool(workflow.task.constraints.requires_user_approval and approval_pending)
        branch_options = self._collect_branch_options(step=step, repair=repair)
        remaining_user_turns = self._remaining_user_turns(workflow=workflow, state_values=state_values)
        stale_assets = [
            str(item)
            for item in state_values.get("__stale_state_slots__", [])
            if str(item)
        ]
        for item in repair.metadata.get("stale_assets", []):
            asset = str(item)
            if asset and asset not in stale_assets:
                stale_assets.append(asset)
        for slot in unsatisfied_state_slots:
            if slot not in stale_assets:
                stale_assets.append(slot)

        if repair.repair_type == RepairType.REQUEST_APPROVAL:
            return UncertaintyReport(
                primary_label="policy_approval",
                confidence=0.95,
                conflicts=[ConstraintConflict(conflict_type="approval", rationale="policy requires confirmation")],
                metadata={
                    "state_keys": sorted(state_values.keys()),
                    "step_id": step_id,
                    "missing_input_keys": missing_input_keys,
                    "missing_assets": missing_assets,
                    "stale_assets": stale_assets,
                    "failed_tool_id": failed_tool_id or None,
                    "backup_tool_id": backup_tool_id or None,
                    "available_tool_ids": available_tool_ids,
                    "alternative_tool_ids": alternative_tool_ids,
                    "branch_options": branch_options,
                    "error_category": error_category,
                    "continuation_backup_tool_id": continuation_backup_tool_id or None,
                    "patch_targets": {"approved": "policy.approved"},
                    "constraint_source": "policy",
                    "constraint_requires_approval": True,
                    "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "forbidden_actions": list(workflow.task.constraints.forbidden_actions),
                        "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "remaining_user_turns": remaining_user_turns,
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
                        "constraint_requires_approval": constraint_requires_approval,
                        "remaining_user_turns": remaining_user_turns,
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
                    "constraint_requires_approval": constraint_requires_approval,
                    "remaining_user_turns": remaining_user_turns,
                },
            )
        return UncertaintyReport(
            primary_label="recoverable_runtime_error",
            confidence=0.6,
            metadata={
                "state_keys": sorted(state_values.keys()),
                "step_id": step_id,
                "remaining_user_turns": remaining_user_turns,
            },
        )

    @staticmethod
    def _repair_missing_targets(repair: Repair) -> List[str]:
        missing: List[str] = []

        def add_targets(raw_targets: Any) -> None:
            if not isinstance(raw_targets, list):
                return
            for item in raw_targets:
                target = str(item or "").strip()
                if target and target not in missing:
                    missing.append(target)

        for source_key in ("missing_assets", "missing_input_keys", "unresolved_required_inputs"):
            add_targets(repair.metadata.get(source_key, []))
        for action in repair.actions:
            metadata = action.metadata if isinstance(action.metadata, dict) else {}
            add_targets(metadata.get("missing_targets", []))
        question = str(getattr(repair.interaction, "question", "") or "")
        for match in re.finditer(r"`([^`]+)`", question):
            for item in str(match.group(1)).split(","):
                target = item.strip()
                if target and target not in missing:
                    missing.append(target)
        return missing

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
        required_input_keys = step.metadata.get("required_input_keys", [])
        if not isinstance(required_input_keys, list):
            required_input_keys = []
        input_bindings = step.metadata.get("input_bindings", {})
        if not isinstance(input_bindings, dict):
            input_bindings = {}
        state_bindings = step.metadata.get("state_bindings", {})
        if not isinstance(state_bindings, dict):
            state_bindings = {}
        implicit_fallbacks = step.metadata.get("implicit_state_fallback_slots", [])
        if not isinstance(implicit_fallbacks, list):
            implicit_fallbacks = []
        for key in required_input_keys:
            key_text = str(key).strip()
            if not key_text:
                continue
            current_value = step.inputs.get(key_text)
            if key_text in missing or (current_value is not None and current_value != ""):
                continue
            if key_text in input_bindings or key_text in state_bindings or key_text in implicit_fallbacks:
                continue
            missing.append(key_text)
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
                if key not in missing_assets:
                    missing_assets.append(key)
            for slot in step.metadata.get("required_state_slots", []):
                slot_text = str(slot)
                if not slot_text:
                    continue
                current_state_value = state_values.get(slot_text)
                if slot_text not in state_values or current_state_value is None or current_state_value == "":
                    if slot_text not in missing_assets:
                        missing_assets.append(slot_text)
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
    def _collect_unsatisfied_state_slots(step: Any, state_values: Dict[str, Any]) -> List[str]:
        if step is None:
            return []
        preflight_policy = step.metadata.get("preflight_state_policy", {})
        if not isinstance(preflight_policy, dict):
            return []
        state_slot = str(preflight_policy.get("state_slot") or "")
        if not state_slot:
            return []
        required_value = preflight_policy.get("required_value")
        current_state_value = state_values.get(state_slot)
        if state_slot not in state_values or current_state_value is None or current_state_value == "":
            return []
        if required_value is not None and state_values.get(state_slot) != required_value:
            return [state_slot]
        return []

    @staticmethod
    def _remaining_user_turns(workflow: Workflow, state_values: Dict[str, Any]) -> Optional[int]:
        remaining_budgets = state_values.get("__remaining_budgets__", {})
        if isinstance(remaining_budgets, dict) and remaining_budgets.get("user_turns") is not None:
            return int(remaining_budgets["user_turns"])
        if workflow.task.constraints.max_user_turns is None:
            return None
        return int(workflow.task.constraints.max_user_turns) - int(state_values.get("__user_turns__", 0))

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
    def _continuation_missing_input_keys(step: Any) -> List[str]:
        if step is None:
            return []
        continuation_hints = step.metadata.get("continuation_hints", [])
        if not isinstance(continuation_hints, list):
            continuation_hints = []
        missing_input_keys: List[str] = []
        for hint in continuation_hints:
            if not isinstance(hint, dict):
                continue
            for item in hint.get("patched_input_keys", []):
                key = str(item).strip()
                if key and key not in missing_input_keys:
                    missing_input_keys.append(key)
        metadata_keys = step.metadata.get("continuation_missing_input_keys", [])
        if isinstance(metadata_keys, list):
            for item in metadata_keys:
                key = str(item).strip()
                if key and key not in missing_input_keys:
                    missing_input_keys.append(key)
        return missing_input_keys

    @staticmethod
    def _continuation_backup_tool_id(step: Any) -> str:
        if step is None:
            return ""
        metadata_backup_tool_id = str(step.metadata.get("continuation_backup_tool_id") or "").strip()
        if metadata_backup_tool_id:
            return metadata_backup_tool_id
        continuation_hints = step.metadata.get("continuation_hints", [])
        if not isinstance(continuation_hints, list):
            return ""
        for hint in continuation_hints:
            if not isinstance(hint, dict):
                continue
            backup_tool_id = str(hint.get("backup_tool_id") or "").strip()
            if backup_tool_id:
                return backup_tool_id
        return ""

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
        return bool(backup_tool_id or alternative_tool_ids)
