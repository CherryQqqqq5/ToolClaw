"""Rule-based capability graph construction from planner candidates and templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from toolclaw.schemas.workflow import CapabilityEdge, CapabilityGraph, CapabilityNode, TaskSpec


@dataclass
class CapabilityTemplate:
    template_id: str
    trigger_keywords: List[str]
    capability_chain: List[CapabilityNode]
    edges: List[CapabilityEdge]
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class GraphBuildDiagnostics:
    selected_templates: List[str] = field(default_factory=list)
    pruned_capabilities: List[str] = field(default_factory=list)
    unresolved_dependencies: List[str] = field(default_factory=list)


class CapabilityTemplateRegistry:
    def __init__(self) -> None:
        self._templates: Dict[str, CapabilityTemplate] = {}

    def register(self, template: CapabilityTemplate) -> None:
        self._templates[template.template_id] = template

    def match(self, task: TaskSpec) -> List[CapabilityTemplate]:
        goal = task.user_goal.lower()
        matches: List[CapabilityTemplate] = []
        for template in self._templates.values():
            if any(keyword.lower() in goal for keyword in template.trigger_keywords):
                matches.append(template)
        return matches


class RuleBasedCapabilityGraphBuilder:
    def __init__(self, registry: CapabilityTemplateRegistry) -> None:
        self.registry = registry

    def build(
        self,
        task: TaskSpec,
        candidates: Sequence["CapabilityCandidate"],
    ) -> tuple[CapabilityGraph, GraphBuildDiagnostics]:
        diagnostics = GraphBuildDiagnostics()
        templates = self.registry.match(task)

        if templates:
            diagnostics.selected_templates = [t.template_id for t in templates]
            chain: List[CapabilityNode] = []
            edges: List[CapabilityEdge] = []
            for template in templates:
                chain.extend(template.capability_chain)
                edges.extend(template.edges)
            return CapabilityGraph(capabilities=chain, edges=edges), diagnostics

        nodes = [
            CapabilityNode(
                capability_id=c.capability_id,
                description=c.description,
                preconditions=list(c.preconditions),
                postconditions=list(c.postconditions),
            )
            for c in sorted(candidates, key=lambda x: x.score, reverse=True)
        ]

        edges: List[CapabilityEdge] = []
        for target in nodes:
            matched_dependency = False
            for source in nodes:
                if source.capability_id == target.capability_id:
                    continue
                if any(postcondition in target.preconditions for postcondition in source.postconditions):
                    edges.append(
                        CapabilityEdge(
                            source=source.capability_id,
                            target=target.capability_id,
                            condition="preconditions_satisfied",
                        )
                    )
                    matched_dependency = True
            if not matched_dependency:
                continue
        if not edges and len(nodes) > 1:
            edges = [
                CapabilityEdge(source=nodes[i].capability_id, target=nodes[i + 1].capability_id, condition="default_sequence")
                for i in range(len(nodes) - 1)
            ]
        return CapabilityGraph(capabilities=nodes, edges=edges), diagnostics
