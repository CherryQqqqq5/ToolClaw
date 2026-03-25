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
class ReusableTargets:
    compile_skill: bool = False
    compile_workflow: bool = True
    compile_policy_snippet: bool = False


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
    policy: WorkflowPolicy = field(default_factory=WorkflowPolicy)
    reusable_targets: ReusableTargets = field(default_factory=ReusableTargets)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

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
            policy=policy,
            reusable_targets=ReusableTargets(
                compile_skill=False,
                compile_workflow=True,
                compile_policy_snippet=False,
            ),
            metadata={"note": "Phase-1 demo workflow"},
        )