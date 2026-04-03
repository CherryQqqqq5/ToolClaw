"""Compile successful traces into reusable skill, workflow, and policy artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from toolclaw.schemas.trace import Trace
from toolclaw.schemas.workflow import Workflow


@dataclass
class WorkflowSnippet:
    snippet_id: str
    task_signature: str
    capability_skeleton: List[str]
    recommended_bindings: Dict[str, str] = field(default_factory=dict)
    version: int = 1
    applicability_conditions: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillHint:
    hint_id: str
    task_signature: str
    step_pattern: List[str]
    trigger_conditions: List[str] = field(default_factory=list)
    version: int = 1
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicySnippet:
    policy_id: str
    task_signature: str
    stop_rules: List[str] = field(default_factory=list)
    approval_rules: List[Dict[str, Any]] = field(default_factory=list)
    recovery_rules: List[Dict[str, Any]] = field(default_factory=list)
    version: int = 1
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompiledArtifacts:
    workflow_snippets: List[WorkflowSnippet] = field(default_factory=list)
    skill_hints: List[SkillHint] = field(default_factory=list)
    policy_snippets: List[PolicySnippet] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SWPCCompiler:
    @staticmethod
    def _serialize_policy_rule(rule: Any) -> Dict[str, Any]:
        merged = dict(rule.metadata)
        merged.update({"trigger": rule.trigger, "action": rule.action})
        return merged

    def compile_from_trace(
        self,
        workflow: Workflow,
        trace: Trace,
        final_state: Dict[str, Any],
    ) -> CompiledArtifacts:
        signature = self.derive_task_signature(workflow)
        workflow_snippet = self.compile_workflow(workflow, trace)
        skill_hint = self.compile_skill(workflow, final_state)
        policy_snippet = self.compile_policy(workflow)

        return CompiledArtifacts(
            workflow_snippets=[workflow_snippet],
            skill_hints=[skill_hint],
            policy_snippets=[policy_snippet],
            metadata={"trace_id": trace.run_id},
        )

    def compile_workflow(self, workflow: Workflow, trace: Trace) -> WorkflowSnippet:
        return WorkflowSnippet(
            snippet_id=f"ws_{workflow.workflow_id}",
            task_signature=self.derive_task_signature(workflow),
            capability_skeleton=[step.capability_id for step in workflow.execution_plan],
            recommended_bindings={binding.capability_id: binding.primary_tool for binding in workflow.tool_bindings},
            applicability_conditions=["phase1_training_free"],
            quality_score=self.score_artifact_quality(trace.metrics.success),
            metadata={"final_success": trace.metrics.success},
        )

    def compile_skill(self, workflow: Workflow, final_state: Dict[str, Any]) -> SkillHint:
        return SkillHint(
            hint_id=f"sh_{workflow.workflow_id}",
            task_signature=self.derive_task_signature(workflow),
            step_pattern=[step.step_id for step in workflow.execution_plan],
            trigger_conditions=["phase1_training_free"],
            quality_score=1.0 if final_state else 0.6,
            metadata={"state_keys": sorted(final_state.keys())},
        )

    def compile_policy(self, workflow: Workflow) -> PolicySnippet:
        return PolicySnippet(
            policy_id=f"ps_{workflow.workflow_id}",
            task_signature=self.derive_task_signature(workflow),
            stop_rules=list(workflow.policy.stop_rules),
            approval_rules=[self._serialize_policy_rule(rule) for rule in workflow.policy.approval_rules],
            recovery_rules=[self._serialize_policy_rule(rule) for rule in workflow.policy.recovery_rules],
            quality_score=0.8,
        )

    def derive_task_signature(
        self,
        workflow: Workflow,
    ) -> str:
        goal = workflow.task.user_goal.lower().strip().replace(" ", "_")
        return f"phase1::{goal}"

    @staticmethod
    def score_artifact_quality(success: bool | None) -> float:
        return 1.0 if success else 0.4
