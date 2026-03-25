from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from toolclaw.interaction.repair_updater import InteractionRequest, UserReply


@dataclass
class SimulatedPolicy:
    mode: str = "cooperative"  # cooperative | strict | abortive
    missing_arg_values: Dict[str, Any] = field(default_factory=dict)
    backup_tool_preferences: Dict[str, str] = field(default_factory=dict)


class UserSimulator:
    def __init__(self, policy: SimulatedPolicy) -> None:
        self.policy = policy

    def reply(self, request: InteractionRequest) -> UserReply:
        if self.policy.mode == "abortive":
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"abort": True},
                accepted=False,
                raw_text="Abort task.",
            )

        payload: Dict[str, Any] = {}
        payload.update(self.policy.missing_arg_values)

        if self.policy.mode == "strict" and not payload:
            payload = {"abort": True}
            accepted = False
        else:
            accepted = True

        return UserReply(
            interaction_id=request.interaction_id,
            payload=payload,
            accepted=accepted,
            raw_text="auto-reply",
        )
