"""Translate classified failures into concrete repair plans for the executor."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from toolclaw.schemas.error import ToolClawError, ErrorCategory
from toolclaw.schemas.repair import (
    PolicyPatch,
    Repair,
    RepairAction,
    RepairActionType,
    RepairDecision,
    RepairInteraction,
    RepairPostConditions,
    RepairResult,
    RepairStatus,
    RepairStrategy,
    RepairType,
    WorkflowPatch,
)

PLACEHOLDER_ARGUMENT_STRINGS = {
    "",
    "unknown",
    "none",
    "null",
    "n/a",
    "na",
    "not provided",
    "not_given",
    "unspecified",
}


@dataclass
class RecoveryConfig:
    ask_user_on_environment_failure_without_backup: bool = True
    default_binding_patch_source: str = "state://auto_bound_value"
    enable_tool_fallback: bool = True
    prefer_user_mediated_binding_repair: bool = False


class RecoveryEngine:
    """
    Phase-1 recovery engine.

    Currently supported mappings:
    1. binding_failure -> rebind_args
    2. environment_failure -> switch_tool / ask_user
    3. policy_failure -> request_approval
    """

    def __init__(self, config: Optional[RecoveryConfig] = None) -> None:
        self.config = config or RecoveryConfig()

    def plan_repair(
        self,
        error: ToolClawError,
        backup_tool_id: Optional[str] = None,
    ) -> Repair:
        if error.category == ErrorCategory.BINDING_FAILURE:
            return self._repair_binding_failure(error)

        if error.category == ErrorCategory.ENVIRONMENT_FAILURE:
            return self._repair_environment_failure(
                error=error,
                backup_tool_id=backup_tool_id,
            )
        if error.category == ErrorCategory.STATE_FAILURE:
            return self._repair_state_failure(error)
        if error.category == ErrorCategory.POLICY_FAILURE:
            return self._repair_policy_failure(error)
        if error.category in {ErrorCategory.ORDERING_FAILURE, ErrorCategory.PERMISSION_FAILURE, ErrorCategory.RECOVERY_FAILURE}:
            return self._repair_replan_or_rollback(error)

        raise NotImplementedError(
            f"Phase-1 recovery currently does not support category={error.category.value}"
        )

    def _repair_binding_failure(self, error: ToolClawError) -> Repair:
        step_id = error.step_id or "unknown_step"
        missing_target = None
        raw_message = str(error.evidence.raw_message or "")
        repaired_inputs = self._sanitize_binding_inputs(
            tool_id=error.evidence.tool_id,
            inputs=error.evidence.inputs,
            raw_message=raw_message,
        )
        evidence_metadata = error.evidence.metadata if isinstance(error.evidence.metadata, dict) else {}
        repair_default_inputs = (
            dict(evidence_metadata.get("repair_default_inputs", {}))
            if isinstance(evidence_metadata.get("repair_default_inputs", {}), dict)
            else {}
        )
        simulated_missing_arg_values = (
            dict(evidence_metadata.get("simulated_missing_arg_values", {}))
            if isinstance(evidence_metadata.get("simulated_missing_arg_values", {}), dict)
            else {}
        )

        parsed_missing = self._extract_missing_required_fields(raw_message)
        if parsed_missing:
            missing_target = parsed_missing[0]

        if error.state_context.missing_assets:
            missing_target = error.state_context.missing_assets[0]

        if not missing_target:
            for candidate in ("target_path", "retrieved_info", "retrieved_summary"):
                if candidate not in repaired_inputs and (
                    candidate in repair_default_inputs or candidate in simulated_missing_arg_values
                ):
                    missing_target = candidate
                    break

        candidate_value = None
        if missing_target:
            candidate_value = repair_default_inputs.get(missing_target, simulated_missing_arg_values.get(missing_target))

        if (
            self.config.prefer_user_mediated_binding_repair
            and missing_target
            and repaired_inputs == error.evidence.inputs
            and self._binding_slot_prefers_user_input(missing_target)
        ):
            suggested_values = {missing_target: candidate_value} if candidate_value not in (None, "") else {}
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.ASK_USER,
                decision=RepairDecision(
                    strategy=RepairStrategy.USER_IN_THE_LOOP,
                    rationale="Binding failure is missing a user-facing argument, so execution asks for an explicit patch before retry.",
                    confidence=0.82,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_ask_{error.error_id}",
                        action_type=RepairActionType.ASK_USER,
                        target=step_id,
                        metadata={"missing_target": missing_target},
                    )
                ],
                interaction=RepairInteraction(
                    ask_user=True,
                    question=f"Provide `{missing_target}` so step {step_id} can continue.",
                    expected_answer_type="target_path_patch" if missing_target == "target_path" else "missing_asset_patch",
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(modified_steps=[step_id] if error.step_id else []),
                post_conditions=RepairPostConditions(
                    expected_effects=[
                        f"{missing_target} is explicitly confirmed or supplied",
                        "the failed step can be retried with a user-mediated patch",
                    ],
                    stop_if=[
                        "same binding_failure repeats twice",
                        "patched value is still rejected by tool constraints",
                    ],
                ),
                result=RepairResult(status=RepairStatus.PENDING, success=None),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "missing_assets": [missing_target],
                    "suggested_values": suggested_values,
                    "phase": "phase1_training_free",
                },
            )

        target_expr = f"{step_id}.inputs.{missing_target}" if missing_target else f"{step_id}.inputs"
        patch_value: object = missing_target or "auto_filled_value"
        rationale = "Binding failure is treated as an argument-mapping error and patched by rebinding inputs."
        expected_effects = [
            "tool arguments become valid",
            "the failed step can be re-executed",
        ]
        if missing_target:
            if candidate_value not in (None, ""):
                patch_value = candidate_value
                rationale = "Binding failure exposes a missing argument, so the repair restores the known default input before retry."
                expected_effects = [
                    f"{missing_target} is restored from benchmark defaults",
                    "the failed step can be re-executed with a concrete patch",
                ]
        if repaired_inputs and repaired_inputs != error.evidence.inputs:
            target_expr = f"{step_id}.inputs"
            patch_value = repaired_inputs
            rationale = "Binding failure matches an invalid-argument pattern, so placeholder and malformed filters are stripped before retry."
            expected_effects = [
                "invalid optional arguments are removed",
                "the failed step can be re-executed with sanitized inputs",
            ]
        elif missing_target and isinstance(patch_value, str) and patch_value == missing_target:
            patch_value = (
                repair_default_inputs.get(missing_target)
                or simulated_missing_arg_values.get(missing_target)
                or self._default_binding_value_for_slot(missing_target)
            )

        repair = Repair(
            repair_id=f"rep_{error.error_id}",
            run_id=error.run_id,
            workflow_id=error.workflow_id,
            triggered_error_ids=[error.error_id],
            repair_type=RepairType.REBIND_ARGS,
            decision=RepairDecision(
                strategy=RepairStrategy.DIRECT_PATCH,
                rationale=rationale,
                confidence=0.80,
            ),
            actions=[
                RepairAction(
                    action_id=f"act_patch_{error.error_id}",
                    action_type=RepairActionType.STATE_PATCH,
                    target=target_expr,
                    value_source=self.config.default_binding_patch_source,
                    value=patch_value,
                    metadata={
                        "category": error.category.value,
                        "subtype": error.subtype,
                    },
                ),
                RepairAction(
                    action_id=f"act_retry_{error.error_id}",
                    action_type=RepairActionType.RE_EXECUTE_STEP,
                    target=step_id,
                ),
            ],
            interaction=RepairInteraction(
                ask_user=False,
                question=None,
                expected_answer_type=None,
                user_response=None,
            ),
            workflow_patch=WorkflowPatch(
                modified_steps=[step_id] if error.step_id else [],
            ),
            post_conditions=RepairPostConditions(
                expected_effects=expected_effects,
                stop_if=[
                    "same binding_failure repeats twice",
                    "hard constraint violated",
                ],
            ),
            result=RepairResult(
                status=RepairStatus.PENDING,
                success=None,
            ),
            metadata={
                "mapped_from_error_category": error.category.value,
                "phase": "phase1_training_free",
            },
        )
        return repair

    @staticmethod
    def _extract_missing_required_fields(raw_message: str) -> list[str]:
        if not raw_message:
            return []
        fields: list[str] = []
        for pattern in (
            r"missing required field\(s\):\s*([a-zA-Z0-9_,\s-]+)",
            r"missing required field:\s*([a-zA-Z0-9_ -]+)",
        ):
            match = re.search(pattern, raw_message, flags=re.IGNORECASE)
            if not match:
                continue
            extracted = [part.strip() for part in match.group(1).split(",") if part.strip()]
            for name in extracted:
                normalized = name.lower().replace(" ", "_")
                if normalized not in fields:
                    fields.append(normalized)
            if fields:
                break
        return fields

    @staticmethod
    def _default_binding_value_for_slot(slot: str) -> object:
        lowered = str(slot).lower()
        if lowered in {"enabled", "is_enabled"}:
            return False
        if lowered in {"state", "status", "mode", "value"}:
            return "updated"
        return "auto_filled_value"

    @staticmethod
    def _binding_slot_prefers_user_input(slot: str) -> bool:
        lowered = str(slot).strip().lower()
        auto_patchable = {"enabled", "is_enabled", "state", "status", "mode", "value"}
        return bool(lowered) and lowered not in auto_patchable

    def _repair_environment_failure(
        self,
        error: ToolClawError,
        backup_tool_id: Optional[str] = None,
    ) -> Repair:
        step_id = error.step_id or "unknown_step"
        failed_tool_id = error.evidence.tool_id

        if backup_tool_id and self.config.enable_tool_fallback:
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.SWITCH_TOOL,
                decision=RepairDecision(
                    strategy=RepairStrategy.FALLBACK,
                    rationale="Environment failure is repaired by switching to a backup tool.",
                    confidence=0.76,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_switch_{error.error_id}",
                        action_type=RepairActionType.SWITCH_TOOL,
                        target=step_id,
                        value_source="backup_tool_registry",
                        value=backup_tool_id,
                        metadata={
                            "from_tool": failed_tool_id,
                            "to_tool": backup_tool_id,
                        },
                    ),
                    RepairAction(
                        action_id=f"act_retry_{error.error_id}",
                        action_type=RepairActionType.RE_EXECUTE_STEP,
                        target=step_id,
                    ),
                ],
                interaction=RepairInteraction(
                    ask_user=False,
                    question=None,
                    expected_answer_type=None,
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(
                    modified_steps=[step_id] if error.step_id else [],
                ),
                post_conditions=RepairPostConditions(
                    expected_effects=[
                        "execution switches to a backup tool",
                        "the failed step can continue with fallback path",
                    ],
                    stop_if=[
                        "backup tool also fails with environment_failure",
                        "hard constraint violated",
                    ],
                ),
                result=RepairResult(
                    status=RepairStatus.PENDING,
                    success=None,
                ),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "failed_tool_id": failed_tool_id,
                    "backup_tool_id": backup_tool_id,
                    "phase": "phase1_training_free",
                },
            )

        if self.config.ask_user_on_environment_failure_without_backup:
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.ASK_USER,
                decision=RepairDecision(
                    strategy=RepairStrategy.USER_IN_THE_LOOP,
                    rationale="No backup tool is available, so the system asks the user for guidance or missing environment information.",
                    confidence=0.72,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_ask_{error.error_id}",
                        action_type=RepairActionType.ASK_USER,
                        target=step_id,
                        metadata={
                            "failed_tool": failed_tool_id,
                        },
                    ),
                ],
                interaction=RepairInteraction(
                    ask_user=True,
                    question=(
                        f"The current tool/environment failed at {step_id}. "
                        "Do you want to provide an alternative tool, missing asset, or allow a different execution path?"
                    ),
                    expected_answer_type="tool_or_asset_hint",
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(
                    modified_steps=[],
                ),
                post_conditions=RepairPostConditions(
                    expected_effects=[
                        "user provides missing environment hint or fallback path",
                    ],
                    stop_if=[
                        "user aborts workflow",
                        "required environment remains unavailable",
                    ],
                ),
                result=RepairResult(
                    status=RepairStatus.PENDING,
                    success=None,
                ),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "failed_tool_id": failed_tool_id,
                    "phase": "phase1_training_free",
                },
            )

        raise NotImplementedError(
            "Environment failure occurred without backup tool, and ask_user fallback is disabled."
        )

    def _repair_policy_failure(self, error: ToolClawError) -> Repair:
        step_id = error.step_id or "unknown_step"
        return Repair(
            repair_id=f"rep_{error.error_id}",
            run_id=error.run_id,
            workflow_id=error.workflow_id,
            triggered_error_ids=[error.error_id],
            repair_type=RepairType.REQUEST_APPROVAL,
            decision=RepairDecision(
                strategy=RepairStrategy.USER_IN_THE_LOOP,
                rationale="Policy gate requires explicit approval before execution can continue.",
                confidence=0.9,
            ),
            actions=[
                RepairAction(
                    action_id=f"act_approve_{error.error_id}",
                    action_type=RepairActionType.REQUEST_APPROVAL,
                    target=step_id,
                )
            ],
            interaction=RepairInteraction(
                ask_user=True,
                question=f"Step {step_id} requires approval due to policy constraints. Approve execution?",
                expected_answer_type="approval",
                user_response=None,
            ),
            workflow_patch=WorkflowPatch(modified_steps=[step_id] if error.step_id else []),
            policy_patch=PolicyPatch(approval_pending=True),
            post_conditions=RepairPostConditions(
                expected_effects=["approval decision is recorded", "execution can resume if approved"],
                stop_if=["user rejects approval"],
            ),
            result=RepairResult(status=RepairStatus.PENDING, success=None),
            metadata={"mapped_from_error_category": error.category.value, "phase": "phase1_training_free"},
        )

    def _repair_state_failure(self, error: ToolClawError) -> Repair:
        step_id = error.step_id or "unknown_step"
        missing_assets = list(error.state_context.missing_assets)
        stale_assets = [
            str(item)
            for item in error.state_context.state_values.get("__stale_state_slots__", [])
            if str(item)
        ]
        preflight_policy = error.evidence.metadata.get("preflight_state_policy", {})
        if not isinstance(preflight_policy, dict):
            preflight_policy = {}
        simulated_missing_arg_values = error.evidence.metadata.get("simulated_missing_arg_values", {})
        if not isinstance(simulated_missing_arg_values, dict):
            simulated_missing_arg_values = {}
        repair_target = str(preflight_policy.get("repair_target") or "")
        if (
            preflight_policy.get("auto_repair")
            and repair_target
            and preflight_policy.get("repair_value") is not None
        ):
            repair_value = preflight_policy["repair_value"]
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.ACQUIRE_MISSING_ASSET,
                decision=RepairDecision(
                    strategy=RepairStrategy.DIRECT_PATCH,
                    rationale="State failure matches a preflight dependency, so the required runtime state is patched before retry.",
                    confidence=0.84,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_state_patch_{error.error_id}",
                        action_type=RepairActionType.STATE_PATCH,
                        target=f"state.{repair_target}",
                        value_source="state://preflight_policy",
                        value=repair_value,
                        metadata={"state_slot": repair_target},
                    ),
                    RepairAction(
                        action_id=f"act_retry_{error.error_id}",
                        action_type=RepairActionType.RE_EXECUTE_STEP,
                        target=step_id,
                    ),
                ],
                interaction=RepairInteraction(
                    ask_user=False,
                    question=None,
                    expected_answer_type=None,
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(modified_steps=[step_id] if error.step_id else []),
                post_conditions=RepairPostConditions(
                    expected_effects=[
                        f"{repair_target} is restored to the required preflight value",
                        "the blocked step can be retried without asking the user",
                    ],
                    stop_if=[
                        "same state_failure repeats twice",
                        "patched state still violates the preflight policy",
                    ],
                ),
                result=RepairResult(status=RepairStatus.PENDING, success=None),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "missing_assets": missing_assets,
                    "stale_assets": stale_assets,
                    "preflight_state_policy": preflight_policy,
                    "phase": "phase1_training_free",
                },
            )
        patchable_slots = [slot for slot in missing_assets if slot in simulated_missing_arg_values and simulated_missing_arg_values.get(slot) not in (None, "")]
        if patchable_slots:
            slot = patchable_slots[0]
            slot_value = simulated_missing_arg_values.get(slot)
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.ACQUIRE_MISSING_ASSET,
                decision=RepairDecision(
                    strategy=RepairStrategy.DIRECT_PATCH,
                    rationale="State failure has benchmark-provided missing_arg_values, so patch state directly before retry.",
                    confidence=0.86,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_state_patch_{error.error_id}",
                        action_type=RepairActionType.STATE_PATCH,
                        target=f"state.{slot}",
                        value_source="state://simulated_missing_arg_values",
                        value=slot_value,
                        metadata={"state_slot": slot},
                    ),
                    RepairAction(
                        action_id=f"act_retry_{error.error_id}",
                        action_type=RepairActionType.RE_EXECUTE_STEP,
                        target=step_id,
                    ),
                ],
                interaction=RepairInteraction(
                    ask_user=False,
                    question=None,
                    expected_answer_type=None,
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(modified_steps=[step_id] if error.step_id else []),
                post_conditions=RepairPostConditions(
                    expected_effects=[f"{slot} is patched from simulated policy defaults", "the blocked step can be retried"],
                    stop_if=["same state_failure repeats twice", "patched value is rejected by tool constraints"],
                ),
                result=RepairResult(status=RepairStatus.PENDING, success=None),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "missing_assets": missing_assets,
                    "stale_assets": stale_assets,
                    "simulated_missing_arg_values": simulated_missing_arg_values,
                    "phase": "phase1_training_free",
                },
            )
        primary_slot = missing_assets[0] if missing_assets else (stale_assets[0] if stale_assets else "state_slot")
        if missing_assets or stale_assets:
            return Repair(
                repair_id=f"rep_{error.error_id}",
                run_id=error.run_id,
                workflow_id=error.workflow_id,
                triggered_error_ids=[error.error_id],
                repair_type=RepairType.ASK_USER,
                decision=RepairDecision(
                    strategy=RepairStrategy.USER_IN_THE_LOOP,
                    rationale="State failure requires either restoring a missing slot or refreshing stale state before retry.",
                    confidence=0.82,
                ),
                actions=[
                    RepairAction(
                        action_id=f"act_state_ask_{error.error_id}",
                        action_type=RepairActionType.ASK_USER,
                        target=step_id,
                        metadata={"state_slot": primary_slot},
                    )
                ],
                interaction=RepairInteraction(
                    ask_user=True,
                    question=f"Provide a fresh value for `{primary_slot}` so step {step_id} can resume safely.",
                    expected_answer_type="state_patch",
                    user_response=None,
                ),
                workflow_patch=WorkflowPatch(modified_steps=[step_id] if error.step_id else []),
                post_conditions=RepairPostConditions(
                    expected_effects=["missing or stale state is patched", "the blocked step can be retried"],
                    stop_if=["state remains missing after patch", "patched state is still stale"],
                ),
                result=RepairResult(status=RepairStatus.PENDING, success=None),
                metadata={
                    "mapped_from_error_category": error.category.value,
                    "missing_assets": missing_assets,
                    "stale_assets": stale_assets,
                    "phase": "phase1_training_free",
                },
            )
        return self._repair_replan_or_rollback(error)

    @staticmethod
    def _sanitize_binding_inputs(
        *,
        tool_id: Optional[str],
        inputs: dict[str, object],
        raw_message: Optional[str],
    ) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        for key, value in inputs.items():
            if value is None:
                continue
            if isinstance(value, str):
                normalized = value.strip()
                if normalized.lower() in PLACEHOLDER_ARGUMENT_STRINGS:
                    continue
                sanitized[key] = normalized
                continue
            sanitized[key] = value

        lowered_message = str(raw_message or "").lower()
        if tool_id == "search_contacts" and (
            "numberparseexception" in lowered_message or "missing or invalid default region" in lowered_message
        ):
            sanitized.pop("phone_number", None)
            sanitized.pop("person_id", None)
            sanitized.pop("relationship", None)
            if sanitized.get("is_self") is False:
                sanitized.pop("is_self", None)

        return sanitized

    def _repair_replan_or_rollback(self, error: ToolClawError) -> Repair:
        step_id = error.step_id or "unknown_step"
        return Repair(
            repair_id=f"rep_{error.error_id}",
            run_id=error.run_id,
            workflow_id=error.workflow_id,
            triggered_error_ids=[error.error_id],
            repair_type=RepairType.REPLAN_SUFFIX,
            decision=RepairDecision(
                strategy=RepairStrategy.ROLLBACK_AND_RETRY,
                rationale="Recover by rolling back to a checkpoint and replanning the remaining suffix.",
                confidence=0.78,
            ),
            actions=[
                RepairAction(
                    action_id=f"act_rollback_{error.error_id}",
                    action_type=RepairActionType.ROLLBACK,
                    target=step_id,
                )
            ],
            workflow_patch=WorkflowPatch(modified_steps=[step_id]),
            post_conditions=RepairPostConditions(
                expected_effects=["rollback restores a safe state", "failed suffix is replanned"],
                stop_if=["no valid checkpoint exists", "replanned suffix still violates hard constraints"],
            ),
            result=RepairResult(status=RepairStatus.PENDING, success=None),
            metadata={"mapped_from_error_category": error.category.value, "phase": "phase1_training_free"},
        )
