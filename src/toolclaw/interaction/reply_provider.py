"""Reply provider abstractions for simulator, human, and LLM-backed interaction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence

from toolclaw.interaction.repair_updater import InteractionRequest, UserReply


class ReplyProvider(Protocol):
    def reply(self, request: InteractionRequest) -> UserReply:
        ...


class SimulatorReplyProvider(ReplyProvider, Protocol):
    def reply(self, request: InteractionRequest) -> UserReply:
        ...


@dataclass
class HumanStdinProvider:
    """Interactive stdin provider for manual experimentation."""

    prompt_prefix: str = "toolclaw"

    def reply(self, request: InteractionRequest) -> UserReply:
        print(f"[{self.prompt_prefix}] question: {request.question}")
        print(f"[{self.prompt_prefix}] expected_answer_type: {request.expected_answer_type}")
        if request.allowed_response_schema:
            print(f"[{self.prompt_prefix}] schema: {json.dumps(request.allowed_response_schema, ensure_ascii=True)}")
        raw = input(f"[{self.prompt_prefix}] reply json (or empty for abstain): ").strip()
        if not raw:
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"abstain": True},
                raw_text="",
                accepted=False,
                status="abstain",
                metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"raw_text": raw},
                raw_text=raw,
                accepted=False,
                status="malformed",
                metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
            )
        return UserReply(
            interaction_id=request.interaction_id,
            payload=payload if isinstance(payload, dict) else {"value": payload},
            raw_text=raw,
            accepted=True,
            status="accept",
            metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
        )


class HumanReplyProvider(HumanStdinProvider):
    """Compatibility alias for a human-backed reply provider."""


@dataclass
class LLMReplyProvider:
    """Thin wrapper around an injected LLM callback for reply generation."""

    completion_fn: Callable[[InteractionRequest], Dict[str, Any]]
    provider_name: str = "llm_reply_provider"

    def reply(self, request: InteractionRequest) -> UserReply:
        result = self.completion_fn(request)
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        if not isinstance(result, dict):
            return UserReply(
                interaction_id=request.interaction_id,
                payload={"raw_result": result},
                raw_text=str(result),
                accepted=False,
                status="malformed",
                metadata={"provider": self.provider_name, "patch_targets": patch_targets},
            )
        payload = dict(result.get("payload", result))
        status = str(result.get("status", "accept"))
        accepted = bool(result.get("accepted", status == "accept"))
        extra_metadata = dict(result.get("metadata", {})) if isinstance(result.get("metadata"), dict) else {}
        return UserReply(
            interaction_id=request.interaction_id,
            payload=payload,
            raw_text=str(result.get("raw_text", "")) or None,
            accepted=accepted,
            status=status,
            metadata={
                "provider": self.provider_name,
                "patch_targets": patch_targets,
                **extra_metadata,
            },
        )


@dataclass
class OracleReplayProvider:
    """Consume task-level oracle replies with simulator fallback."""

    oracle_replies: Sequence[Dict[str, Any]]
    fallback_provider: ReplyProvider
    provider_name: str = "oracle_replay"
    _cursor: int = 0

    def reply(self, request: InteractionRequest) -> UserReply:
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        match = self._consume_matching(request)
        if match is None:
            fallback = self.fallback_provider.reply(request)
            fallback_metadata = dict(fallback.metadata or {})
            fallback_metadata.update(
                {
                    "provider": self.provider_name,
                    "oracle_reply_consumed": False,
                    "oracle_reply_mismatch": True,
                    "oracle_reply_cursor": int(self._cursor),
                    "patch_targets": patch_targets,
                }
            )
            return UserReply(
                interaction_id=fallback.interaction_id,
                payload=dict(fallback.payload),
                raw_text=fallback.raw_text,
                accepted=bool(fallback.accepted),
                status=str(fallback.status),
                metadata=fallback_metadata,
            )
        payload = self._oracle_payload(request, match)
        return UserReply(
            interaction_id=request.interaction_id,
            payload=payload,
            raw_text=str(match.get("reply", "")),
            accepted=True,
            status="accept",
            metadata={
                "provider": self.provider_name,
                "patch_targets": patch_targets,
                "oracle_reply_consumed": True,
                "oracle_reply_mismatch": False,
                "oracle_reply_index": int(match.get("__oracle_index__", -1)),
                "oracle_reply_trigger_type": str(match.get("trigger_type") or ""),
                "oracle_reply_slot": str(match.get("slot") or ""),
                "oracle_reply_cursor": int(self._cursor),
            },
        )

    def _consume_matching(self, request: InteractionRequest) -> Optional[Dict[str, Any]]:
        q_type = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "").lower()
        q_text = str(request.question or "").lower()
        targets = {str(k).lower() for k in dict(request.metadata.get("patch_targets", {})).keys()}
        for idx in range(self._cursor, len(self.oracle_replies)):
            item = self.oracle_replies[idx]
            if not isinstance(item, dict):
                continue
            if self._oracle_matches(item, q_type=q_type, q_text=q_text, targets=targets):
                self._cursor = idx + 1
                consumed = dict(item)
                consumed["__oracle_index__"] = idx
                return consumed
        if self._cursor < len(self.oracle_replies):
            item = self.oracle_replies[self._cursor]
            if isinstance(item, dict):
                self._cursor += 1
                consumed = dict(item)
                consumed["__oracle_index__"] = self._cursor - 1
                return consumed
        return None

    @staticmethod
    def _oracle_matches(oracle: Dict[str, Any], *, q_type: str, q_text: str, targets: set[str]) -> bool:
        trigger = str(oracle.get("trigger_type") or "").lower()
        slot = str(oracle.get("slot") or "").lower()
        is_permission = ("approval" in q_type) or ("permission" in q_type) or ("approve" in q_text)
        if trigger == "permission_query":
            return is_permission
        if trigger == "missing_slot_query":
            if slot and (slot in q_text or slot in targets):
                return True
            return not is_permission
        return True

    @staticmethod
    def _oracle_payload(request: InteractionRequest, oracle: Dict[str, Any]) -> Dict[str, Any]:
        reply_text = str(oracle.get("reply", "") or "").strip()
        q_text = str(request.question or "").lower()
        q_type = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "").lower()
        if ("approval" in q_type) or ("permission" in q_type) or ("approve" in q_text):
            approved = bool(re.search(r"\b(yes|yeah|yep|ok|okay|sure|go ahead|allow)\b", reply_text, flags=re.I))
            denied = bool(re.search(r"\b(no|don't|do not|deny|stop)\b", reply_text, flags=re.I))
            if denied:
                approved = False
            return {"approved": approved}

        schema = request.allowed_response_schema or {}
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = schema.get("required", []) if isinstance(schema, dict) else []
        if isinstance(required, list) and required:
            payload: Dict[str, Any] = {}
            for key in required:
                if key == "tool_id":
                    tool_schema = properties.get("tool_id", {}) if isinstance(properties, dict) else {}
                    if isinstance(tool_schema, dict) and isinstance(tool_schema.get("enum"), list) and tool_schema["enum"]:
                        payload[key] = str(tool_schema["enum"][0])
                    else:
                        payload[key] = reply_text
                else:
                    payload[key] = reply_text
            return payload
        if isinstance(properties, dict) and len(properties) == 1:
            only_key = next(iter(properties.keys()))
            return {str(only_key): reply_text}
        return {"value": reply_text}


def build_reply_provider(
    backend: str,
    *,
    simulator_factory: Callable[[], ReplyProvider],
    llm_completion_fn: Optional[Callable[[InteractionRequest], Dict[str, Any]]] = None,
) -> ReplyProvider:
    normalized = str(backend or "simulator").strip().lower()
    if normalized == "human":
        return HumanReplyProvider()
    if normalized == "llm":
        if llm_completion_fn is None:
            raise ValueError("LLMReplyProvider requires llm_completion_fn")
        return LLMReplyProvider(completion_fn=llm_completion_fn)
    return simulator_factory()
