"""Schema definitions for repair plans, workflow patches, and repair status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Phase(str, Enum):
    PHASE1_TRAINING_FREE = "phase1_training_free"


class RepairType(str, Enum):
    ASK_USER = "ask_user"
    REQUEST_APPROVAL = "request_approval"
    REBIND_ARGS = "rebind_args"
    SWITCH_TOOL = "switch_tool"
    SWITCH_BACKUP_PATH = "switch_backup_path"
    INSERT_MISSING_STEP = "insert_missing_step"
    REORDER_STEPS = "reorder_steps"
    ROLLBACK_TO_CHECKPOINT = "rollback_to_checkpoint"
    ACQUIRE_MISSING_ASSET = "acquire_missing_asset"
    RELAX_NONCRITICAL_CONSTRAINT = "relax_noncritical_constraint"
    REROUTE_BRANCH = "reroute_branch"
    REPLAN_SUFFIX = "replan_suffix"
    ABORT_WORKFLOW = "abort_workflow"


class RepairStrategy(str, Enum):
    DIRECT_PATCH = "direct_patch"
    USER_IN_THE_LOOP = "user_in_the_loop"
    FALLBACK = "fallback"
    ROLLBACK_AND_RETRY = "rollback_and_retry"
    SAFE_ABORT = "safe_abort"


class RepairStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class RepairActionType(str, Enum):
    STATE_PATCH = "state_patch"
    RE_EXECUTE_STEP = "re_execute_step"
    SWITCH_TOOL = "switch_tool"
    INSERT_STEP = "insert_step"
    REMOVE_STEP = "remove_step"
    REORDER_STEPS = "reorder_steps"
    ROLLBACK = "rollback"
    ASK_USER = "ask_user"
    REQUEST_APPROVAL = "request_approval"
    UPDATE_POLICY_FLAG = "update_policy_flag"
    ABORT = "abort"


@dataclass
class RepairDecision:
    strategy: RepairStrategy
    rationale: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairAction:
    action_id: str
    action_type: RepairActionType
    target: Optional[str] = None
    value_source: Optional[str] = None
    value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairInteraction:
    ask_user: bool = False
    question: Optional[str] = None
    expected_answer_type: Optional[str] = None
    user_response: Optional[Any] = None


@dataclass
class WorkflowPatch:
    modified_steps: List[str] = field(default_factory=list)
    reordered_steps: List[str] = field(default_factory=list)
    inserted_steps: List[str] = field(default_factory=list)
    removed_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPatch:
    inserted_edges: List[Dict[str, Any]] = field(default_factory=list)
    removed_edges: List[Dict[str, Any]] = field(default_factory=list)
    node_updates: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class PolicyPatch:
    approval_pending: Optional[bool] = None
    approved_actions: List[str] = field(default_factory=list)
    budget_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssetPatch:
    missing_assets_resolved: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RepairPostConditions:
    expected_effects: List[str] = field(default_factory=list)
    stop_if: List[str] = field(default_factory=list)


@dataclass
class RepairResult:
    status: RepairStatus = RepairStatus.PENDING
    success: Optional[bool] = None
    followup_error_id: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Repair:
    repair_id: str
    run_id: str
    workflow_id: str
    triggered_error_ids: List[str] = field(default_factory=list)
    trigger_event_id: Optional[str] = None
    phase: Phase = Phase.PHASE1_TRAINING_FREE
    repair_type: RepairType = RepairType.REBIND_ARGS
    decision: RepairDecision = field(
        default_factory=lambda: RepairDecision(
            strategy=RepairStrategy.DIRECT_PATCH,
            rationale="default repair decision",
            confidence=0.0,
        )
    )
    actions: List[RepairAction] = field(default_factory=list)
    interaction: RepairInteraction = field(default_factory=RepairInteraction)
    workflow_patch: WorkflowPatch = field(default_factory=WorkflowPatch)
    graph_patch: GraphPatch = field(default_factory=GraphPatch)
    policy_patch: PolicyPatch = field(default_factory=PolicyPatch)
    asset_patch: AssetPatch = field(default_factory=AssetPatch)
    post_conditions: RepairPostConditions = field(default_factory=RepairPostConditions)
    result: RepairResult = field(default_factory=RepairResult)
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def mark_applied(self) -> None:
        self.result.status = RepairStatus.APPLIED

    def mark_succeeded(self, message: Optional[str] = None) -> None:
        self.result.status = RepairStatus.SUCCEEDED
        self.result.success = True
        self.result.message = message

    def mark_failed(
        self,
        followup_error_id: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        self.result.status = RepairStatus.FAILED
        self.result.success = False
        self.result.followup_error_id = followup_error_id
        self.result.message = message

    @property
    def requires_user(self) -> bool:
        return self.interaction.ask_user

    @classmethod
    def demo(cls) -> "Repair":
        return cls(
            repair_id="rep_demo_001",
            run_id="run_demo_001",
            workflow_id="wf_demo_001",
            triggered_error_ids=["err_demo_001"],
            trigger_event_id="evt_04",
            repair_type=RepairType.REBIND_ARGS,
            decision=RepairDecision(
                strategy=RepairStrategy.DIRECT_PATCH,
                rationale="The argument mismatch is recoverable from existing state.",
                confidence=0.82,
            ),
            actions=[
                RepairAction(
                    action_id="act_01",
                    action_type=RepairActionType.STATE_PATCH,
                    target="step_02.inputs.target_path",
                    value_source="state://default_report_path",
                    value="outputs/reports/demo_report.txt",
                ),
                RepairAction(
                    action_id="act_02",
                    action_type=RepairActionType.RE_EXECUTE_STEP,
                    target="step_02",
                ),
            ],
            interaction=RepairInteraction(
                ask_user=False,
                question=None,
                expected_answer_type=None,
                user_response=None,
            ),
            workflow_patch=WorkflowPatch(
                modified_steps=["step_02"],
                reordered_steps=[],
                inserted_steps=[],
                removed_steps=[],
            ),
            post_conditions=RepairPostConditions(
                expected_effects=[
                    "tool arguments become valid",
                    "step_02 can be re-executed successfully",
                ],
                stop_if=[
                    "same error repeats twice",
                    "hard constraint violated",
                ],
            ),
            result=RepairResult(
                status=RepairStatus.PENDING,
                success=None,
            ),
            metadata={"note": "Phase-1 demo repair"},
        )
