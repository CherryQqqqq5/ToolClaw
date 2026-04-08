"""Workflow schema for tasks, capability graphs, execution steps, and runtime graphs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Phase(str, Enum):
    PHASE1_TRAINING_FREE = "phase1_training_free"


class Platform(str, Enum):
    LOCAL = "local"
    WEB = "web"
    API = "api"
    MIXED = "mixed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    USER_QUERY = "user_query"
    POLICY_CHECK = "policy_check"
    REPAIR = "repair"


@dataclass
class TaskConstraints:
    budget_limit: Optional[float] = None
    time_limit: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_user_approval: bool = False
    forbidden_actions: List[str] = field(default_factory=list)
    max_tool_calls: Optional[int] = None
    max_user_turns: Optional[int] = None
    max_repair_attempts: Optional[int] = None
    max_recovery_budget: Optional[float] = None


@dataclass
class TaskSpec:
    task_id: str
    user_goal: str
    success_criteria: List[str] = field(default_factory=list)
    constraints: TaskConstraints = field(default_factory=TaskConstraints)


@dataclass
class Permissions:
    network: bool = True
    filesystem_read: bool = True
    filesystem_write: bool = False
    external_api: bool = True


@dataclass
class EnvironmentContext:
    platform: Platform = Platform.MIXED
    available_assets: List[str] = field(default_factory=list)
    missing_assets: List[str] = field(default_factory=list)
    permissions: Permissions = field(default_factory=Permissions)


@dataclass
class ToolSpec:
    tool_id: str
    description: str
    input_schema_ref: Optional[str] = None
    output_schema_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityNode:
    capability_id: str
    description: str
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class CapabilityEdge:
    source: str
    target: str
    condition: Optional[str] = None


@dataclass
class CapabilityGraph:
    capabilities: List[CapabilityNode] = field(default_factory=list)
    edges: List[CapabilityEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolBinding:
    capability_id: str
    primary_tool: str
    backup_tools: List[str] = field(default_factory=list)
    binding_confidence: float = 0.0


@dataclass
class WorkflowStep:
    step_id: str
    capability_id: str
    tool_id: Optional[str]
    action_type: ActionType = ActionType.TOOL_CALL
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None
    checkpoint: bool = False
    rollback_to: Optional[str] = None
    requires_user_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyRule:
    rule_id: str
    trigger: str
    action: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowPolicy:
    approval_rules: List[PolicyRule] = field(default_factory=list)
    recovery_rules: List[PolicyRule] = field(default_factory=list)
    stop_rules: List[str] = field(default_factory=list)


@dataclass
class ApprovalGate:
    required: bool = False
    authority: str = "user"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointPolicy:
    enabled: bool = True
    reason: Optional[str] = None


@dataclass
class RollbackPolicy:
    rollback_to_step_id: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class FallbackRoute:
    tool_id: str
    condition: Optional[str] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreflightRequirement:
    asset_key: str
    source: str = "step_input"
    required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyState:
    approval_pending: bool = False
    approved_actions: List[str] = field(default_factory=list)
    risk_level: str = "medium"
    budget_limit: Optional[float] = None
    budget_spent: float = 0.0
    forbidden_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionCursor:
    active_node_id: Optional[str] = None
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)
    missing_assets: List[str] = field(default_factory=list)
    policy_state: PolicyState = field(default_factory=PolicyState)


@dataclass
class ReusableTargets:
    compile_skill: bool = False
    compile_workflow: bool = True
    compile_policy_snippet: bool = False


@dataclass
class WorkflowEdge:
    source: str
    target: str
    condition: Optional[str] = None
    edge_type: str = "default"


@dataclass
class WorkflowNode:
    node_id: str
    capability_id: str
    selected_tool: Optional[str] = None
    tool_candidates: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    checkpoint_policy: CheckpointPolicy = field(default_factory=CheckpointPolicy)
    rollback_policy: RollbackPolicy = field(default_factory=RollbackPolicy)
    approval_gate: ApprovalGate = field(default_factory=ApprovalGate)
    fallback_routes: List[FallbackRoute] = field(default_factory=list)
    preflight_requirements: List[PreflightRequirement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowGraph:
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    entry_nodes: List[str] = field(default_factory=list)
    exit_nodes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowContext:
    environment: EnvironmentContext = field(default_factory=EnvironmentContext)
    candidate_tools: List[ToolSpec] = field(default_factory=list)


@dataclass
class Workflow:
    workflow_id: str
    version: str
    phase: Phase
    task: TaskSpec
    context: WorkflowContext = field(default_factory=WorkflowContext)
    capability_graph: CapabilityGraph = field(default_factory=CapabilityGraph)
    tool_bindings: List[ToolBinding] = field(default_factory=list)
    execution_plan: List[WorkflowStep] = field(default_factory=list)
    workflow_graph: WorkflowGraph = field(default_factory=WorkflowGraph)
    policy: WorkflowPolicy = field(default_factory=WorkflowPolicy)
    reusable_targets: ReusableTargets = field(default_factory=ReusableTargets)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_graph_dict(self) -> Dict[str, Any]:
        return asdict(self.workflow_graph)

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        for step in self.execution_plan:
            if step.step_id == step_id:
                return step
        return None

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        for node in self.workflow_graph.nodes:
            if node.node_id == node_id:
                return node
        return None

    def topo_sorted_nodes(self) -> List[WorkflowNode]:
        if not self.workflow_graph.nodes:
            return [
                WorkflowNode(
                    node_id=step.step_id,
                    capability_id=step.capability_id,
                    selected_tool=step.tool_id,
                    tool_candidates=[step.tool_id] if step.tool_id else [],
                    inputs=dict(step.inputs),
                    expected_output=step.expected_output,
                    checkpoint_policy=CheckpointPolicy(enabled=step.checkpoint),
                    rollback_policy=RollbackPolicy(rollback_to_step_id=step.rollback_to),
                    approval_gate=ApprovalGate(required=step.requires_user_confirmation),
                    metadata=dict(step.metadata),
                )
                for step in self.execution_plan
            ]

        indegree: Dict[str, int] = {node.node_id: 0 for node in self.workflow_graph.nodes}
        adjacency: Dict[str, List[str]] = {node.node_id: [] for node in self.workflow_graph.nodes}
        for edge in self.workflow_graph.edges:
            indegree[edge.target] = indegree.get(edge.target, 0) + 1
            adjacency.setdefault(edge.source, []).append(edge.target)

        ready = [node.node_id for node in self.workflow_graph.nodes if indegree.get(node.node_id, 0) == 0]
        ordered: List[WorkflowNode] = []
        node_by_id = {node.node_id: node for node in self.workflow_graph.nodes}
        while ready:
            current = ready.pop(0)
            ordered.append(node_by_id[current])
            for nxt in adjacency.get(current, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    ready.append(nxt)

        if len(ordered) != len(self.workflow_graph.nodes):
            return list(self.workflow_graph.nodes)
        return ordered

    def patch_with_resume(self, resume_patch: Any) -> None:
        for step in self.execution_plan:
            if step.step_id == getattr(resume_patch, "resume_step_id", None):
                for key, value in getattr(resume_patch, "state_updates", {}).items():
                    if key not in {"abort", "tool_id", "approved"}:
                        step.inputs[key] = value
                tool_id = getattr(resume_patch, "binding_patch", {}).get("tool_id")
                if tool_id:
                    step.tool_id = tool_id
                break

        if not self.workflow_graph.nodes:
            return

        for node in self.workflow_graph.nodes:
            if node.node_id == getattr(resume_patch, "resume_step_id", None):
                for key, value in getattr(resume_patch, "state_updates", {}).items():
                    if key not in {"abort", "tool_id", "approved"}:
                        node.inputs[key] = value
                tool_id = getattr(resume_patch, "binding_patch", {}).get("tool_id")
                if tool_id:
                    node.selected_tool = tool_id
                break

    @classmethod
    def demo(cls) -> "Workflow":
        """Minimal demo workflow for Phase-1 sanity checks."""
        task = TaskSpec(
            task_id="task_demo_001",
            user_goal="Retrieve a file summary and save a report.",
            success_criteria=[
                "required information is retrieved",
                "report artifact is generated",
            ],
            constraints=TaskConstraints(
                risk_level=RiskLevel.MEDIUM,
                requires_user_approval=False,
            ),
        )

        context = WorkflowContext(
            environment=EnvironmentContext(
                platform=Platform.MIXED,
                available_assets=[],
                missing_assets=[],
                permissions=Permissions(
                    network=True,
                    filesystem_read=True,
                    filesystem_write=True,
                    external_api=True,
                ),
            ),
            candidate_tools=[
                ToolSpec(
                    tool_id="search_tool",
                    description="Search information from a source.",
                    input_schema_ref="schema://search_tool_input",
                ),
                ToolSpec(
                    tool_id="write_tool",
                    description="Write output artifact.",
                    input_schema_ref="schema://write_tool_input",
                ),
            ],
        )

        capability_graph = CapabilityGraph(
            capabilities=[
                CapabilityNode(
                    capability_id="cap_retrieve",
                    description="Retrieve relevant information",
                    postconditions=["information_obtained"],
                ),
                CapabilityNode(
                    capability_id="cap_write",
                    description="Write final report artifact",
                    preconditions=["information_obtained"],
                    postconditions=["artifact_ready"],
                ),
            ],
            edges=[
                CapabilityEdge(
                    source="cap_retrieve",
                    target="cap_write",
                    condition="information_obtained == true",
                )
            ],
        )

        tool_bindings = [
            ToolBinding(
                capability_id="cap_retrieve",
                primary_tool="search_tool",
                binding_confidence=0.90,
            ),
            ToolBinding(
                capability_id="cap_write",
                primary_tool="write_tool",
                binding_confidence=0.88,
            ),
        ]

        execution_plan = [
            WorkflowStep(
                step_id="step_01",
                capability_id="cap_retrieve",
                tool_id="search_tool",
                action_type=ActionType.TOOL_CALL,
                inputs={"query": "target document summary"},
                expected_output="retrieved_info",
                checkpoint=True,
            ),
            WorkflowStep(
                step_id="step_02",
                capability_id="cap_write",
                tool_id="write_tool",
                action_type=ActionType.TOOL_CALL,
                inputs={"target_path": "outputs/reports/demo_report.txt"},
                expected_output="report_artifact",
                checkpoint=True,
                rollback_to="step_01",
            ),
        ]

        workflow_graph = WorkflowGraph(
            nodes=[
                WorkflowNode(
                    node_id="step_01",
                    capability_id="cap_retrieve",
                    selected_tool="search_tool",
                    tool_candidates=["search_tool"],
                    inputs={"query": "target document summary"},
                    expected_output="retrieved_info",
                    checkpoint_policy=CheckpointPolicy(enabled=True, reason="step_boundary"),
                ),
                WorkflowNode(
                    node_id="step_02",
                    capability_id="cap_write",
                    selected_tool="write_tool",
                    tool_candidates=["write_tool"],
                    inputs={"target_path": "outputs/reports/demo_report.txt"},
                    expected_output="report_artifact",
                    dependencies=["step_01"],
                    checkpoint_policy=CheckpointPolicy(enabled=True, reason="step_boundary"),
                    rollback_policy=RollbackPolicy(rollback_to_step_id="step_01", reason="write_failure"),
                ),
            ],
            edges=[WorkflowEdge(source="step_01", target="step_02", condition="retrieved_info != null")],
            entry_nodes=["step_01"],
            exit_nodes=["step_02"],
        )

        policy = WorkflowPolicy(
            approval_rules=[
                PolicyRule(
                    rule_id="apr_01",
                    trigger="risk_level == high",
                    action="ask_user",
                )
            ],
            recovery_rules=[
                PolicyRule(
                    rule_id="rec_01",
                    trigger="tool_unavailable",
                    action="switch_backup_tool",
                )
            ],
            stop_rules=[
                "success_criteria_satisfied",
                "hard_constraint_violated",
                "user_abort",
            ],
        )

        return cls(
            workflow_id="wf_demo_001",
            version="0.1",
            phase=Phase.PHASE1_TRAINING_FREE,
            task=task,
            context=context,
            capability_graph=capability_graph,
            tool_bindings=tool_bindings,
            execution_plan=execution_plan,
            workflow_graph=workflow_graph,
            policy=policy,
            reusable_targets=ReusableTargets(
                compile_skill=False,
                compile_workflow=True,
                compile_policy_snippet=False,
            ),
            metadata={"note": "Phase-1 demo workflow"},
        )
