"""Budget estimation and limit enforcement for step-level execution decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from toolclaw.schemas.workflow import Workflow, WorkflowStep


@dataclass
class CostEstimate:
    tool_calls: int = 1
    token_cost: float = 0.0
    latency_ms: int = 0
    dollar_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BudgetDecision:
    allow: bool
    budget_remaining: Optional[float]
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class BudgetGuard:
    def estimate_tool_cost(self, step: WorkflowStep) -> CostEstimate:
        tool_id = step.tool_id or ""
        dollar_cost = 0.01
        latency_ms = 100
        if "search" in tool_id:
            dollar_cost = 0.02
            latency_ms = 150
        elif "write" in tool_id:
            dollar_cost = 0.015
            latency_ms = 80
        elif "shell" in tool_id:
            dollar_cost = 0.03
            latency_ms = 200
        return CostEstimate(
            token_cost=dollar_cost * 1000,
            dollar_cost=dollar_cost,
            latency_ms=latency_ms,
            metadata={"tool_id": tool_id},
        )

    def check_budget(
        self,
        workflow: Workflow,
        spent_so_far: float,
        estimate: CostEstimate,
    ) -> BudgetDecision:
        limit = workflow.task.constraints.budget_limit
        if limit is None:
            return BudgetDecision(allow=True, budget_remaining=None, reason="no budget limit")

        remaining = limit - spent_so_far
        if remaining < estimate.dollar_cost:
            return BudgetDecision(
                allow=False,
                budget_remaining=remaining,
                reason="budget_limit_exceeded",
                metadata={"required_cost": estimate.dollar_cost},
            )

        return BudgetDecision(
            allow=True,
            budget_remaining=remaining - estimate.dollar_cost,
            reason="within_budget",
            metadata={"required_cost": estimate.dollar_cost},
        )

    def consume_budget(self, spent_so_far: float, estimate: CostEstimate) -> float:
        return spent_so_far + estimate.dollar_cost
