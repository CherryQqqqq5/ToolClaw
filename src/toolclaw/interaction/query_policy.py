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
        missing_input_keys = [str(item) for item in report.metadata.get("missing_input_keys", []) if str(item)]
        missing_assets = [str(item) for item in report.metadata.get("missing_assets", []) if str(item)]
        stale_assets = [str(item) for item in report.metadata.get("stale_assets", []) if str(item)]
        error_category = str(report.metadata.get("error_category") or "unknown")
        backup_tool_id = str(report.metadata.get("backup_tool_id") or "")
        alternative_tool_ids = [
            str(item) for item in report.metadata.get("alternative_tool_ids", []) if str(item)
        ]
        branch_options = [str(item) for item in report.metadata.get("branch_options", []) if str(item)]
        remaining_user_turns = report.metadata.get("remaining_user_turns")
        last_turn = remaining_user_turns is not None and int(remaining_user_turns) <= 1
        if report.primary_label in {"approval_needed", "policy_approval"}:
            base_plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            repair_plan = None
            if self._should_compound_approval_with_repair(
                missing_input_keys=missing_input_keys,
                missing_assets=missing_assets,
                stale_assets=stale_assets,
                error_category=error_category,
                branch_options=branch_options,
            ):
                repair_plan = self._repair_component_plan(
                    missing_input_keys=missing_input_keys,
                    missing_assets=missing_assets,
                    stale_assets=stale_assets,
                    error_category=error_category,
                    backup_tool_id=backup_tool_id,
                    alternative_tool_ids=alternative_tool_ids,
                    branch_options=branch_options,
                )
            return self._compound_with_approval(base_plan=repair_plan or base_plan, last_turn=last_turn)
        plan: QueryPlan
        if report.primary_label in {"missing_info", "missing_asset"}:
            if missing_input_keys == ["target_path"] or missing_assets == ["target_path"]:
                plan = QueryPlan(
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
                    urgency="critical" if last_turn else "high",
                )
                return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
            if missing_input_keys:
                properties = {key: {"type": "string"} for key in missing_input_keys}
                plan = QueryPlan(
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
                    urgency="critical" if last_turn else "high",
                )
                return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
            if missing_assets:
                primary_asset = missing_assets[0]
                plan = QueryPlan(
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
                    urgency="critical" if last_turn else "high",
                )
                return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        if report.primary_label == "stale_state":
            primary_asset = stale_assets[0] if stale_assets else (missing_assets[0] if missing_assets else "state_slot")
            plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        if report.primary_label == "constraint_conflict":
            plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        if report.primary_label == "branch_disambiguation":
            properties: Dict[str, Any] = {}
            required: list[str] = []
            patch_targets: Dict[str, str] = {}
            if not branch_options:
                plan = self._tool_or_asset_hint_query(
                    backup_tool_id=backup_tool_id,
                    alternative_tool_ids=alternative_tool_ids,
                    error_category=error_category,
                    last_turn=last_turn,
                )
                return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
            question_text = "Choose the fallback execution branch that should run next."
            if branch_options:
                properties["branch_choice"] = {"type": "string", "enum": branch_options}
                required.append("branch_choice")
                patch_targets["branch_choice"] = "state.selected_branch"
                question_text = "Choose the execution branch that should run next."
            plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        if report.primary_label == "execution_guidance":
            plan = self._tool_or_asset_hint_query(
                backup_tool_id=backup_tool_id,
                alternative_tool_ids=alternative_tool_ids,
                error_category=error_category,
                last_turn=last_turn,
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        if report.primary_label == "tool_mismatch":
            if backup_tool_id:
                plan = QueryPlan(
                    ask=True,
                    question_type="tool_switch",
                    question_text="The current tool binding looks wrong. Switch to the backup tool?",
                    response_schema={
                        "type": "object",
                        "properties": {"use_backup_tool": {"type": "boolean"}},
                        "required": ["use_backup_tool"],
                        "additionalProperties": False,
                    },
                    urgency="critical" if last_turn else "high",
                )
                return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
            properties: Dict[str, Any] = {"tool_id": {"type": "string"}}
            if alternative_tool_ids:
                properties["tool_id"]["enum"] = alternative_tool_ids
            plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
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
            plan = QueryPlan(
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
                urgency="critical" if last_turn else "high",
            )
            return self._compound_with_approval(base_plan=plan, last_turn=last_turn) if self._approval_required(report) else plan
        return QueryPlan(ask=False, question_type="none", question_text="")

    @staticmethod
    def _approval_required(report: UncertaintyReport) -> bool:
        if report.primary_label in {"approval_needed", "policy_approval"}:
            return True
        return bool(report.metadata.get("constraint_requires_approval"))

    def _repair_component_plan(
        self,
        *,
        missing_input_keys: list[str],
        missing_assets: list[str],
        stale_assets: list[str],
        error_category: str,
        backup_tool_id: str,
        alternative_tool_ids: list[str],
        branch_options: list[str],
    ) -> QueryPlan | None:
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
        if stale_assets:
            primary_asset = stale_assets[0]
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
        if branch_options:
            return QueryPlan(
                ask=True,
                question_type="branch_choice",
                question_text="Choose the execution branch that should run next.",
                response_schema={
                    "type": "object",
                    "properties": {"branch_choice": {"type": "string", "enum": branch_options}},
                    "required": ["branch_choice"],
                    "additionalProperties": False,
                },
                patch_targets={"branch_choice": "state.selected_branch"},
                urgency="high",
            )
        if error_category == "environment_failure":
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
        if backup_tool_id or alternative_tool_ids:
            return self._tool_or_asset_hint_query(
                backup_tool_id=backup_tool_id,
                alternative_tool_ids=alternative_tool_ids,
                error_category=error_category,
            )
        return None

    @staticmethod
    def _should_compound_approval_with_repair(
        *,
        missing_input_keys: list[str],
        missing_assets: list[str],
        stale_assets: list[str],
        error_category: str,
        branch_options: list[str],
    ) -> bool:
        if missing_input_keys or missing_assets or stale_assets or branch_options:
            return True
        return error_category == "environment_failure"

    @staticmethod
    def _compound_with_approval(base_plan: QueryPlan, *, last_turn: bool = False) -> QueryPlan:
        if not base_plan.ask:
            return base_plan
        properties = dict(base_plan.response_schema.get("properties", {}))
        properties["approved"] = {"type": "boolean"}
        required = list(base_plan.response_schema.get("required", []))
        if "approved" not in required:
            required = ["approved", *required]
        patch_targets = dict(base_plan.patch_targets)
        patch_targets["approved"] = "policy.approved"
        question_text = base_plan.question_text
        if base_plan.question_type != "approval":
            question_text = f"Approve this blocked action and, in the same reply, {base_plan.question_text[:1].lower()}{base_plan.question_text[1:]}"
            if last_turn:
                question_text = f"{question_text} This is the last available user turn, so respond with the approval and fix together."
        return QueryPlan(
            ask=True,
            question_type="approval_and_patch" if base_plan.question_type != "approval" else "approval",
            question_text=question_text,
            response_schema={
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
            patch_targets=patch_targets,
            target_scope=f"policy_and_{base_plan.target_scope}",
            urgency="critical" if last_turn else "high",
        )

    @staticmethod
    def _tool_or_asset_hint_query(
        *,
        backup_tool_id: str,
        alternative_tool_ids: list[str],
        error_category: str,
        last_turn: bool = False,
    ) -> QueryPlan:
        properties: Dict[str, Any] = {
            "fallback_execution_path": {"type": "string"},
            "input_patch": {"type": "object"},
            "clear_failure_flag": {"type": "boolean"},
        }
        if backup_tool_id or alternative_tool_ids:
            properties["tool_id"] = {"type": "string"}
            if alternative_tool_ids:
                properties["tool_id"]["enum"] = alternative_tool_ids
        question_text = "The current path is blocked. Provide one direct fix: `tool_id`, `fallback_execution_path`, or `input_patch`."
        if error_category == "environment_failure":
            question_text = "The environment is blocked. Provide one direct fix: `tool_id`, `fallback_execution_path`, or `input_patch`."
        return QueryPlan(
            ask=True,
            question_type="tool_or_asset_hint",
            question_text=question_text,
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
            urgency="critical" if last_turn else "high",
        )
