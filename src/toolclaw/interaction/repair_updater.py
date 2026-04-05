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
                    "approved": {"type": "boolean"},
                    "abort": {"type": "boolean"},
                },
            },
            metadata={
                "repair_type": repair.repair_type.value,
                "failed_tool_id": failed_tool_id,
                "backup_tool_id": repair.metadata.get("backup_tool_id"),
                "mapped_from_error_category": repair.metadata.get("mapped_from_error_category"),
            },
        )

    def ingest_reply(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        state_values: Dict[str, Any],
    ) -> ResumePatch:
        state_updates = self._normalize_state_updates(reply.payload)
        binding_patch = {}
        policy_updates = {}
        selected_tool_id = self._selected_tool_id(repair=repair, payload=reply.payload)
        if selected_tool_id:
            binding_patch["tool_id"] = selected_tool_id
        if "approved" in reply.payload:
            policy_updates["approved"] = bool(reply.payload["approved"])
        if self._should_clear_environment_failure(repair=repair, payload=reply.payload):
            state_updates["force_environment_failure"] = False
        resume_step_id = self._resolve_repair_step_id(workflow=workflow, repair=repair)
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
            },
        )

    def validate_reply(
        self,
        request: InteractionRequest,
        reply: UserReply,
    ) -> bool:
        if request.interaction_id != reply.interaction_id:
            return False
        if not reply.accepted:
            return False
        return isinstance(reply.payload, dict)

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
        return "Please provide missing data"

    @staticmethod
    def _normalize_state_updates(payload: Dict[str, Any]) -> Dict[str, Any]:
        state_updates: Dict[str, Any] = {}
        input_patch = payload.get("input_patch")
        if isinstance(input_patch, dict):
            state_updates.update(input_patch)
        for key, value in payload.items():
            if key in {"tool_id", "approved", "abort", "use_backup_tool", "clear_failure_flag", "input_patch"}:
                continue
            if key == "fallback_execution_path":
                state_updates.setdefault("target_path", value)
                continue
            state_updates[key] = value
        return state_updates

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
    def _resolve_repair_step_id(workflow: Workflow, repair: Repair) -> str:
        if repair.workflow_patch.modified_steps:
            return repair.workflow_patch.modified_steps[0]

        for action in repair.actions:
            if action.target and action.target.startswith("step_"):
                return action.target.split(".")[0]

        return workflow.execution_plan[-1].step_id if workflow.execution_plan else "step_01"
