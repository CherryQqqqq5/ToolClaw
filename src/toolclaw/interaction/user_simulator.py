"""Simulator-backed reply provider for benchmark and offline interaction runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from toolclaw.interaction.repair_updater import InteractionRequest, UserReply
from toolclaw.interaction.reply_provider import ReplyProvider


@dataclass
class SimulatedPolicy:
    mode: str = "cooperative"  # cooperative | strict | abortive | abstain | malformed
    missing_arg_values: Dict[str, Any] = field(default_factory=dict)
    backup_tool_preferences: Dict[str, str] = field(default_factory=dict)
    approval_responses: Dict[str, bool] = field(default_factory=dict)
    constraint_overrides: Dict[str, Any] = field(default_factory=dict)
    tool_switch_hints: Dict[str, str] = field(default_factory=dict)


class UserSimulator(ReplyProvider):
    def __init__(self, policy: SimulatedPolicy) -> None:
        self.policy = policy

    def reply(self, request: InteractionRequest) -> UserReply:
        if self.policy.mode == "abortive":
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"abort": True},
                accepted=False,
                status="deny",
                raw_text="Abort task.",
            )
        if self.policy.mode == "abstain":
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"abstain": True},
                accepted=False,
                status="abstain",
                raw_text="No preference.",
            )
        if self.policy.mode == "malformed":
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"raw_text": "???"},
                accepted=False,
                status="malformed",
                raw_text="???",
            )

        payload: Dict[str, Any] = {}
        payload.update(self.policy.missing_arg_values)
        payload.update(self.policy.constraint_overrides)
        payload.update(self.policy.tool_switch_hints)
        if request.metadata.get("recommended_backup_tool") and "tool_id" not in payload:
            payload["tool_id"] = request.metadata["recommended_backup_tool"]
        if request.metadata.get("clear_failure_flag_recommended") and "clear_failure_flag" not in payload:
            payload["clear_failure_flag"] = True
        if "approval" in request.expected_answer_type or "approve" in request.question.lower():
            payload["approved"] = self.policy.approval_responses.get(request.interaction_id, True)

        if self.policy.mode == "strict" and not payload:
            payload = {"abstain": True}
            accepted = False
            status = "abstain"
        else:
            accepted = True
            status = "accept"

        return UserReply(
            interaction_id=request.interaction_id,
            payload=payload,
            accepted=accepted,
            status=status,
            raw_text="auto-reply",
            metadata={
                "patch_targets": dict(request.metadata.get("patch_targets", {})),
                "expected_answer_type": request.expected_answer_type,
                "escalation_level": int(request.metadata.get("escalation_level", 0)),
            },
        )
