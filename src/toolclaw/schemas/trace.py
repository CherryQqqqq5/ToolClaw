"""Trace schema for step events, snapshots, policy checks, and run-level metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunMode(str, Enum):
    BASELINE = "baseline"
    TOOLCLAW = "toolclaw"


class EventType(str, Enum):
    PLAN_GENERATED = "plan_generated"
    PREFLIGHT_CHECK = "preflight_check"
    POLICY_CHECK = "policy_check"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    USER_QUERY = "user_query"
    USER_REPLY = "user_reply"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    REPAIR_TRIGGERED = "repair_triggered"
    REPAIR_APPLIED = "repair_applied"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_CREATED = "checkpoint_created"
    ROLLBACK = "rollback"
    REPLAN_TRIGGERED = "replan_triggered"
    REPLAN_APPLIED = "replan_applied"
    STOP = "stop"
    ABORT = "abort"


@dataclass
class RunMetadata:
    model_name: str
    mode: RunMode
    start_time: str = field(default_factory=utc_now_iso)
    end_time: Optional[str] = None
    benchmark: Optional[str] = None
    task_source: Optional[str] = None
    primary_failtax: Optional[str] = None
    failtaxes: List[str] = field(default_factory=list)
    budget_profile: Dict[str, Any] = field(default_factory=dict)
    task_annotations: Dict[str, Any] = field(default_factory=dict)
    budget_limits: Dict[str, Any] = field(default_factory=dict)
    budget_usage: Dict[str, Any] = field(default_factory=dict)
    interaction_modules: List[str] = field(default_factory=list)
    run_manifest: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyState:
    approval_pending: bool = False
    risk_level: str = "medium"
    budget_remaining: Optional[float] = None


@dataclass
class PolicyEvent:
    rule_id: Optional[str] = None
    decision: str = "allow"
    rationale: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckpointRecord:
    checkpoint_id: str
    step_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostMetrics:
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    estimated_latency_ms: int = 0
    actual_latency_ms: int = 0


@dataclass
class StateSnapshot:
    snapshot_id: str
    timestamp: str
    active_step_id: Optional[str]
    completed_steps: List[str] = field(default_factory=list)
    pending_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    missing_assets: List[str] = field(default_factory=list)
    policy_state: PolicyState = field(default_factory=PolicyState)
    state_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceEvent:
    event_id: str
    timestamp: str
    step_id: Optional[str]
    event_type: EventType
    actor: str
    tool_id: Optional[str] = None
    input_ref: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceMetrics:
    total_steps: int = 0
    tool_calls: int = 0
    user_queries: int = 0
    repair_actions: int = 0
    success: Optional[bool] = None
    token_cost: Optional[float] = None
    latency_ms: Optional[int] = None
    clarification_precision: float = 0.0
    clarification_recall: float = 0.0
    unnecessary_question_rate: float = 0.0
    patch_success_rate: float = 0.0
    post_answer_retry_count: int = 0
    recovery_budget_used: float = 0.0
    budget_violation: bool = False
    budget_violation_reason: Optional[str] = None
    safe_abort: bool = False
    policy_compliance_success: bool = False
    state_repair_success: bool = False


@dataclass
class Trace:
    run_id: str
    workflow_id: str
    task_id: str
    phase: str = "phase2_workflow_intelligence"
    metadata: RunMetadata = field(
        default_factory=lambda: RunMetadata(
            model_name="frozen_base_model",
            mode=RunMode.TOOLCLAW,
        )
    )
    state_snapshots: List[StateSnapshot] = field(default_factory=list)
    events: List[TraceEvent] = field(default_factory=list)
    metrics: TraceMetrics = field(default_factory=TraceMetrics)

    def add_snapshot(
        self,
        snapshot_id: str,
        active_step_id: Optional[str],
        completed_steps: Optional[List[str]] = None,
        pending_steps: Optional[List[str]] = None,
        failed_steps: Optional[List[str]] = None,
        missing_assets: Optional[List[str]] = None,
        policy_state: Optional[PolicyState] = None,
        state_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.state_snapshots.append(
            StateSnapshot(
                snapshot_id=snapshot_id,
                timestamp=utc_now_iso(),
                active_step_id=active_step_id,
                completed_steps=completed_steps or [],
                pending_steps=pending_steps or [],
                failed_steps=failed_steps or [],
                missing_assets=missing_assets or [],
                policy_state=policy_state or PolicyState(),
                state_values=state_values or {},
            )
        )

    def add_event(
        self,
        event_id: str,
        event_type: EventType,
        actor: str,
        step_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        input_ref: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.events.append(
            TraceEvent(
                event_id=event_id,
                timestamp=utc_now_iso(),
                step_id=step_id,
                event_type=event_type,
                actor=actor,
                tool_id=tool_id,
                input_ref=input_ref,
                tool_args=tool_args,
                output=output,
                message=message,
                metadata=metadata or {},
            )
        )

        if event_type == EventType.TOOL_CALL:
            self.metrics.tool_calls += 1
        elif event_type == EventType.USER_QUERY:
            self.metrics.user_queries += 1
        elif event_type == EventType.REPAIR_APPLIED:
            self.metrics.repair_actions += 1

    def finalize(
        self,
        success: bool,
        total_steps: Optional[int] = None,
        token_cost: Optional[float] = None,
        latency_ms: Optional[int] = None,
    ) -> None:
        self.metadata.end_time = utc_now_iso()
        self.metrics.success = success
        if total_steps is not None:
            self.metrics.total_steps = total_steps
        if token_cost is not None:
            self.metrics.token_cost = token_cost
        if latency_ms is not None:
            self.metrics.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def demo(cls) -> "Trace":
        trace = cls(
            run_id="run_demo_001",
            workflow_id="wf_demo_001",
            task_id="task_demo_001",
            metadata=RunMetadata(
                model_name="frozen_base_model",
                mode=RunMode.TOOLCLAW,
                benchmark="tau",
                task_source="demo_task",
            ),
        )

        trace.add_snapshot(
            snapshot_id="snap_00",
            active_step_id=None,
            completed_steps=[],
            pending_steps=["step_01", "step_02"],
            state_values={"status": "initialized"},
        )

        trace.add_event(
            event_id="evt_01",
            event_type=EventType.PLAN_GENERATED,
            actor="planner",
            input_ref="task_demo_001",
            output={"summary": "Generated workflow with 2 steps"},
        )

        trace.add_event(
            event_id="evt_02",
            event_type=EventType.TOOL_CALL,
            actor="executor",
            step_id="step_01",
            tool_id="search_tool",
            tool_args={"query": "target document summary"},
        )

        trace.add_event(
            event_id="evt_03",
            event_type=EventType.TOOL_RESULT,
            actor="environment",
            step_id="step_01",
            tool_id="search_tool",
            output={"status": "success", "payload_ref": "artifact://retrieved_info"},
        )

        trace.add_snapshot(
            snapshot_id="snap_01",
            active_step_id="step_02",
            completed_steps=["step_01"],
            pending_steps=["step_02"],
            state_values={"information_obtained": True},
        )

        trace.add_event(
            event_id="evt_04",
            event_type=EventType.TOOL_CALL,
            actor="executor",
            step_id="step_02",
            tool_id="write_tool",
            tool_args={"target_path": "outputs/reports/demo_report.txt"},
        )

        trace.add_event(
            event_id="evt_05",
            event_type=EventType.TOOL_RESULT,
            actor="environment",
            step_id="step_02",
            tool_id="write_tool",
            output={"status": "failed", "reason": "missing required field: target_path"},
        )

        trace.add_event(
            event_id="evt_06",
            event_type=EventType.REPAIR_TRIGGERED,
            actor="recovery_engine",
            step_id="step_02",
            tool_id="write_tool",
            output={"repair_type": "rebind_args"},
        )

        trace.add_event(
            event_id="evt_07",
            event_type=EventType.REPAIR_APPLIED,
            actor="executor",
            step_id="step_02",
            tool_id="write_tool",
            output={
                "patched_target_path": "outputs/reports/demo_report.txt",
                "status": "success",
            },
        )

        trace.add_event(
            event_id="evt_08",
            event_type=EventType.STOP,
            actor="executor",
            output={"status": "success", "reason": "success_criteria_satisfied"},
        )

        trace.finalize(success=True, total_steps=2)
        return trace
