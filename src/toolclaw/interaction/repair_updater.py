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
        return InteractionRequest(
            interaction_id=f"int_{repair.repair_id}",
            question=repair.interaction.question or "Please provide missing data",
            expected_answer_type=repair.interaction.expected_answer_type or "json_patch",
            context_summary={
                "workflow_id": workflow.workflow_id,
                "step_id": step_id,
                "state_keys": sorted(state_values.keys()),
            },
            allowed_response_schema={
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "tool_id": {"type": "string"},
                    "approved": {"type": "boolean"},
                    "abort": {"type": "boolean"},
                },
            },
        )

    def ingest_reply(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        state_values: Dict[str, Any],
    ) -> ResumePatch:
        _ = state_values
        state_updates = dict(reply.payload)
        binding_patch = {}
        policy_updates = {}
        if "tool_id" in reply.payload:
            binding_patch["tool_id"] = reply.payload["tool_id"]
        if "approved" in reply.payload:
            policy_updates["approved"] = bool(reply.payload["approved"])
        resume_step_id = self._resolve_repair_step_id(workflow=workflow, repair=repair)
        return ResumePatch(
            workflow=workflow,
            resume_step_id=resume_step_id,
            state_updates=state_updates,
            policy_updates=policy_updates,
            binding_patch=binding_patch,
            missing_asset_patch={k: v for k, v in reply.payload.items() if k not in {"tool_id", "approved", "abort"}},
            metadata={"interaction_id": reply.interaction_id, "accepted": reply.accepted},
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
    def _resolve_repair_step_id(workflow: Workflow, repair: Repair) -> str:
        if repair.workflow_patch.modified_steps:
            return repair.workflow_patch.modified_steps[0]

        for action in repair.actions:
            if action.target and action.target.startswith("step_"):
                return action.target.split(".")[0]

        return workflow.execution_plan[-1].step_id if workflow.execution_plan else "step_01"
