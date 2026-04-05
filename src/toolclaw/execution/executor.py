"""Sequential execution runtime with policy gates, repair, rollback, and suffix replan."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
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
from toolclaw.tools.mock_tools import ToolExecutionError, run_mock_tool


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


class SequentialExecutor:
    """Minimal sequential executor for phase-1 end-to-end traces."""

    def __init__(
        self,
        recovery_engine: Optional[RecoveryEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        failtax_classifier: Optional[FailTaxClassifier] = None,
        planner: Optional["HTGPPlanner"] = None,
    ) -> None:
        self.recovery_engine = recovery_engine or RecoveryEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.failtax_classifier = failtax_classifier or FailTaxClassifier()
        self.planner = planner

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
        trace = Trace(
            run_id=run_id,
            workflow_id=workflow.workflow_id,
            task_id=workflow.task.task_id,
            metadata=RunMetadata(model_name="phase1_executor", mode=RunMode.TOOLCLAW),
        )

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
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._write_trace(trace, output_path)
                return ExecutionOutcome(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(tracker.state_values),
                    trace_path=output_path,
                    last_error_id=f"err_policy_{step.step_id}",
                )

            step_result = self._execute_step(step=step, trace=trace)
            if step_result.ok:
                tracker.mark_completed(step.step_id)
                tracker.state_values[step.expected_output or step.step_id] = step_result.output.get("payload")
                after_decision = self.policy_engine.evaluate_after_step(step, workflow, tracker.state_values)
                tracker.state_values.update(after_decision.state_patch)
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
            failure_record = self.failtax_classifier.classify_failure(step_result.error, step=step, state_values=tracker.state_values)
            step_result.error.failtax_label = failure_record.failtax_label.value
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

            repair_result = self._apply_repair(
                workflow=workflow,
                step=step,
                repair=repair,
                trace=trace,
                backup_tool_map=backup_tool_map,
            )
            if repair_result.blocked:
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

    def _execute_step(self, step: WorkflowStep, trace: Trace) -> StepExecutionResult:
        trace.add_event(
            event_id=f"evt_call_{step.step_id}",
            event_type=EventType.TOOL_CALL,
            actor="executor",
            step_id=step.step_id,
            tool_id=step.tool_id,
            tool_args=step.inputs,
        )

        try:
            result = run_mock_tool(step.tool_id or "", dict(step.inputs))
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
            error = self._build_error(step, trace, exc)
            return StepExecutionResult(ok=False, step_id=step.step_id, tool_id=step.tool_id, error=error)

    def _apply_repair(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        repair: Repair,
        trace: Trace,
        backup_tool_map: Dict[str, str],
    ) -> RepairApplyResult:
        patched_inputs = dict(step.inputs)
        selected_tool = step.tool_id
        should_reexecute = False

        for action in repair.actions:
            action_type = action.action_type.value
            if action_type == "state_patch" and action.target:
                target = action.target
                if ".inputs." in target:
                    key = target.split(".inputs.", 1)[1]
                    patched_inputs[key] = action.value
                elif target.endswith(".inputs") and isinstance(action.value, dict):
                    patched_inputs.update(action.value)
            elif action_type == "switch_tool":
                if isinstance(action.value, str):
                    selected_tool = action.value
                else:
                    selected_tool = self._resolve_switch_tool_target(step=step, repair=repair, backup_tool_map=backup_tool_map)
                if selected_tool:
                    step.tool_id = selected_tool
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
            return RepairApplyResult(applied=False, message=f"repair not executable: {repair.repair_type.value}")

        if not selected_tool:
            return RepairApplyResult(applied=False, message="no tool available for re-execution")

        step.inputs = patched_inputs
        try:
            retry_result = run_mock_tool(selected_tool, dict(step.inputs))
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
                evidence=ErrorEvidence(tool_id=selected_tool, raw_message=str(exc), inputs=dict(step.inputs)),
                root_cause_hypothesis=["repair retry failed during execution"],
                state_context=StateContext(active_capability=step.capability_id, active_step_id=step.step_id),
                recoverability=Recoverability(recoverable=True, requires_rollback=True),
                failtax_label="recovery_failure",
            )
            return RepairApplyResult(applied=False, message=str(exc), followup_error=error)
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
            state_patch={step.expected_output or step.step_id: retry_result.get("payload")},
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

        from toolclaw.planner.htgp import PlanningRequest

        trace.add_event(
            event_id=f"evt_replan_triggered_{step.step_id}",
            event_type=EventType.REPLAN_TRIGGERED,
            actor="executor",
            step_id=step.step_id,
            output={"error_id": error.error_id, "rollback_to": rollback_step_id},
        )
        request = PlanningRequest(task=workflow.task, context=workflow.context, policy=workflow.policy)
        replanned = self.planner.replan_from_error(
            request=request,
            failed_workflow=workflow,
            error=error,
            state_values=dict(tracker.state_values),
        )
        trace.add_event(
            event_id=f"evt_replan_applied_{step.step_id}",
            event_type=EventType.REPLAN_APPLIED,
            actor="executor",
            step_id=step.step_id,
            output={"new_steps": len(replanned.workflow.execution_plan)},
            metadata={"replanned_from": workflow.workflow_id},
        )
        return replanned.workflow, self._step_index(replanned.workflow, step.step_id)

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

    def _build_error(
        self,
        step: WorkflowStep,
        trace: Trace,
        exc: Exception,
    ) -> ToolClawError:
        message = str(exc)
        if "missing required field" in message:
            category = ErrorCategory.BINDING_FAILURE
        elif "permission" in message:
            category = ErrorCategory.PERMISSION_FAILURE
        elif "order" in message or "dependency" in message:
            category = ErrorCategory.ORDERING_FAILURE
        else:
            category = ErrorCategory.ENVIRONMENT_FAILURE

        return ToolClawError(
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
                inputs=dict(step.inputs),
            ),
            root_cause_hypothesis=["tool invocation failed in sequential execution"],
            state_context=StateContext(
                active_capability=step.capability_id,
                active_step_id=step.step_id,
                missing_assets=["target_path"] if "target_path" in message else [],
                state_values={},
                policy_flags={"approval_pending": False},
            ),
            recoverability=Recoverability(
                recoverable=True,
                requires_user_input=(category == ErrorCategory.ENVIRONMENT_FAILURE),
                requires_tool_switch=(category == ErrorCategory.ENVIRONMENT_FAILURE),
                requires_rollback=False,
                requires_approval=False,
            ),
            failtax_label=category.value,
        )

    @staticmethod
    def run_preflight(workflow: Workflow) -> "PreflightReport":
        missing_assets = []
        warnings = []
        for step in workflow.execution_plan:
            if step.capability_id == "cap_write" and not step.inputs.get("target_path"):
                missing_assets.append(f"{step.step_id}.target_path")
            if not step.tool_id:
                warnings.append(f"{step.step_id} has no bound tool")
        return PreflightReport(ok=not warnings, missing_assets=missing_assets, warnings=warnings)

    @staticmethod
    def _write_trace(trace: Trace, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")


from toolclaw.interaction.repair_updater import ResumePatch  # noqa: E402
from toolclaw.planner.htgp import HTGPPlanner  # noqa: E402


@dataclass
class PreflightReport:
    ok: bool
    missing_assets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "missing_assets": list(self.missing_assets), "warnings": list(self.warnings)}
