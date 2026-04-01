"""Map runtime failures into a compact fail-taxonomy for recovery and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from toolclaw.schemas.error import ErrorCategory, FailTaxLabel, FailureRecord, ToolClawError
from toolclaw.schemas.workflow import WorkflowStep


@dataclass
class FailTaxEvidence:
    category: ErrorCategory
    root_cause: str
    recoverable: bool = True


class FailTaxClassifier:
    def classify_failure(
        self,
        error: ToolClawError,
        step: Optional[WorkflowStep] = None,
        state_values: Optional[Dict[str, Any]] = None,
    ) -> FailureRecord:
        state_values = state_values or {}
        raw_message = (error.evidence.raw_message or "").lower()

        if error.category == ErrorCategory.BINDING_FAILURE:
            label = FailTaxLabel.BINDING_FAILURE
            cause = "missing or invalid tool arguments"
        elif error.category == ErrorCategory.ORDERING_FAILURE:
            label = FailTaxLabel.ORDERING_FAILURE
            cause = "dependency ordering violated"
        elif error.category == ErrorCategory.STATE_FAILURE:
            label = FailTaxLabel.STATE_FAILURE
            cause = "required state not present"
        elif error.category == ErrorCategory.PERMISSION_FAILURE:
            label = FailTaxLabel.PERMISSION_FAILURE
            cause = "permission missing"
        elif error.category == ErrorCategory.RECOVERY_FAILURE:
            label = FailTaxLabel.RECOVERY_FAILURE
            cause = "repair path failed"
        elif error.category == ErrorCategory.POLICY_FAILURE:
            label = FailTaxLabel.POLICY_FAILURE
            cause = "policy constraint blocked execution"
        elif "order" in raw_message or "dependency" in raw_message:
            label = FailTaxLabel.ORDERING_FAILURE
            cause = "dependency ordering violated"
        elif "permission" in raw_message or "approval" in raw_message:
            label = FailTaxLabel.PERMISSION_FAILURE
            cause = "permission missing"
        else:
            label = FailTaxLabel.ENVIRONMENT_FAILURE
            cause = "tool or environment unavailable"

        return FailureRecord(
            failtax_label=label,
            category=error.category,
            subtype=error.subtype,
            step_id=error.step_id,
            tool_id=(step.tool_id if step else error.evidence.tool_id),
            root_cause=cause,
            recoverable=error.recoverability.recoverable,
            evidence={"state_keys": sorted(state_values.keys())},
            metadata={"error_id": error.error_id},
        )
