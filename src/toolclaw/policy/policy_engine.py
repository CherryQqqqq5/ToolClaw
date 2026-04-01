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
        if risk.requires_confirmation and not already_approved:
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
        return PolicyDecision(
            allow=True,
            create_checkpoint=step.checkpoint,
            reason="post_step_update",
            cost=cost,
            state_patch={"__budget_spent__": spent},
            policy_events=[{"type": "budget_update", "spent": spent}],
        )

    def apply_policy_patch(self, state_values: Dict[str, Any], patch: Dict[str, Any]) -> None:
        state_values.update(patch)
