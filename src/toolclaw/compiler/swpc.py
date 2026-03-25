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
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillHint:
    hint_id: str
    task_signature: str
    step_pattern: List[str]
    trigger_conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicySnippet:
    policy_id: str
    task_signature: str
    stop_rules: List[str] = field(default_factory=list)
    approval_rules: List[Dict[str, Any]] = field(default_factory=list)
    recovery_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompiledArtifacts:
    workflow_snippets: List[WorkflowSnippet] = field(default_factory=list)
    skill_hints: List[SkillHint] = field(default_factory=list)
    policy_snippets: List[PolicySnippet] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SWPCCompiler:
    def compile_from_trace(
        self,
        workflow: Workflow,
        trace: Trace,
        final_state: Dict[str, Any],
    ) -> CompiledArtifacts:
        signature = self.derive_task_signature(workflow)
        workflow_snippet = WorkflowSnippet(
            snippet_id=f"ws_{workflow.workflow_id}",
            task_signature=signature,
            capability_skeleton=[step.capability_id for step in workflow.execution_plan],
            recommended_bindings={binding.capability_id: binding.primary_tool for binding in workflow.tool_bindings},
            metadata={"final_success": trace.metrics.success},
        )

        skill_hint = SkillHint(
            hint_id=f"sh_{workflow.workflow_id}",
            task_signature=signature,
            step_pattern=[step.step_id for step in workflow.execution_plan],
            trigger_conditions=["phase1_training_free"],
            metadata={"state_keys": sorted(final_state.keys())},
        )

        policy_snippet = PolicySnippet(
            policy_id=f"ps_{workflow.workflow_id}",
            task_signature=signature,
            stop_rules=list(workflow.policy.stop_rules),
            approval_rules=[rule.metadata | {"trigger": rule.trigger, "action": rule.action} for rule in workflow.policy.approval_rules],
            recovery_rules=[rule.metadata | {"trigger": rule.trigger, "action": rule.action} for rule in workflow.policy.recovery_rules],
        )

        return CompiledArtifacts(
            workflow_snippets=[workflow_snippet],
            skill_hints=[skill_hint],
            policy_snippets=[policy_snippet],
            metadata={"trace_id": trace.run_id},
        )

    def derive_task_signature(
        self,
        workflow: Workflow,
    ) -> str:
        goal = workflow.task.user_goal.lower().strip().replace(" ", "_")
        return f"phase1::{goal}"
