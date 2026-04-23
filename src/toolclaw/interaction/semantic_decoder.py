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
    control_updates: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticDecoder:
    YES_RE = re.compile(r"\b(yes|yeah|yep|ok|okay|sure|go ahead|allow|confirm)\b", re.I)
    NO_RE = re.compile(r"\b(no|don't|do not|deny|reject|stop|cancel)\b", re.I)
    NON_ANSWER_RE = re.compile(r"\b(i don't know|dont know|unknown|irrelevant answer|wrong parameter|n/?a|not sure)\b", re.I)

    def decode(self, request: InteractionRequest, raw_reply: RawUserReply) -> DecodedInteractionSignal:
        payload = dict(raw_reply.raw_payload or {})
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        q_text = str(request.question or "").lower()
        q_type = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "").lower()
        text = str(raw_reply.raw_text or "").strip()
        expected_targets = self._expected_targets(patch_targets)
        is_permission = ("approval" in q_type) or ("permission" in q_type) or ("approve" in q_text)
        slot_updates: Dict[str, Any] = {}
        approvals: Dict[str, bool] = {}
        control_updates: Dict[str, Any] = {}

        if raw_reply.status in {"deny", "abstain", "malformed"}:
            return DecodedInteractionSignal(
                intent_type="reject" if raw_reply.status == "deny" else "unknown",
                metadata={
                    "decode_strategy": "passthrough_status",
                    "decode_confidence": 1.0,
                    "raw_status": raw_reply.status,
                    "decoded_is_usable": False,
                    "target_alignment": 0.0,
                    "semantic_conflict": raw_reply.status != "deny",
                    "selected_target": "",
                    "expected_targets": expected_targets,
                },
            )

        if isinstance(payload.get("input_patch"), dict):
            slot_updates.update(dict(payload.get("input_patch", {})))
        if "approved" in payload:
            approvals["approved"] = bool(payload.get("approved"))
        for key, value in payload.items():
            if key in {"input_patch", "approved"}:
                continue
            target = patch_targets.get(key)
            if key in {"tool_id", "use_backup_tool", "clear_failure_flag", "fallback_execution_path", "branch_choice"}:
                control_updates[key] = value
                continue
            if isinstance(target, str) and (target.startswith("step.inputs.") or target.startswith("state.")):
                slot_updates[key] = value
                continue
            if isinstance(target, str) and target in {"binding.primary_tool", "policy.approved"}:
                control_updates[key] = value
                continue
            if key not in {"abort"}:
                slot_updates[key] = value
        if approvals or slot_updates or control_updates:
            selected_targets = self._selected_targets(slot_updates, approvals, control_updates, patch_targets)
            target_alignment = self._target_alignment(selected_targets, expected_targets)
            semantic_conflict = self._payload_semantic_conflict(
                is_permission=is_permission,
                approvals=approvals,
                selected_targets=selected_targets,
                expected_targets=expected_targets,
            )
            if approvals and (slot_updates or control_updates):
                intent_type = "compound_patch"
            elif approvals:
                intent_type = "permission_confirm"
            elif control_updates:
                intent_type = "action_confirm"
            else:
                intent_type = "slot_fill"
            return DecodedInteractionSignal(
                intent_type=intent_type,
                approvals=approvals,
                slot_updates=slot_updates,
                control_updates=control_updates,
                metadata={
                    "decode_strategy": "payload",
                    "decode_confidence": 1.0,
                    "decoded_is_usable": bool(target_alignment >= 0.5 and not semantic_conflict),
                    "target_alignment": target_alignment,
                    "semantic_conflict": semantic_conflict,
                    "selected_target": next(iter(selected_targets), ""),
                    "selected_targets": sorted(selected_targets),
                    "expected_targets": expected_targets,
                },
            )

        if is_permission:
            if self.YES_RE.search(text):
                candidate_slots = [str(k) for k in patch_targets.keys() if k and k not in {"approved", "tool_id"}]
                normalized_text = self.YES_RE.sub("", text, count=1).strip(" ,.;:")
                selected_targets = {"approved"}
                if normalized_text and candidate_slots:
                    selected_targets.add(candidate_slots[0])
                target_alignment = self._target_alignment(selected_targets, expected_targets or ["approved"])
                return DecodedInteractionSignal(
                    intent_type="compound_patch" if normalized_text and candidate_slots else "permission_confirm",
                    approvals={"approved": True},
                    slot_updates={candidate_slots[0]: normalized_text} if normalized_text and candidate_slots else {},
                    metadata={
                        "decode_strategy": "rule",
                        "decode_confidence": 0.9,
                        "decoded_is_usable": target_alignment >= 0.5,
                        "target_alignment": target_alignment,
                        "semantic_conflict": False,
                        "selected_target": next(iter(selected_targets), ""),
                        "selected_targets": sorted(selected_targets),
                        "expected_targets": expected_targets or ["approved"],
                    },
                )
            if self.NO_RE.search(text):
                return DecodedInteractionSignal(
                    intent_type="reject",
                    approvals={"approved": False},
                    metadata={
                        "decode_strategy": "rule",
                        "decode_confidence": 0.9,
                        "decoded_is_usable": True,
                        "target_alignment": 1.0,
                        "semantic_conflict": False,
                        "selected_target": "approved",
                        "selected_targets": ["approved"],
                        "expected_targets": expected_targets or ["approved"],
                    },
                )
            if text:
                return DecodedInteractionSignal(
                    intent_type="unknown",
                    metadata={
                        "decode_strategy": "rule",
                        "decode_confidence": 0.0,
                        "decoded_is_usable": False,
                        "target_alignment": 0.0,
                        "semantic_conflict": True,
                        "selected_target": "",
                        "selected_targets": [],
                        "expected_targets": expected_targets or ["approved"],
                    },
                )

        candidate_slots = [str(k) for k in patch_targets.keys() if k and k not in {"approved", "tool_id"}]
        if text and self.NON_ANSWER_RE.search(text):
            return DecodedInteractionSignal(
                intent_type="unknown",
                metadata={
                    "decode_strategy": "rule",
                    "decode_confidence": 0.0,
                    "decoded_is_usable": False,
                    "target_alignment": 0.0,
                    "semantic_conflict": True,
                    "selected_target": "",
                    "selected_targets": [],
                    "expected_targets": expected_targets,
                },
            )
        if text and candidate_slots:
            slot = candidate_slots[0]
            target_alignment = self._target_alignment({slot}, expected_targets)
            return DecodedInteractionSignal(
                intent_type="slot_fill",
                slot_updates={slot: text},
                metadata={
                    "decode_strategy": "rule",
                    "decode_confidence": 0.7,
                    "selected_slot": slot,
                    "decoded_is_usable": target_alignment >= 0.5,
                    "target_alignment": target_alignment,
                    "semantic_conflict": target_alignment < 0.5,
                    "selected_target": slot,
                    "selected_targets": [slot],
                    "expected_targets": expected_targets,
                },
            )
        if text:
            return DecodedInteractionSignal(
                intent_type="goal_clarification",
                slot_updates={"value": text},
                metadata={
                    "decode_strategy": "rule",
                    "decode_confidence": 0.5,
                    "decoded_is_usable": False,
                    "target_alignment": 0.0,
                    "semantic_conflict": True,
                    "selected_target": "value",
                    "selected_targets": ["value"],
                    "expected_targets": expected_targets,
                },
            )
        return DecodedInteractionSignal(
            intent_type="unknown",
            metadata={
                "decode_strategy": "fallback",
                "decode_confidence": 0.0,
                "decoded_is_usable": False,
                "target_alignment": 0.0,
                "semantic_conflict": True,
                "selected_target": "",
                "selected_targets": [],
                "expected_targets": expected_targets,
            },
        )

    @staticmethod
    def _expected_targets(patch_targets: Dict[str, Any]) -> list[str]:
        targets: list[str] = []
        for key, target in patch_targets.items():
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
        for item in targets:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @classmethod
    def _selected_targets(
        cls,
        slot_updates: Dict[str, Any],
        approvals: Dict[str, bool],
        control_updates: Dict[str, Any],
        patch_targets: Dict[str, Any],
    ) -> set[str]:
        selected = {str(key) for key in slot_updates if str(key)}
        selected.update(str(key) for key in control_updates if str(key))
        if "approved" in approvals:
            selected.add("approved")
        normalized = set(selected)
        for key in selected:
            target = str(patch_targets.get(key) or "")
            if target.startswith("step.inputs."):
                normalized.add(target.split("step.inputs.", 1)[1])
            elif target.startswith("state."):
                normalized.add(target.split("state.", 1)[1])
            elif target == "policy.approved":
                normalized.add("approved")
            elif target == "binding.primary_tool":
                normalized.add("tool_id")
        return normalized

    @staticmethod
    def _target_alignment(selected_targets: set[str], expected_targets: list[str]) -> float:
        if not selected_targets:
            return 0.0
        if not expected_targets:
            return 1.0
        expected = {str(item) for item in expected_targets if str(item)}
        if not expected:
            return 1.0
        return 1.0 if selected_targets.intersection(expected) else 0.0

    @staticmethod
    def _payload_semantic_conflict(
        *,
        is_permission: bool,
        approvals: Dict[str, bool],
        selected_targets: set[str],
        expected_targets: list[str],
    ) -> bool:
        if is_permission and "approved" not in approvals:
            return True
        if expected_targets and not selected_targets.intersection(set(expected_targets)):
            return True
        return False


def compile_decoded_signal_to_user_reply(
    request: InteractionRequest,
    raw_reply: RawUserReply,
    signal: DecodedInteractionSignal,
) -> UserReply:
    patch_targets = dict(request.metadata.get("patch_targets", {}))
    payload = RepairUpdater.compile_semantic_payload(
        slot_updates=dict(signal.slot_updates),
        approvals=dict(signal.approvals),
        control_updates=dict(signal.control_updates),
    )

    status = str(raw_reply.status or "accept")
    accepted = bool(raw_reply.accepted)
    if signal.intent_type == "reject":
        status = "deny"
        accepted = False
        if "approved" not in payload and (
            "approval" in str(request.expected_answer_type or "").lower()
            or "approve" in str(request.question or "").lower()
        ):
            payload["approved"] = False
    elif signal.intent_type == "unknown" and status not in {"abstain", "malformed"}:
        status = "accept"

    decode_metadata = dict(signal.metadata)
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
            "decoded_control_updates": dict(signal.control_updates),
            "decoded_constraints_trace_only": dict(signal.constraints),
            "decoded_is_usable": bool(decode_metadata.get("decoded_is_usable", False)),
            "target_alignment": float(decode_metadata.get("target_alignment", 0.0) or 0.0),
            "semantic_conflict": bool(decode_metadata.get("semantic_conflict", False)),
            "selected_target": str(decode_metadata.get("selected_target") or ""),
            "selected_targets": list(decode_metadata.get("selected_targets", []))
            if isinstance(decode_metadata.get("selected_targets"), list)
            else [],
            "expected_targets": list(decode_metadata.get("expected_targets", []))
            if isinstance(decode_metadata.get("expected_targets"), list)
            else [],
            "decode_metadata": decode_metadata,
        },
    )
