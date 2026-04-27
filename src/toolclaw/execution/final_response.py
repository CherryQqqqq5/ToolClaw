"""Gold-free final response synthesis for completed workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from toolclaw.execution.completion_verifier import CompletionVerificationResult
from toolclaw.schemas.trace import Trace
from toolclaw.schemas.workflow import Workflow, WorkflowStep


POLICY_VERSION = "generic_final_response_v1"
GOLD_FIELD_TOKENS = (
    "milestone",
    "reference_result_summary",
    "official_milestone_mapping",
    "official_similarity",
    "official_expected",
    "scorer_gold",
    "gold_message",
)


@dataclass
class FinalResponseSynthesis:
    content: str
    policy_version: str = POLICY_VERSION
    evidence_sources: List[str] = field(default_factory=list)
    used_gold: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FinalResponseSynthesizer:
    """Create a benchmark-facing final response from runtime-visible evidence only."""

    def synthesize(
        self,
        *,
        workflow: Workflow,
        trace: Trace,
        state_values: Dict[str, Any],
        completion_verification: Optional[CompletionVerificationResult] = None,
    ) -> FinalResponseSynthesis:
        tool_events = self._successful_tool_events(trace)
        action = self._infer_action(workflow=workflow, events=tool_events)
        object_label = self._object_label(workflow=workflow, events=tool_events, state_values=state_values)
        detail = self._detail_phrase(events=tool_events, state_values=state_values)
        content = self._render(action=action, object_label=object_label, detail=detail)
        evidence_sources = ["task_goal", "workflow_steps"]
        if tool_events:
            evidence_sources.append("tool_results")
        if self._public_state_keys(state_values):
            evidence_sources.append("state_values")
        if completion_verification is not None:
            evidence_sources.append("completion_verifier")
        return FinalResponseSynthesis(
            content=content,
            evidence_sources=evidence_sources,
            used_gold=False,
            metadata={
                "action_kind": action,
                "tool_result_count": len(tool_events),
                "state_key_count": len(self._public_state_keys(state_values)),
                "completion_verifier_recommended_action": getattr(
                    completion_verification,
                    "recommended_action",
                    None,
                ),
                "gold_free": True,
            },
        )

    @staticmethod
    def _successful_tool_events(trace: Trace) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for event in trace.events:
            event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            if event_type != "tool_result":
                continue
            output = event.output if isinstance(event.output, dict) else {}
            status = str(output.get("status") or "").lower()
            if status in {"success", "ok", "succeeded", ""}:
                events.append(
                    {
                        "tool_id": event.tool_id or "",
                        "step_id": event.step_id or "",
                        "output": FinalResponseSynthesizer._sanitize_mapping(output),
                    }
                )
        return events

    def _infer_action(self, *, workflow: Workflow, events: Sequence[Dict[str, Any]]) -> str:
        text = " ".join(
            [
                workflow.task.user_goal or "",
                " ".join(step.capability_id or "" for step in workflow.execution_plan),
                " ".join(step.tool_id or "" for step in workflow.execution_plan),
                " ".join(str(step.expected_output or "") for step in workflow.execution_plan),
                " ".join(str(event.get("tool_id") or "") for event in events),
            ]
        ).lower()
        if self._has_any(text, ("send", "message", "email", "sms", "text", "notify", "reply")):
            return "send"
        if self._has_any(text, ("update", "modify", "set", "toggle", "enable", "disable", "change", "status")):
            return "update"
        if self._has_any(text, ("create", "add", "schedule", "remind", "book")):
            return "create"
        if self._has_any(text, ("delete", "remove", "clear", "cancel")):
            return "delete"
        if self._has_any(text, ("write", "save", "store", "persist", "file", "artifact", "report")):
            return "write"
        if self._has_any(text, ("find", "lookup", "search", "retrieve", "read", "fetch", "get")):
            return "retrieve"
        return "complete"

    def _object_label(
        self,
        *,
        workflow: Workflow,
        events: Sequence[Dict[str, Any]],
        state_values: Dict[str, Any],
    ) -> str:
        candidate = self._first_public_value(
            self._iter_step_values(workflow.execution_plan),
            max_len=48,
        )
        if candidate:
            return candidate
        candidate = self._first_public_value(
            self._iter_event_values(events),
            max_len=48,
        )
        if candidate:
            return candidate
        candidate = self._first_public_value(
            self._iter_state_values(state_values),
            max_len=48,
        )
        return candidate or "the requested task"

    def _detail_phrase(self, *, events: Sequence[Dict[str, Any]], state_values: Dict[str, Any]) -> str:
        for event in events:
            output = event.get("output") if isinstance(event.get("output"), dict) else {}
            payload = output.get("payload") or output.get("message") or output.get("result")
            detail = self._clean_text(payload, max_len=80)
            if detail:
                return detail
        state_keys = self._public_state_keys(state_values)
        if state_keys:
            return "updated runtime state: " + ", ".join(state_keys[:3])
        return ""

    @staticmethod
    def _render(*, action: str, object_label: str, detail: str) -> str:
        templates = {
            "send": "I sent the requested message for {object_label}.",
            "update": "I completed the requested update for {object_label}.",
            "create": "I created the requested item for {object_label}.",
            "delete": "I completed the requested removal for {object_label}.",
            "write": "I saved the requested output for {object_label}.",
            "retrieve": "I found the requested information for {object_label}.",
            "complete": "I completed the requested task for {object_label}.",
        }
        response = templates.get(action, templates["complete"]).format(object_label=object_label)
        if detail and detail.lower() not in response.lower():
            response = f"{response} Result: {detail}."
        return re.sub(r"\s+", " ", response).strip()

    @classmethod
    def _sanitize_mapping(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        clean: Dict[str, Any] = {}
        for key, item in value.items():
            if cls._is_gold_key(key):
                continue
            clean[str(key)] = cls._sanitize_value(item)
        return clean

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return cls._sanitize_mapping(value)
        if isinstance(value, list):
            return [cls._sanitize_value(item) for item in value if not cls._looks_like_gold_payload(item)]
        if cls._looks_like_gold_payload(value):
            return ""
        return value

    @staticmethod
    def _is_gold_key(key: Any) -> bool:
        text = str(key or "").lower()
        return any(token in text for token in GOLD_FIELD_TOKENS)

    @classmethod
    def _looks_like_gold_payload(cls, value: Any) -> bool:
        if isinstance(value, (dict, list)):
            return False
        text = str(value or "")
        return any(token in text.lower() for token in ("secret_milestone", "secret_reference", "scorer_gold"))

    @staticmethod
    def _public_state_keys(state_values: Dict[str, Any]) -> List[str]:
        return sorted(
            str(key)
            for key, value in state_values.items()
            if not str(key).startswith("__") and value not in (None, "")
        )

    @classmethod
    def _iter_step_values(cls, steps: Iterable[WorkflowStep]) -> Iterable[Any]:
        for step in steps:
            for key, value in step.inputs.items():
                if not cls._is_gold_key(key):
                    yield value
            yield step.expected_output

    @classmethod
    def _iter_event_values(cls, events: Sequence[Dict[str, Any]]) -> Iterable[Any]:
        for event in events:
            output = event.get("output") if isinstance(event.get("output"), dict) else {}
            for key in ("target", "recipient", "path", "payload", "message", "result"):
                if key in output:
                    yield output.get(key)

    @classmethod
    def _iter_state_values(cls, state_values: Dict[str, Any]) -> Iterable[Any]:
        for key, value in state_values.items():
            if str(key).startswith("__") or cls._is_gold_key(key):
                continue
            yield value

    @classmethod
    def _first_public_value(cls, values: Iterable[Any], *, max_len: int) -> str:
        for value in values:
            text = cls._clean_text(value, max_len=max_len)
            if text:
                return text
        return ""

    @classmethod
    def _clean_text(cls, value: Any, *, max_len: int) -> str:
        if value is None or isinstance(value, (dict, list)):
            return ""
        if cls._looks_like_gold_payload(value):
            return ""
        text = re.sub(r"\s+", " ", str(value)).strip().strip(". ")

        if not text or text.lower() in {"none", "null", "unknown", "n/a"}:
            return ""
        if len(text) > max_len:
            text = text[: max_len - 1].rstrip() + "..."
        return text

    @staticmethod
    def _has_any(text: str, tokens: Sequence[str]) -> bool:
        return any(token in text for token in tokens)
