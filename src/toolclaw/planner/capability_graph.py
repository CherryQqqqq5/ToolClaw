"""Rule-based capability graph construction from planner candidates and templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.planner.capability_intents import infer_capability_from_text
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
        benchmark_hints: Optional[Dict[str, Any]] = None,
    ) -> tuple[CapabilityGraph, GraphBuildDiagnostics]:
        benchmark_hints = benchmark_hints or {}
        diagnostics = GraphBuildDiagnostics()
        templates = self.registry.match(task)

        if templates:
            diagnostics.selected_templates = [t.template_id for t in templates]
            chain: List[CapabilityNode] = []
            edges: List[CapabilityEdge] = []
            for template in templates:
                chain.extend(template.capability_chain)
                edges.extend(template.edges)
            chain = self._prune_and_order_nodes(chain, benchmark_hints=benchmark_hints, diagnostics=diagnostics)
            chain = self._topologically_order_nodes(chain, edges)
            return CapabilityGraph(
                capabilities=chain,
                edges=self._rebuild_edges(chain),
                metadata={
                    "branch_options": list(benchmark_hints.get("branch_options", [])),
                    "milestones": list(benchmark_hints.get("milestones", [])),
                },
            ), diagnostics

        nodes = [
            CapabilityNode(
                capability_id=c.capability_id,
                description=c.description,
                preconditions=list(c.preconditions),
                postconditions=list(c.postconditions),
            )
            for c in sorted(candidates, key=lambda x: x.score, reverse=True)
        ]
        nodes = self._prune_and_order_nodes(nodes, benchmark_hints=benchmark_hints, diagnostics=diagnostics)

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
            edges = self._rebuild_edges(nodes)
        nodes = self._topologically_order_nodes(nodes, edges)
        return CapabilityGraph(
            capabilities=nodes,
            edges=edges,
            metadata={
                "branch_options": list(benchmark_hints.get("branch_options", [])),
                "milestones": list(benchmark_hints.get("milestones", [])),
            },
        ), diagnostics

    def _prune_and_order_nodes(
        self,
        nodes: Sequence[CapabilityNode],
        *,
        benchmark_hints: Dict[str, Any],
        diagnostics: GraphBuildDiagnostics,
    ) -> List[CapabilityNode]:
        ordered_nodes = list(nodes)
        if len(ordered_nodes) <= 1:
            return ordered_nodes

        milestone_order = self._capability_order_from_texts(benchmark_hints.get("milestones", []))
        allow_order = self._capability_order_from_texts(benchmark_hints.get("tool_allow_list", []))
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        categories = {str(item) for item in benchmark_hints.get("categories", []) if str(item)}

        preferred_order = milestone_order or allow_order
        if preferred_order:
            preferred_ids = set(preferred_order)
            pruned = [node.capability_id for node in ordered_nodes if node.capability_id not in preferred_ids]
            filtered_nodes = [node for node in ordered_nodes if node.capability_id in preferred_ids]
            if filtered_nodes:
                diagnostics.pruned_capabilities.extend(
                    capability_id for capability_id in pruned if capability_id not in diagnostics.pruned_capabilities
                )
                rank = {capability_id: index for index, capability_id in enumerate(preferred_order)}
                filtered_nodes.sort(key=lambda node: (rank.get(node.capability_id, len(rank)), ordered_nodes.index(node)))
                ordered_nodes = filtered_nodes

        should_cap_by_budget = bool(preferred_order) and "multiple_user_turn" not in categories
        if should_cap_by_budget and isinstance(ideal_tool_calls, int) and ideal_tool_calls > 0 and len(ordered_nodes) > ideal_tool_calls:
            for node in ordered_nodes[ideal_tool_calls:]:
                if node.capability_id not in diagnostics.pruned_capabilities:
                    diagnostics.pruned_capabilities.append(node.capability_id)
            ordered_nodes = ordered_nodes[:ideal_tool_calls]

        return ordered_nodes

    @staticmethod
    def _rebuild_edges(nodes: Sequence[CapabilityNode]) -> List[CapabilityEdge]:
        if len(nodes) <= 1:
            return []
        return [
            CapabilityEdge(source=nodes[index].capability_id, target=nodes[index + 1].capability_id, condition="default_sequence")
            for index in range(len(nodes) - 1)
        ]

    @staticmethod
    def _topologically_order_nodes(
        nodes: Sequence[CapabilityNode],
        edges: Sequence[CapabilityEdge],
    ) -> List[CapabilityNode]:
        if len(nodes) <= 1 or not edges:
            return list(nodes)

        node_by_id = {node.capability_id: node for node in nodes}
        original_rank = {node.capability_id: index for index, node in enumerate(nodes)}
        indegree = {node.capability_id: 0 for node in nodes}
        adjacency: Dict[str, List[str]] = {node.capability_id: [] for node in nodes}
        for edge in edges:
            if edge.source not in node_by_id or edge.target not in node_by_id:
                continue
            adjacency[edge.source].append(edge.target)
            indegree[edge.target] += 1

        ready = sorted(
            [capability_id for capability_id, degree in indegree.items() if degree == 0],
            key=lambda capability_id: original_rank[capability_id],
        )
        ordered: List[CapabilityNode] = []
        while ready:
            capability_id = ready.pop(0)
            ordered.append(node_by_id[capability_id])
            for target in adjacency.get(capability_id, []):
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
                    ready.sort(key=lambda candidate_id: original_rank[candidate_id])

        if len(ordered) != len(nodes):
            return list(nodes)
        return ordered

    @classmethod
    def _capability_order_from_texts(cls, raw_values: Sequence[Any]) -> List[str]:
        ordered: List[str] = []
        for raw in raw_values:
            capability_id = cls._infer_capability_from_text(raw)
            if capability_id and capability_id not in ordered:
                ordered.append(capability_id)
        return ordered

    @staticmethod
    def _infer_capability_from_text(raw_value: Any) -> Optional[str]:
        return infer_capability_from_text(raw_value)
