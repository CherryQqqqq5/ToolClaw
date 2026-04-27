"""Gold-free workflow completion diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Dict, List

from toolclaw.schemas.trace import Trace
from toolclaw.schemas.workflow import Workflow


@dataclass
class CompletionVerificationResult:
    completion_verified: bool
    confidence: float
    missing_evidence: List[str] = field(default_factory=list)
    recommended_action: str = "finalize"
    verifier_reason: str = "runtime evidence is sufficient"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CompletionVerifier:
    """Conservative diagnostic verifier that uses only runtime-visible evidence."""

    def verify(
        self,
        *,
        workflow: Workflow,
        trace: Trace,
        state_values: Dict[str, Any],
    ) -> CompletionVerificationResult:
        events = list(trace.events)
        missing: List[str] = []
        successful_results: List[Dict[str, Any]] = []
        user_queries = 0
        approval_requests = 0
        approval_responses = 0

        for event in events:
            event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            output = event.output if isinstance(event.output, dict) else {}
            if event_type == "tool_result" and str(output.get("status") or "").lower() in {"success", "ok", "succeeded"}:
                successful_results.append(output)
            elif event_type == "user_query":
                user_queries += 1
            elif event_type == "approval_request":
                approval_requests += 1
            elif event_type == "approval_response":
                approval_responses += 1

        if workflow.execution_plan and not successful_results:
            missing.append("successful_tool_result")

        if workflow.task.constraints.requires_user_approval and not (approval_requests and approval_responses):
            missing.append("required_approval_exchange")

        if self._should_have_clarified(workflow=workflow, user_queries=user_queries):
            missing.append("user_clarification_for_ambiguous_goal")

        if successful_results and self._only_generic_completion_artifact(successful_results):
            missing.append("task_relevant_final_evidence")

        pending_slots = self._unresolved_required_inputs(workflow=workflow, state_values=state_values)
        if pending_slots:
            missing.append("unresolved_required_inputs")

        if missing:
            action = self._recommended_action(missing)
            return CompletionVerificationResult(
                completion_verified=False,
                confidence=0.35,
                missing_evidence=missing,
                recommended_action=action,
                verifier_reason="runtime evidence is insufficient for a benchmark-facing completion decision",
                metadata={
                    "successful_tool_results": len(successful_results),
                    "user_queries": user_queries,
                    "approval_requests": approval_requests,
                    "approval_responses": approval_responses,
                    "unresolved_required_inputs": pending_slots,
                    "gold_free": True,
                },
            )

        return CompletionVerificationResult(
            completion_verified=True,
            confidence=0.8,
            missing_evidence=[],
            recommended_action="finalize",
            verifier_reason="completed workflow has concrete runtime evidence",
            metadata={
                "successful_tool_results": len(successful_results),
                "user_queries": user_queries,
                "approval_requests": approval_requests,
                "approval_responses": approval_responses,
                "gold_free": True,
            },
        )

    @staticmethod
    def _unresolved_required_inputs(*, workflow: Workflow, state_values: Dict[str, Any]) -> List[str]:
        unresolved: List[str] = []
        for step in workflow.execution_plan:
            for key in step.metadata.get("unresolved_required_inputs", []) if isinstance(step.metadata, dict) else []:
                text = str(key or "").strip()
                if text and text not in step.inputs and text not in state_values and text not in unresolved:
                    unresolved.append(text)
        return unresolved

    def _should_have_clarified(self, *, workflow: Workflow, user_queries: int) -> bool:
        if user_queries > 0:
            return False
        if not self._system_message_requests_clarification(workflow):
            return False
        goal = str(workflow.task.user_goal or "")
        return self._looks_like_missing_typed_value(goal)

    @staticmethod
    def _system_message_requests_clarification(workflow: Workflow) -> bool:
        messages = workflow.metadata.get("messages") if isinstance(workflow.metadata, dict) else None
        if not isinstance(messages, list):
            return False
        for message in messages:
            if not isinstance(message, dict):
                continue
            sender = str(message.get("sender") or message.get("role") or "").lower()
            content = str(message.get("content") or "").lower()
            if sender == "system" and ("ask for clarification" in content or "don't make assumptions" in content):
                return True
        return False

    @staticmethod
    def _looks_like_missing_typed_value(goal: str) -> bool:
        text = goal.lower()
        temporal_intent = any(token in text for token in ("remind", "schedule", "appointment", "meeting", "alarm"))
        has_time_or_date = bool(
            re.search(
                r"\b(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|am|pm|a\.m\.|p\.m\.|\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2}|january|february|march|april|may|june|july|august|september|october|november|december)\b",
                text,
            )
        )
        if temporal_intent and not has_time_or_date:
            return True
        entity_intent = any(token in text for token in ("remove", "delete", "modify", "update", "send", "message", "email"))
        ambiguous_reference = any(token in text for token in ("latest", "oldest", "recent", "that", "it", "them", "the contact", "the message"))
        return entity_intent and ambiguous_reference

    @staticmethod
    def _only_generic_completion_artifact(successful_results: List[Dict[str, Any]]) -> bool:
        payloads = [str(result.get("payload") or "") for result in successful_results]
        if not payloads:
            return False
        generic_payloads = 0
        for payload in payloads:
            low = payload.lower()
            if low.startswith("wrote artifact to ") or low.startswith("summary for:") or "backup write success at" in low:
                generic_payloads += 1
        return generic_payloads == len(payloads)

    @staticmethod
    def _recommended_action(missing: List[str]) -> str:
        if "user_clarification_for_ambiguous_goal" in missing or "required_approval_exchange" in missing:
            return "ask_user"
        if "unresolved_required_inputs" in missing or "successful_tool_result" in missing:
            return "repair"
        if "task_relevant_final_evidence" in missing:
            return "synthesize_final_response"
        return "diagnose"
