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
    patch_targets: Dict[str, str] = field(default_factory=dict)
    target_scope: str = "step"
    urgency: str = "normal"


class QueryPolicy:
    def decide_query(self, report: UncertaintyReport) -> QueryPlan:
        if report.primary_label == "approval_needed":
            return QueryPlan(
                ask=True,
                question_type="approval",
                question_text="Approve this blocked action?",
                response_schema={
                    "type": "object",
                    "properties": {"approved": {"type": "boolean"}},
                    "required": ["approved"],
                    "additionalProperties": False,
                },
                patch_targets={"approved": "policy.approved"},
                urgency="high",
            )
        if report.primary_label == "missing_info":
            missing_input_keys = [str(item) for item in report.metadata.get("missing_input_keys", []) if str(item)]
            error_category = str(report.metadata.get("error_category") or "unknown")
            if missing_input_keys == ["target_path"]:
                return QueryPlan(
                    ask=True,
                    question_type="target_path_patch",
                    question_text="Provide `target_path` so the blocked write step can continue.",
                    response_schema={
                        "type": "object",
                        "properties": {"target_path": {"type": "string"}},
                        "required": ["target_path"],
                        "additionalProperties": False,
                    },
                    patch_targets={"target_path": "step.inputs.target_path"},
                    urgency="high",
                )
            if error_category == "environment_failure":
                return QueryPlan(
                    ask=True,
                    question_type="environment_resolution",
                    question_text="The environment failed. Provide one direct fix: `tool_id`, `fallback_execution_path`, or `clear_failure_flag`.",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "tool_id": {"type": "string"},
                            "fallback_execution_path": {"type": "string"},
                            "clear_failure_flag": {"type": "boolean"},
                        },
                        "additionalProperties": False,
                    },
                    patch_targets={
                        "tool_id": "binding.primary_tool",
                        "fallback_execution_path": "step.inputs.target_path",
                        "clear_failure_flag": "state.force_environment_failure",
                    },
                    urgency="high",
                )
            if missing_input_keys:
                properties = {key: {"type": "string"} for key in missing_input_keys}
                return QueryPlan(
                    ask=True,
                    question_type="input_patch",
                    question_text=f"Provide the missing field(s): {', '.join(missing_input_keys)}.",
                    response_schema={
                        "type": "object",
                        "properties": properties,
                        "required": list(missing_input_keys),
                        "additionalProperties": False,
                    },
                    patch_targets={key: f"step.inputs.{key}" for key in missing_input_keys},
                    urgency="high",
                )
            return QueryPlan(
                ask=True,
                question_type="asset_or_constraint",
                question_text="Required information is missing. Provide one direct patch for the blocked step.",
                response_schema={
                    "type": "object",
                    "properties": {
                        "tool_id": {"type": "string"},
                        "fallback_execution_path": {"type": "string"},
                        "input_patch": {"type": "object"},
                    },
                    "additionalProperties": False,
                },
                patch_targets={
                    "tool_id": "binding.primary_tool",
                    "fallback_execution_path": "step.inputs.target_path",
                },
            )
        return QueryPlan(ask=False, question_type="none", question_text="")
