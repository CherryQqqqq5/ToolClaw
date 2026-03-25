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
    ) -> List[BindingResult]:
        forbidden_tools = forbidden_tools or []
        return [
            self.bind_one(
                BindingRequest(
                    capability=cap,
                    candidate_tools=candidate_tools,
                    context=context,
                    forbidden_tools=forbidden_tools,
                )
            )
            for cap in capabilities
        ]
