from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Phase(str, Enum):
    PHASE1_TRAINING_FREE = "phase1_training_free"


class ErrorCategory(str, Enum):
    SELECTION_FAILURE = "selection_failure"
    BINDING_FAILURE = "binding_failure"
    ORDERING_FAILURE = "ordering_failure"
    STATE_FAILURE = "state_failure"
    CONSTRAINT_FAILURE = "constraint_failure"
    PERMISSION_FAILURE = "permission_failure"
    ENVIRONMENT_FAILURE = "environment_failure"
    INTERACTION_FAILURE = "interaction_failure"
    RECOVERY_FAILURE = "recovery_failure"


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FATAL = "fatal"


class ErrorStage(str, Enum):
    PLANNING = "planning"
    BINDING = "binding"
    EXECUTION = "execution"
    INTERACTION = "interaction"
    RECOVERY = "recovery"


@dataclass
class ErrorEvidence:
    tool_id: Optional[str] = None
    raw_message: Optional[str] = None
    exception_type: Optional[str] = None
    related_events: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateContext:
    active_capability: Optional[str] = None
    active_step_id: Optional[str] = None
    missing_assets: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)
    policy_flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Recoverability:
    recoverable: bool = True
    requires_user_input: bool = False
    requires_tool_switch: bool = False
    requires_rollback: bool = False
    requires_approval: bool = False


@dataclass
class ToolClawError:
    error_id: str
    run_id: str
    workflow_id: str
    step_id: Optional[str]
    timestamp: str = field(default_factory=utc_now_iso)
    phase: Phase = Phase.PHASE1_TRAINING_FREE
    category: ErrorCategory = ErrorCategory.ENVIRONMENT_FAILURE
    subtype: str = "unknown"
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    stage: ErrorStage = ErrorStage.EXECUTION
    symptoms: List[str] = field(default_factory=list)
    evidence: ErrorEvidence = field(default_factory=ErrorEvidence)
    root_cause_hypothesis: List[str] = field(default_factory=list)
    state_context: StateContext = field(default_factory=StateContext)
    recoverability: Recoverability = field(default_factory=Recoverability)
    failtax_label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_fatal(self) -> bool:
        return self.severity == ErrorSeverity.FATAL

    @property
    def needs_user(self) -> bool:
        return self.recoverability.requires_user_input

    @classmethod
    def demo(cls) -> "ToolClawError":
        return cls(
            error_id="err_demo_001",
            run_id="run_demo_001",
            workflow_id="wf_demo_001",
            step_id="step_02",
            category=ErrorCategory.BINDING_FAILURE,
            subtype="wrong_argument_mapping",
            severity=ErrorSeverity.MEDIUM,
            stage=ErrorStage.EXECUTION,
            symptoms=[
                "tool returned invalid-argument error",
                "required field missing in tool input",
            ],
            evidence=ErrorEvidence(
                tool_id="write_tool",
                raw_message="missing required field: target_path",
                related_events=["evt_04"],
                inputs={"target_path": None},
            ),
            root_cause_hypothesis=[
                "executor failed to bind a required argument",
                "required asset was not propagated from previous state",
            ],
            state_context=StateContext(
                active_capability="cap_write",
                active_step_id="step_02",
                missing_assets=["target_path"],
                state_values={"information_obtained": True},
                policy_flags={"approval_pending": False, "risk_level": "medium"},
            ),
            recoverability=Recoverability(
                recoverable=True,
                requires_user_input=False,
                requires_tool_switch=False,
                requires_rollback=False,
                requires_approval=False,
            ),
            failtax_label="binding_failure",
            metadata={"note": "Phase-1 demo error"},
        )