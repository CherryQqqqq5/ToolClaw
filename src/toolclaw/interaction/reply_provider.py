"""Reply provider abstractions for simulator, human, and LLM-backed interaction."""

from __future__ import annotations

import json
import hashlib
import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol, Sequence

from toolclaw.interaction.repair_updater import InteractionRequest


@dataclass
class RawUserReply:
    interaction_id: str
    raw_text: str
    raw_payload: Dict[str, Any]
    status: str = "accept"
    accepted: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    @property
    def payload(self) -> Dict[str, Any]:
        return self.raw_payload


class ReplyProvider(Protocol):
    def reply(self, request: InteractionRequest) -> RawUserReply:
        ...


class SimulatorReplyProvider(ReplyProvider, Protocol):
    def reply(self, request: InteractionRequest) -> RawUserReply:
        ...


@dataclass
class HumanStdinProvider:
    """Interactive stdin provider for manual experimentation."""

    prompt_prefix: str = "toolclaw"

    def reply(self, request: InteractionRequest) -> RawUserReply:
        print(f"[{self.prompt_prefix}] question: {request.question}")
        print(f"[{self.prompt_prefix}] expected_answer_type: {request.expected_answer_type}")
        if request.allowed_response_schema:
            print(f"[{self.prompt_prefix}] schema: {json.dumps(request.allowed_response_schema, ensure_ascii=True)}")
        raw = input(f"[{self.prompt_prefix}] reply json (or empty for abstain): ").strip()
        if not raw:
            return RawUserReply(
                interaction_id=request.interaction_id,
                raw_payload={"abstain": True},
                raw_text="",
                accepted=False,
                status="abstain",
                metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return RawUserReply(
                interaction_id=request.interaction_id,
                raw_payload={"raw_text": raw},
                raw_text=raw,
                accepted=False,
                status="malformed",
                metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
            )
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_payload=payload if isinstance(payload, dict) else {"value": payload},
            raw_text=raw,
            accepted=True,
            status="accept",
            metadata={"patch_targets": dict(request.metadata.get("patch_targets", {}))},
        )


class HumanReplyProvider(HumanStdinProvider):
    """Compatibility alias for a human-backed reply provider."""


@dataclass
class DeterministicNoisyReplyProvider:
    """Deterministic adversarial replies for interaction causality ablations."""

    provider_name: str = "deterministic_noisy"

    def reply(self, request: InteractionRequest) -> RawUserReply:
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        choices = [
            ("I don't know", {"raw_text": "I don't know"}),
            ("irrelevant answer", {"raw_text": "irrelevant answer"}),
            ("wrong parameter", {"input_patch": {"value": "wrong_parameter"}}),
        ]
        digest = hashlib.sha256(str(request.interaction_id).encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(choices)
        raw_text, payload = choices[index]
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_text=raw_text,
            raw_payload=payload,
            status="accept",
            accepted=True,
            metadata={
                "provider": self.provider_name,
                "noisy_reply": True,
                "noise_index": index,
                "patch_targets": patch_targets,
            },
        )


@dataclass
class DeterministicModeReplyProvider:
    """Deterministic benchmark-only user modes for interaction live ablations."""

    mode: str
    provider_name: str = "deterministic_mode"

    def reply(self, request: InteractionRequest) -> RawUserReply:
        normalized = str(self.mode or "noisy").strip().lower()
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        suggested_values = request.metadata.get("suggested_values", {})
        if not isinstance(suggested_values, dict):
            suggested_values = {}
        if normalized == "irrelevant":
            raw_text = "irrelevant answer"
            payload: Dict[str, Any] = {"raw_text": raw_text}
        elif normalized == "wrong_parameter":
            raw_text = "wrong parameter"
            payload = {"input_patch": {"value": "wrong_parameter"}}
        elif normalized == "partial":
            raw_text = "partial answer"
            payload = self._partial_payload(request, patch_targets, suggested_values)
        else:
            choices = [
                ("I don't know", {"raw_text": "I don't know"}),
                ("irrelevant answer", {"raw_text": "irrelevant answer"}),
                ("not enough information", {"raw_text": "not enough information"}),
            ]
            digest = hashlib.sha256(str(request.interaction_id).encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % len(choices)
            raw_text, payload = choices[index]
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_text=raw_text,
            raw_payload=payload,
            status="accept",
            accepted=True,
            metadata={
                "provider": self.provider_name,
                "interaction_live_user_mode": normalized,
                "patch_targets": patch_targets,
            },
        )

    @staticmethod
    def _partial_payload(
        request: InteractionRequest,
        patch_targets: Dict[str, Any],
        suggested_values: Dict[str, Any],
    ) -> Dict[str, Any]:
        if "approved" in patch_targets or "approval" in str(request.expected_answer_type or "").lower():
            return {"approved": True}
        for key in patch_targets:
            key_text = str(key)
            if key_text == "approved":
                continue
            if key_text in suggested_values:
                return {key_text: suggested_values[key_text]}
            return {key_text: f"partial_{key_text}"}
        return {"raw_text": "partial answer"}


@dataclass
class CLIReplyProvider:
    """Invoke external CLI command and capture reply."""

    command: Sequence[str] | str
    timeout_s: float = 30.0
    provider_name: str = "cli_reply_provider"

    def _resolve_command(self) -> list[str]:
        if isinstance(self.command, str):
            cmd = shlex.split(self.command.strip())
        else:
            cmd = [str(part) for part in self.command if str(part)]
        if not cmd:
            raise ValueError("CLIReplyProvider requires a non-empty command")
        return cmd

    def reply(self, request: InteractionRequest) -> RawUserReply:
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        req_payload = {
            "interaction_id": request.interaction_id,
            "question": request.question,
            "expected_answer_type": request.expected_answer_type,
            "allowed_response_schema": dict(request.allowed_response_schema),
            "context_summary": dict(request.context_summary),
            "metadata": dict(request.metadata),
        }
        cmd = self._resolve_command()
        try:
            proc = subprocess.run(
                cmd,
                input=json.dumps(req_payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=max(float(self.timeout_s), 0.0) or None,
                check=False,
            )
        except Exception as exc:
            return RawUserReply(
                interaction_id=request.interaction_id,
                raw_text=str(exc),
                raw_payload={"error": str(exc)},
                status="malformed",
                accepted=False,
                metadata={
                    "provider": self.provider_name,
                    "patch_targets": patch_targets,
                    "command": cmd,
                },
            )

        stdout_text = str(proc.stdout or "").strip()
        stderr_text = str(proc.stderr or "").strip()
        if proc.returncode != 0:
            return RawUserReply(
                interaction_id=request.interaction_id,
                raw_text=stdout_text or stderr_text,
                raw_payload={
                    "returncode": proc.returncode,
                    "stderr": stderr_text,
                    "stdout": stdout_text,
                },
                status="malformed",
                accepted=False,
                metadata={
                    "provider": self.provider_name,
                    "patch_targets": patch_targets,
                    "command": cmd,
                    "returncode": proc.returncode,
                },
            )

        payload: Dict[str, Any] = {}
        status = "accept"
        accepted = True
        extra_metadata: Dict[str, Any] = {}
        if stdout_text:
            try:
                parsed = json.loads(stdout_text)
                if isinstance(parsed, dict):
                    payload = dict(parsed.get("payload", parsed))
                    status = str(parsed.get("status", "accept"))
                    accepted = bool(parsed.get("accepted", status == "accept"))
                    if isinstance(parsed.get("metadata"), dict):
                        extra_metadata = dict(parsed["metadata"])
                else:
                    payload = {"value": parsed}
            except json.JSONDecodeError:
                payload = {"value": stdout_text}
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_text=stdout_text,
            raw_payload=payload,
            status=status,
            accepted=accepted,
            metadata={
                "provider": self.provider_name,
                "patch_targets": patch_targets,
                "command": cmd,
                "stderr": stderr_text,
                **extra_metadata,
            },
        )


@dataclass
class LLMReplyProvider:
    """Thin wrapper around an injected LLM callback for reply generation."""

    completion_fn: Callable[[InteractionRequest], Dict[str, Any]]
    provider_name: str = "llm_reply_provider"

    def reply(self, request: InteractionRequest) -> RawUserReply:
        result = self.completion_fn(request)
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        if not isinstance(result, dict):
            return RawUserReply(
                interaction_id=request.interaction_id,
                raw_payload={"raw_result": result},
                raw_text=str(result),
                accepted=False,
                status="malformed",
                metadata={"provider": self.provider_name, "patch_targets": patch_targets},
            )
        payload = dict(result.get("payload", result))
        status = str(result.get("status", "accept"))
        accepted = bool(result.get("accepted", status == "accept"))
        extra_metadata = dict(result.get("metadata", {})) if isinstance(result.get("metadata"), dict) else {}
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_payload=payload,
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

    def reply(self, request: InteractionRequest) -> RawUserReply:
        patch_targets = dict(request.metadata.get("patch_targets", {}))
        match = self._consume_matching(request)
        if match is None:
            fallback = self.fallback_provider.reply(request)
            fallback_metadata = dict(getattr(fallback, "metadata", {}) or {})
            fallback_metadata.update(
                {
                    "provider": self.provider_name,
                    "oracle_reply_consumed": False,
                    "oracle_reply_mismatch": True,
                    "oracle_reply_cursor": int(self._cursor),
                    "patch_targets": patch_targets,
                }
            )
            fallback_payload = getattr(fallback, "raw_payload", None)
            if not isinstance(fallback_payload, dict):
                fallback_payload = dict(getattr(fallback, "payload", {}) or {})
            return RawUserReply(
                interaction_id=getattr(fallback, "interaction_id", request.interaction_id),
                raw_payload=fallback_payload,
                raw_text=str(getattr(fallback, "raw_text", "") or ""),
                accepted=bool(getattr(fallback, "accepted", True)),
                status=str(getattr(fallback, "status", "accept")),
                metadata=fallback_metadata,
            )
        payload = self._oracle_payload(request, match)
        return RawUserReply(
            interaction_id=request.interaction_id,
            raw_payload=payload,
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
        if isinstance(oracle.get("payload"), dict):
            return dict(oracle["payload"])
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
    cli_command: Optional[Sequence[str] | str] = None,
) -> ReplyProvider:
    normalized = str(backend or "simulator").strip().lower()
    if normalized == "human":
        return HumanReplyProvider()
    if normalized == "cli":
        if cli_command is None:
            raise ValueError("CLIReplyProvider requires cli_command")
        return CLIReplyProvider(command=cli_command)
    if normalized == "llm":
        if llm_completion_fn is None:
            raise ValueError("LLMReplyProvider requires llm_completion_fn")
        return LLMReplyProvider(completion_fn=llm_completion_fn)
    return simulator_factory()
