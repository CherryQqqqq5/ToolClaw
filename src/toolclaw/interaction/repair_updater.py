from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid

from toolclaw.schemas.repair import (
    Repair,
    RepairActionType,
    RepairStatus,
    RepairType,
)
from toolclaw.schemas.workflow import Workflow


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class InteractionRequest:
    interaction_id: str
    repair_id: str
    workflow_id: str
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
    resume_step_id: Optional[str]
    state_updates: Dict[str, Any] = field(default_factory=dict)
    policy_updates: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RepairUpdater:
    """
    把 ask_user 风格 repair 转成：
    1) 给用户/模拟器的结构化 query
    2) 用户回复后的 workflow/state patch
    """

    def build_query(
        self,
        workflow: Workflow,
        repair: Repair,
        state_values: Dict[str, Any],
    ) -> InteractionRequest:
        question = (
            repair.interaction.question
            or repair.result.message
            or "Additional user input is required to continue this workflow."
        )
        expected = repair.interaction.expected_answer_type or "json"

        context_summary = {
            "task_id": workflow.task.task_id,
            "user_goal": workflow.task.user_goal,
            "triggered_error_ids": list(repair.triggered_error_ids),
            "repair_type": repair.repair_type.value,
            "current_state_keys": sorted(state_values.keys()),
        }

        allowed_response_schema = self._build_expected_schema(repair)

        return InteractionRequest(
            interaction_id=_new_id("irc"),
            repair_id=repair.repair_id,
            workflow_id=workflow.workflow_id,
            question=question,
            expected_answer_type=expected,
            context_summary=context_summary,
            allowed_response_schema=allowed_response_schema,
            metadata={"source": "RepairUpdater.build_query"},
        )

    def validate_reply(
        self,
        request: InteractionRequest,
        reply: UserReply,
    ) -> bool:
        if request.interaction_id != reply.interaction_id:
            return False
        if not reply.accepted:
            return True
        if not isinstance(reply.payload, dict):
            return False

        answer_type = request.expected_answer_type.lower()
        if answer_type in {"json", "dict", "object"}:
            return isinstance(reply.payload, dict)
        if answer_type in {"string", "text"}:
            return "answer" in reply.payload or "text" in reply.payload
        if answer_type in {"tool_id"}:
            return "tool_id" in reply.payload
        return True

    def ingest_reply(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        state_values: Dict[str, Any],
    ) -> ResumePatch:
        patched_workflow = deepcopy(workflow)
        state_updates: Dict[str, Any] = {}
        policy_updates: Dict[str, Any] = {}
        resume_step_id: Optional[str] = None

        if not reply.accepted:
            repair.result.status = RepairStatus.ABORTED
            policy_updates["user_abort"] = True
            return ResumePatch(
                workflow=patched_workflow,
                resume_step_id=None,
                state_updates=state_updates,
                policy_updates=policy_updates,
                metadata={"decision": "abort_by_user"},
            )

        # 记录用户响应，便于 trace / audit
        repair.interaction.user_response = reply.payload

        if repair.repair_type == RepairType.ASK_USER:
            resume_step_id = self._infer_resume_step_id(patched_workflow, repair)
            state_updates.update(self._extract_generic_state_updates(reply.payload))

        # 逐 action 应用 patch
        for action in repair.actions:
            if action.action_type == RepairActionType.STATE_PATCH:
                self._apply_state_patch_action(
                    workflow=patched_workflow,
                    action=action,
                    reply_payload=reply.payload,
                    state_updates=state_updates,
                )
            elif action.action_type == RepairActionType.SWITCH_TOOL:
                self._apply_switch_tool_action(
                    workflow=patched_workflow,
                    action=action,
                    reply_payload=reply.payload,
                )
            elif action.action_type == RepairActionType.RE_EXECUTE_STEP:
                resume_step_id = action.target
            elif action.action_type == RepairActionType.UPDATE_POLICY_FLAG:
                if action.target:
                    policy_updates[action.target] = reply.payload.get(
                        action.target,
                        action.value if action.value is not None else True,
                    )
            elif action.action_type == RepairActionType.ASK_USER:
                # 本次 ingest 已经拿到用户回复，因此只需要把答复写回 state
                state_updates.update(self._extract_generic_state_updates(reply.payload))
            elif action.action_type == RepairActionType.ABORT:
                policy_updates["abort"] = True
                resume_step_id = None

        # fallback：如果 repair 没指定 RE_EXECUTE_STEP，则尝试从 workflow_patch.modified_steps 推断
        if resume_step_id is None:
            if repair.workflow_patch.modified_steps:
                resume_step_id = repair.workflow_patch.modified_steps[0]
            else:
                resume_step_id = self._infer_resume_step_id(patched_workflow, repair)

        repair.mark_applied()

        return ResumePatch(
            workflow=patched_workflow,
            resume_step_id=resume_step_id,
            state_updates=state_updates,
            policy_updates=policy_updates,
            metadata={
                "source": "RepairUpdater.ingest_reply",
                "repair_type": repair.repair_type.value,
            },
        )

    def _build_expected_schema(self, repair: Repair) -> Dict[str, Any]:
        if repair.repair_type == RepairType.SWITCH_TOOL:
            return {
                "type": "object",
                "properties": {
                    "tool_id": {"type": "string"},
                },
                "required": ["tool_id"],
            }
        if repair.repair_type == RepairType.REBIND_ARGS:
            return {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {},
                },
                "required": ["field", "value"],
            }
        return {
            "type": "object",
            "properties": {
                "answer": {},
            },
        }

    def _infer_resume_step_id(self, workflow: Workflow, repair: Repair) -> Optional[str]:
        if repair.workflow_patch.modified_steps:
            return repair.workflow_patch.modified_steps[0]
        if workflow.execution_plan:
            return workflow.execution_plan[-1].step_id
        return None

    def _extract_generic_state_updates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        updates = {}
        if "answer" in payload:
            updates["user_answer"] = payload["answer"]
        if "text" in payload:
            updates["user_text"] = payload["text"]
        if "tool_id" in payload:
            updates["selected_tool_id"] = payload["tool_id"]
        if "field" in payload and "value" in payload:
            updates[f"user_patch::{payload['field']}"] = payload["value"]
        return updates

    def _apply_state_patch_action(
        self,
        workflow: Workflow,
        action,
        reply_payload: Dict[str, Any],
        state_updates: Dict[str, Any],
    ) -> None:
        """
        支持两种最小 patch：
        1) target = 'step_02.inputs.target_path'
        2) target = 'state://some_key'
        """
        target = action.target or ""
        if target.startswith("state://"):
            key = target.replace("state://", "", 1)
            state_updates[key] = self._resolve_action_value(action, reply_payload)
            return

        parts = target.split(".")
        if len(parts) >= 3 and parts[1] == "inputs":
            step_id = parts[0]
            input_key = parts[2]
            for step in workflow.execution_plan:
                if step.step_id == step_id:
                    step.inputs[input_key] = self._resolve_action_value(action, reply_payload)
                    return

    def _apply_switch_tool_action(
        self,
        workflow: Workflow,
        action,
        reply_payload: Dict[str, Any],
    ) -> None:
        new_tool_id = reply_payload.get("tool_id")
        if not new_tool_id:
            new_tool_id = self._resolve_action_value(action, reply_payload)

        if not new_tool_id:
            return

        target = action.target
        if target:
            # 先改 step.tool_id
            for step in workflow.execution_plan:
                if step.step_id == target:
                    step.tool_id = new_tool_id
                    break

        # 再同步到 binding
        capability_id = None
        for step in workflow.execution_plan:
            if step.step_id == target:
                capability_id = step.capability_id
                break

        if capability_id:
            for binding in workflow.tool_bindings:
                if binding.capability_id == capability_id:
                    old_primary = binding.primary_tool
                    binding.primary_tool = new_tool_id
                    if old_primary and old_primary != new_tool_id:
                        if old_primary not in binding.backup_tools:
                            binding.backup_tools.insert(0, old_primary)
                    break

    def _resolve_action_value(self, action, reply_payload: Dict[str, Any]) -> Any:
        if action.value_source == "user_reply.field_value":
            return reply_payload.get("value")
        if action.value_source == "user_reply.tool_id":
            return reply_payload.get("tool_id")
        if action.value_source == "user_reply.answer":
            return reply_payload.get("answer")
        if action.value is not None:
            return action.value

        # 宽松 fallback
        if "value" in reply_payload:
            return reply_payload["value"]
        if "answer" in reply_payload:
            return reply_payload["answer"]
        return None