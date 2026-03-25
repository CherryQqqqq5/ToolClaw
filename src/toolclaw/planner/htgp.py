from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.error import ToolClawError
from toolclaw.schemas.workflow import (
    ActionType,
    CapabilityGraph,
    CapabilityNode,
    Phase,
    TaskSpec,
    ToolBinding,
    ToolSpec,
    Workflow,
    WorkflowContext,
    WorkflowPolicy,
    WorkflowStep,
)

__all__ = [
    "PlanningHints",
    "PlanningRequest",
    "PlanningArtifact",
    "PlanningDiagnostics",
    "PlanningResult",
    "CapabilityCandidate",
    "CapabilitySelector",
    "RuleBasedCapabilitySelector",
    "CapabilityGraphBuilder",
    "PolicyInjector",
    "HTGPPlanner",
    "DefaultCapabilityGraphBuilder",
    "build_default_planner",
]


@dataclass
class PlanningHints:
    preferred_capabilities: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    reusable_asset_ids: List[str] = field(default_factory=list)
    prior_failures: List[str] = field(default_factory=list)
    user_style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningRequest:
    task: TaskSpec
    context: WorkflowContext
    policy: Optional[WorkflowPolicy] = None
    hints: PlanningHints = field(default_factory=PlanningHints)
    planner_mode: str = "phase1_rule_based"


@dataclass
class PlanningArtifact:
    capability_graph: CapabilityGraph
    tool_bindings: List[ToolBinding]
    execution_plan: List[WorkflowStep]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningDiagnostics:
    unresolved_capabilities: List[str] = field(default_factory=list)
    rejected_tools: Dict[str, str] = field(default_factory=dict)
    binding_scores: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PlanningResult:
    workflow: Workflow
    artifact: PlanningArtifact
    diagnostics: PlanningDiagnostics = field(default_factory=PlanningDiagnostics)


@dataclass
class CapabilityCandidate:
    capability_id: str
    description: str
    score: float
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilitySelector:
    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        raise NotImplementedError


class RuleBasedCapabilitySelector(CapabilitySelector):
    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        _ = context
        goal = task.user_goal.lower()
        candidates: List[CapabilityCandidate] = []
        if any(word in goal for word in ["search", "retrieve", "find", "collect"]):
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_retrieve",
                    description="Retrieve relevant information",
                    score=0.9,
                    postconditions=["information_obtained"],
                )
            )
        if any(word in goal for word in ["summarize", "analyze"]):
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_summarize",
                    description="Summarize retrieved information",
                    score=0.82,
                    preconditions=["information_obtained"],
                    postconditions=["summary_ready"],
                )
            )
        if any(word in goal for word in ["write", "report", "save", "output"]):
            preconditions = ["summary_ready"] if any(c.capability_id == "cap_summarize" for c in candidates) else ["information_obtained"]
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_write",
                    description="Write final report artifact",
                    score=0.85,
                    preconditions=preconditions,
                    postconditions=["artifact_ready"],
                )
            )
        if not candidates:
            candidates = [
                CapabilityCandidate(
                    capability_id="cap_retrieve",
                    description="Retrieve relevant information",
                    score=0.6,
                    postconditions=["information_obtained"],
                ),
                CapabilityCandidate(
                    capability_id="cap_write",
                    description="Write final report artifact",
                    score=0.6,
                    preconditions=["information_obtained"],
                    postconditions=["artifact_ready"],
                ),
            ]
        preferred = set(hints.preferred_capabilities)
        for candidate in candidates:
            if candidate.capability_id in preferred:
                candidate.score += 0.1
        return candidates


class CapabilityGraphBuilder:
    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
    ) -> CapabilityGraph:
        raise NotImplementedError


class PolicyInjector:
    def inject(
        self,
        graph: CapabilityGraph,
        task: TaskSpec,
        context: WorkflowContext,
        policy: Optional[WorkflowPolicy],
    ) -> CapabilityGraph:
        _ = task, context
        if not policy:
            return graph

        gated_capabilities = {rule.trigger for rule in policy.approval_rules if rule.action == "ask_user"}
        for capability in graph.capabilities:
            if capability.capability_id in gated_capabilities and "requires_approval" not in capability.preconditions:
                capability.preconditions.append("requires_approval")
        return graph

    def compile_execution_plan(
        self,
        graph: CapabilityGraph,
        bindings: List[ToolBinding],
        task: TaskSpec,
    ) -> List[WorkflowStep]:
        binding_by_cap = {binding.capability_id: binding for binding in bindings}
        steps: List[WorkflowStep] = []
        for idx, capability in enumerate(graph.capabilities, start=1):
            binding = binding_by_cap.get(capability.capability_id)
            tool_id = binding.primary_tool if binding else None
            if capability.capability_id == "cap_retrieve":
                inputs = {"query": task.user_goal}
                expected_output = "retrieved_info"
            elif capability.capability_id == "cap_summarize":
                inputs = {"source_key": "retrieved_info"}
                expected_output = "summary_text"
            elif capability.capability_id == "cap_write":
                inputs = {"target_path": "outputs/reports/planned_report.txt"}
                expected_output = "report_artifact"
            else:
                inputs = {}
                expected_output = None

            steps.append(
                WorkflowStep(
                    step_id=f"step_{idx:02d}",
                    capability_id=capability.capability_id,
                    tool_id=tool_id,
                    action_type=ActionType.TOOL_CALL,
                    inputs=inputs,
                    expected_output=expected_output,
                    checkpoint=True,
                    metadata={"policy_gate": "default_phase1"},
                )
            )
        return steps


class HTGPPlanner:
    def __init__(
        self,
        capability_selector: CapabilitySelector,
        graph_builder: CapabilityGraphBuilder,
        binder: ToolBinder,
        policy_injector: PolicyInjector,
        asset_registry: Optional["AssetRegistry"] = None,
    ) -> None:
        self.capability_selector = capability_selector
        self.graph_builder = graph_builder
        self.binder = binder
        self.policy_injector = policy_injector
        self.asset_registry = asset_registry

    def plan(self, request: PlanningRequest) -> PlanningResult:
        diagnostics = PlanningDiagnostics()
        reusable_profile = self._load_reusable_profile(request)
        candidates = self.capability_selector.select(request.task, request.context, request.hints)
        if reusable_profile["capability_order"]:
            order = reusable_profile["capability_order"]
            rank = {cap_id: idx for idx, cap_id in enumerate(order)}
            candidates.sort(key=lambda c: rank.get(c.capability_id, len(rank)))
        built_graph = self.graph_builder.build(request.task, candidates)
        graph = built_graph[0] if isinstance(built_graph, tuple) else built_graph
        graph = self.policy_injector.inject(graph, request.task, request.context, request.policy)

        binding_results = self.binder.bind_graph(
            capabilities=graph.capabilities,
            candidate_tools=request.context.candidate_tools,
            context=request.context,
            forbidden_tools=request.hints.forbidden_tools,
        )

        bindings: List[ToolBinding] = []
        for capability, binding_result in zip(graph.capabilities, binding_results):
            if binding_result.binding is None:
                diagnostics.unresolved_capabilities.append(capability.capability_id)
                diagnostics.warnings.append(f"unresolved capability: {capability.capability_id}")
                continue

            bindings.append(binding_result.binding)
            recommended_tool = reusable_profile["recommended_bindings"].get(capability.capability_id)
            if recommended_tool:
                binding_result.binding.primary_tool = recommended_tool
            diagnostics.binding_scores[capability.capability_id] = binding_result.binding.binding_confidence

        execution_plan = self.policy_injector.compile_execution_plan(graph, bindings, request.task)

        workflow = Workflow(
            workflow_id=f"wf_{request.task.task_id}",
            version="0.1",
            phase=Phase.PHASE1_TRAINING_FREE,
            task=request.task,
            context=request.context,
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            policy=request.policy or Workflow.demo().policy,
            metadata={"planner_mode": request.planner_mode},
        )

        artifact = PlanningArtifact(
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            metadata={"candidate_count": len(candidates)},
        )
        return PlanningResult(workflow=workflow, artifact=artifact, diagnostics=diagnostics)

    def replan_from_error(
        self,
        request: PlanningRequest,
        failed_workflow: Workflow,
        error: ToolClawError,
        state_values: Dict[str, Any],
    ) -> PlanningResult:
        replanning_hints = PlanningHints(
            preferred_capabilities=list(request.hints.preferred_capabilities),
            forbidden_tools=list(request.hints.forbidden_tools),
            reusable_asset_ids=list(request.hints.reusable_asset_ids),
            prior_failures=list(request.hints.prior_failures) + [error.category.value],
            user_style=dict(request.hints.user_style),
        )

        # simple phase-1 strategy: preserve task/context/policy and re-run planning.
        result = self.plan(
            PlanningRequest(
                task=request.task,
                context=request.context,
                policy=request.policy,
                hints=replanning_hints,
                planner_mode=request.planner_mode,
            )
        )
        result.workflow.metadata["replanned_from_workflow_id"] = failed_workflow.workflow_id
        result.workflow.metadata["replan_state_keys"] = list(state_values.keys())
        if error.evidence.tool_id:
            result.diagnostics.rejected_tools[error.evidence.tool_id] = "failed_in_previous_run"
        return result

    def _load_reusable_profile(self, request: PlanningRequest) -> Dict[str, Any]:
        profile: Dict[str, Any] = {"capability_order": [], "recommended_bindings": {}}
        if not self.asset_registry:
            return profile

        asset_ids = list(request.hints.reusable_asset_ids)
        if not asset_ids and self.asset_registry:
            signature = f"phase1::{request.task.user_goal.lower().strip().replace(' ', '_')}"
            matches = self.asset_registry.query(signature, top_k=5)
            asset_ids = [m.asset_id for m in matches]

        for asset_id in asset_ids:
            asset = self.asset_registry.get(asset_id)
            if asset is None:
                continue
            capability_skeleton = getattr(asset, "capability_skeleton", None)
            recommended_bindings = getattr(asset, "recommended_bindings", None)
            if capability_skeleton:
                profile["capability_order"] = list(capability_skeleton)
            if recommended_bindings:
                profile["recommended_bindings"].update(dict(recommended_bindings))
        return profile


class DefaultCapabilityGraphBuilder(CapabilityGraphBuilder):
    def __init__(self, delegate: RuleBasedCapabilityGraphBuilder) -> None:
        self.delegate = delegate

    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
    ) -> CapabilityGraph:
        graph, _ = self.delegate.build(task=task, candidates=candidates)
        return graph


def build_default_planner(asset_registry: Optional["AssetRegistry"] = None) -> HTGPPlanner:
    from toolclaw.planner.capability_graph import CapabilityTemplateRegistry

    selector = RuleBasedCapabilitySelector()
    graph_builder = DefaultCapabilityGraphBuilder(
        RuleBasedCapabilityGraphBuilder(registry=CapabilityTemplateRegistry())
    )
    binder = ToolBinder()
    policy_injector = PolicyInjector()
    return HTGPPlanner(
        capability_selector=selector,
        graph_builder=graph_builder,
        binder=binder,
        policy_injector=policy_injector,
        asset_registry=asset_registry,
    )


from toolclaw.registry import AssetRegistry  # noqa: E402
