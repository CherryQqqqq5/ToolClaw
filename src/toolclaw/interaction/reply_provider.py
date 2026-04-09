"""Reply provider abstractions for simulator, human, and LLM-backed interaction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol

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
