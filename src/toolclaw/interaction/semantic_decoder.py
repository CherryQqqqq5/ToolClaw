"""Semantic decoding and compatibility compilation for interaction replies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict

from toolclaw.interaction.repair_updater import InteractionRequest, RepairUpdater, UserReply
from toolclaw.interaction.reply_provider import RawUserReply


@dataclass
class DecodedInteractionSignal:
    intent_type: str
    slot_updates: Dict[str, Any] = field(default_factory=dict)
    approvals: Dict[str, bool] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticDecoder:
    YES_RE = re.compile(r"\b(yes|yeah|yep|ok|okay|sure|go ahead|allow|confirm)\b", re.I)
    NO_RE = re.compile(r"\b(no|don't|do not|deny|reject|stop|cancel)\b", re.I)

    def decode(self, request: InteractionRequest, raw_reply: RawUserReply) -> DecodedInteractionSignal:
        payload = dict(raw_reply.raw_payload or {})
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        q_text = str(request.question or "").lower()
        q_type = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "").lower()
        text = str(raw_reply.raw_text or "").strip()

        if raw_reply.status in {"deny", "abstain", "malformed"}:
            return DecodedInteractionSignal(
                intent_type="reject" if raw_reply.status == "deny" else "unknown",
                metadata={
                    "decode_strategy": "passthrough_status",
                    "decode_confidence": 1.0,
                    "raw_status": raw_reply.status,
                },
            )

        if "approved" in payload:
            return DecodedInteractionSignal(
                intent_type="permission_confirm",
                approvals={"approved": bool(payload.get("approved"))},
                metadata={"decode_strategy": "payload", "decode_confidence": 1.0},
            )
        if "tool_id" in payload and payload.get("tool_id"):
            return DecodedInteractionSignal(
                intent_type="action_confirm",
                slot_updates={"tool_id": payload.get("tool_id")},
                metadata={"decode_strategy": "payload", "decode_confidence": 1.0},
            )
        if "input_patch" in payload and isinstance(payload.get("input_patch"), dict):
            return DecodedInteractionSignal(
                intent_type="slot_fill",
                slot_updates=dict(payload.get("input_patch", {})),
                metadata={"decode_strategy": "payload", "decode_confidence": 1.0},
            )

        is_permission = ("approval" in q_type) or ("permission" in q_type) or ("approve" in q_text)
        if is_permission:
            if self.YES_RE.search(text):
                return DecodedInteractionSignal(
                    intent_type="permission_confirm",
                    approvals={"approved": True},
                    metadata={"decode_strategy": "rule", "decode_confidence": 0.9},
                )
            if self.NO_RE.search(text):
                return DecodedInteractionSignal(
                    intent_type="reject",
                    approvals={"approved": False},
                    metadata={"decode_strategy": "rule", "decode_confidence": 0.9},
                )

        candidate_slots = [str(k) for k in patch_targets.keys() if k and k not in {"approved", "tool_id"}]
        if text and candidate_slots:
            slot = candidate_slots[0]
            return DecodedInteractionSignal(
                intent_type="slot_fill",
                slot_updates={slot: text},
                metadata={"decode_strategy": "rule", "decode_confidence": 0.7, "selected_slot": slot},
            )
        if text:
            return DecodedInteractionSignal(
                intent_type="goal_clarification",
                slot_updates={"value": text},
                metadata={"decode_strategy": "rule", "decode_confidence": 0.5},
            )
        return DecodedInteractionSignal(
            intent_type="unknown",
            metadata={"decode_strategy": "fallback", "decode_confidence": 0.0},
        )


def compile_decoded_signal_to_user_reply(
    request: InteractionRequest,
    raw_reply: RawUserReply,
    signal: DecodedInteractionSignal,
) -> UserReply:
    patch_targets = dict(request.metadata.get("patch_targets", {}))
    payload = RepairUpdater.compile_semantic_payload(
        slot_updates=dict(signal.slot_updates),
        approvals=dict(signal.approvals),
    )

    status = str(raw_reply.status or "accept")
    accepted = bool(raw_reply.accepted)
    if signal.intent_type == "reject":
        status = "deny"
        accepted = False
        if "approved" not in payload:
            payload["approved"] = False
    elif signal.intent_type == "unknown" and status not in {"abstain", "malformed"}:
        status = "accept"

    return UserReply(
        interaction_id=request.interaction_id,
        payload=payload,
        raw_text=str(raw_reply.raw_text or ""),
        accepted=accepted,
        status=status,
        metadata={
            **dict(raw_reply.metadata or {}),
            "patch_targets": patch_targets,
            "decoded_intent_type": signal.intent_type,
            "decoded_slot_updates": dict(signal.slot_updates),
            "decoded_approvals": dict(signal.approvals),
            "decoded_constraints_trace_only": dict(signal.constraints),
            "decode_metadata": dict(signal.metadata),
        },
    )
