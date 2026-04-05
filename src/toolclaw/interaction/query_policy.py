"""Policy that decides whether to ask the user and how to shape the question."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from toolclaw.interaction.uncertainty_detector import UncertaintyReport


@dataclass
class QueryPlan:
    ask: bool
    question_type: str
    question_text: str
    response_schema: Dict[str, Any] = field(default_factory=dict)
    target_scope: str = "step"
    urgency: str = "normal"


class QueryPolicy:
    def decide_query(self, report: UncertaintyReport) -> QueryPlan:
        if report.primary_label == "approval_needed":
            return QueryPlan(
                ask=True,
                question_type="approval",
                question_text="This action requires approval. Do you approve continuing?",
                response_schema={"type": "object", "properties": {"approved": {"type": "boolean"}}},
                urgency="high",
            )
        if report.primary_label == "missing_info":
            return QueryPlan(
                ask=True,
                question_type="asset_or_constraint",
                question_text="Required information is missing. Please provide the missing asset, constraint, or preferred fallback.",
                response_schema={
                    "type": "object",
                    "properties": {
                        "target_path": {"type": "string"},
                        "tool_id": {"type": "string"},
                        "fallback_execution_path": {"type": "string"},
                        "clear_failure_flag": {"type": "boolean"},
                        "input_patch": {"type": "object"},
                        "approved": {"type": "boolean"},
                    },
                },
            )
        return QueryPlan(ask=False, question_type="none", question_text="")
