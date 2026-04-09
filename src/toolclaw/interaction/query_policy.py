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
        if report.primary_label in {"approval_needed", "policy_approval"}:
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
        missing_input_keys = [str(item) for item in report.metadata.get("missing_input_keys", []) if str(item)]
        missing_assets = [str(item) for item in report.metadata.get("missing_assets", []) if str(item)]
        stale_assets = [str(item) for item in report.metadata.get("stale_assets", []) if str(item)]
        error_category = str(report.metadata.get("error_category") or "unknown")
        backup_tool_id = str(report.metadata.get("backup_tool_id") or "")
        alternative_tool_ids = [
            str(item) for item in report.metadata.get("alternative_tool_ids", []) if str(item)
        ]
        branch_options = [str(item) for item in report.metadata.get("branch_options", []) if str(item)]
        if report.primary_label in {"missing_info", "missing_asset"}:
            if missing_input_keys == ["target_path"] or missing_assets == ["target_path"]:
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
            if missing_input_keys:
                properties = {key: {"type": "string"} for key in missing_input_keys}
                return QueryPlan(
                    ask=True,
                    question_type="missing_asset_patch",
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
            if missing_assets:
                primary_asset = missing_assets[0]
                return QueryPlan(
                    ask=True,
                    question_type="missing_asset_value",
                    question_text=f"Provide `{primary_asset}` so the blocked step can continue.",
                    response_schema={
                        "type": "object",
                        "properties": {primary_asset: {"type": "string"}},
                        "required": [primary_asset],
                        "additionalProperties": False,
                    },
                    patch_targets={primary_asset: f"state.{primary_asset}"},
                    urgency="high",
                )
        if report.primary_label == "stale_state":
            primary_asset = stale_assets[0] if stale_assets else (missing_assets[0] if missing_assets else "state_slot")
            return QueryPlan(
                ask=True,
                question_type="stale_state_patch",
                question_text=f"Provide a fresh value for `{primary_asset}` so the stale state can be refreshed before retry.",
                response_schema={
                    "type": "object",
                    "properties": {primary_asset: {"type": "string"}},
                    "required": [primary_asset],
                    "additionalProperties": False,
                },
                patch_targets={primary_asset: f"state.{primary_asset}"},
                target_scope="state",
                urgency="high",
            )
        if report.primary_label == "constraint_conflict":
            return QueryPlan(
                ask=True,
                question_type="constraint_resolution",
                question_text="Resolve the blocking constraint with a single approval decision.",
                response_schema={
                    "type": "object",
                    "properties": {"approved": {"type": "boolean"}},
                    "required": ["approved"],
                    "additionalProperties": False,
                },
                patch_targets={"approved": "policy.approved"},
                urgency="high",
            )
        if report.primary_label == "branch_disambiguation":
            properties: Dict[str, Any] = {}
            required: list[str] = []
            patch_targets: Dict[str, str] = {}
            question_text = "Choose the fallback execution branch that should run next."
            if branch_options:
                properties["branch_choice"] = {"type": "string", "enum": branch_options}
                required.append("branch_choice")
                patch_targets["branch_choice"] = "state.selected_branch"
                question_text = "Choose the execution branch that should run next."
            else:
                properties["fallback_execution_path"] = {"type": "string"}
                required.append("fallback_execution_path")
                patch_targets["fallback_execution_path"] = "step.inputs.target_path"
            return QueryPlan(
                ask=True,
                question_type="branch_choice",
                question_text=question_text,
                response_schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
                patch_targets=patch_targets,
                urgency="high",
            )
        if report.primary_label == "tool_mismatch":
            if backup_tool_id:
                return QueryPlan(
                    ask=True,
                    question_type="tool_switch",
                    question_text="The current tool binding looks wrong. Switch to the backup tool?",
                    response_schema={
                        "type": "object",
                        "properties": {"use_backup_tool": {"type": "boolean"}},
                        "required": ["use_backup_tool"],
                        "additionalProperties": False,
                    },
                    urgency="high",
                )
            properties: Dict[str, Any] = {"tool_id": {"type": "string"}}
            if alternative_tool_ids:
                properties["tool_id"]["enum"] = alternative_tool_ids
            return QueryPlan(
                ask=True,
                question_type="tool_switch",
                question_text="Provide the replacement `tool_id` for this blocked step.",
                response_schema={
                    "type": "object",
                    "properties": properties,
                    "required": ["tool_id"],
                    "additionalProperties": False,
                },
                patch_targets={"tool_id": "binding.primary_tool"},
                urgency="high",
            )
        if report.primary_label == "environment_unavailable" or (
            report.primary_label == "missing_info" and error_category == "environment_failure"
        ):
            properties: Dict[str, Any] = {
                "clear_failure_flag": {"type": "boolean"},
                "fallback_execution_path": {"type": "string"},
            }
            if backup_tool_id or alternative_tool_ids:
                properties["tool_id"] = {"type": "string"}
                if alternative_tool_ids:
                    properties["tool_id"]["enum"] = alternative_tool_ids
            return QueryPlan(
                ask=True,
                question_type="environment_resolution",
                question_text="The environment is unavailable. Provide one direct fix: `tool_id`, `fallback_execution_path`, or `clear_failure_flag`.",
                response_schema={
                    "type": "object",
                    "properties": properties,
                    "additionalProperties": False,
                },
                patch_targets={
                    "tool_id": "binding.primary_tool",
                    "fallback_execution_path": "step.inputs.target_path",
                    "clear_failure_flag": "state.force_environment_failure",
                },
                urgency="high",
            )
        return QueryPlan(ask=False, question_type="none", question_text="")
