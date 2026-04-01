"""Heuristic risk scoring used to decide whether a step requires confirmation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from toolclaw.schemas.workflow import TaskConstraints, Workflow, WorkflowStep


@dataclass
class RiskRule:
    rule_id: str
    trigger_keyword: str
    score_delta: float
    rationale: str


@dataclass
class RiskAssessment:
    score: float
    level: str
    requires_confirmation: bool = False
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskController:
    def __init__(self) -> None:
        self.rules = [
            RiskRule("risk_write", "write", 0.25, "write-like actions can modify external state"),
            RiskRule("risk_shell", "shell", 0.45, "shell execution can have broad side effects"),
            RiskRule("risk_delete", "delete", 0.55, "delete-like actions are destructive"),
        ]

    def score_step_risk(
        self,
        step: WorkflowStep,
        workflow: Optional[Workflow] = None,
    ) -> RiskAssessment:
        score = 0.1
        reasons = []
        haystacks = [step.capability_id.lower(), (step.tool_id or "").lower(), " ".join(step.metadata.keys()).lower()]
        for rule in self.rules:
            if any(rule.trigger_keyword in haystack for haystack in haystacks):
                score += rule.score_delta
                reasons.append(rule.rationale)

        task_constraints: TaskConstraints = workflow.task.constraints if workflow else TaskConstraints()
        if task_constraints.risk_level.value == "high":
            score += 0.25
            reasons.append("task risk level is high")
        elif task_constraints.risk_level.value == "medium":
            score += 0.1

        score = min(score, 1.0)
        level = "low" if score < 0.35 else "medium" if score < 0.7 else "high"
        requires_confirmation = (
            task_constraints.requires_user_approval
            or step.requires_user_confirmation
            or bool(step.metadata.get("requires_approval"))
            or level == "high"
        )
        return RiskAssessment(
            score=score,
            level=level,
            requires_confirmation=requires_confirmation,
            rationale="; ".join(reasons) if reasons else "default phase-1 risk scoring",
            metadata={"step_id": step.step_id},
        )
