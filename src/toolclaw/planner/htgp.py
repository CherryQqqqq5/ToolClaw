"""Hierarchical Tool Graph Planner that builds workflows from capabilities before tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from toolclaw.compiler.swpc import build_task_signature_candidates
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
    benchmark_hints_used: List[str] = field(default_factory=list)
    overplanning_risk: Dict[str, Any] = field(default_factory=dict)


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
        benchmark_hints = self._benchmark_hints(context=context, hints=hints)
        goal = task.user_goal.lower()
        candidates: List[CapabilityCandidate] = []
        minimal_capability = self._minimal_capability_hint(goal=goal, benchmark_hints=benchmark_hints)
        if minimal_capability is not None:
            return [minimal_capability]
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
            if candidate.capability_id in benchmark_hints["preferred_capabilities"]:
                candidate.score += 0.08
        return candidates

    @staticmethod
    def _benchmark_hints(context: WorkflowContext, hints: PlanningHints) -> Dict[str, Any]:
        user_style = dict(hints.user_style)
        categories = [str(item) for item in user_style.get("categories", []) if str(item)]
        tool_allow_list = [str(item) for item in user_style.get("tool_allow_list", []) if str(item)]
        if not tool_allow_list:
            tool_allow_list = [tool.tool_id for tool in context.candidate_tools]
        ideal_tool_calls = HTGPPlanner._coerce_int(user_style.get("ideal_tool_calls"))
        preferred_capabilities = []
        if any(category in {"single_tool", "state_dependency"} for category in categories):
            preferred_capabilities.append("cap_write")
        if any(category in {"multiple_tool", "canonicalization"} for category in categories):
            preferred_capabilities.append("cap_retrieve")
        return {
            "categories": categories,
            "tool_allow_list": tool_allow_list,
            "ideal_tool_calls": ideal_tool_calls,
            "preferred_capabilities": preferred_capabilities,
        }

    @staticmethod
    def _minimal_capability_hint(goal: str, benchmark_hints: Dict[str, Any]) -> Optional[CapabilityCandidate]:
        categories = set(benchmark_hints.get("categories", []))
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        tool_allow_list = benchmark_hints.get("tool_allow_list", [])
        should_minimize = (
            "multiple_user_turn" not in categories
            and (
                ideal_tool_calls == 1
                or len(tool_allow_list) == 1
                or "single_tool" in categories
            )
        )
        if not should_minimize:
            return None
        capability_id = "cap_write" if any(token in goal for token in ["write", "save", "send", "report", "set"]) else "cap_retrieve"
        description = "Complete the single-step tool action" if capability_id == "cap_write" else "Retrieve the required result"
        postconditions = ["artifact_ready"] if capability_id == "cap_write" else ["information_obtained"]
        return CapabilityCandidate(
            capability_id=capability_id,
            description=description,
            score=0.95,
            postconditions=postconditions,
            metadata={"selected_from_benchmark_hints": True},
        )


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
        benchmark_hints: Optional[Dict[str, Any]] = None,
    ) -> List[WorkflowStep]:
        benchmark_hints = benchmark_hints or {}
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
                if benchmark_hints.get("ideal_tool_calls") == 1:
                    inputs["query"] = task.user_goal
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
                        "benchmark_hint_step": bool(benchmark_hints),
                    },
                )
            )
        return steps

    def compile_workflow_graph(
        self,
        graph: CapabilityGraph,
        steps: List[WorkflowStep],
        bindings: Optional[List[ToolBinding]] = None,
    ) -> WorkflowGraph:
        nodes: List[WorkflowNode] = []
        edges: List[WorkflowEdge] = []
        binding_by_capability = {binding.capability_id: binding for binding in (bindings or [])}
        for idx, step in enumerate(steps):
            binding = binding_by_capability.get(step.capability_id)
            nodes.append(
                WorkflowNode(
                    node_id=step.step_id,
                    capability_id=step.capability_id,
                    selected_tool=step.tool_id,
                    tool_candidates=([step.tool_id] if step.tool_id else []) + (list(binding.backup_tools) if binding else []),
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
                edges.append(WorkflowEdge(source=steps[idx - 1].step_id, target=step.step_id, condition="on_success"))
            if binding and binding.backup_tools:
                edges.append(WorkflowEdge(source=step.step_id, target=step.step_id, condition="on_tool_failure_use_backup"))
            if step.requires_user_confirmation:
                edges.append(WorkflowEdge(source=step.step_id, target=step.step_id, condition="on_approval_resume"))
        return WorkflowGraph(
            nodes=nodes,
            edges=edges,
            entry_nodes=[steps[0].step_id] if steps else [],
            exit_nodes=[steps[-1].step_id] if steps else [],
            metadata={"capability_count": len(graph.capabilities), "has_conditional_edges": any(edge.condition for edge in edges)},
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
        benchmark_hints = self._benchmark_hints(request)
        diagnostics.benchmark_hints_used = sorted(benchmark_hints["used_keys"])
        candidates = self.capability_selector.select(request.task, request.context, request.hints)
        bypass_applied = self._should_bypass(request, benchmark_hints)
        if bypass_applied and candidates:
            diagnostics.warnings.append("planner_bypass_applied:minimal_path")
            minimal_candidate = candidates[0]
            graph = CapabilityGraph(
                capabilities=[
                    CapabilityNode(
                        capability_id=minimal_candidate.capability_id,
                        description=minimal_candidate.description,
                        preconditions=list(minimal_candidate.preconditions),
                        postconditions=list(minimal_candidate.postconditions),
                    )
                ],
                edges=[],
            )
        else:
            built_graph = self.graph_builder.build(request.task, candidates)
            graph = built_graph[0] if isinstance(built_graph, tuple) else built_graph
        reusable_profile = self._load_reusable_profile(request, graph)
        if reusable_profile["capability_order"]:
            order = reusable_profile["capability_order"]
            rank = {cap_id: idx for idx, cap_id in enumerate(order)}
            graph.capabilities.sort(key=lambda capability: rank.get(capability.capability_id, len(rank)))
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

        execution_plan = self.policy_injector.compile_execution_plan(graph, bindings, request.task, benchmark_hints=benchmark_hints)
        workflow_graph = self.policy_injector.compile_workflow_graph(graph, execution_plan, bindings=bindings)
        diagnostics.overplanning_risk = self._overplanning_risk(
            request=request,
            execution_plan=execution_plan,
            bindings=bindings,
            bypass_applied=bypass_applied,
            benchmark_hints=benchmark_hints,
        )
        if diagnostics.overplanning_risk.get("expanded_single_tool_task"):
            diagnostics.warnings.append("overplanning_risk:single_tool_expanded")
        if diagnostics.overplanning_risk.get("steps_exceed_ideal"):
            diagnostics.warnings.append("overplanning_risk:steps_exceed_ideal_tool_calls")
        if diagnostics.overplanning_risk.get("used_disallowed_tool"):
            diagnostics.warnings.append("overplanning_risk:used_tool_outside_allow_list")

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
            metadata={
                "planner_mode": request.planner_mode,
                "task_family": str(request.hints.user_style.get("task_family", "t0_general")),
                "failure_type": str(request.hints.user_style.get("failure_type", "none")),
                "scenario": str(request.hints.user_style.get("scenario", "success")),
            },
        )
        self._apply_request_overrides(workflow, request.workflow_overrides)
        self._apply_reusable_hints(workflow, reusable_profile)

        artifact = PlanningArtifact(
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            metadata={"candidate_count": len(candidates), "bypass_applied": bypass_applied, "benchmark_hints_used": diagnostics.benchmark_hints_used},
        )
        return PlanningResult(workflow=workflow, artifact=artifact, diagnostics=diagnostics)

    @staticmethod
    def _benchmark_hints(request: PlanningRequest) -> Dict[str, Any]:
        user_style = dict(request.hints.user_style)
        categories = [str(item) for item in user_style.get("categories", []) if str(item)]
        tool_allow_list = [str(item) for item in user_style.get("tool_allow_list", []) if str(item)]
        milestones = [str(item) for item in user_style.get("milestones", []) if str(item)]
        ideal_tool_calls = HTGPPlanner._coerce_int(user_style.get("ideal_tool_calls"))
        ideal_turn_count = HTGPPlanner._coerce_int(user_style.get("ideal_turn_count"))
        used_keys = [
            key
            for key in ("categories", "tool_allow_list", "ideal_tool_calls", "ideal_turn_count", "milestones")
            if user_style.get(key)
        ]
        return {
            "categories": categories,
            "tool_allow_list": tool_allow_list,
            "ideal_tool_calls": ideal_tool_calls,
            "ideal_turn_count": ideal_turn_count,
            "milestones": milestones,
            "used_keys": used_keys,
        }

    @staticmethod
    def _should_bypass(request: PlanningRequest, benchmark_hints: Dict[str, Any]) -> bool:
        categories = set(benchmark_hints.get("categories", []))
        tool_allow_list = benchmark_hints.get("tool_allow_list", [])
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        return bool(
            "multiple_user_turn" not in categories
            and (
                ideal_tool_calls == 1
                or len(tool_allow_list) == 1
                or "single_tool" in categories
            )
        )

    @staticmethod
    def _overplanning_risk(
        *,
        request: PlanningRequest,
        execution_plan: List[WorkflowStep],
        bindings: List[ToolBinding],
        bypass_applied: bool,
        benchmark_hints: Dict[str, Any],
    ) -> Dict[str, Any]:
        categories = set(benchmark_hints.get("categories", []))
        tool_allow_list = set(benchmark_hints.get("tool_allow_list", []))
        ideal_tool_calls = benchmark_hints.get("ideal_tool_calls")
        planned_tools = [step.tool_id for step in execution_plan if step.tool_id]
        return {
            "bypass_applied": bypass_applied,
            "single_tool_task": len(tool_allow_list) == 1 or "single_tool" in categories,
            "planned_steps": len(execution_plan),
            "ideal_tool_calls": ideal_tool_calls,
            "expanded_single_tool_task": (len(tool_allow_list) == 1 or "single_tool" in categories) and len(execution_plan) > 1,
            "steps_exceed_ideal": isinstance(ideal_tool_calls, int) and len(execution_plan) > ideal_tool_calls,
            "used_disallowed_tool": bool(tool_allow_list) and any(tool_id not in tool_allow_list for tool_id in planned_tools),
            "bound_capabilities": [binding.capability_id for binding in bindings],
        }

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

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

    def _load_reusable_profile(self, request: PlanningRequest, graph: Optional[CapabilityGraph] = None) -> Dict[str, Any]:
        profile: Dict[str, Any] = {"capability_order": [], "recommended_bindings": {}, "recommended_inputs": {}}
        if not self.asset_registry:
            return profile

        asset_ids = list(request.hints.reusable_asset_ids)
        if not asset_ids and self.asset_registry:
            capability_skeleton = [capability.capability_id for capability in graph.capabilities] if graph else []
            signatures = build_task_signature_candidates(
                user_goal=request.task.user_goal,
                task_family=request.hints.user_style.get("task_family"),
                capability_skeleton=capability_skeleton,
                failure_context=request.hints.user_style.get("failure_type"),
            )
            matches = []
            for signature in signatures:
                matches.extend(self.asset_registry.query(signature, top_k=5))
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
