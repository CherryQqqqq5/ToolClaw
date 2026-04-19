"""Compile successful traces into reusable skill, workflow, and policy artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
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
        f"phase1::family={family}::caps={capability_token}::fail={failure}",
        f"phase1::family={family}::fail={failure}::goal={goal}",
        f"phase1::family={family}::fail={failure}",
        f"phase1::{goal}",
    ]
    deduped: List[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def collect_required_state_slots(workflow: Workflow) -> List[str]:
    slots: List[str] = []
    for slot in workflow.metadata.get("state_slots", []):
        text = str(slot).strip()
        if text and text not in slots:
            slots.append(text)
    for step in workflow.execution_plan:
        for slot in step.metadata.get("required_state_slots", []):
            text = str(slot).strip()
            if text and text not in slots:
                slots.append(text)
    return slots


_PAIR_SUFFIX_RE = re.compile(r"__pair\d+$")
_NUMERIC_SUFFIX_RE = re.compile(r"_\d+$")


def _semantic_reuse_family(value: Any) -> str:
    family = str(value or "").strip()
    if not family:
        return ""
    family = _PAIR_SUFFIX_RE.sub("", family)
    family = _NUMERIC_SUFFIX_RE.sub("", family)
    return family


class SWPCCompiler:
    @staticmethod
    def _signature_metadata(workflow: Workflow) -> tuple[str, List[str]]:
        task_family = workflow.metadata.get("task_family")
        failure_context = workflow.metadata.get("failure_type") or workflow.metadata.get("scenario")
        capability_skeleton = [step.capability_id for step in workflow.execution_plan]
        signatures = build_task_signature_candidates(
            user_goal=workflow.task.user_goal,
            task_family=str(task_family) if task_family else None,
            capability_skeleton=capability_skeleton,
            failure_context=str(failure_context) if failure_context else None,
        )
        primary = signatures[0]
        aliases = signatures[1:]
        return primary, aliases

    @staticmethod
    def _serialize_policy_rule(rule: Any) -> Dict[str, Any]:
        merged = dict(rule.metadata)
        merged.update({"trigger": rule.trigger, "action": rule.action})
        return merged

    @staticmethod
    def _reuse_metadata(workflow: Workflow) -> Dict[str, Any]:
        capability_skeleton = [step.capability_id for step in workflow.execution_plan]
        failure_context = str(
            workflow.metadata.get("failure_type")
            or workflow.metadata.get("scenario")
            or "none"
        ).strip()
        task_family = str(workflow.metadata.get("task_family") or "t0_general").strip()
        reuse_family_id = str(workflow.metadata.get("reuse_family_id") or "").strip()
        return {
            "source_task_id": str(workflow.task.task_id or "").strip(),
            "task_family": task_family or "t0_general",
            "failure_context": failure_context or "none",
            "capability_skeleton": capability_skeleton,
            "required_state_slots": collect_required_state_slots(workflow),
            "reuse_family_id": reuse_family_id,
            "semantic_reuse_family": _semantic_reuse_family(reuse_family_id),
        }

    def compile_from_trace(
        self,
        workflow: Workflow,
        trace: Trace,
        final_state: Dict[str, Any],
    ) -> CompiledArtifacts:
        compile_gate = self.evaluate_compile_gate(workflow=workflow, trace=trace)
        if not compile_gate["allow_compile"]:
            return CompiledArtifacts(
                metadata={
                    "trace_id": trace.run_id,
                    "compile_gate": compile_gate,
                }
            )
        signature = self.derive_task_signature(workflow)
        workflow_snippet = self.compile_workflow(workflow, trace, quality_score=compile_gate["quality_score"], compile_gate=compile_gate)
        skill_hint = self.compile_skill(workflow, final_state, quality_score=compile_gate["quality_score"], compile_gate=compile_gate)
        policy_snippet = self.compile_policy(workflow, quality_score=compile_gate["quality_score"], compile_gate=compile_gate)

        return CompiledArtifacts(
            workflow_snippets=[workflow_snippet],
            skill_hints=[skill_hint],
            policy_snippets=[policy_snippet],
            metadata={"trace_id": trace.run_id, "compile_gate": compile_gate, "task_signature": signature},
        )

    def compile_workflow(
        self,
        workflow: Workflow,
        trace: Trace,
        *,
        quality_score: float,
        compile_gate: Dict[str, Any],
    ) -> WorkflowSnippet:
        primary_signature, alias_signatures = self._signature_metadata(workflow)
        reuse_metadata = self._reuse_metadata(workflow)
        return WorkflowSnippet(
            snippet_id=f"ws_{workflow.workflow_id}",
            task_signature=primary_signature,
            capability_skeleton=[step.capability_id for step in workflow.execution_plan],
            recommended_bindings={binding.capability_id: binding.primary_tool for binding in workflow.tool_bindings},
            recommended_inputs={step.capability_id: dict(step.inputs) for step in workflow.execution_plan},
            applicability_conditions=["phase1_training_free"],
            quality_score=quality_score,
            metadata={
                "final_success": trace.metrics.success,
                "compile_gate": dict(compile_gate),
                "task_signature_aliases": alias_signatures,
                "promotion_status": compile_gate.get("promotion_status"),
                "promotion_mode": compile_gate.get("promotion_mode"),
                "verifier_backed": bool(compile_gate.get("verifier_backed")),
                "promotion_version": "phase1.v1",
                **reuse_metadata,
            },
        )

    def compile_skill(
        self,
        workflow: Workflow,
        final_state: Dict[str, Any],
        *,
        quality_score: float,
        compile_gate: Dict[str, Any],
    ) -> SkillHint:
        primary_signature, alias_signatures = self._signature_metadata(workflow)
        reuse_metadata = self._reuse_metadata(workflow)
        return SkillHint(
            hint_id=f"sh_{workflow.workflow_id}",
            task_signature=primary_signature,
            step_pattern=[step.step_id for step in workflow.execution_plan],
            trigger_conditions=["phase1_training_free"],
            quality_score=quality_score if final_state else min(quality_score, 0.6),
            metadata={
                "state_keys": sorted(final_state.keys()),
                "compile_gate": dict(compile_gate),
                "task_signature_aliases": alias_signatures,
                "promotion_status": compile_gate.get("promotion_status"),
                "promotion_mode": compile_gate.get("promotion_mode"),
                "verifier_backed": bool(compile_gate.get("verifier_backed")),
                "promotion_version": "phase1.v1",
                **reuse_metadata,
            },
        )

    def compile_policy(
        self,
        workflow: Workflow,
        *,
        quality_score: float,
        compile_gate: Dict[str, Any],
    ) -> PolicySnippet:
        primary_signature, alias_signatures = self._signature_metadata(workflow)
        reuse_metadata = self._reuse_metadata(workflow)
        return PolicySnippet(
            policy_id=f"ps_{workflow.workflow_id}",
            task_signature=primary_signature,
            stop_rules=list(workflow.policy.stop_rules),
            approval_rules=[self._serialize_policy_rule(rule) for rule in workflow.policy.approval_rules],
            recovery_rules=[self._serialize_policy_rule(rule) for rule in workflow.policy.recovery_rules],
            quality_score=max(0.5, min(quality_score, 0.9)),
            metadata={
                "compile_gate": dict(compile_gate),
                "task_signature_aliases": alias_signatures,
                "promotion_status": compile_gate.get("promotion_status"),
                "promotion_mode": compile_gate.get("promotion_mode"),
                "verifier_backed": bool(compile_gate.get("verifier_backed")),
                "promotion_version": "phase1.v1",
                **reuse_metadata,
            },
        )

    def derive_task_signature(
        self,
        workflow: Workflow,
    ) -> str:
        primary_signature, _ = self._signature_metadata(workflow)
        return primary_signature

    @staticmethod
    def score_artifact_quality(success: bool | None) -> float:
        return 1.0 if success else 0.4

    def evaluate_compile_gate(
        self,
        *,
        workflow: Workflow,
        trace: Trace,
    ) -> Dict[str, Any]:
        benchmark_hints = dict(workflow.metadata.get("benchmark_hints", {}))
        objective = dict(benchmark_hints.get("overplanning_objective", {}))
        if not objective:
            objective = dict(workflow.capability_graph.metadata.get("overplanning_objective", {}))

        tool_calls = int(getattr(trace.metrics, "tool_calls", 0) or 0)
        user_queries = int(getattr(trace.metrics, "user_queries", 0) or 0)
        repair_actions = int(getattr(trace.metrics, "repair_actions", 0) or 0)
        success = bool(getattr(trace.metrics, "success", False))
        expected_tool_calls = self._coerce_positive_int(benchmark_hints.get("ideal_tool_calls")) or max(len(workflow.execution_plan), 1)
        expected_turns = self._coerce_non_negative_int(benchmark_hints.get("ideal_turn_count"))
        if expected_turns is None:
            expected_turns = 1 if any(step.requires_user_confirmation for step in workflow.execution_plan) else 0

        tool_efficiency = self._efficiency_score(tool_calls, expected_tool_calls, step_penalty=0.15)
        turn_efficiency = self._efficiency_score(user_queries, expected_turns, step_penalty=0.2)
        repair_budget = max(1, expected_tool_calls - 1)
        repair_score = max(0.0, 1.0 - 0.25 * max(repair_actions - repair_budget, 0))
        quality_score = round((tool_efficiency + turn_efficiency + repair_score) / 3.0, 4)
        objective_consistent = self._workflow_matches_objective(workflow, objective)
        objective_active = bool(objective.get("active"))
        min_quality_score = 0.55 if objective_active else 0.35
        contamination_guard = self._contamination_guard(workflow=workflow, benchmark_hints=benchmark_hints)
        verifier_backed = bool(
            workflow.metadata.get("verifier_backed")
            or workflow.metadata.get("verifier_passed")
            or benchmark_hints.get("verifier_backed")
            or benchmark_hints.get("verifier_passed")
        )
        allow_compile = (
            success
            and objective_consistent
            and quality_score >= min_quality_score
            and not contamination_guard["blocked"]
        )
        promotion_status = "promoted" if allow_compile else "rejected"
        rejection_reasons: List[str] = []
        if not success:
            rejection_reasons.append("trace_unsuccessful")
        if not objective_consistent:
            rejection_reasons.append("objective_inconsistent")
        if quality_score < min_quality_score:
            rejection_reasons.append("quality_below_threshold")
        if contamination_guard["blocked"]:
            rejection_reasons.append(str(contamination_guard["reason"]))

        return {
            "allow_compile": allow_compile,
            "objective_active": objective_active,
            "objective_consistent": objective_consistent,
            "quality_score": quality_score,
            "min_quality_score": min_quality_score,
            "tool_efficiency": tool_efficiency,
            "turn_efficiency": turn_efficiency,
            "repair_score": repair_score,
            "tool_calls": tool_calls,
            "user_queries": user_queries,
            "repair_actions": repair_actions,
            "expected_tool_calls": expected_tool_calls,
            "expected_turns": expected_turns,
            "promotion_status": promotion_status,
            "promotion_mode": "verifier_backed" if verifier_backed else "heuristic_only",
            "verifier_backed": verifier_backed,
            "rejection_reasons": rejection_reasons,
            "contamination_guard": contamination_guard,
        }

    @staticmethod
    def _contamination_guard(*, workflow: Workflow, benchmark_hints: Dict[str, Any]) -> Dict[str, Any]:
        workflow_guard = workflow.metadata.get("contamination_guard", {})
        guard = dict(workflow_guard) if isinstance(workflow_guard, dict) else {}
        split = str(
            guard.get("reuse_split")
            or workflow.metadata.get("reuse_split")
            or benchmark_hints.get("reuse_split")
            or workflow.metadata.get("split")
            or benchmark_hints.get("split")
            or ""
        ).strip().lower()
        allow_compile = guard.get("allow_compile")
        blocked_reason = ""
        if allow_compile is False:
            blocked_reason = "contamination_guard_blocked"
        elif split in {"eval", "heldout", "held_out", "test"}:
            blocked_reason = f"heldout_split:{split}"
        return {
            "blocked": bool(blocked_reason),
            "reason": blocked_reason or None,
            "reuse_split": split or None,
        }

    @staticmethod
    def _workflow_matches_objective(workflow: Workflow, objective: Dict[str, Any]) -> bool:
        if not objective.get("active"):
            return True
        preferred_capabilities = [str(item) for item in objective.get("preferred_capabilities", []) if str(item)]
        allowed_tools = {str(item) for item in objective.get("allowed_tools", []) if str(item)}
        max_steps = objective.get("max_steps")

        capability_ids = [step.capability_id for step in workflow.execution_plan]
        tool_ids = [step.tool_id for step in workflow.execution_plan if step.tool_id]
        if preferred_capabilities:
            allowed_capabilities = set(preferred_capabilities)
            if any(capability_id not in allowed_capabilities for capability_id in capability_ids):
                return False
            rank = {capability_id: index for index, capability_id in enumerate(preferred_capabilities)}
            ordered_ranks = [rank[capability_id] for capability_id in capability_ids if capability_id in rank]
            if ordered_ranks != sorted(ordered_ranks):
                return False
        if allowed_tools and any(tool_id not in allowed_tools for tool_id in tool_ids):
            return False
        if isinstance(max_steps, int) and max_steps > 0 and len(workflow.execution_plan) > max_steps:
            return False
        return True

    @staticmethod
    def _efficiency_score(actual: int, expected: int, *, step_penalty: float) -> float:
        baseline = max(expected, 0)
        if baseline <= 0:
            baseline = 0
        overage = max(int(actual) - baseline, 0)
        return max(0.0, 1.0 - step_penalty * overage)

    @staticmethod
    def _coerce_positive_int(value: Any) -> int | None:
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            return None
        return coerced if coerced > 0 else None

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> int | None:
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            return None
        return coerced if coerced >= 0 else None
