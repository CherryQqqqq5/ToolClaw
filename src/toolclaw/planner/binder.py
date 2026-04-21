"""Capability-to-tool binding logic used by the phase-1 planner."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.schemas.workflow import CapabilityNode, ToolBinding, ToolSpec, WorkflowContext


@dataclass
class ToolMatch:
    tool_id: str
    score: float
    reasons: List[str] = field(default_factory=list)
    arg_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BindingRequest:
    capability: CapabilityNode
    candidate_tools: Sequence[ToolSpec]
    context: WorkflowContext
    state_values: Dict[str, Any] = field(default_factory=dict)
    forbidden_tools: List[str] = field(default_factory=list)
    preferred_tools: List[str] = field(default_factory=list)
    required_state_slots: List[str] = field(default_factory=list)
    state_preconditions: List[str] = field(default_factory=list)
    ordering_sensitive: bool = False
    backup_tool_map: Dict[str, str] = field(default_factory=dict)


@dataclass
class BindingResult:
    binding: Optional[ToolBinding]
    alternatives: List[ToolMatch] = field(default_factory=list)
    unresolved_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolBinder:
    """Rule-based capability-to-tool binder for phase-1."""

    _TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
    _RETRIEVE_HINTS = {"retrieve", "search", "find", "lookup", "fetch", "collect", "summary", "summarize"}
    _WRITE_HINTS = {"write", "writer", "save", "report", "artifact", "final", "draft", "reply", "send"}
    _WRITE_POSITIVE_HINTS = {"primary", "standard", "approved", "normal", "main"}
    _WRITE_NEGATIVE_HINTS = {"backup", "fallback", "reserve", "reserved", "outage", "legacy", "ordering", "order", "violate", "violates"}
    _RETRIEVE_CAPABILITY_IDS = {"cap_retrieve", "cap_search", "cap_lookup"}
    _WRITE_CAPABILITY_IDS = {"cap_write", "cap_send", "cap_reply"}
    _STATE_ADMIN_HINTS = {"set", "status", "state", "toggle", "enable", "disable", "update"}

    @classmethod
    def _tokens(cls, *values: str) -> set[str]:
        tokens: set[str] = set()
        for value in values:
            if isinstance(value, (list, tuple, set)):
                tokens.update(cls._tokens(*value))
                continue
            if isinstance(value, dict):
                tokens.update(cls._tokens(*value.keys()))
                tokens.update(cls._tokens(*value.values()))
                continue
            for token in cls._TOKEN_PATTERN.findall(str(value or "").lower()):
                tokens.add(token)
        return tokens

    @classmethod
    def _metadata_tokens(cls, metadata: Dict[str, Any]) -> set[str]:
        return cls._tokens(
            metadata.get("affordances", []),
            metadata.get("semantic_tags", []),
            metadata.get("preferred_capabilities", []),
            metadata.get("disallowed_capabilities", []),
            metadata.get("usage_notes"),
            metadata.get("failure_priors", []),
            metadata.get("strengths", []),
            metadata.get("weaknesses", []),
        )

    @staticmethod
    def _normalized_items(value: Any) -> set[str]:
        if isinstance(value, str):
            return {value.strip().lower()} if value.strip() else set()
        if isinstance(value, Iterable):
            items: set[str] = set()
            for item in value:
                text = str(item or "").strip().lower()
                if text:
                    items.add(text)
            return items
        return set()

    @staticmethod
    def _tool_parameters(metadata: Dict[str, Any]) -> Dict[str, Any]:
        parameters = metadata.get("parameters") or metadata.get("schema") or {}
        return dict(parameters) if isinstance(parameters, dict) else {}

    @classmethod
    def _tool_required_input_keys(cls, metadata: Dict[str, Any]) -> List[str]:
        explicit = metadata.get("required_inputs")
        if isinstance(explicit, list):
            return [str(item) for item in explicit if str(item)]
        parameters = cls._tool_parameters(metadata)
        required = parameters.get("required")
        if isinstance(required, list):
            return [str(item) for item in required if str(item)]
        return []

    @staticmethod
    def _binding_source_payload(*, source: str, confidence: float, state_key: Optional[str] = None, rationale: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"source": source, "confidence": float(confidence)}
        if state_key:
            payload["state_key"] = state_key
        if rationale:
            payload["rationale"] = rationale
        return payload

    def bind_one(self, request: BindingRequest) -> BindingResult:
        capability_name = request.capability.description.lower()
        matches: List[ToolMatch] = []
        sole_candidate = len(request.candidate_tools) == 1
        preferred_tools = set(request.preferred_tools)
        capability_tokens = self._tokens(request.capability.capability_id, request.capability.description)
        required_state_slots = self._normalized_items(request.required_state_slots)
        state_preconditions = self._normalized_items(request.state_preconditions)
        state_requirement_tokens = self._tokens(sorted(required_state_slots), sorted(state_preconditions))
        backup_only_tools = {
            str(backup_tool_id).strip()
            for backup_tool_id in request.backup_tool_map.values()
            if str(backup_tool_id).strip()
        }

        for tool in request.candidate_tools:
            if tool.tool_id in request.forbidden_tools:
                continue

            score = 0.1
            reasons: List[str] = []
            metadata = tool.metadata if isinstance(tool.metadata, dict) else {}
            tool_tokens = self._tokens(tool.tool_id, tool.description)
            metadata_tokens = self._metadata_tokens(metadata)
            if metadata_tokens:
                tool_tokens = tool_tokens.union(metadata_tokens)
            overlap = capability_tokens.intersection(tool_tokens)
            if overlap:
                score += min(0.35, 0.1 * len(overlap))
                reasons.append(f"token_overlap:{'+'.join(sorted(overlap))}")

            is_retrieve = bool({"retrieve", "search", "find", "lookup", "fetch"}.intersection(capability_tokens))
            is_retrieve = is_retrieve or request.capability.capability_id in self._RETRIEVE_CAPABILITY_IDS
            is_write = bool({"write", "save", "report", "artifact", "send", "reply"}.intersection(capability_tokens)) or "write" in capability_name
            is_write = is_write or request.capability.capability_id in self._WRITE_CAPABILITY_IDS

            preferred_capabilities = self._normalized_items(metadata.get("preferred_capabilities", []))
            disallowed_capabilities = self._normalized_items(metadata.get("disallowed_capabilities", []))
            affordances = self._normalized_items(metadata.get("affordances", []))
            failure_priors = self._normalized_items(metadata.get("failure_priors", []))
            tool_required_state_slots = self._normalized_items(
                metadata.get("required_state_slots")
                or metadata.get("consumes_state_slots")
                or metadata.get("state_preconditions")
                or []
            )
            required_input_keys = self._tool_required_input_keys(metadata)
            tool_produced_state_slots = self._normalized_items(
                metadata.get("produces_state_slots")
                or metadata.get("state_outputs")
                or []
            )

            capability_id = request.capability.capability_id.lower()
            if capability_id in preferred_capabilities:
                score += 0.45
                reasons.append("metadata:preferred_capability")
            if capability_id in disallowed_capabilities:
                score -= 0.7
                reasons.append("metadata:disallowed_capability")

            retrieve_overlap = self._RETRIEVE_HINTS.intersection(tool_tokens)
            write_overlap = self._WRITE_HINTS.intersection(tool_tokens)
            state_admin_overlap = self._STATE_ADMIN_HINTS.intersection(tool_tokens).union(
                self._STATE_ADMIN_HINTS.intersection(affordances)
            )

            if is_retrieve:
                if retrieve_overlap:
                    score += 0.65
                    reasons.append("semantic_match:retrieve_tool")
                if affordances.intersection(self._RETRIEVE_HINTS):
                    score += 0.3
                    reasons.append("metadata:retrieve_affordance")
                if "write" in tool_tokens:
                    score -= 0.2
                    reasons.append("penalty:write_tool_for_retrieve")
            if is_write:
                if write_overlap:
                    score += 0.65
                    reasons.append("semantic_match:write_tool")
                if affordances.intersection(self._WRITE_HINTS):
                    score += 0.3
                    reasons.append("metadata:write_affordance")
                positive_write_hints = self._WRITE_POSITIVE_HINTS.intersection(tool_tokens)
                if positive_write_hints:
                    score += 0.2
                    reasons.append(f"preferred_write_semantics:{'+'.join(sorted(positive_write_hints))}")
                negative_write_hints = self._WRITE_NEGATIVE_HINTS.intersection(tool_tokens)
                if negative_write_hints:
                    penalty = 0.25 if {"backup", "fallback", "outage", "reserved", "reserve"}.intersection(negative_write_hints) else 0.45
                    score -= penalty
                    reasons.append(f"penalty:write_distractor:{'+'.join(sorted(negative_write_hints))}")
            if required_state_slots:
                if tool_required_state_slots and required_state_slots.issubset(tool_required_state_slots):
                    score += 0.35
                    reasons.append("state_preconditions:tool_consumes_required_slots")
                elif tool_required_state_slots and tool_required_state_slots.intersection(required_state_slots):
                    score += 0.18
                    reasons.append("state_preconditions:partial_state_slot_match")
                if tool_produced_state_slots.intersection(required_state_slots):
                    score -= 0.35
                    reasons.append("penalty:tool_produces_dependency_state")

                state_slot_overlap = state_requirement_tokens.intersection(tool_tokens)
                if request.ordering_sensitive and state_slot_overlap and state_admin_overlap and not is_retrieve:
                    score -= 0.45
                    reasons.append(
                        f"penalty:ordering_state_prep_tool:{'+'.join(sorted(state_slot_overlap))}"
                    )
                elif request.ordering_sensitive and state_slot_overlap and write_overlap:
                    score += 0.12
                    reasons.append(
                        f"ordering_sensitive:consumer_tool:{'+'.join(sorted(state_slot_overlap))}"
                    )
                elif is_write and not state_admin_overlap and write_overlap:
                    score += 0.08
                    reasons.append("state_preconditions:write_after_state_ready")
            if request.state_values.get("__failure_context__"):
                failure_context = str(request.state_values["__failure_context__"]).strip().lower()
                if failure_context and failure_context in failure_priors:
                    score -= 0.2
                    reasons.append("metadata:failure_prior_penalty")
            if tool.tool_id in backup_only_tools and tool.tool_id not in preferred_tools:
                score -= 0.3
                reasons.append("penalty:planner_backup_only_tool")
            if tool.tool_id in request.backup_tool_map:
                score += 0.12
                reasons.append("planner:primary_has_declared_backup")
            if tool.tool_id in preferred_tools:
                score += 0.9
                reasons.append("reusable_preference")
            if sole_candidate and score <= 0.15:
                score = 0.55
                reasons.append("sole_candidate_tool")

            if score > 0.15:
                input_bindings: Dict[str, str] = {}
                grounding_sources: Dict[str, Any] = {}
                grounding_confidence: Dict[str, float] = {}
                unresolved_required_inputs: List[str] = []
                for input_key in required_input_keys:
                    normalized_key = str(input_key).strip()
                    if not normalized_key:
                        continue
                    if normalized_key in request.state_values:
                        input_bindings[normalized_key] = normalized_key
                        grounding_sources[normalized_key] = self._binding_source_payload(
                            source="state_value",
                            state_key=normalized_key,
                            confidence=0.95,
                            rationale="existing state value matches the required input key",
                        )
                        grounding_confidence[normalized_key] = 0.95
                        continue
                    if normalized_key.lower() in required_state_slots:
                        input_bindings[normalized_key] = normalized_key
                        grounding_sources[normalized_key] = self._binding_source_payload(
                            source="required_state_slot",
                            state_key=normalized_key,
                            confidence=0.85,
                            rationale="required state slot name matches the required input key",
                        )
                        grounding_confidence[normalized_key] = 0.85
                        continue
                    unresolved_required_inputs.append(normalized_key)
                    grounding_sources[normalized_key] = self._binding_source_payload(
                        source="unresolved",
                        confidence=0.0,
                        rationale="tool requires the input but binder has no generic source for it",
                    )
                    grounding_confidence[normalized_key] = 0.0
                matches.append(
                    ToolMatch(
                        tool_id=tool.tool_id,
                        score=round(score, 4),
                        reasons=reasons,
                        arg_hints={
                            "required_input_keys": list(required_input_keys),
                            "input_bindings": input_bindings,
                            "grounding_sources": grounding_sources,
                            "grounding_confidence": grounding_confidence,
                            "unresolved_required_inputs": unresolved_required_inputs,
                        },
                    )
                )

        matches.sort(key=lambda m: (-m.score, m.tool_id))
        if not matches:
            return BindingResult(binding=None, unresolved_reason="no_tool_match")

        primary = matches[0]
        backup_tools = [m.tool_id for m in matches[1:3]]
        declared_backup = str(request.backup_tool_map.get(primary.tool_id) or "").strip()
        if declared_backup and declared_backup not in request.forbidden_tools:
            candidate_tool_ids = {tool.tool_id for tool in request.candidate_tools}
            if declared_backup in candidate_tool_ids and declared_backup != primary.tool_id:
                backup_tools = [declared_backup] + [tool_id for tool_id in backup_tools if tool_id != declared_backup]
        binding = ToolBinding(
            capability_id=request.capability.capability_id,
            primary_tool=primary.tool_id,
            backup_tools=backup_tools,
            binding_confidence=primary.score,
            required_input_keys=list(primary.arg_hints.get("required_input_keys", [])),
            input_bindings=dict(primary.arg_hints.get("input_bindings", {})),
            grounding_sources=dict(primary.arg_hints.get("grounding_sources", {})),
            grounding_confidence=dict(primary.arg_hints.get("grounding_confidence", {})),
            unresolved_required_inputs=list(primary.arg_hints.get("unresolved_required_inputs", [])),
        )
        return BindingResult(
            binding=binding,
            alternatives=matches,
            metadata={
                "tool_choice_evidence": list(primary.reasons),
                "required_input_keys": list(binding.required_input_keys),
                "input_bindings": dict(binding.input_bindings),
                "grounding_sources": dict(binding.grounding_sources),
                "grounding_confidence": dict(binding.grounding_confidence),
                "unresolved_required_inputs": list(binding.unresolved_required_inputs),
            },
        )

    def bind_graph(
        self,
        capabilities: Sequence[CapabilityNode],
        candidate_tools: Sequence[ToolSpec],
        context: WorkflowContext,
        forbidden_tools: Optional[List[str]] = None,
        preferred_bindings: Optional[Dict[str, str]] = None,
        state_values: Optional[Dict[str, Any]] = None,
        step_hints: Optional[Sequence[Dict[str, Any]]] = None,
        backup_tool_map: Optional[Dict[str, str]] = None,
    ) -> List[BindingResult]:
        forbidden_tools = forbidden_tools or []
        preferred_bindings = preferred_bindings or {}
        state_values = state_values or {}
        step_hints = list(step_hints or [])
        backup_tool_map = backup_tool_map or {}
        return [
            self.bind_one(
                BindingRequest(
                    capability=cap,
                    candidate_tools=candidate_tools,
                    context=context,
                    state_values=dict(state_values),
                    forbidden_tools=forbidden_tools,
                    preferred_tools=[preferred_bindings[cap.capability_id]]
                    if preferred_bindings.get(cap.capability_id)
                    else [],
                    required_state_slots=list(step_hints[idx].get("required_state_slots", []))
                    if idx < len(step_hints)
                    else [],
                    state_preconditions=list(step_hints[idx].get("state_preconditions", []))
                    if idx < len(step_hints)
                    else [],
                    ordering_sensitive=bool(step_hints[idx].get("ordering_sensitive"))
                    if idx < len(step_hints)
                    else False,
                    backup_tool_map=dict(backup_tool_map),
                )
            )
            for idx, cap in enumerate(capabilities)
        ]
