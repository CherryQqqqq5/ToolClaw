from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple
import uuid

from toolclaw.schemas.workflow import (
    ActionType,
    CapabilityEdge,
    CapabilityGraph,
    CapabilityNode,
    Phase,
    PolicyRule,
    ReusableTargets,
    TaskSpec,
    ToolBinding,
    ToolSpec,
    Workflow,
    WorkflowContext,
    WorkflowPolicy,
    WorkflowStep,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class PlanningHints:
    preferred_capabilities: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    reusable_asset_ids: List[str] = field(default_factory=list)
    prior_failures: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningRequest:
    task: TaskSpec
    context: WorkflowContext
    policy: Optional[WorkflowPolicy] = None
    hints: PlanningHints = field(default_factory=PlanningHints)
    workflow_id: Optional[str] = None
    version: str = "0.1"


@dataclass
class CapabilityCandidate:
    capability_id: str
    description: str
    score: float
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningDiagnostics:
    selected_capabilities: List[str] = field(default_factory=list)
    unresolved_capabilities: List[str] = field(default_factory=list)
    rejected_tools: Dict[str, str] = field(default_factory=dict)
    binding_scores: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PlanningResult:
    workflow: Workflow
    diagnostics: PlanningDiagnostics = field(default_factory=PlanningDiagnostics)


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
    forbidden_tools: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BindingResult:
    binding: Optional[ToolBinding]
    alternatives: List[ToolMatch] = field(default_factory=list)
    unresolved_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssetRegistry(Protocol):
    def query(self, task_signature: str, top_k: int = 5) -> List[Dict[str, Any]]:
        ...


class CapabilitySelector(Protocol):
    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        ...


class CapabilityGraphBuilder(Protocol):
    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
    ) -> CapabilityGraph:
        ...


class ToolBinder(Protocol):
    def bind_one(self, request: BindingRequest) -> BindingResult:
        ...


class PolicyInjector(Protocol):
    def inject(
        self,
        graph: CapabilityGraph,
        task: TaskSpec,
        context: WorkflowContext,
        policy: Optional[WorkflowPolicy],
    ) -> WorkflowPolicy:
        ...

    def compile_execution_plan(
        self,
        graph: CapabilityGraph,
        bindings: List[ToolBinding],
        task: TaskSpec,
    ) -> List[WorkflowStep]:
        ...


class KeywordCapabilitySelector:
    """
    Phase-1 最小版能力选择器：
    根据 task.user_goal 的关键词产生 capability candidates。
    """

    def select(
        self,
        task: TaskSpec,
        context: WorkflowContext,
        hints: PlanningHints,
    ) -> List[CapabilityCandidate]:
        goal = task.user_goal.lower()
        candidates: List[CapabilityCandidate] = []

        # 通用 retrieve
        if any(k in goal for k in ["find", "search", "retrieve", "look up", "read", "summar"]):
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_retrieve",
                    description="Retrieve relevant information",
                    score=0.90,
                    postconditions=["information_obtained"],
                )
            )

        # 通用 write
        if any(k in goal for k in ["write", "draft", "report", "save", "export", "generate"]):
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_write",
                    description="Write or generate an output artifact",
                    score=0.88,
                    preconditions=["information_obtained"],
                    postconditions=["artifact_ready"],
                )
            )

        # 分析
        if any(k in goal for k in ["analyze", "compare", "evaluate", "assess"]):
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_analyze",
                    description="Analyze retrieved information",
                    score=0.86,
                    preconditions=["information_obtained"],
                    postconditions=["analysis_ready"],
                )
            )

        # 用户交互
        if task.constraints.requires_user_approval:
            candidates.append(
                CapabilityCandidate(
                    capability_id="cap_approval",
                    description="Request user approval before high-risk action",
                    score=0.95,
                    postconditions=["approval_recorded"],
                )
            )

        # fallback: 至少给一个 retrieve/write 风格链路
        if not candidates:
            candidates = [
                CapabilityCandidate(
                    capability_id="cap_retrieve",
                    description="Retrieve relevant information",
                    score=0.60,
                    postconditions=["information_obtained"],
                ),
                CapabilityCandidate(
                    capability_id="cap_write",
                    description="Write final output",
                    score=0.60,
                    preconditions=["information_obtained"],
                    postconditions=["artifact_ready"],
                ),
            ]

        # hints 加权
        preferred = set(hints.preferred_capabilities)
        for c in candidates:
            if c.capability_id in preferred:
                c.score += 0.10

        # 去重
        dedup: Dict[str, CapabilityCandidate] = {}
        for c in candidates:
            if c.capability_id not in dedup or c.score > dedup[c.capability_id].score:
                dedup[c.capability_id] = c
        return list(dedup.values())


class RuleBasedCapabilityGraphBuilder:
    """
    把 capability candidates 排成最小 DAG。
    """

    def build(
        self,
        task: TaskSpec,
        candidates: Sequence[CapabilityCandidate],
    ) -> CapabilityGraph:
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
        node_ids = [n.capability_id for n in nodes]

        def has_cap(cap_id: str) -> bool:
            return cap_id in node_ids

        if has_cap("cap_retrieve") and has_cap("cap_analyze"):
            edges.append(
                CapabilityEdge(
                    source="cap_retrieve",
                    target="cap_analyze",
                    condition="information_obtained == true",
                )
            )

        if has_cap("cap_analyze") and has_cap("cap_write"):
            edges.append(
                CapabilityEdge(
                    source="cap_analyze",
                    target="cap_write",
                    condition="analysis_ready == true",
                )
            )
        elif has_cap("cap_retrieve") and has_cap("cap_write"):
            edges.append(
                CapabilityEdge(
                    source="cap_retrieve",
                    target="cap_write",
                    condition="information_obtained == true",
                )
            )

        if has_cap("cap_approval"):
            # 最简单策略：approval 放在 write 前
            if has_cap("cap_write"):
                edges.append(
                    CapabilityEdge(
                        source="cap_approval",
                        target="cap_write",
                        condition="approval_recorded == true",
                    )
                )

        return CapabilityGraph(capabilities=nodes, edges=edges)


class HeuristicToolBinder:
    """
    通过 tool description 和 capability description 的词匹配做最小 binding。
    """

    def bind_one(self, request: BindingRequest) -> BindingResult:
        cap = request.capability
        cap_text = f"{cap.capability_id} {cap.description}".lower()

        scored: List[ToolMatch] = []
        for tool in request.candidate_tools:
            if tool.tool_id in request.forbidden_tools:
                continue
            tool_text = f"{tool.tool_id} {tool.description}".lower()
            score = self._score(cap_text, tool_text)
            reasons = []
            if "retrieve" in cap_text or "search" in cap_text:
                if any(k in tool_text for k in ["search", "retrieve", "read", "fetch"]):
                    score += 0.30
                    reasons.append("retrieve-like lexical match")
            if "write" in cap_text or "report" in cap_text or "generate" in cap_text:
                if any(k in tool_text for k in ["write", "save", "export", "generate"]):
                    score += 0.30
                    reasons.append("write-like lexical match")
            if "analyze" in cap_text or "compare" in cap_text:
                if any(k in tool_text for k in ["analyze", "compare", "evaluate", "summarize"]):
                    score += 0.30
                    reasons.append("analysis-like lexical match")

            scored.append(
                ToolMatch(
                    tool_id=tool.tool_id,
                    score=round(score, 4),
                    reasons=reasons,
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)

        if not scored or scored[0].score < 0.20:
            return BindingResult(
                binding=None,
                alternatives=scored[:3],
                unresolved_reason=f"No reliable tool match for capability={cap.capability_id}",
            )

        primary = scored[0]
        backups = [m.tool_id for m in scored[1:3]]

        return BindingResult(
            binding=ToolBinding(
                capability_id=cap.capability_id,
                primary_tool=primary.tool_id,
                backup_tools=backups,
                binding_confidence=min(primary.score, 1.0),
            ),
            alternatives=scored[:3],
        )

    @staticmethod
    def _score(cap_text: str, tool_text: str) -> float:
        cap_tokens = set(cap_text.replace("_", " ").split())
        tool_tokens = set(tool_text.replace("_", " ").split())
        if not cap_tokens or not tool_tokens:
            return 0.0
        overlap = cap_tokens.intersection(tool_tokens)
        return len(overlap) / max(len(cap_tokens), 1)


class DefaultPolicyInjector:
    def inject(
        self,
        graph: CapabilityGraph,
        task: TaskSpec,
        context: WorkflowContext,
        policy: Optional[WorkflowPolicy],
    ) -> WorkflowPolicy:
        if policy is not None:
            return policy

        approval_rules = []
        if task.constraints.requires_user_approval:
            approval_rules.append(
                PolicyRule(
                    rule_id="apr_auto_01",
                    trigger="requires_user_approval == true",
                    action="ask_user",
                )
            )

        recovery_rules = [
            PolicyRule(
                rule_id="rec_auto_switch_tool",
                trigger="tool_unavailable",
                action="switch_backup_tool",
            ),
            PolicyRule(
                rule_id="rec_auto_rebind_args",
                trigger="binding_failure",
                action="rebind_args",
            ),
        ]

        stop_rules = [
            "success_criteria_satisfied",
            "hard_constraint_violated",
            "user_abort",
        ]
        return WorkflowPolicy(
            approval_rules=approval_rules,
            recovery_rules=recovery_rules,
            stop_rules=stop_rules,
        )

    def compile_execution_plan(
        self,
        graph: CapabilityGraph,
        bindings: List[ToolBinding],
        task: TaskSpec,
    ) -> List[WorkflowStep]:
        binding_map = {b.capability_id: b for b in bindings}

        # 简单拓扑顺序：先选入度小的；Phase-1 足够
        indegree: Dict[str, int] = {n.capability_id: 0 for n in graph.capabilities}
        outgoing: Dict[str, List[str]] = {n.capability_id: [] for n in graph.capabilities}
        for e in graph.edges:
            indegree[e.target] = indegree.get(e.target, 0) + 1
            outgoing.setdefault(e.source, []).append(e.target)

        queue = [cid for cid, deg in indegree.items() if deg == 0]
        ordered: List[str] = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for nxt in outgoing.get(current, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        # fallback
        if len(ordered) != len(graph.capabilities):
            ordered = [n.capability_id for n in graph.capabilities]

        steps: List[WorkflowStep] = []
        for idx, cap_id in enumerate(ordered, start=1):
            binding = binding_map.get(cap_id)
            step = WorkflowStep(
                step_id=f"step_{idx:02d}",
                capability_id=cap_id,
                tool_id=binding.primary_tool if binding else None,
                action_type=ActionType.TOOL_CALL if binding else ActionType.USER_QUERY,
                inputs={},
                expected_output=f"{cap_id}_output",
                checkpoint=True,
                rollback_to=f"step_{idx-1:02d}" if idx > 1 else None,
                requires_user_confirmation=(cap_id == "cap_approval"),
                metadata={"generated_by": "htgp_phase1"},
            )

            if cap_id == "cap_retrieve":
                step.inputs = {"query": task.user_goal}
            elif cap_id == "cap_analyze":
                step.inputs = {"source": "state://retrieved_info"}
            elif cap_id == "cap_write":
                step.inputs = {"target_path": "outputs/generated_artifact.txt"}
            elif cap_id == "cap_approval":
                step.action_type = ActionType.USER_QUERY
                step.inputs = {"question": f"Approve task: {task.user_goal}"}

            steps.append(step)

        return steps


class HTGPPlanner:
    def __init__(
        self,
        capability_selector: Optional[CapabilitySelector] = None,
        graph_builder: Optional[CapabilityGraphBuilder] = None,
        binder: Optional[ToolBinder] = None,
        policy_injector: Optional[PolicyInjector] = None,
        asset_registry: Optional[AssetRegistry] = None,
    ) -> None:
        self.capability_selector = capability_selector or KeywordCapabilitySelector()
        self.graph_builder = graph_builder or RuleBasedCapabilityGraphBuilder()
        self.binder = binder or HeuristicToolBinder()
        self.policy_injector = policy_injector or DefaultPolicyInjector()
        self.asset_registry = asset_registry

    def plan(self, request: PlanningRequest) -> PlanningResult:
        diagnostics = PlanningDiagnostics()

        candidates = self.capability_selector.select(
            task=request.task,
            context=request.context,
            hints=request.hints,
        )
        diagnostics.selected_capabilities = [c.capability_id for c in candidates]

        graph = self.graph_builder.build(
            task=request.task,
            candidates=candidates,
        )

        bindings: List[ToolBinding] = []
        for node in graph.capabilities:
            result = self.binder.bind_one(
                BindingRequest(
                    capability=node,
                    candidate_tools=request.context.candidate_tools,
                    context=request.context,
                    forbidden_tools=request.hints.forbidden_tools,
                )
            )
            if result.binding is not None:
                bindings.append(result.binding)
                diagnostics.binding_scores[node.capability_id] = result.binding.binding_confidence
            else:
                diagnostics.unresolved_capabilities.append(node.capability_id)
                diagnostics.warnings.append(result.unresolved_reason or "unknown binding failure")

        policy = self.policy_injector.inject(
            graph=graph,
            task=request.task,
            context=request.context,
            policy=request.policy,
        )

        execution_plan = self.policy_injector.compile_execution_plan(
            graph=graph,
            bindings=bindings,
            task=request.task,
        )

        workflow = Workflow(
            workflow_id=request.workflow_id or _new_id("wf"),
            version=request.version,
            phase=Phase.PHASE1_TRAINING_FREE,
            task=request.task,
            context=request.context,
            capability_graph=graph,
            tool_bindings=bindings,
            execution_plan=execution_plan,
            policy=policy,
            reusable_targets=ReusableTargets(
                compile_skill=False,
                compile_workflow=True,
                compile_policy_snippet=False,
            ),
            metadata={
                "planner": "HTGPPlanner",
                "mode": "phase1_rule_based",
                "reused_assets": list(request.hints.reusable_asset_ids),
            },
        )
        return PlanningResult(workflow=workflow, diagnostics=diagnostics)

    def replan_from_error(
        self,
        request: PlanningRequest,
        failed_workflow: Workflow,
        error_metadata: Dict[str, Any],
        state_values: Dict[str, Any],
    ) -> PlanningResult:
        """
        最小 replan：把失败工具加入 forbidden_tools，然后重新 plan。
        后面可以升级成局部重规划。
        """
        hints = PlanningHints(
            preferred_capabilities=list(request.hints.preferred_capabilities),
            forbidden_tools=list(request.hints.forbidden_tools),
            reusable_asset_ids=list(request.hints.reusable_asset_ids),
            prior_failures=list(request.hints.prior_failures),
            metadata=dict(request.hints.metadata),
        )

        failed_tool_id = error_metadata.get("tool_id")
        if failed_tool_id:
            hints.forbidden_tools.append(failed_tool_id)

        new_request = PlanningRequest(
            task=request.task,
            context=request.context,
            policy=request.policy or failed_workflow.policy,
            hints=hints,
            workflow_id=f"{failed_workflow.workflow_id}_replan",
            version=failed_workflow.version,
        )
        return self.plan(new_request)