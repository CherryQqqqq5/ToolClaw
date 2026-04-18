"""Sequential execution runtime with policy gates, repair, rollback, and suffix replan."""

from __future__ import annotations

import concurrent.futures
import json
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Dict, Optional

from toolclaw.execution.failtax import FailTaxClassifier
from toolclaw.execution.recovery import RecoveryEngine
from toolclaw.execution.state_tracker import StateTracker
from toolclaw.policy.policy_engine import PolicyEngine
from toolclaw.schemas.error import (
    ErrorCategory,
    ErrorEvidence,
    ErrorSeverity,
    ErrorStage,
    Recoverability,
    StateContext,
    ToolClawError,
)
from toolclaw.schemas.repair import Repair
from toolclaw.schemas.trace import EventType, RunMetadata, RunMode, Trace
from toolclaw.schemas.workflow import Workflow, WorkflowStep
from toolclaw.tools.mock_tools import ToolExecutionError
from toolclaw.tools.runtime import run_tool

PLACEHOLDER_ARGUMENT_STRINGS = {
    "",
    "unknown",
    "none",
    "null",
    "n/a",
    "na",
    "not provided",
    "not_given",
    "unspecified",
}


@dataclass
class PendingInteraction:
    interaction_id: str
    run_id: str
    workflow_id: str
    step_id: str
    repair: Repair
    question: str
    expected_answer_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionOutcome:
    run_id: str
    workflow: Workflow
    success: bool
    blocked: bool = False
    pending_interaction: Optional[PendingInteraction] = None
    final_state: Dict[str, Any] = field(default_factory=dict)
    trace_path: Optional[str] = None
    last_error_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepExecutionResult:
    ok: bool
    step_id: str
    tool_id: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[ToolClawError] = None


@dataclass
class RepairApplyResult:
    applied: bool
    blocked: bool = False
    pending_interaction: Optional[PendingInteraction] = None
    workflow: Optional[Workflow] = None
    state_patch: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    followup_error: Optional[ToolClawError] = None


@dataclass
class ExecutorConfig:
    allow_repair: bool = True
    max_suffix_replans_per_signature: int = 2
    max_total_suffix_replans: int = 8
    suffix_replan_timeout_s: float = 6.0
    max_repeat_failures_per_signature: int = 32


class SequentialExecutor:
    """Minimal sequential executor for phase-1 end-to-end traces."""

    def __init__(
        self,
        recovery_engine: Optional[RecoveryEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        failtax_classifier: Optional[FailTaxClassifier] = None,
        planner: Optional["HTGPPlanner"] = None,
        config: Optional[ExecutorConfig] = None,
    ) -> None:
        self.recovery_engine = recovery_engine or RecoveryEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.failtax_classifier = failtax_classifier or FailTaxClassifier()
        self.planner = planner
        self.config = config or ExecutorConfig()

    def run(
        self,
        workflow: Workflow,
        run_id: str = "run_e2e_001",
        output_path: str = "outputs/traces/run_e2e_001.json",
        backup_tool_map: Optional[Dict[str, str]] = None,
    ) -> Trace:
        outcome = self.run_until_blocked(
            workflow=workflow,
            run_id=run_id,
            output_path=output_path,
            backup_tool_map=backup_tool_map,
        )
        if outcome.blocked:
            raise RuntimeError("run() cannot complete because interaction is required")

        trace = Trace(
            run_id=outcome.run_id,
            workflow_id=workflow.workflow_id,
            task_id=workflow.task.task_id,
        )
        payload = Path(output_path).read_text(encoding="utf-8")
        trace_dict = json.loads(payload)
        # Preserve external behavior expected by existing tests.
        trace.metrics.success = trace_dict["metrics"]["success"]
        trace.metrics.tool_calls = trace_dict["metrics"]["tool_calls"]
        trace.metrics.repair_actions = trace_dict["metrics"]["repair_actions"]
        trace.metrics.total_steps = trace_dict["metrics"]["total_steps"]
        trace.metrics.user_queries = trace_dict["metrics"].get("user_queries", 0)
        trace.metrics.clarification_precision = trace_dict["metrics"].get("clarification_precision", 0.0)
        trace.metrics.clarification_recall = trace_dict["metrics"].get("clarification_recall", 0.0)
        trace.metrics.unnecessary_question_rate = trace_dict["metrics"].get("unnecessary_question_rate", 0.0)
        trace.metrics.patch_success_rate = trace_dict["metrics"].get("patch_success_rate", 0.0)
        trace.metrics.post_answer_retry_count = trace_dict["metrics"].get("post_answer_retry_count", 0)
        trace.metrics.recovery_budget_used = trace_dict["metrics"].get("recovery_budget_used", 0.0)
        trace.metrics.budget_violation = trace_dict["metrics"].get("budget_violation", False)
        trace.metrics.budget_violation_reason = trace_dict["metrics"].get("budget_violation_reason")
        trace.events = []
        for event in trace_dict["events"]:
            trace.add_event(
                event_id=event["event_id"],
                event_type=EventType(event["event_type"]),
                actor=event["actor"],
                step_id=event.get("step_id"),
                tool_id=event.get("tool_id"),
                output=event.get("output"),
                tool_args=event.get("tool_args"),
                message=event.get("message"),
                metadata=event.get("metadata"),
            )
        trace.metrics.success = trace_dict["metrics"]["success"]
        trace.metrics.tool_calls = trace_dict["metrics"]["tool_calls"]
        trace.metrics.repair_actions = trace_dict["metrics"]["repair_actions"]
        trace.metrics.total_steps = trace_dict["metrics"]["total_steps"]
        trace.metrics.user_queries = trace_dict["metrics"].get("user_queries", 0)
        trace.metrics.clarification_precision = trace_dict["metrics"].get("clarification_precision", 0.0)
        trace.metrics.clarification_recall = trace_dict["metrics"].get("clarification_recall", 0.0)
        trace.metrics.unnecessary_question_rate = trace_dict["metrics"].get("unnecessary_question_rate", 0.0)
        trace.metrics.patch_success_rate = trace_dict["metrics"].get("patch_success_rate", 0.0)
        trace.metrics.post_answer_retry_count = trace_dict["metrics"].get("post_answer_retry_count", 0)
        trace.metrics.recovery_budget_used = trace_dict["metrics"].get("recovery_budget_used", 0.0)
        trace.metrics.budget_violation = trace_dict["metrics"].get("budget_violation", False)
        trace.metrics.budget_violation_reason = trace_dict["metrics"].get("budget_violation_reason")
        return trace

    def run_until_blocked(
        self,
        workflow: Workflow,
        run_id: str,
        output_path: str,
        start_step_index: int = 0,
        backup_tool_map: Optional[Dict[str, str]] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> ExecutionOutcome:
        backup_tool_map = backup_tool_map or {}
        tracker = StateTracker()
        if initial_state:
            tracker.state_values.update(initial_state)
        self._apply_resume_state_overrides(workflow, tracker.state_values, resumed=bool(initial_state))
        if workflow.task.user_goal and "query" not in tracker.state_values:
            tracker.state_values["query"] = workflow.task.user_goal
        trace = Trace(
            run_id=run_id,
            workflow_id=workflow.workflow_id,
            task_id=workflow.task.task_id,
            metadata=RunMetadata(model_name="phase1_executor", mode=RunMode.TOOLCLAW),
        )
        trace.metadata.task_annotations = self._task_annotations(workflow)
        trace.metadata.primary_failtax = workflow.metadata.get("primary_failtax")
        trace.metadata.failtaxes = list(workflow.metadata.get("failtaxes", []))
        trace.metadata.budget_profile = dict(workflow.metadata.get("budget_profile", {}))
        trace.metadata.budget_limits = self._budget_limits(workflow)
        trace.metadata.interaction_modules = [
            "uncertainty_detector",
            "query_policy",
            "answer_patch_compiler",
        ]
        trace.metadata.run_manifest["tool_runtime_backend"] = str(workflow.metadata.get("tool_execution_backend", "mock"))
        tracker.state_values.setdefault("__tool_calls__", 0)
        tracker.state_values.setdefault("__user_turns__", 0)
        tracker.state_values.setdefault("__repair_attempts__", 0)
        tracker.state_values.setdefault("__recovery_budget_spent__", 0.0)
        tracker.state_values.setdefault("__remaining_budgets__", self._remaining_budgets(workflow, tracker.state_values))
        self._update_trace_budget_usage(trace, tracker.state_values)

        trace.add_event(
            event_id="evt_000",
            event_type=EventType.PLAN_GENERATED,
            actor="executor",
            output={"steps": len(workflow.execution_plan)},
        )
        trace.add_event(
            event_id="evt_preflight_000",
            event_type=EventType.PREFLIGHT_CHECK,
            actor="executor",
            output=self.run_preflight(workflow).to_dict(),
        )

        idx = start_step_index
        repeat_failure_counts: Dict[str, int] = {}
        while idx < len(workflow.execution_plan):
            step = workflow.execution_plan[idx]
            tracker.set_current_step(step.step_id)
            pending = [s.step_id for s in workflow.execution_plan[idx + 1 :]]
            trace.add_snapshot(
                snapshot_id=f"snap_{idx + 1:02d}_start",
                **tracker.snapshot(pending_steps=pending),
            )
            policy_decision = self.policy_engine.evaluate_before_step(step, workflow, tracker.state_values)
            trace.add_event(
                event_id=f"evt_policy_before_{step.step_id}",
                event_type=EventType.POLICY_CHECK,
                actor="policy_engine",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output={"allow": policy_decision.allow, "reason": policy_decision.reason},
                metadata={"events": policy_decision.policy_events},
            )
            if policy_decision.require_confirmation:
                if self._auto_approve_from_simulated_policy(
                    workflow=workflow,
                    step=step,
                    trace=trace,
                    state_values=tracker.state_values,
                ):
                    continue
                tracker.state_values.setdefault("__approval_pending_steps__", [])
                if step.step_id not in tracker.state_values["__approval_pending_steps__"]:
                    tracker.state_values["__approval_pending_steps__"].append(step.step_id)
                error = ToolClawError(
                    error_id=f"err_policy_{step.step_id}",
                    run_id=run_id,
                    workflow_id=workflow.workflow_id,
                    step_id=step.step_id,
                    category=ErrorCategory.POLICY_FAILURE,
                    subtype="approval_required",
                    severity=ErrorSeverity.MEDIUM,
                    stage=ErrorStage.EXECUTION,
                    symptoms=[policy_decision.reason],
                    evidence=ErrorEvidence(tool_id=step.tool_id, raw_message=policy_decision.reason, inputs=dict(step.inputs)),
                    root_cause_hypothesis=["policy requires confirmation before executing step"],
                    state_context=StateContext(
                        active_capability=step.capability_id,
                        active_step_id=step.step_id,
                        missing_assets=[],
                        state_values=dict(tracker.state_values),
                        policy_flags={"approval_pending": True},
                    ),
                    recoverability=Recoverability(
                        recoverable=True,
                        requires_user_input=True,
                        requires_tool_switch=False,
                        requires_rollback=False,
                        requires_approval=True,
                    ),
                    failtax_label="policy_failure",
                )
                repair = self.recovery_engine.plan_repair(error)
                pending_interaction = self._materialize_pending_interaction(workflow, step, repair)
                trace.add_event(
                    event_id=f"evt_repair_triggered_{step.step_id}",
                    event_type=EventType.REPAIR_TRIGGERED,
                    actor="recovery_engine",
                    step_id=step.step_id,
                    tool_id=step.tool_id,
                    output=repair.to_dict(),
                )
                trace.add_event(
                    event_id="evt_stop_blocked",
                    event_type=EventType.STOP,
                    actor="executor",
                    output={"status": "blocked", "reason": "awaiting_user_interaction"},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    blocked=True,
                    pending_interaction=pending_interaction,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=error.error_id,
                )
            if policy_decision.abort:
                trace.add_event(
                    event_id="evt_stop_policy_abort",
                    event_type=EventType.STOP,
                    actor="executor",
                    step_id=step.step_id,
                    output={"status": "failed", "reason": policy_decision.reason},
                )
                if "exceeded" in policy_decision.reason:
                    self._mark_budget_violation(trace, policy_decision.reason)
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._update_trace_budget_usage(trace, tracker.state_values)
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=f"err_policy_{step.step_id}",
                )

            state_error = self._check_state_failure(step=step, trace=trace, state_values=tracker.state_values)
            step_result = state_error or self._execute_step(workflow=workflow, step=step, trace=trace, state_values=tracker.state_values)
            tracker.state_values["__tool_calls__"] = trace.metrics.tool_calls
            self._update_trace_budget_usage(trace, tracker.state_values)
            if step_result.ok:
                tracker.mark_completed(step.step_id)
                tracker.state_values[step.expected_output or step.step_id] = step_result.output.get("payload")
                if isinstance(step_result.output.get("state_patch"), dict):
                    tracker.state_values.update(step_result.output["state_patch"])
                self._clear_state_slot_flags(tracker.state_values, [step.expected_output or step.step_id])
                after_decision = self.policy_engine.evaluate_after_step(step, workflow, tracker.state_values)
                tracker.state_values.update(after_decision.state_patch)
                tracker.state_values["__remaining_budgets__"] = self._remaining_budgets(workflow, tracker.state_values)
                self._update_trace_budget_usage(trace, tracker.state_values)
                if step.checkpoint:
                    checkpoint_id = self._checkpoint_id_for_step(step.step_id)
                    tracker.save_checkpoint(checkpoint_id)
                    trace.add_event(
                        event_id=f"evt_checkpoint_{step.step_id}",
                        event_type=EventType.CHECKPOINT_CREATED,
                        actor="executor",
                        step_id=step.step_id,
                        output={"checkpoint_id": checkpoint_id},
                    )
                idx += 1
                continue

            if step_result.error is None:
                raise RuntimeError("step execution failed without error object")

            tracker.mark_failed(step.step_id)
            repeat_signature = "::".join(
                [
                    str(step.step_id or "unknown_step"),
                    str(step_result.error.category.value if step_result.error.category else "unknown_category"),
                    str(step_result.error.subtype or "unknown_subtype"),
                    str(step.tool_id or "unknown_tool"),
                ]
            )
            current_repeats = int(repeat_failure_counts.get(repeat_signature, 0) or 0) + 1
            repeat_failure_counts[repeat_signature] = current_repeats
            if current_repeats > int(self.config.max_repeat_failures_per_signature):
                trace.add_event(
                    event_id=f"evt_stop_repeat_failure_{step.step_id}",
                    event_type=EventType.STOP,
                    actor="executor",
                    step_id=step.step_id,
                    tool_id=step.tool_id,
                    output={"status": "failed", "reason": "repeat_failure_limit_reached"},
                    metadata={
                        "repeat_signature": repeat_signature,
                        "repeat_count": current_repeats,
                        "max_repeat_failures_per_signature": int(self.config.max_repeat_failures_per_signature),
                    },
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._update_trace_budget_usage(trace, tracker.state_values)
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                    metadata={"stopped_reason": "repeat_failure_limit_reached"},
                )
            failure_record = self.failtax_classifier.classify_failure(step_result.error, step=step, state_values=tracker.state_values)
            step_result.error.failtax_label = failure_record.failtax_label.value
            if not self.config.allow_repair:
                trace.add_event(
                    event_id="evt_stop_failed",
                    event_type=EventType.STOP,
                    actor="executor",
                    step_id=step.step_id,
                    tool_id=step.tool_id,
                    output={"status": "failed", "reason": "repair_disabled"},
                    metadata={"failtax_label": failure_record.failtax_label.value, "root_cause": failure_record.root_cause},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._update_trace_budget_usage(trace, tracker.state_values)
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                    metadata={"stopped_reason": "repair_disabled"},
                )
            backup_tool_id = backup_tool_map.get(step.tool_id or "")
            try:
                repair = self.recovery_engine.plan_repair(step_result.error, backup_tool_id=backup_tool_id)
            except NotImplementedError:
                repair = None
            if repair is None:
                replanned = self._attempt_rollback_and_suffix_replan(
                    workflow=workflow,
                    step=step,
                    error=step_result.error,
                    trace=trace,
                    tracker=tracker,
                )
                if replanned is not None:
                    workflow, idx = replanned
                    continue
                trace.add_event(
                    event_id="evt_stop_failed",
                    event_type=EventType.STOP,
                    actor="executor",
                    output={"status": "failed", "reason": "unsupported_recovery_path"},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                )
            trace.add_event(
                event_id=f"evt_repair_triggered_{step.step_id}",
                event_type=EventType.REPAIR_TRIGGERED,
                actor="recovery_engine",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output=repair.to_dict(),
                metadata={"failtax_label": failure_record.failtax_label.value, "root_cause": failure_record.root_cause},
            )
            tracker.state_values["__repair_attempts__"] = int(tracker.state_values.get("__repair_attempts__", 0)) + 1
            tracker.state_values["__recovery_budget_spent__"] = float(tracker.state_values.get("__recovery_budget_spent__", 0.0)) + 1.0
            tracker.state_values["__remaining_budgets__"] = self._remaining_budgets(workflow, tracker.state_values)
            self._update_trace_budget_usage(trace, tracker.state_values)
            repair_budget_violation = self._repair_budget_violation(workflow, tracker.state_values)
            if repair_budget_violation is not None:
                trace.add_event(
                    event_id="evt_stop_budget_violation",
                    event_type=EventType.STOP,
                    actor="executor",
                    step_id=step.step_id,
                    tool_id=step.tool_id,
                    output={"status": "failed", "reason": repair_budget_violation},
                    metadata={"failtax_label": failure_record.failtax_label.value, "root_cause": failure_record.root_cause},
                )
                self._mark_budget_violation(trace, repair_budget_violation)
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                    metadata={"stopped_reason": repair_budget_violation},
                )

            repair_result = self._apply_repair(
                workflow=workflow,
                step=step,
                repair=repair,
                trace=trace,
                backup_tool_map=backup_tool_map,
                state_values=tracker.state_values,
            )
            if repair_result.blocked:
                trace.add_event(
                    event_id="evt_stop_blocked",
                    event_type=EventType.STOP,
                    actor="executor",
                    output={"status": "blocked", "reason": "awaiting_user_interaction"},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._update_trace_budget_usage(trace, tracker.state_values)
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    blocked=True,
                    pending_interaction=repair_result.pending_interaction,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                )

            if not repair_result.applied:
                replanned = self._attempt_rollback_and_suffix_replan(
                    workflow=workflow,
                    step=step,
                    error=repair_result.followup_error or step_result.error,
                    trace=trace,
                    tracker=tracker,
                )
                if replanned is not None:
                    workflow, idx = replanned
                    continue
                trace.add_event(
                    event_id="evt_stop_failed",
                    event_type=EventType.STOP,
                    actor="executor",
                    output={"status": "failed", "reason": repair_result.message or "step_execution_failed"},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._update_trace_budget_usage(trace, tracker.state_values)
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=step_result.error.error_id,
                )

            tracker.mark_completed(step.step_id)
            tracker.state_values.update(repair_result.state_patch)
            tracker.state_values["__tool_calls__"] = trace.metrics.tool_calls
            tracker.state_values["__remaining_budgets__"] = self._remaining_budgets(workflow, tracker.state_values)
            self._update_trace_budget_usage(trace, tracker.state_values)
            if step.checkpoint:
                checkpoint_id = self._checkpoint_id_for_step(step.step_id)
                tracker.save_checkpoint(checkpoint_id)
                trace.add_event(
                    event_id=f"evt_checkpoint_{step.step_id}",
                    event_type=EventType.CHECKPOINT_CREATED,
                    actor="executor",
                    step_id=step.step_id,
                    output={"checkpoint_id": checkpoint_id},
                )
            idx += 1

        trace.add_event(
            event_id="evt_stop_success",
            event_type=EventType.STOP,
            actor="executor",
            output={"status": "success", "reason": "success_criteria_satisfied"},
        )
        trace.finalize(success=True, total_steps=len(workflow.execution_plan))
        self._update_trace_budget_usage(trace, tracker.state_values)
        self._write_trace(trace, output_path)
        return ExecutionOutcome(
            run_id=run_id,
            workflow=workflow,
            success=True,
            final_state=dict(tracker.state_values),
            trace_path=output_path,
        )

    def resume_from_patch(
        self,
        workflow: Workflow,
        run_id: str,
        output_path: str,
        resume_patch: "ResumePatch",
        backup_tool_map: Optional[Dict[str, str]] = None,
    ) -> ExecutionOutcome:
        workflow = resume_patch.workflow
        initial_state = dict(resume_patch.base_state)
        initial_state.update(resume_patch.state_updates)
        self._clear_state_slot_flags(initial_state, list(resume_patch.state_updates.keys()))
        approved_steps = set(initial_state.get("__approved_steps__", []))
        approved_steps.update(initial_state.get("__approved_steps__", []))
        if resume_patch.policy_updates.get("approved"):
            approved_steps.add(resume_patch.resume_step_id)
            initial_state["__approved_steps__"] = sorted(approved_steps)
            initial_state["approved"] = True
        if resume_patch.resume_step_id in {step.step_id for step in workflow.execution_plan}:
            for step in workflow.execution_plan:
                if step.step_id == resume_patch.resume_step_id:
                    for key, value in resume_patch.state_updates.items():
                        if key in {"abort", "tool_id", "approved", "__approved_steps__"}:
                            continue
                        step.inputs[key] = value
                    if resume_patch.binding_patch.get("tool_id"):
                        step.tool_id = resume_patch.binding_patch["tool_id"]
                    break

        start_step_index = 0
        for idx, step in enumerate(workflow.execution_plan):
            if step.step_id == resume_patch.resume_step_id:
                start_step_index = idx
                break

        return self.run_until_blocked(
            workflow=workflow,
            run_id=run_id,
            output_path=output_path,
            start_step_index=start_step_index,
            backup_tool_map=backup_tool_map,
            initial_state=initial_state,
        )

    def _execute_step(self, workflow: Workflow, step: WorkflowStep, trace: Trace, state_values: Dict[str, Any]) -> StepExecutionResult:
        trace.metadata.task_annotations["chosen_tool"] = step.tool_id
        tool_args = self._materialize_tool_args(step=step, state_values=state_values)
        # Persist inferred dependency fills so retries/replans keep consistent inputs.
        for key in ("target_path", "retrieved_info", "query"):
            if key in tool_args and key not in step.inputs:
                step.inputs[key] = tool_args[key]
        trace.add_event(
            event_id=f"evt_call_{step.step_id}",
            event_type=EventType.TOOL_CALL,
            actor="executor",
            step_id=step.step_id,
            tool_id=step.tool_id,
            tool_args=tool_args,
        )

        try:
            result = run_tool(step.tool_id or "", dict(tool_args), workflow=workflow)
            trace.add_event(
                event_id=f"evt_result_{step.step_id}",
                event_type=EventType.TOOL_RESULT,
                actor="environment",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output=result,
            )
            return StepExecutionResult(ok=True, step_id=step.step_id, tool_id=step.tool_id, output=result)
        except ToolExecutionError as exc:
            error = self._build_error(workflow, step, trace, exc, tool_args)
            return StepExecutionResult(ok=False, step_id=step.step_id, tool_id=step.tool_id, error=error)

    def _apply_repair(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        repair: Repair,
        trace: Trace,
        backup_tool_map: Dict[str, str],
        state_values: Dict[str, Any],
    ) -> RepairApplyResult:
        patched_inputs = dict(step.inputs)
        selected_tool = step.tool_id
        original_tool_id = step.tool_id
        should_reexecute = False
        extra_state_patch: Dict[str, Any] = {}

        for action in repair.actions:
            action_type = action.action_type.value
            if action_type == "state_patch" and action.target:
                target = action.target
                if ".inputs." in target:
                    key = target.split(".inputs.", 1)[1]
                    patched_inputs[key] = action.value
                elif target.endswith(".inputs") and isinstance(action.value, dict):
                    patched_inputs.update(action.value)
                elif target.startswith("state."):
                    state_key = target.split("state.", 1)[1]
                    if state_key:
                        extra_state_patch[state_key] = action.value
            elif action_type == "switch_tool":
                if isinstance(action.value, str):
                    selected_tool = action.value
                else:
                    selected_tool = self._resolve_switch_tool_target(step=step, repair=repair, backup_tool_map=backup_tool_map)
                if selected_tool:
                    step.tool_id = selected_tool
                    if original_tool_id and selected_tool != original_tool_id:
                        patched_inputs.pop("force_environment_failure", None)
                        extra_state_patch["force_environment_failure"] = False
                    for binding in workflow.tool_bindings:
                        if binding.capability_id == step.capability_id:
                            previous_primary = binding.primary_tool
                            binding.primary_tool = selected_tool
                            if previous_primary not in binding.backup_tools:
                                binding.backup_tools.append(previous_primary)
                            break
            elif action_type == "re_execute_step":
                should_reexecute = True
            elif action_type == "ask_user":
                pending = self._materialize_pending_interaction(workflow, step, repair)
                return RepairApplyResult(applied=False, blocked=True, pending_interaction=pending)

        if repair.repair_type.value == "ask_user" and not should_reexecute:
            pending = self._materialize_pending_interaction(workflow, step, repair)
            return RepairApplyResult(applied=False, blocked=True, pending_interaction=pending)

        if not should_reexecute:
            should_reexecute = repair.repair_type.value in {"switch_tool", "rebind_args"}

        if not should_reexecute:
            if repair.repair_type.value == "replan_suffix":
                return RepairApplyResult(applied=False, message="request_suffix_replan")
            return RepairApplyResult(applied=False, message=f"repair not executable: {repair.repair_type.value}")

        if not selected_tool:
            return RepairApplyResult(applied=False, message="no tool available for re-execution")

        step.inputs = patched_inputs
        trace.metadata.task_annotations["chosen_tool"] = selected_tool
        retry_state_values = dict(state_values)
        retry_state_values.update(extra_state_patch)
        retry_tool_args = self._materialize_tool_args(step=step, state_values=retry_state_values)
        trace.add_event(
            event_id=f"evt_repair_call_{step.step_id}",
            event_type=EventType.TOOL_CALL,
            actor="executor",
            step_id=step.step_id,
            tool_id=selected_tool,
            tool_args=retry_tool_args,
            metadata={"origin": "repair_retry", "repair_type": repair.repair_type.value},
        )
        try:
            retry_result = run_tool(selected_tool, dict(retry_tool_args), workflow=workflow)
        except ToolExecutionError as exc:
            error = ToolClawError(
                error_id=f"err_retry_{step.step_id}",
                run_id=trace.run_id,
                workflow_id=trace.workflow_id,
                step_id=step.step_id,
                category=ErrorCategory.RECOVERY_FAILURE,
                subtype="repair_retry_failed",
                severity=ErrorSeverity.MEDIUM,
                stage=ErrorStage.RECOVERY,
                symptoms=[str(exc)],
                evidence=ErrorEvidence(tool_id=selected_tool, raw_message=str(exc), inputs=dict(retry_tool_args)),
                root_cause_hypothesis=["repair retry failed during execution"],
                state_context=StateContext(active_capability=step.capability_id, active_step_id=step.step_id),
                recoverability=Recoverability(recoverable=True, requires_rollback=True),
                failtax_label="recovery_failure",
            )
            return RepairApplyResult(applied=False, message=str(exc), followup_error=error)
        trace.add_event(
            event_id=f"evt_repair_result_{step.step_id}",
            event_type=EventType.TOOL_RESULT,
            actor="environment",
            step_id=step.step_id,
            tool_id=selected_tool,
            output=retry_result,
            metadata={"origin": "repair_retry", "repair_type": repair.repair_type.value},
        )
        trace.add_event(
            event_id=f"evt_repair_applied_{step.step_id}",
            event_type=EventType.REPAIR_APPLIED,
            actor="executor",
            step_id=step.step_id,
            tool_id=selected_tool,
            output={"repair_type": repair.repair_type.value, "result": retry_result},
        )
        return RepairApplyResult(
            applied=True,
            workflow=workflow,
            state_patch={
                **extra_state_patch,
                **(retry_result.get("state_patch") if isinstance(retry_result.get("state_patch"), dict) else {}),
                (step.expected_output or step.step_id): retry_result.get("payload"),
            },
        )

    @staticmethod
    def _resolve_switch_tool_target(
        step: WorkflowStep,
        repair: Repair,
        backup_tool_map: Dict[str, str],
    ) -> Optional[str]:
        for action in repair.actions:
            if action.action_type.value == "switch_tool" and isinstance(action.value, str):
                return action.value
        return backup_tool_map.get(step.tool_id or "")

    def _materialize_pending_interaction(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        repair: Repair,
    ) -> PendingInteraction:
        return PendingInteraction(
            interaction_id=f"int_{repair.repair_id}",
            run_id=repair.run_id,
            workflow_id=workflow.workflow_id,
            step_id=step.step_id,
            repair=repair,
            question=repair.interaction.question or "Please provide guidance.",
            expected_answer_type=repair.interaction.expected_answer_type or "json_patch",
            metadata={
                "repair_type": repair.repair_type.value,
                "mapped_from_error_category": repair.metadata.get("mapped_from_error_category"),
                "failed_tool_id": repair.metadata.get("failed_tool_id") or step.tool_id,
                "backup_tool_id": repair.metadata.get("backup_tool_id"),
            },
        )

    def _attempt_rollback_and_suffix_replan(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        error: ToolClawError,
        trace: Trace,
        tracker: StateTracker,
    ) -> Optional[tuple[Workflow, int]]:
        rollback_step_id = step.rollback_to
        if rollback_step_id is None:
            rollback_step_id = self._fallback_rollback_step_id(workflow=workflow, step=step, tracker=tracker)
        if rollback_step_id is None:
            return None

        checkpoint_id = self._checkpoint_id_for_step(rollback_step_id)
        if not tracker.restore_checkpoint(checkpoint_id):
            return None

        trace.add_event(
            event_id=f"evt_rollback_{step.step_id}",
            event_type=EventType.ROLLBACK,
            actor="executor",
            step_id=step.step_id,
            output={"rollback_to": rollback_step_id, "checkpoint_id": checkpoint_id},
        )

        if self.planner is None:
            start_idx = self._step_index(workflow, step.step_id)
            return workflow, start_idx

        trace.add_event(
            event_id=f"evt_replan_triggered_{step.step_id}",
            event_type=EventType.REPLAN_TRIGGERED,
            actor="executor",
            step_id=step.step_id,
            output={"error_id": error.error_id, "rollback_to": rollback_step_id},
        )
        total_replans = int(tracker.state_values.get("__suffix_replan_total__", 0) or 0)
        if total_replans >= int(self.config.max_total_suffix_replans):
            trace.add_event(
                event_id=f"evt_replan_skipped_total_{step.step_id}",
                event_type=EventType.REPLAN_TRIGGERED,
                actor="executor",
                step_id=step.step_id,
                output={
                    "skipped": True,
                    "reason": "suffix_replan_total_limit_reached",
                    "attempts": total_replans,
                    "max_attempts": int(self.config.max_total_suffix_replans),
                },
            )
            return None
        replan_counts = tracker.state_values.setdefault("__suffix_replan_counts__", {})
        if not isinstance(replan_counts, dict):
            replan_counts = {}
            tracker.state_values["__suffix_replan_counts__"] = replan_counts
        signature = "::".join(
            [
                str(step.step_id or "unknown_step"),
                str(error.category.value if error.category else "unknown_category"),
                str(error.subtype or "unknown_subtype"),
            ]
        )
        current_count = int(replan_counts.get(signature, 0) or 0)
        if current_count >= int(self.config.max_suffix_replans_per_signature):
            trace.add_event(
                event_id=f"evt_replan_skipped_{step.step_id}",
                event_type=EventType.REPLAN_TRIGGERED,
                actor="executor",
                step_id=step.step_id,
                output={
                    "skipped": True,
                    "reason": "suffix_replan_limit_reached",
                    "signature": signature,
                    "attempts": current_count,
                    "max_attempts": int(self.config.max_suffix_replans_per_signature),
                },
            )
            return None
        replan_counts[signature] = current_count + 1
        tracker.state_values["__suffix_replan_total__"] = total_replans + 1
        request = self.planner.request_from_workflow(workflow)
        pool: concurrent.futures.ThreadPoolExecutor | None = None
        future: concurrent.futures.Future[Any] | None = None
        try:
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(
                self.planner.replan_from_error,
                request=request,
                failed_workflow=workflow,
                error=error,
                state_values=dict(tracker.state_values),
            )
            replanned = future.result(timeout=float(self.config.suffix_replan_timeout_s))
        except concurrent.futures.TimeoutError:
            if future is not None:
                future.cancel()
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)
            trace.add_event(
                event_id=f"evt_replan_timeout_{step.step_id}",
                event_type=EventType.REPLAN_TRIGGERED,
                actor="executor",
                step_id=step.step_id,
                output={
                    "skipped": True,
                    "reason": "suffix_replan_timeout",
                    "timeout_s": float(self.config.suffix_replan_timeout_s),
                    "signature": signature,
                },
            )
            return None
        finally:
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)
        trace.add_event(
            event_id=f"evt_replan_applied_{step.step_id}",
            event_type=EventType.REPLAN_APPLIED,
            actor="executor",
            step_id=step.step_id,
            output={"new_steps": len(replanned.workflow.execution_plan)},
            metadata={
                "replanned_from": workflow.workflow_id,
                "benchmark_hints_used": list(replanned.diagnostics.benchmark_hints_used),
                "replan_context": dict(replanned.workflow.metadata.get("replan_context", {})),
            },
        )
        return replanned.workflow, self._step_index(replanned.workflow, step.step_id)

    def _fallback_rollback_step_id(
        self,
        *,
        workflow: Workflow,
        step: WorkflowStep,
        tracker: StateTracker,
    ) -> Optional[str]:
        if tracker.completed_steps:
            return tracker.completed_steps[-1]
        current_index = self._step_index(workflow, step.step_id)
        if current_index <= 0:
            return None
        return workflow.execution_plan[current_index - 1].step_id

    @staticmethod
    def _checkpoint_id_for_step(step_id: str) -> str:
        return f"cp_{step_id}"

    @staticmethod
    def _step_index(workflow: Workflow, step_id: Optional[str]) -> int:
        if step_id is None:
            return 0
        for idx, step in enumerate(workflow.execution_plan):
            if step.step_id == step_id:
                return idx
        return 0

    @staticmethod
    def _materialize_tool_args(step: WorkflowStep, state_values: Dict[str, Any]) -> Dict[str, Any]:
        tool_args = dict(step.inputs)
        state_bindings = step.metadata.get("state_bindings", {})
        if isinstance(state_bindings, dict):
            for input_key, state_key in state_bindings.items():
                if state_key in state_values:
                    tool_args[str(input_key)] = state_values[state_key]
        # Dependency-driven fallback wiring: carry required slots from previous state
        # into current step inputs so write-like steps do not execute with empty args.
        required_slots = [str(item) for item in step.metadata.get("required_state_slots", []) if str(item)]
        for slot in required_slots:
            if slot in state_values and slot not in tool_args:
                tool_args[slot] = state_values[slot]
        if step.capability_id == "cap_write":
            if "retrieved_info" in state_values and "retrieved_info" not in tool_args:
                tool_args["retrieved_info"] = state_values["retrieved_info"]
            if "query" in state_values and "query" not in tool_args:
                tool_args["query"] = state_values["query"]
        inferred_preflight = SequentialExecutor._preflight_state_policy_for_step(step)
        state_slot = str(inferred_preflight.get("state_slot") or "")
        if state_slot and state_slot in state_values and SequentialExecutor._tool_uses_outbound_cellular(step.tool_id):
            tool_args.setdefault("cellular_on", state_values[state_slot])
        return SequentialExecutor._sanitize_tool_args(step.tool_id, tool_args)

    @staticmethod
    def _auto_approve_from_simulated_policy(
        *,
        workflow: Workflow,
        step: WorkflowStep,
        trace: Trace,
        state_values: Dict[str, Any],
    ) -> bool:
        simulated_policy = workflow.metadata.get("simulated_policy")
        if not isinstance(simulated_policy, dict) or not simulated_policy:
            return False
        mode = str(simulated_policy.get("mode", "cooperative")).strip().lower()
        if mode not in {"cooperative", "auto", "approve"}:
            return False
        state_values.setdefault("__approved_steps__", [])
        if step.step_id not in state_values["__approved_steps__"]:
            state_values["__approved_steps__"].append(step.step_id)
        state_values["approved"] = True
        trace.add_event(
            event_id=f"evt_auto_approval_{step.step_id}",
            event_type=EventType.APPROVAL_RESPONSE,
            actor="simulated_policy",
            step_id=step.step_id,
            tool_id=step.tool_id,
            output={"approved": True, "source": "simulated_policy"},
            metadata={"mode": mode},
        )
        return True

    def _check_state_failure(
        self,
        *,
        step: WorkflowStep,
        trace: Trace,
        state_values: Dict[str, Any],
    ) -> Optional[StepExecutionResult]:
        self._inject_step_state_failures(step=step, state_values=state_values)
        required_slots = [str(item) for item in step.metadata.get("required_state_slots", []) if str(item)]
        stale_slots = [str(item) for item in state_values.get("__stale_state_slots__", []) if str(item)]
        missing_slots = [slot for slot in required_slots if slot not in state_values or state_values.get(slot) in {None, ""}]
        stale_required = [slot for slot in required_slots if slot in stale_slots]
        preflight_policy = self._preflight_state_policy_for_step(step)
        simulated_missing_arg_values = step.metadata.get("simulated_missing_arg_values", {})
        if not isinstance(simulated_missing_arg_values, dict):
            simulated_missing_arg_values = {}
        unsatisfied_slots: list[str] = []
        state_slot = str(preflight_policy.get("state_slot") or "")
        required_value = preflight_policy.get("required_value")
        if state_slot:
            if state_slot not in required_slots:
                required_slots.append(state_slot)
            if state_slot not in state_values or state_values.get(state_slot) in {None, ""}:
                if state_slot not in missing_slots:
                    missing_slots.append(state_slot)
            elif required_value is not None and state_values.get(state_slot) != required_value:
                unsatisfied_slots.append(state_slot)
        if not missing_slots and not stale_required and not unsatisfied_slots:
            return None
        for slot in missing_slots:
            if slot not in stale_slots:
                state_values.setdefault("__missing_assets__", [])
                if slot not in state_values["__missing_assets__"]:
                    state_values["__missing_assets__"].append(slot)
        preflight_blocked = bool(preflight_policy) and bool(missing_slots or unsatisfied_slots)
        subtype = "preflight_state_unsatisfied" if preflight_blocked else ("stale_state" if stale_required else "missing_state_slot")
        symptoms = []
        if missing_slots:
            symptoms.append(f"missing required state slot(s): {', '.join(missing_slots)}")
        if stale_required:
            symptoms.append(f"stale state slot(s): {', '.join(stale_required)}")
        if unsatisfied_slots:
            symptoms.append(f"preflight state requirement not satisfied: {', '.join(unsatisfied_slots)}")
        error = ToolClawError(
            error_id=f"err_state_{step.step_id}",
            run_id=trace.run_id,
            workflow_id=trace.workflow_id,
            step_id=step.step_id,
            category=ErrorCategory.STATE_FAILURE,
            subtype=subtype,
            severity=ErrorSeverity.MEDIUM,
            stage=ErrorStage.EXECUTION,
            symptoms=symptoms,
            evidence=ErrorEvidence(
                tool_id=step.tool_id,
                raw_message="; ".join(symptoms),
                inputs=self._materialize_tool_args(step=step, state_values=state_values),
                metadata={
                    "required_state_slots": required_slots,
                    "preflight_state_policy": preflight_policy,
                    "simulated_missing_arg_values": simulated_missing_arg_values,
                },
            ),
            root_cause_hypothesis=["required state was missing or stale before tool execution"],
            state_context=StateContext(
                active_capability=step.capability_id,
                active_step_id=step.step_id,
                missing_assets=missing_slots or unsatisfied_slots or stale_required,
                state_values=dict(state_values),
                policy_flags={"approval_pending": False},
            ),
            recoverability=Recoverability(
                recoverable=True,
                requires_user_input=True,
                requires_tool_switch=False,
                requires_rollback=False,
                requires_approval=False,
            ),
            failtax_label="state_failure",
        )
        return StepExecutionResult(ok=False, step_id=step.step_id, tool_id=step.tool_id, error=error)

    @staticmethod
    def _inject_step_state_failures(
        *,
        step: WorkflowStep,
        state_values: Dict[str, Any],
    ) -> None:
        injected = set(str(item) for item in state_values.get("__state_faults_injected__", []) if str(item))

        missing_slots = [str(item) for item in step.metadata.get("inject_missing_state_slots_once", []) if str(item)]
        missing_key = f"{step.step_id}:missing"
        if missing_slots and missing_key not in injected:
            for slot in missing_slots:
                state_values.pop(slot, None)
                state_values.setdefault("__missing_assets__", [])
                if slot not in state_values["__missing_assets__"]:
                    state_values["__missing_assets__"].append(slot)
            injected.add(missing_key)

        stale_slots = [str(item) for item in step.metadata.get("inject_stale_state_slots_once", []) if str(item)]
        stale_key = f"{step.step_id}:stale"
        if stale_slots and stale_key not in injected:
            existing_stale = set(str(item) for item in state_values.get("__stale_state_slots__", []) if str(item))
            existing_stale.update(stale_slots)
            state_values["__stale_state_slots__"] = sorted(existing_stale)
            injected.add(stale_key)

        if injected:
            state_values["__state_faults_injected__"] = sorted(injected)

    @staticmethod
    def _apply_resume_state_overrides(workflow: Workflow, state_values: Dict[str, Any], resumed: bool) -> None:
        if not resumed or workflow.metadata.get("__resume_state_override_applied__"):
            return
        drop_slots = [str(item) for item in workflow.metadata.get("resume_state_drop_slots", []) if str(item)]
        for slot in drop_slots:
            state_values.pop(slot, None)
        stale_slots = set(str(item) for item in state_values.get("__stale_state_slots__", []) if str(item))
        stale_slots.update(str(item) for item in workflow.metadata.get("resume_state_stale_slots", []) if str(item))
        if stale_slots:
            state_values["__stale_state_slots__"] = sorted(stale_slots)
        workflow.metadata["__resume_state_override_applied__"] = True

    @staticmethod
    def _clear_state_slot_flags(state_values: Dict[str, Any], slots: list[str]) -> None:
        if not slots:
            return
        stale = [str(item) for item in state_values.get("__stale_state_slots__", []) if str(item)]
        missing = [str(item) for item in state_values.get("__missing_assets__", []) if str(item)]
        slot_set = {str(slot) for slot in slots if str(slot)}
        if stale:
            state_values["__stale_state_slots__"] = [slot for slot in stale if slot not in slot_set]
        if missing:
            state_values["__missing_assets__"] = [slot for slot in missing if slot not in slot_set]

    def _build_error(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        trace: Trace,
        exc: Exception,
        tool_args: Dict[str, Any],
    ) -> ToolClawError:
        message = str(exc)
        preflight_policy = self._preflight_state_policy_for_step(step)
        lowered_message = message.lower()
        if "missing required field" in message:
            category = ErrorCategory.BINDING_FAILURE
        elif "numberparseexception" in lowered_message or "missing or invalid default region" in lowered_message:
            category = ErrorCategory.BINDING_FAILURE
        elif "cellular service is not enabled" in lowered_message:
            category = ErrorCategory.STATE_FAILURE
        elif "write target mismatch" in message or "stale state" in message or "state slot" in message:
            category = ErrorCategory.STATE_FAILURE
        elif "permission" in message:
            category = ErrorCategory.PERMISSION_FAILURE
        elif "order" in message or "dependency" in message:
            category = ErrorCategory.ORDERING_FAILURE
        else:
            category = ErrorCategory.ENVIRONMENT_FAILURE

        repair_default_inputs = dict(step.metadata.get("repair_default_inputs", {}))
        simulated_policy = workflow.metadata.get("simulated_policy", {})
        simulated_missing_arg_values = (
            dict(simulated_policy.get("missing_arg_values", {}))
            if isinstance(simulated_policy, dict) and isinstance(simulated_policy.get("missing_arg_values", {}), dict)
            else {}
        )
        if not simulated_missing_arg_values:
            step_level_simulated = step.metadata.get("simulated_missing_arg_values", {})
            if isinstance(step_level_simulated, dict):
                simulated_missing_arg_values = dict(step_level_simulated)
        inferred_missing_assets: list[str] = []
        if category == ErrorCategory.BINDING_FAILURE:
            if step.capability_id == "cap_write" and not tool_args.get("target_path"):
                inferred_missing_assets.append("target_path")
            required_slots = [str(item) for item in step.metadata.get("required_state_slots", []) if str(item)]
            for slot in required_slots:
                if slot not in inferred_missing_assets and tool_args.get(slot) in {None, ""}:
                    inferred_missing_assets.append(slot)

        error_obj = ToolClawError(
            error_id=f"err_{step.step_id}",
            run_id=trace.run_id,
            workflow_id=trace.workflow_id,
            step_id=step.step_id,
            category=category,
            subtype="tool_execution_error",
            severity=ErrorSeverity.MEDIUM,
            stage=ErrorStage.EXECUTION,
            symptoms=[message],
            evidence=ErrorEvidence(
                tool_id=step.tool_id,
                raw_message=message,
                related_events=[f"evt_call_{step.step_id}"],
                inputs=dict(tool_args),
                metadata={
                    "preflight_state_policy": preflight_policy,
                    "repair_default_inputs": repair_default_inputs,
                    "simulated_missing_arg_values": simulated_missing_arg_values,
                },
            ),
            root_cause_hypothesis=["tool invocation failed in sequential execution"],
            state_context=StateContext(
                active_capability=step.capability_id,
                active_step_id=step.step_id,
                missing_assets=(
                    ["cellular_service_status"]
                    if "cellular service is not enabled" in lowered_message
                    else (
                        ["target_path"]
                        if ("target_path" in message or "write target mismatch" in message)
                        else inferred_missing_assets
                    )
                ),
                state_values={},
                policy_flags={"approval_pending": False},
            ),
            recoverability=Recoverability(
                recoverable=True,
                requires_user_input=(category in {ErrorCategory.ENVIRONMENT_FAILURE, ErrorCategory.STATE_FAILURE}),
                requires_tool_switch=(category == ErrorCategory.ENVIRONMENT_FAILURE),
                requires_rollback=False,
                requires_approval=False,
            ),
            failtax_label=category.value,
        )
        return error_obj

    @staticmethod
    def run_preflight(workflow: Workflow) -> "PreflightReport":
        missing_assets = []
        warnings = []
        for step in workflow.execution_plan:
            if step.capability_id == "cap_write" and not step.inputs.get("target_path"):
                missing_assets.append(f"{step.step_id}.target_path")
            if not step.tool_id:
                warnings.append(f"{step.step_id} has no bound tool")
            preflight_policy = SequentialExecutor._preflight_state_policy_for_step(step)
            state_slot = str(preflight_policy.get("state_slot") or "")
            if state_slot:
                missing_assets.append(f"{step.step_id}.{state_slot}")
        return PreflightReport(ok=not warnings, missing_assets=missing_assets, warnings=warnings)

    @staticmethod
    def _sanitize_tool_args(tool_id: Optional[str], tool_args: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in tool_args.items():
            if value is None:
                continue
            if isinstance(value, str):
                normalized = value.strip()
                if normalized.lower() in PLACEHOLDER_ARGUMENT_STRINGS:
                    continue
                sanitized[key] = normalized
                continue
            sanitized[key] = value

        if tool_id == "search_contacts":
            for key in ("person_id", "phone_number", "relationship"):
                value = sanitized.get(key)
                if isinstance(value, str) and value.strip().lower() in PLACEHOLDER_ARGUMENT_STRINGS:
                    sanitized.pop(key, None)
            if sanitized.get("is_self") is False and any(field in sanitized for field in ("name", "person_id", "phone_number", "relationship")):
                sanitized.pop("is_self", None)

        return sanitized

    @staticmethod
    def _tool_uses_outbound_cellular(tool_id: Optional[str]) -> bool:
        normalized = str(tool_id or "").strip().lower()
        return "send_message" in normalized or normalized in {"send_sms", "send_text"}

    @staticmethod
    def _preflight_state_policy_for_step(step: WorkflowStep) -> Dict[str, Any]:
        existing = step.metadata.get("preflight_state_policy")
        if isinstance(existing, dict) and existing:
            return dict(existing)
        allowed_tools = {str(item) for item in step.metadata.get("allowed_tools", []) if str(item)}
        if SequentialExecutor._tool_uses_outbound_cellular(step.tool_id) and {
            "get_cellular_service_status",
            "set_cellular_service_status",
        }.intersection(allowed_tools):
            return {
                "state_slot": "cellular_service_status",
                "required_value": True,
                "repair_target": "cellular_service_status",
                "repair_value": True,
                "auto_repair": "set_cellular_service_status" in allowed_tools,
                "reason": "outbound messaging requires cellular connectivity",
            }
        return {}

    @staticmethod
    def _write_trace(trace: Trace, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def _task_annotations(workflow: Workflow) -> Dict[str, Any]:
        keys = (
            "primary_failtax",
            "failtaxes",
            "failure_step",
            "expected_recovery_path",
            "gold_tool",
            "chosen_tool",
            "state_slots",
            "dependency_edges",
        )
        return {key: workflow.metadata.get(key) for key in keys if workflow.metadata.get(key) is not None}

    @staticmethod
    def _budget_limits(workflow: Workflow) -> Dict[str, Any]:
        constraints = workflow.task.constraints
        return {
            "max_tool_calls": constraints.max_tool_calls,
            "max_user_turns": constraints.max_user_turns,
            "max_repair_attempts": constraints.max_repair_attempts,
            "max_recovery_budget": constraints.max_recovery_budget,
            "budget_limit": constraints.budget_limit,
            "time_limit": constraints.time_limit,
        }

    @classmethod
    def _remaining_budgets(cls, workflow: Workflow, state_values: Dict[str, Any]) -> Dict[str, Any]:
        limits = cls._budget_limits(workflow)
        return {
            "tool_calls": (limits["max_tool_calls"] - int(state_values.get("__tool_calls__", 0)))
            if limits["max_tool_calls"] is not None
            else None,
            "user_turns": (limits["max_user_turns"] - int(state_values.get("__user_turns__", 0)))
            if limits["max_user_turns"] is not None
            else None,
            "repair_attempts": (limits["max_repair_attempts"] - int(state_values.get("__repair_attempts__", 0)))
            if limits["max_repair_attempts"] is not None
            else None,
            "recovery_budget": (float(limits["max_recovery_budget"]) - float(state_values.get("__recovery_budget_spent__", 0.0)))
            if limits["max_recovery_budget"] is not None
            else None,
        }

    @staticmethod
    def _mark_budget_violation(trace: Trace, reason: str) -> None:
        trace.metrics.budget_violation = True
        trace.metrics.budget_violation_reason = reason

    @staticmethod
    def _update_trace_budget_usage(trace: Trace, state_values: Dict[str, Any]) -> None:
        trace.metadata.budget_usage = {
            "tool_calls": int(state_values.get("__tool_calls__", trace.metrics.tool_calls)),
            "user_turns": int(state_values.get("__user_turns__", trace.metrics.user_queries)),
            "repair_attempts": int(state_values.get("__repair_attempts__", 0)),
            "recovery_budget_used": float(state_values.get("__recovery_budget_spent__", 0.0)),
            "remaining_budgets": dict(state_values.get("__remaining_budgets__", {})),
        }
        trace.metrics.recovery_budget_used = float(state_values.get("__recovery_budget_spent__", 0.0))

    @staticmethod
    def _repair_budget_violation(workflow: Workflow, state_values: Dict[str, Any]) -> Optional[str]:
        constraints = workflow.task.constraints
        if constraints.max_repair_attempts is not None and int(state_values.get("__repair_attempts__", 0)) > int(constraints.max_repair_attempts):
            return "max_repair_attempts_exceeded"
        if constraints.max_recovery_budget is not None and float(state_values.get("__recovery_budget_spent__", 0.0)) > float(constraints.max_recovery_budget):
            return "max_recovery_budget_exceeded"
        return None

from toolclaw.interaction.repair_updater import ResumePatch  # noqa: E402
from toolclaw.planner.htgp import HTGPPlanner  # noqa: E402


@dataclass
class PreflightReport:
    ok: bool
    missing_assets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "missing_assets": list(self.missing_assets), "warnings": list(self.warnings)}
