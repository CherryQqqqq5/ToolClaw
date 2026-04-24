"""Rule-based capability graph construction from planner candidates and templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.planner.capability_intents import CAPABILITY_PROFILES_BY_ID, infer_capability_from_text, tokenize_values
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
                metadata=self._graph_metadata(benchmark_hints, diagnostics),
            ), diagnostics

        nodes = [
            self._node_from_candidate(c)
            for c in sorted(candidates, key=lambda x: x.score, reverse=True)
        ]
        nodes = self._expand_structural_nodes(task=task, nodes=nodes, benchmark_hints=benchmark_hints)
        nodes = self._prune_and_order_nodes(nodes, benchmark_hints=benchmark_hints, diagnostics=diagnostics)

        edges = self._dependency_edges(nodes)
        if not edges and len(nodes) > 1:
            edges = self._rebuild_edges(nodes)
        nodes = self._topologically_order_nodes(nodes, edges)
        return CapabilityGraph(
            capabilities=nodes,
            edges=edges,
            metadata=self._graph_metadata(benchmark_hints, diagnostics),
        ), diagnostics

    @staticmethod
    def _graph_metadata(benchmark_hints: Dict[str, Any], diagnostics: GraphBuildDiagnostics) -> Dict[str, Any]:
        return {
            "branch_options": list(benchmark_hints.get("branch_options", [])),
            "milestones": list(benchmark_hints.get("milestones", [])),
            "graph_diagnostics": {
                "selected_templates": list(diagnostics.selected_templates),
                "pruned_capabilities": list(diagnostics.pruned_capabilities),
                "unresolved_dependencies": list(diagnostics.unresolved_dependencies),
            },
        }

    @staticmethod
    def _node_key(node: CapabilityNode) -> str:
        return str(node.instance_id or node.capability_id)

    @classmethod
    def _node_from_profile(cls, capability_id: str, *, instance_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> CapabilityNode:
        profile = CAPABILITY_PROFILES_BY_ID[capability_id]
        node_metadata = dict(metadata or {})
        preconditions = node_metadata.pop("preconditions", None)
        return CapabilityNode(
            capability_id=profile.capability_id,
            description=profile.description,
            preconditions=list(preconditions) if isinstance(preconditions, list) else list(profile.preconditions),
            postconditions=list(profile.postconditions),
            instance_id=instance_id,
            metadata=node_metadata,
        )

    @classmethod
    def _node_from_candidate(cls, candidate: "CapabilityCandidate") -> CapabilityNode:
        return CapabilityNode(
            capability_id=candidate.capability_id,
            description=candidate.description,
            preconditions=list(candidate.preconditions),
            postconditions=list(candidate.postconditions),
            instance_id=str(candidate.metadata.get("instance_id")) if isinstance(candidate.metadata, dict) and candidate.metadata.get("instance_id") else None,
            metadata=dict(candidate.metadata or {}),
        )

    @classmethod
    def _expand_structural_nodes(
        cls,
        *,
        task: TaskSpec,
        nodes: Sequence[CapabilityNode],
        benchmark_hints: Dict[str, Any],
    ) -> List[CapabilityNode]:
        _ = benchmark_hints
        tokens = tokenize_values(task.user_goal)
        capability_ids = {node.capability_id for node in nodes}

        if {"primary", "secondary"}.issubset(tokens) and tokens.intersection({"merge", "combine", "aggregate", "synthesize"}):
            return [
                cls._node_from_profile(
                    "cap_retrieve",
                    instance_id="cap_retrieve.primary",
                    metadata={"instance_role": "primary", "structural_template": "multi_source_merge"},
                ),
                cls._node_from_profile(
                    "cap_retrieve",
                    instance_id="cap_retrieve.secondary",
                    metadata={"instance_role": "secondary", "structural_template": "multi_source_merge"},
                ),
                cls._node_from_profile("cap_merge", metadata={"structural_template": "multi_source_merge"}),
                cls._node_from_profile("cap_write", metadata={"structural_template": "multi_source_merge", "preconditions": ["merged_state_ready"]}),
            ]

        if {"cap_select", "cap_modify", "cap_verify"}.issubset(capability_ids) or (
            tokens.intersection({"branch", "select", "route", "choose"})
            and tokens.intersection({"execute", "modify", "update"})
            and tokens.intersection({"verify", "validate", "confirm", "test"})
        ):
            return [
                cls._node_from_profile("cap_retrieve", metadata={"structural_template": "branch_select_execute"}),
                cls._node_from_profile("cap_select", metadata={"structural_template": "branch_select_execute"}),
                cls._node_from_profile("cap_modify", metadata={"structural_template": "branch_select_execute", "preconditions": ["selected_branch_ready"]}),
                cls._node_from_profile("cap_verify", metadata={"structural_template": "branch_select_execute", "preconditions": ["branch_executed"]}),
            ]

        if {"cap_check", "cap_modify", "cap_verify"}.issubset(capability_ids) or (
            tokens.intersection({"check", "inspect", "audit", "status"})
            and tokens.intersection({"modify", "update", "patch", "change"})
            and tokens.intersection({"verify", "validate", "confirm", "test"})
        ):
            return [
                cls._node_from_profile("cap_check", metadata={"structural_template": "check_modify_verify"}),
                cls._node_from_profile("cap_modify", metadata={"structural_template": "check_modify_verify", "preconditions": ["state_checked"]}),
                cls._node_from_profile("cap_verify", metadata={"structural_template": "check_modify_verify", "preconditions": ["state_modified"]}),
            ]

        if {"cap_retrieve", "cap_summarize", "cap_write"}.issubset(capability_ids):
            return [
                cls._node_from_profile("cap_retrieve", metadata={"structural_template": "retrieve_summarize_write"}),
                cls._node_from_profile("cap_summarize", metadata={"structural_template": "retrieve_summarize_write"}),
                cls._node_from_profile("cap_write", metadata={"structural_template": "retrieve_summarize_write", "preconditions": ["summary_ready"]}),
            ]

        deduped: List[CapabilityNode] = []
        seen: set[str] = set()
        for node in nodes:
            key = cls._node_key(node)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(node)
        return deduped

    @classmethod
    def _dependency_edges(cls, nodes: Sequence[CapabilityNode]) -> List[CapabilityEdge]:
        edges: List[CapabilityEdge] = []
        for target in nodes:
            matched_dependency = False
            for source in nodes:
                if cls._node_key(source) == cls._node_key(target):
                    continue
                if any(postcondition in target.preconditions for postcondition in source.postconditions):
                    edges.append(
                        CapabilityEdge(
                            source=cls._node_key(source),
                            target=cls._node_key(target),
                            condition="preconditions_satisfied",
                        )
                    )
                    matched_dependency = True
            if not matched_dependency:
                continue
        return edges

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
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        categories = {str(item) for item in benchmark_hints.get("categories", []) if str(item)}
        allow_order = [] if "planner_sensitive" in categories else self._capability_order_from_texts(benchmark_hints.get("tool_allow_list", []))

        preferred_order = milestone_order or allow_order
        if allow_order and len(allow_order) > len(preferred_order):
            preferred_order = allow_order
        if preferred_order:
            preferred_ids = set(preferred_order)
            pruned = [self._node_key(node) for node in ordered_nodes if node.capability_id not in preferred_ids]
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
                key = self._node_key(node)
                if key not in diagnostics.pruned_capabilities:
                    diagnostics.pruned_capabilities.append(key)
            ordered_nodes = ordered_nodes[:ideal_tool_calls]

        return ordered_nodes

    @classmethod
    def _rebuild_edges(cls, nodes: Sequence[CapabilityNode]) -> List[CapabilityEdge]:
        if len(nodes) <= 1:
            return []
        return [
            CapabilityEdge(source=cls._node_key(nodes[index]), target=cls._node_key(nodes[index + 1]), condition="default_sequence")
            for index in range(len(nodes) - 1)
        ]

    @classmethod
    def _topologically_order_nodes(
        cls,
        nodes: Sequence[CapabilityNode],
        edges: Sequence[CapabilityEdge],
    ) -> List[CapabilityNode]:
        if len(nodes) <= 1 or not edges:
            return list(nodes)

        node_by_id = {cls._node_key(node): node for node in nodes}
        original_rank = {cls._node_key(node): index for index, node in enumerate(nodes)}
        indegree = {cls._node_key(node): 0 for node in nodes}
        adjacency: Dict[str, List[str]] = {cls._node_key(node): [] for node in nodes}
        for edge in edges:
            if edge.source not in node_by_id or edge.target not in node_by_id:
                continue
            adjacency[edge.source].append(edge.target)
            indegree[edge.target] += 1

        ready = sorted(
            [capability_key for capability_key, degree in indegree.items() if degree == 0],
            key=lambda capability_key: original_rank[capability_key],
        )
        ordered: List[CapabilityNode] = []
        while ready:
            capability_key = ready.pop(0)
            ordered.append(node_by_id[capability_key])
            for target in adjacency.get(capability_key, []):
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
