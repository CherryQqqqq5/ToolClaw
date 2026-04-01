"""Runtime state container for completed steps, checkpoints, and transient values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CheckpointState:
    checkpoint_id: str
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateTracker:
    """Minimal step-level state tracker for phase-1 execution."""

    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)
    checkpoints: Dict[str, CheckpointState] = field(default_factory=dict)

    def set_current_step(self, step_id: Optional[str]) -> None:
        self.current_step_id = step_id

    def mark_completed(self, step_id: str) -> None:
        if step_id in self.failed_steps:
            self.failed_steps.remove(step_id)
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)
        self.current_step_id = None

    def mark_failed(self, step_id: str) -> None:
        if step_id not in self.failed_steps:
            self.failed_steps.append(step_id)
        self.current_step_id = step_id

    def snapshot(self, pending_steps: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "active_step_id": self.current_step_id,
            "completed_steps": list(self.completed_steps),
            "pending_steps": list(pending_steps or []),
            "failed_steps": list(self.failed_steps),
            "state_values": dict(self.state_values),
        }

    def save_checkpoint(self, checkpoint_id: str) -> None:
        self.checkpoints[checkpoint_id] = CheckpointState(
            checkpoint_id=checkpoint_id,
            completed_steps=list(self.completed_steps),
            failed_steps=list(self.failed_steps),
            state_values=dict(self.state_values),
        )

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        checkpoint = self.checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return False
        self.completed_steps = list(checkpoint.completed_steps)
        self.failed_steps = list(checkpoint.failed_steps)
        self.state_values = dict(checkpoint.state_values)
        self.current_step_id = None
        return True

    def update_policy_state(self, patch: Dict[str, Any]) -> None:
        self.state_values.update(patch)

    def register_missing_asset(self, asset_key: str) -> None:
        self.state_values.setdefault("__missing_assets__", [])
        if asset_key not in self.state_values["__missing_assets__"]:
            self.state_values["__missing_assets__"].append(asset_key)
