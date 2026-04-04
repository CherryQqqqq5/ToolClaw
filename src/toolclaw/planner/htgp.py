"""Hierarchical Tool Graph Planner that builds workflows from capabilities before tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import RuleBasedCapabilityGraphBuilder
from toolclaw.schemas.error import ToolClawError
from toolclaw.schemas.workflow import (
    ActionType,
    ApprovalGate,
    CapabilityGraph,
    CapabilityNode,
    CheckpointPolicy,
    Phase,
    RollbackPolicy,
    TaskSpec,
    ToolBinding,
    ToolSpec,
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
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
    workflow_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


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

        for capability in graph.capabilities:
            if self._requires_approval(task=task, capability=capability, policy=policy) and "requires_approval" not in capability.preconditions:
                capability.preconditions.append("requires_approval")
        return graph

    @staticmethod
    def _requires_approval(
        task: TaskSpec,
        capability: CapabilityNode,
        policy: WorkflowPolicy,
    ) -> bool:
        for rule in policy.approval_rules:
            if rule.action != "ask_user":
                continue
            if PolicyInjector._trigger_matches(rule.trigger, task=task, capability=capability):
                return True
        return False

    @staticmethod
    def _trigger_matches(
        trigger: str,
        task: TaskSpec,
        capability: CapabilityNode,
    ) -> bool:
        normalized = trigger.strip().lower()
        if not normalized:
            return False
        if normalized in {"always", "*"}:
            return True
        if normalized == capability.capability_id.lower():
            return True
        if normalized in capability.description.lower():
            return True
        if "==" not in normalized:
            return False

        lhs, rhs = [part.strip() for part in normalized.split("==", 1)]
        rhs = rhs.strip("'\"")
        if lhs == "risk_level":
            return task.constraints.risk_level.value == rhs
        if lhs == "capability_id":
            return capability.capability_id.lower() == rhs
        if lhs == "requires_user_approval":
            expected = rhs in {"true", "1", "yes"}
            return bool(task.constraints.requires_user_approval) is expected
        return False

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
                    requires_user_confirmation=("requires_approval" in capability.preconditions),
                    metadata={
                        "policy_gate": "default_phase1",
                        "requires_approval": "requires_approval" in capability.preconditions,
                    },
                )
            )
        return steps

    def compile_workflow_graph(
        self,
        graph: CapabilityGraph,
        steps: List[WorkflowStep],
    ) -> WorkflowGraph:
        nodes: List[WorkflowNode] = []
        edges: List[WorkflowEdge] = []
        for idx, step in enumerate(steps):
            nodes.append(
                WorkflowNode(
                    node_id=step.step_id,
                    capability_id=step.capability_id,
                    selected_tool=step.tool_id,
                    tool_candidates=[step.tool_id] if step.tool_id else [],
                    inputs=dict(step.inputs),
                    expected_output=step.expected_output,
                    dependencies=[steps[idx - 1].step_id] if idx > 0 else [],
                    checkpoint_policy=CheckpointPolicy(enabled=step.checkpoint, reason="planner_injected"),
                    rollback_policy=RollbackPolicy(rollback_to_step_id=step.rollback_to),
                    approval_gate=ApprovalGate(required=step.requires_user_confirmation),
                    metadata=dict(step.metadata),
                )
            )
            if idx > 0:
                edges.append(WorkflowEdge(source=steps[idx - 1].step_id, target=step.step_id))
        return WorkflowGraph(
            nodes=nodes,
            edges=edges,
            entry_nodes=[steps[0].step_id] if steps else [],
            exit_nodes=[steps[-1].step_id] if steps else [],
            metadata={"capability_count": len(graph.capabilities)},
        )


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
        workflow_graph = self.policy_injector.compile_workflow_graph(graph, execution_plan)

        workflow = Workflow(
            workflow_id=f"wf_{request.task.task_id}",
            version="0.1",
            phase=Phase.PHASE1_TRAINING_FREE,
            task=request.task,
            context=request.context,
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            workflow_graph=workflow_graph,
            policy=request.policy or Workflow.demo().policy,
            metadata={"planner_mode": request.planner_mode},
        )
        self._apply_request_overrides(workflow, request.workflow_overrides)
        self._apply_reusable_hints(workflow, reusable_profile)

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
        if error.evidence.tool_id and error.evidence.tool_id not in replanning_hints.forbidden_tools:
            replanning_hints.forbidden_tools.append(error.evidence.tool_id)

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
        failed_index = 0
        for idx, step in enumerate(failed_workflow.execution_plan):
            if step.step_id == error.step_id:
                failed_index = idx
                break

        prefix = failed_workflow.execution_plan[:failed_index]
        replanned_suffix_source = result.workflow.execution_plan[failed_index:] or result.workflow.execution_plan
        replanned_suffix: List[WorkflowStep] = []
        for offset, step in enumerate(replanned_suffix_source, start=failed_index + 1):
            replanned_suffix.append(
                WorkflowStep(
                    step_id=f"step_{offset:02d}",
                    capability_id=step.capability_id,
                    tool_id=step.tool_id,
                    action_type=step.action_type,
                    inputs=dict(step.inputs),
                    expected_output=step.expected_output,
                    checkpoint=step.checkpoint,
                    rollback_to=step.rollback_to,
                    requires_user_confirmation=step.requires_user_confirmation,
                    metadata=dict(step.metadata),
                )
            )
        result.workflow.execution_plan = prefix + replanned_suffix
        result.workflow.workflow_graph = self.policy_injector.compile_workflow_graph(
            result.workflow.capability_graph,
            result.workflow.execution_plan,
        )
        result.workflow.metadata["replanned_from_workflow_id"] = failed_workflow.workflow_id
        result.workflow.metadata["replan_state_keys"] = list(state_values.keys())
        result.workflow.metadata["replanned_suffix_from_step_id"] = error.step_id
        if error.evidence.tool_id:
            result.diagnostics.rejected_tools[error.evidence.tool_id] = "failed_in_previous_run"
        return result

    @staticmethod
    def _apply_request_overrides(workflow: Workflow, overrides: Dict[str, Dict[str, Any]]) -> None:
        if not overrides:
            return

        step_overrides = overrides.get("steps", {})
        if not isinstance(step_overrides, dict):
            return

        graph_nodes = {node.node_id: node for node in workflow.workflow_graph.nodes}
        bindings_by_capability = {binding.capability_id: binding for binding in workflow.tool_bindings}
        for step in workflow.execution_plan:
            patch = step_overrides.get(step.step_id)
            if not isinstance(patch, dict):
                continue

            if "inputs" in patch and isinstance(patch["inputs"], dict):
                step.inputs = dict(patch["inputs"])
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.inputs = dict(step.inputs)

            if "tool_id" in patch:
                step.tool_id = patch["tool_id"]
                node = graph_nodes.get(step.step_id)
                if node is not None:
                    node.selected_tool = step.tool_id
                    node.tool_candidates = [step.tool_id] if step.tool_id else []
                binding = bindings_by_capability.get(step.capability_id)
                if binding is not None and step.tool_id:
                    binding.primary_tool = step.tool_id

    def _load_reusable_profile(self, request: PlanningRequest) -> Dict[str, Any]:
        profile: Dict[str, Any] = {"capability_order": [], "recommended_bindings": {}, "recommended_inputs": {}}
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
            recommended_inputs = getattr(asset, "recommended_inputs", None)
            if capability_skeleton:
                profile["capability_order"] = list(capability_skeleton)
            if recommended_bindings:
                profile["recommended_bindings"].update(dict(recommended_bindings))
            if recommended_inputs:
                profile["recommended_inputs"].update(
                    {
                        capability_id: dict(inputs)
                        for capability_id, inputs in dict(recommended_inputs).items()
                        if isinstance(inputs, dict)
                    }
                )
        return profile

    @staticmethod
    def _apply_reusable_hints(workflow: Workflow, reusable_profile: Dict[str, Any]) -> None:
        recommended_inputs = reusable_profile.get("recommended_inputs", {})
        if not isinstance(recommended_inputs, dict):
            return

        graph_nodes = {node.node_id: node for node in workflow.workflow_graph.nodes}
        for step in workflow.execution_plan:
            suggested_inputs = recommended_inputs.get(step.capability_id)
            if not isinstance(suggested_inputs, dict):
                continue
            for key, value in suggested_inputs.items():
                if key not in step.inputs:
                    step.inputs[key] = value
            node = graph_nodes.get(step.step_id)
            if node is not None:
                for key, value in suggested_inputs.items():
                    if key not in node.inputs:
                        node.inputs[key] = value


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
