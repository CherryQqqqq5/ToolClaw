"""Capability-to-tool binding logic used by the phase-1 planner."""

from __future__ import annotations

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

    @classmethod
    def _tokens(cls, *values: str) -> set[str]:
        tokens: set[str] = set()
        for value in values:
            for token in cls._TOKEN_PATTERN.findall(str(value or "").lower()):
                tokens.add(token)
        return tokens

    def bind_one(self, request: BindingRequest) -> BindingResult:
        capability_name = request.capability.description.lower()
        matches: List[ToolMatch] = []
        sole_candidate = len(request.candidate_tools) == 1
        preferred_tools = set(request.preferred_tools)
        capability_tokens = self._tokens(request.capability.capability_id, request.capability.description)

        for tool in request.candidate_tools:
            if tool.tool_id in request.forbidden_tools:
                continue

            score = 0.1
            reasons: List[str] = []
            tool_tokens = self._tokens(tool.tool_id, tool.description)
            overlap = capability_tokens.intersection(tool_tokens)
            if overlap:
                score += min(0.35, 0.1 * len(overlap))
                reasons.append(f"token_overlap:{'+'.join(sorted(overlap))}")

            is_retrieve = bool({"retrieve", "search", "find", "lookup", "fetch"}.intersection(capability_tokens))
            is_write = bool({"write", "save", "report", "artifact", "send", "reply"}.intersection(capability_tokens)) or "write" in capability_name

            if is_retrieve:
                retrieve_overlap = self._RETRIEVE_HINTS.intersection(tool_tokens)
                if retrieve_overlap:
                    score += 0.65
                    reasons.append("semantic_match:retrieve_tool")
                if "write" in tool_tokens:
                    score -= 0.2
                    reasons.append("penalty:write_tool_for_retrieve")
            if is_write:
                write_overlap = self._WRITE_HINTS.intersection(tool_tokens)
                if write_overlap:
                    score += 0.65
                    reasons.append("semantic_match:write_tool")
                positive_write_hints = self._WRITE_POSITIVE_HINTS.intersection(tool_tokens)
                if positive_write_hints:
                    score += 0.2
                    reasons.append(f"preferred_write_semantics:{'+'.join(sorted(positive_write_hints))}")
                negative_write_hints = self._WRITE_NEGATIVE_HINTS.intersection(tool_tokens)
                if negative_write_hints:
                    penalty = 0.25 if {"backup", "fallback", "outage", "reserved", "reserve"}.intersection(negative_write_hints) else 0.45
                    score -= penalty
                    reasons.append(f"penalty:write_distractor:{'+'.join(sorted(negative_write_hints))}")
            if tool.tool_id in preferred_tools:
                score += 0.35
                reasons.append("reusable_preference")
            if sole_candidate and score <= 0.15:
                score = 0.55
                reasons.append("sole_candidate_tool")

            if score > 0.15:
                matches.append(ToolMatch(tool_id=tool.tool_id, score=round(score, 4), reasons=reasons))

        matches.sort(key=lambda m: (-m.score, m.tool_id))
        if not matches:
            return BindingResult(binding=None, unresolved_reason="no_tool_match")

        primary = matches[0]
        backup_tools = [m.tool_id for m in matches[1:3]]
        binding = ToolBinding(
            capability_id=request.capability.capability_id,
            primary_tool=primary.tool_id,
            backup_tools=backup_tools,
            binding_confidence=primary.score,
        )
        return BindingResult(binding=binding, alternatives=matches)

    def bind_graph(
        self,
        capabilities: Sequence[CapabilityNode],
        candidate_tools: Sequence[ToolSpec],
        context: WorkflowContext,
        forbidden_tools: Optional[List[str]] = None,
        preferred_bindings: Optional[Dict[str, str]] = None,
    ) -> List[BindingResult]:
        forbidden_tools = forbidden_tools or []
        preferred_bindings = preferred_bindings or {}
        return [
            self.bind_one(
                BindingRequest(
                    capability=cap,
                    candidate_tools=candidate_tools,
                    context=context,
                    forbidden_tools=forbidden_tools,
                    preferred_tools=[preferred_bindings[cap.capability_id]]
                    if preferred_bindings.get(cap.capability_id)
                    else [],
                )
            )
            for cap in capabilities
        ]
