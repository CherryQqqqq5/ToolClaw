"""Capability-to-tool binding logic used by the phase-1 planner."""

from __future__ import annotations

from dataclasses import dataclass, field
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

    def bind_one(self, request: BindingRequest) -> BindingResult:
        capability_name = request.capability.description.lower()
        matches: List[ToolMatch] = []
        sole_candidate = len(request.candidate_tools) == 1
        preferred_tools = set(request.preferred_tools)

        for tool in request.candidate_tools:
            if tool.tool_id in request.forbidden_tools:
                continue

            score = 0.1
            reasons: List[str] = []
            if "retrieve" in capability_name or "search" in capability_name:
                if "search" in tool.tool_id:
                    score += 0.8
                    reasons.append("keyword_match:retrieve->search")
            if "write" in capability_name:
                if "write" in tool.tool_id:
                    score += 0.8
                    reasons.append("keyword_match:write->write")
            if tool.tool_id in preferred_tools:
                score += 0.2
                reasons.append("reusable_preference")
            if sole_candidate and score <= 0.15:
                score = 0.55
                reasons.append("sole_candidate_tool")

            if score > 0.15:
                matches.append(ToolMatch(tool_id=tool.tool_id, score=score, reasons=reasons))

        matches.sort(key=lambda m: m.score, reverse=True)
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
