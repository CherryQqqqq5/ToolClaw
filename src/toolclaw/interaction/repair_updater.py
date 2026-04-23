"""Convert user replies into workflow, policy, and binding patches for resumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from toolclaw.schemas.repair import Repair
from toolclaw.schemas.workflow import Workflow


@dataclass
class InteractionRequest:
    interaction_id: str
    question: str
    expected_answer_type: str
    context_summary: Dict[str, Any] = field(default_factory=dict)
    allowed_response_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserReply:
    interaction_id: str
    payload: Dict[str, Any]
    raw_text: Optional[str] = None
    accepted: bool = True
    status: str = "accept"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResumePatch:
    workflow: Workflow
    resume_step_id: str
    base_state: Dict[str, Any] = field(default_factory=dict)
    state_updates: Dict[str, Any] = field(default_factory=dict)
    policy_updates: Dict[str, Any] = field(default_factory=dict)
    graph_patch: Dict[str, Any] = field(default_factory=dict)
    binding_patch: Dict[str, Any] = field(default_factory=dict)
    missing_asset_patch: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RepairUpdater:
    def build_query(
        self,
        workflow: Workflow,
        repair: Repair,
        state_values: Dict[str, Any],
    ) -> InteractionRequest:
        step_id = self._resolve_repair_step_id(workflow=workflow, repair=repair)
        step = workflow.get_step(step_id)
        failed_tool_id = str(repair.metadata.get("failed_tool_id") or (step.tool_id if step else "") or "")
        missing_input_keys = []
        if step is not None:
            if step.capability_id == "cap_write" and not step.inputs.get("target_path"):
                missing_input_keys.append("target_path")
        branch_options = []
        if step is not None and isinstance(step.metadata.get("branch_options"), list):
            branch_options = [str(item) for item in step.metadata.get("branch_options", []) if str(item)]
        if not branch_options and isinstance(repair.metadata.get("branch_options"), list):
            branch_options = [str(item) for item in repair.metadata.get("branch_options", []) if str(item)]
        stale_assets = [str(item) for item in repair.metadata.get("stale_assets", []) if str(item)]
        missing_assets = [str(item) for item in repair.metadata.get("missing_assets", []) if str(item)]
        return InteractionRequest(
            interaction_id=f"int_{repair.repair_id}",
            question=self._default_question(repair=repair, step_id=step_id, missing_input_keys=missing_input_keys),
            expected_answer_type=repair.interaction.expected_answer_type or "json_patch",
            context_summary={
                "workflow_id": workflow.workflow_id,
                "step_id": step_id,
                "state_keys": sorted(state_values.keys()),
                "failed_tool_id": failed_tool_id,
                "missing_input_keys": missing_input_keys,
                "missing_assets": list(state_values.get("__missing_assets__", [])),
                "stale_assets": stale_assets,
                "branch_options": branch_options,
            },
            allowed_response_schema={
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "tool_id": {"type": "string"},
                    "input_patch": {"type": "object"},
                    "fallback_execution_path": {"type": "string"},
                    "clear_failure_flag": {"type": "boolean"},
                    "use_backup_tool": {"type": "boolean"},
                    "branch_choice": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "abort": {"type": "boolean"},
                },
            },
            metadata={
                "repair_type": repair.repair_type.value,
                "failed_tool_id": failed_tool_id,
                "backup_tool_id": repair.metadata.get("backup_tool_id"),
                "mapped_from_error_category": repair.metadata.get("mapped_from_error_category"),
                "branch_options": branch_options,
                "missing_assets": missing_assets,
                "stale_assets": stale_assets,
                "patch_targets": self._default_patch_targets(repair=repair, missing_input_keys=missing_input_keys),
                "primary_failtax": workflow.metadata.get("primary_failtax"),
                "budget_profile": dict(workflow.metadata.get("budget_profile", {}))
                if isinstance(workflow.metadata.get("budget_profile"), dict)
                else workflow.metadata.get("budget_profile"),
            },
        )

    def ingest_reply(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        state_values: Dict[str, Any],
    ) -> ResumePatch:
        patch_targets = reply.metadata.get("patch_targets", {})
        state_updates = self._normalize_state_updates(reply.payload, patch_targets=patch_targets)
        binding_patch = {}
        policy_updates = {}
        selected_tool_id = self._selected_tool_id(repair=repair, payload=reply.payload)
        if selected_tool_id:
            binding_patch["tool_id"] = selected_tool_id
        if self._approval_from_payload(reply.payload, patch_targets=patch_targets) is not None:
            policy_updates["approved"] = self._approval_from_payload(reply.payload, patch_targets=patch_targets)
        elif "approved" in reply.payload:
            policy_updates["approved"] = bool(reply.payload["approved"])
        if self._should_clear_environment_failure(repair=repair, payload=reply.payload):
            state_updates["force_environment_failure"] = False
        elif repair.metadata.get("mapped_from_error_category") == "state_failure" and state_updates:
            state_updates["force_environment_failure"] = False
        if repair.metadata.get("mapped_from_error_category") == "state_failure" and state_updates:
            stale_slots = [str(item) for item in state_values.get("__stale_state_slots__", []) if str(item)]
            refreshed_slots = {str(key) for key in state_updates.keys() if str(key)}
            if stale_slots:
                remaining = [slot for slot in stale_slots if slot not in refreshed_slots]
                state_updates["__stale_state_slots__"] = remaining
        resume_step_id = self._resolve_repair_step_id(workflow=workflow, repair=repair)
        expected_patch_targets = self._expected_patch_targets(patch_targets)
        actual_patch_targets = self._actual_patch_targets(
            state_updates=state_updates,
            policy_updates=policy_updates,
            binding_patch=binding_patch,
        )
        target_alignment = float(reply.metadata.get("target_alignment", 0.0) or 0.0)
        semantic_conflict = bool(reply.metadata.get("semantic_conflict", False))
        decoded_is_usable = bool(reply.metadata.get("decoded_is_usable", False))
        effect_scope = self._effect_scope(
            state_updates=state_updates,
            policy_updates=policy_updates,
            binding_patch=binding_patch,
        )
        effective_patch = (
            bool(effect_scope)
            and decoded_is_usable
            and not semantic_conflict
            and target_alignment >= 0.5
            and self._targets_overlap(expected_patch_targets, actual_patch_targets)
        )
        return ResumePatch(
            workflow=workflow,
            resume_step_id=resume_step_id,
            base_state=dict(state_values),
            state_updates=state_updates,
            policy_updates=policy_updates,
            binding_patch=binding_patch,
            missing_asset_patch={
                k: v
                for k, v in state_updates.items()
                if k not in {"force_environment_failure", "__failure_escalation_level__"}
            },
            metadata={
                "interaction_id": reply.interaction_id,
                "accepted": reply.accepted,
                "repair_type": repair.repair_type.value,
                "escalation_level": int(reply.metadata.get("escalation_level", 0)),
                "answer_patch": {
                    "patched_slots": sorted(str(key) for key in state_updates.keys()),
                    "patched_constraints": dict(policy_updates),
                    "patched_bindings": dict(binding_patch),
                    "compound_patch": bool((state_updates or binding_patch) and policy_updates),
                    "patch_confidence": 1.0 if state_updates or policy_updates or binding_patch else 0.0,
                    "compiler_status": "compiled" if state_updates or policy_updates or binding_patch else "noop",
                    "decoded_is_usable": decoded_is_usable,
                    "target_alignment": target_alignment,
                    "semantic_conflict": semantic_conflict,
                    "effective_patch": effective_patch,
                    "effect_scope": effect_scope or "none",
                    "expected_patch_targets": expected_patch_targets,
                    "actual_patch_targets": actual_patch_targets,
                },
            },
        )

    def validate_reply(
        self,
        request: InteractionRequest,
        reply: UserReply,
    ) -> bool:
        if request.interaction_id != reply.interaction_id:
            return False
        if reply.status in {"deny", "abstain"}:
            return True
        if reply.status == "malformed":
            return False
        return isinstance(reply.payload, dict)

    @staticmethod
    def compile_semantic_payload(
        *,
        slot_updates: Dict[str, Any] | None = None,
        approvals: Dict[str, Any] | None = None,
        control_updates: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Compatibility helper: semantic signal -> UserReply payload."""
        payload: Dict[str, Any] = {}
        if isinstance(slot_updates, dict):
            payload.update(slot_updates)
        if isinstance(approvals, dict) and "approved" in approvals:
            payload["approved"] = bool(approvals.get("approved"))
        if isinstance(control_updates, dict):
            payload.update(control_updates)
        return payload

    def apply_reply_to_workflow(self, workflow: Workflow, resume_patch: ResumePatch) -> Workflow:
        workflow.patch_with_resume(resume_patch)
        return workflow

    @staticmethod
    def _default_question(repair: Repair, step_id: str, missing_input_keys: list[str]) -> str:
        if repair.interaction.question:
            return repair.interaction.question
        if repair.metadata.get("mapped_from_error_category") == "environment_failure":
            if missing_input_keys:
                missing = ", ".join(missing_input_keys)
                return (
                    f"Step {step_id} hit an environment failure. "
                    f"Provide missing inputs ({missing}), an alternate tool, or a fallback execution path."
                )
            return (
                f"Step {step_id} hit an environment failure. "
                "Provide an alternate tool, fallback execution path, or confirm that the current failure flag can be cleared."
            )
        if repair.metadata.get("mapped_from_error_category") == "state_failure":
            stale_assets = [str(item) for item in repair.metadata.get("stale_assets", []) if str(item)]
            missing_assets = [str(item) for item in repair.metadata.get("missing_assets", []) if str(item)]
            target_assets = stale_assets or missing_assets
            if target_assets:
                return (
                    f"Step {step_id} is blocked by state inconsistency. "
                    f"Provide a fresh value for {', '.join(target_assets)} so execution can retry safely."
                )
        return "Please provide missing data"

    @staticmethod
    def _normalize_state_updates(payload: Dict[str, Any], *, patch_targets: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state_updates: Dict[str, Any] = {}
        schema_targets = patch_targets if isinstance(patch_targets, dict) else {}
        input_patch = payload.get("input_patch")
        if isinstance(input_patch, dict):
            state_updates.update(input_patch)
        for key, value in payload.items():
            if key in {"tool_id", "approved", "abort", "use_backup_tool", "clear_failure_flag", "input_patch"}:
                continue
            target = schema_targets.get(key)
            if isinstance(target, str):
                if target.startswith("step.inputs."):
                    state_updates[target.split("step.inputs.", 1)[1]] = value
                    continue
                if target.startswith("state."):
                    state_key = target.split("state.", 1)[1]
                    if state_key == "force_environment_failure":
                        continue
                    state_updates[state_key] = value
                    continue
                if target == "binding.primary_tool":
                    continue
                if target == "policy.approved":
                    continue
            if key == "fallback_execution_path":
                state_updates.setdefault("target_path", value)
                continue
            state_updates[key] = value
        return state_updates

    @staticmethod
    def _expected_patch_targets(patch_targets: Dict[str, Any] | None) -> list[str]:
        targets: list[str] = []
        schema_targets = patch_targets if isinstance(patch_targets, dict) else {}
        for key, target in schema_targets.items():
            key_text = str(key or "").strip()
            target_text = str(target or "").strip()
            if key_text:
                targets.append(key_text)
            if target_text.startswith("step.inputs."):
                targets.append(target_text.split("step.inputs.", 1)[1])
            elif target_text.startswith("state."):
                targets.append(target_text.split("state.", 1)[1])
            elif target_text == "policy.approved":
                targets.append("approved")
            elif target_text == "binding.primary_tool":
                targets.append("tool_id")
        seen: set[str] = set()
        result: list[str] = []
        for target in targets:
            if target and target not in seen:
                seen.add(target)
                result.append(target)
        return result

    @staticmethod
    def _actual_patch_targets(
        *,
        state_updates: Dict[str, Any],
        policy_updates: Dict[str, Any],
        binding_patch: Dict[str, Any],
    ) -> list[str]:
        targets: list[str] = [str(key) for key in state_updates if str(key) and not str(key).startswith("__")]
        if "approved" in policy_updates:
            targets.append("approved")
        if "tool_id" in binding_patch:
            targets.append("tool_id")
        seen: set[str] = set()
        result: list[str] = []
        for target in targets:
            if target and target not in seen:
                seen.add(target)
                result.append(target)
        return result

    @staticmethod
    def _targets_overlap(expected_patch_targets: list[str], actual_patch_targets: list[str]) -> bool:
        if not actual_patch_targets:
            return False
        if not expected_patch_targets:
            return True
        return bool(set(expected_patch_targets).intersection(set(actual_patch_targets)))

    @staticmethod
    def _effect_scope(
        *,
        state_updates: Dict[str, Any],
        policy_updates: Dict[str, Any],
        binding_patch: Dict[str, Any],
    ) -> str:
        scopes: list[str] = []
        if state_updates:
            scopes.append("slot")
        if policy_updates:
            scopes.append("policy")
        if binding_patch:
            scopes.append("binding")
        return "+".join(scopes)

    @staticmethod
    def _approval_from_payload(payload: Dict[str, Any], *, patch_targets: Dict[str, Any] | None = None) -> Optional[bool]:
        schema_targets = patch_targets if isinstance(patch_targets, dict) else {}
        for key, target in schema_targets.items():
            if target == "policy.approved" and key in payload:
                return bool(payload[key])
        return None

    @staticmethod
    def _selected_tool_id(repair: Repair, payload: Dict[str, Any]) -> Optional[str]:
        tool_id = payload.get("tool_id")
        if isinstance(tool_id, str) and tool_id:
            return tool_id
        if payload.get("use_backup_tool") and isinstance(repair.metadata.get("backup_tool_id"), str):
            return str(repair.metadata["backup_tool_id"])
        return None

    @staticmethod
    def _should_clear_environment_failure(repair: Repair, payload: Dict[str, Any]) -> bool:
        if repair.metadata.get("mapped_from_error_category") != "environment_failure":
            return False
        if "clear_failure_flag" in payload:
            return bool(payload["clear_failure_flag"])
        return True

    @staticmethod
    def _default_patch_targets(repair: Repair, missing_input_keys: list[str]) -> Dict[str, str]:
        patch_targets: Dict[str, str] = {}
        branch_options = [str(item) for item in repair.metadata.get("branch_options", []) if str(item)]
        for key in missing_input_keys:
            patch_targets[key] = f"step.inputs.{key}"
        if repair.metadata.get("mapped_from_error_category") == "environment_failure":
            patch_targets.setdefault("tool_id", "binding.primary_tool")
            patch_targets.setdefault("fallback_execution_path", "step.inputs.target_path")
            patch_targets.setdefault("clear_failure_flag", "state.force_environment_failure")
        if repair.metadata.get("mapped_from_error_category") == "state_failure":
            for key in [str(item) for item in repair.metadata.get("missing_assets", []) if str(item)]:
                if key == "target_path":
                    patch_targets.setdefault(key, "step.inputs.target_path")
                else:
                    patch_targets.setdefault(key, f"state.{key}")
            for key in [str(item) for item in repair.metadata.get("stale_assets", []) if str(item)]:
                if key == "target_path":
                    patch_targets.setdefault(key, "step.inputs.target_path")
                else:
                    patch_targets.setdefault(key, f"state.{key}")
        if branch_options:
            patch_targets.setdefault("branch_choice", "state.selected_branch")
        if repair.repair_type.value == "request_approval":
            patch_targets["approved"] = "policy.approved"
        return patch_targets

    @staticmethod
    def _resolve_repair_step_id(workflow: Workflow, repair: Repair) -> str:
        if repair.workflow_patch.modified_steps:
            return repair.workflow_patch.modified_steps[0]

        for action in repair.actions:
            if action.target and action.target.startswith("step_"):
                return action.target.split(".")[0]

        return workflow.execution_plan[-1].step_id if workflow.execution_plan else "step_01"


class AnswerPatchCompiler(RepairUpdater):
    """Explicit alias for the reply-to-patch compiler used in interaction evaluation."""
