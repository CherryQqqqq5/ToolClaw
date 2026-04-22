"""Execution-time policy checks that combine risk, budget, and approval requirements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from toolclaw.policy.budget_guard import BudgetDecision, BudgetGuard, CostEstimate
from toolclaw.policy.risk_control import RiskAssessment, RiskController
from toolclaw.schemas.workflow import Workflow, WorkflowStep


@dataclass
class PolicyDecision:
    allow: bool
    require_confirmation: bool = False
    create_checkpoint: bool = False
    abort: bool = False
    reason: str = ""
    risk: Optional[RiskAssessment] = None
    cost: Optional[CostEstimate] = None
    budget: Optional[BudgetDecision] = None
    state_patch: Dict[str, Any] = field(default_factory=dict)
    policy_events: List[Dict[str, Any]] = field(default_factory=list)


class PolicyEngine:
    def __init__(
        self,
        risk_controller: Optional[RiskController] = None,
        budget_guard: Optional[BudgetGuard] = None,
    ) -> None:
        self.risk_controller = risk_controller or RiskController()
        self.budget_guard = budget_guard or BudgetGuard()

    def evaluate_before_step(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        state_values: Dict[str, Any],
    ) -> PolicyDecision:
        risk = self.risk_controller.score_step_risk(step, workflow)
        cost = self.budget_guard.estimate_tool_cost(step)
        spent = float(state_values.get("__budget_spent__", 0.0))
        budget = self.budget_guard.check_budget(workflow, spent, cost)

        forbidden_action = self._matches_forbidden_action(step=step, workflow=workflow)
        if forbidden_action is not None:
            return PolicyDecision(
                allow=False,
                abort=True,
                reason="forbidden_action",
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "forbidden_action", "action": forbidden_action}],
            )

        missing_permission = self._missing_permission(step=step, workflow=workflow)
        if missing_permission is not None:
            return PolicyDecision(
                allow=False,
                abort=True,
                reason="permission_denied",
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "permission", "permission": missing_permission}],
            )

        if self._would_exceed_time_limit(workflow=workflow, state_values=state_values, cost=cost):
            return PolicyDecision(
                allow=False,
                abort=True,
                reason="time_limit_exceeded",
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "time_limit", "required_latency_ms": cost.latency_ms}],
            )

        discrete_budget_violation = self._discrete_budget_violation(workflow=workflow, state_values=state_values)
        if discrete_budget_violation is not None:
            return PolicyDecision(
                allow=False,
                abort=True,
                reason=discrete_budget_violation,
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "budget", "reason": discrete_budget_violation}],
            )

        if not budget.allow:
            return PolicyDecision(
                allow=False,
                abort=True,
                reason=budget.reason,
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "budget", "reason": budget.reason}],
            )

        already_approved = step.step_id in state_values.get("__approved_steps__", [])
        requires_confirmation = bool(risk.requires_confirmation and not already_approved)
        approval_scope = str(workflow.metadata.get("approval_scope") or "").strip().lower()
        approval_target_step = str(workflow.metadata.get("approval_target_step") or "").strip()
        if requires_confirmation and approval_scope == "failure_step" and approval_target_step:
            requires_confirmation = step.step_id == approval_target_step
        if requires_confirmation:
            return PolicyDecision(
                allow=False,
                require_confirmation=True,
                create_checkpoint=True,
                reason="approval_required",
                risk=risk,
                cost=cost,
                budget=budget,
                policy_events=[{"type": "approval", "reason": risk.rationale}],
            )

        return PolicyDecision(
            allow=True,
            create_checkpoint=step.checkpoint,
            reason="allowed",
            risk=risk,
            cost=cost,
            budget=budget,
            policy_events=[{"type": "allow", "risk_level": risk.level}],
        )

    def evaluate_after_step(
        self,
        step: WorkflowStep,
        workflow: Workflow,
        state_values: Dict[str, Any],
    ) -> PolicyDecision:
        cost = self.budget_guard.estimate_tool_cost(step)
        spent = self.budget_guard.consume_budget(float(state_values.get("__budget_spent__", 0.0)), cost)
        time_spent_ms = float(state_values.get("__time_spent_ms__", 0.0)) + float(cost.latency_ms)
        tool_calls = int(state_values.get("__tool_calls__", 0))
        constraints = workflow.task.constraints
        remaining_budgets = {
            "tool_calls": (constraints.max_tool_calls - tool_calls) if constraints.max_tool_calls is not None else None,
            "user_turns": (
                constraints.max_user_turns - int(state_values.get("__user_turns__", 0))
            )
            if constraints.max_user_turns is not None
            else None,
            "repair_attempts": (
                constraints.max_repair_attempts - int(state_values.get("__repair_attempts__", 0))
            )
            if constraints.max_repair_attempts is not None
            else None,
            "recovery_budget": (
                float(constraints.max_recovery_budget) - float(state_values.get("__recovery_budget_spent__", 0.0))
            )
            if constraints.max_recovery_budget is not None
            else None,
        }
        return PolicyDecision(
            allow=True,
            create_checkpoint=step.checkpoint,
            reason="post_step_update",
            cost=cost,
            state_patch={
                "__budget_spent__": spent,
                "__time_spent_ms__": time_spent_ms,
                "__remaining_budgets__": remaining_budgets,
            },
            policy_events=[
                {"type": "budget_update", "spent": spent},
                {"type": "time_update", "spent_ms": time_spent_ms},
                {"type": "remaining_budgets", "remaining": remaining_budgets},
            ],
        )

    def apply_policy_patch(self, state_values: Dict[str, Any], patch: Dict[str, Any]) -> None:
        state_values.update(patch)

    @staticmethod
    def _matches_forbidden_action(step: WorkflowStep, workflow: Workflow) -> Optional[str]:
        haystacks = [
            (step.tool_id or "").lower(),
            step.capability_id.lower(),
            step.action_type.value.lower(),
            " ".join(step.metadata.keys()).lower(),
        ]
        for forbidden in workflow.task.constraints.forbidden_actions:
            token = str(forbidden).strip().lower()
            if token and any(token in haystack for haystack in haystacks):
                return token
        return None

    @staticmethod
    def _missing_permission(step: WorkflowStep, workflow: Workflow) -> Optional[str]:
        permissions = workflow.context.environment.permissions
        haystack = " ".join(
            [
                step.capability_id.lower(),
                (step.tool_id or "").lower(),
                step.expected_output or "",
            ]
        ).lower()
        if any(keyword in haystack for keyword in {"write", "save", "output", "report"}) and not permissions.filesystem_write:
            return "filesystem_write"
        if any(keyword in haystack for keyword in {"search", "retrieve", "web", "download"}) and not permissions.network:
            return "network"
        if "api" in haystack and not permissions.external_api:
            return "external_api"
        return None

    @staticmethod
    def _would_exceed_time_limit(
        workflow: Workflow,
        state_values: Dict[str, Any],
        cost: CostEstimate,
    ) -> bool:
        limit = workflow.task.constraints.time_limit
        if limit is None:
            return False
        spent_ms = float(state_values.get("__time_spent_ms__", 0.0))
        return spent_ms + float(cost.latency_ms) > float(limit)

    @staticmethod
    def _discrete_budget_violation(
        workflow: Workflow,
        state_values: Dict[str, Any],
    ) -> Optional[str]:
        constraints = workflow.task.constraints
        if constraints.max_tool_calls is not None and int(state_values.get("__tool_calls__", 0)) >= int(constraints.max_tool_calls):
            return "max_tool_calls_exceeded"
        if constraints.max_repair_attempts is not None and int(state_values.get("__repair_attempts__", 0)) > int(constraints.max_repair_attempts):
            return "max_repair_attempts_exceeded"
        if constraints.max_recovery_budget is not None and float(state_values.get("__recovery_budget_spent__", 0.0)) > float(constraints.max_recovery_budget):
            return "max_recovery_budget_exceeded"
        return None
