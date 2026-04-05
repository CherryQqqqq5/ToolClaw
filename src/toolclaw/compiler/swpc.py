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
    recommended_inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
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


def _normalize_signature_token(value: Any, *, default: str = "none") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    normalized = []
    last_was_sep = False
    for char in text:
        if char.isalnum():
            normalized.append(char)
            last_was_sep = False
        else:
            if not last_was_sep:
                normalized.append("_")
                last_was_sep = True
    token = "".join(normalized).strip("_")
    return token or default


def build_task_signature_candidates(
    *,
    user_goal: str,
    task_family: str | None = None,
    capability_skeleton: List[str] | None = None,
    failure_context: str | None = None,
) -> List[str]:
    goal = _normalize_signature_token(user_goal, default="task")
    family = _normalize_signature_token(task_family, default="t0_general")
    failure = _normalize_signature_token(failure_context, default="none")
    capabilities = capability_skeleton or []
    capability_token = "+".join(_normalize_signature_token(capability, default="cap") for capability in capabilities) if capabilities else "unspecified"
    candidates = [
        f"phase1::family={family}::caps={capability_token}::fail={failure}::goal={goal}",
        f"phase1::family={family}::fail={failure}::goal={goal}",
        f"phase1::{goal}",
    ]
    deduped: List[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


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
            recommended_inputs={step.capability_id: dict(step.inputs) for step in workflow.execution_plan},
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
        task_family = workflow.metadata.get("task_family")
        failure_context = workflow.metadata.get("failure_type") or workflow.metadata.get("scenario")
        capability_skeleton = [step.capability_id for step in workflow.execution_plan]
        return build_task_signature_candidates(
            user_goal=workflow.task.user_goal,
            task_family=str(task_family) if task_family else None,
            capability_skeleton=capability_skeleton,
            failure_context=str(failure_context) if failure_context else None,
        )[0]

    @staticmethod
    def score_artifact_quality(success: bool | None) -> float:
        return 1.0 if success else 0.4
