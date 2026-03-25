from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StateTracker:
    """Minimal step-level state tracker for phase-1 execution."""

    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    state_values: Dict[str, Any] = field(default_factory=dict)

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
