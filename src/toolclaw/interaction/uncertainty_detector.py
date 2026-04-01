"""Classify blocked states into actionable uncertainty labels for IRC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from toolclaw.schemas.repair import Repair, RepairType
from toolclaw.schemas.workflow import Workflow


@dataclass
class InformationGap:
    gap_type: str
    target: Optional[str] = None
    rationale: str = ""


@dataclass
class ConstraintConflict:
    conflict_type: str
    rationale: str = ""


@dataclass
class UncertaintyReport:
    primary_label: str
    confidence: float
    information_gaps: List[InformationGap] = field(default_factory=list)
    conflicts: List[ConstraintConflict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UncertaintyDetector:
    def analyze_failure(
        self,
        workflow: Workflow,
        repair: Repair,
        state_values: Dict[str, Any],
    ) -> UncertaintyReport:
        _ = workflow
        if repair.repair_type == RepairType.REQUEST_APPROVAL:
            return UncertaintyReport(
                primary_label="approval_needed",
                confidence=0.95,
                conflicts=[ConstraintConflict(conflict_type="approval", rationale="policy requires confirmation")],
                metadata={"state_keys": sorted(state_values.keys())},
            )
        if repair.repair_type == RepairType.ASK_USER:
            return UncertaintyReport(
                primary_label="missing_info",
                confidence=0.85,
                information_gaps=[InformationGap(gap_type="asset_or_constraint", rationale="repair requires user guidance")],
                metadata={"state_keys": sorted(state_values.keys())},
            )
        return UncertaintyReport(
            primary_label="recoverable_runtime_error",
            confidence=0.6,
            metadata={"state_keys": sorted(state_values.keys())},
        )
