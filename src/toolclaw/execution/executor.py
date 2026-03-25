from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from toolclaw.execution.recovery import RecoveryEngine
from toolclaw.execution.state_tracker import StateTracker
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


class SequentialExecutor:
    """Minimal sequential executor for phase-1 end-to-end traces."""

    def __init__(self, recovery_engine: Optional[RecoveryEngine] = None) -> None:
        self.recovery_engine = recovery_engine or RecoveryEngine()

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
    ) -> ExecutionOutcome:
        backup_tool_map = backup_tool_map or {}
        tracker = StateTracker()
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

        for idx in range(start_step_index, len(workflow.execution_plan)):
            step = workflow.execution_plan[idx]
            tracker.set_current_step(step.step_id)
            pending = [s.step_id for s in workflow.execution_plan[idx + 1 :]]
            trace.add_snapshot(
                snapshot_id=f"snap_{idx + 1:02d}_start",
                **tracker.snapshot(pending_steps=pending),
            )

            step_result = self._execute_step(step=step, trace=trace)
            if step_result.ok:
                tracker.mark_completed(step.step_id)
                tracker.state_values[step.expected_output or step.step_id] = step_result.output.get("payload")
                continue

            if step_result.error is None:
                raise RuntimeError("step execution failed without error object")

            tracker.mark_failed(step.step_id)
            backup_tool_id = backup_tool_map.get(step.tool_id or "")
            repair = self.recovery_engine.plan_repair(step_result.error, backup_tool_id=backup_tool_id)
            trace.add_event(
                event_id=f"evt_repair_triggered_{step.step_id}",
                event_type=EventType.REPAIR_TRIGGERED,
                actor="recovery_engine",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output=repair.to_dict(),
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
    ) -> ExecutionOutcome:
        workflow = resume_patch.workflow
        if resume_patch.resume_step_id in {step.step_id for step in workflow.execution_plan}:
            for step in workflow.execution_plan:
                if step.step_id == resume_patch.resume_step_id:
                    for key, value in resume_patch.state_updates.items():
                        if key in {"abort", "tool_id"}:
                            continue
                        step.inputs[key] = value
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
        if repair.repair_type.value == "switch_tool":
            backup_tool_id = self._resolve_switch_tool_target(step=step, repair=repair, backup_tool_map=backup_tool_map)
            if not backup_tool_id:
                return RepairApplyResult(applied=False, message="no backup tool")

            step.tool_id = backup_tool_id
            for binding in workflow.tool_bindings:
                if binding.capability_id == step.capability_id:
                    previous_primary = binding.primary_tool
                    binding.primary_tool = backup_tool_id
                    if previous_primary not in binding.backup_tools:
                        binding.backup_tools.append(previous_primary)
                    break

            retry_result = run_mock_tool(backup_tool_id, dict(step.inputs))
            trace.add_event(
                event_id=f"evt_repair_applied_{step.step_id}",
                event_type=EventType.REPAIR_APPLIED,
                actor="executor",
                step_id=step.step_id,
                tool_id=backup_tool_id,
                output={"repair_type": repair.repair_type.value, "result": retry_result},
            )
            return RepairApplyResult(
                applied=True,
                workflow=workflow,
                state_patch={step.expected_output or step.step_id: retry_result.get("payload")},
            )

        if repair.repair_type.value == "rebind_args":
            patched = dict(step.inputs)
            for action in repair.actions:
                if action.action_type.value != "state_patch" or not action.target:
                    continue
                target = action.target
                if ".inputs." in target:
                    key = target.split(".inputs.", 1)[1]
                    patched[key] = action.value
                elif target.endswith(".inputs") and isinstance(action.value, dict):
                    patched.update(action.value)

            retry_result = run_mock_tool(step.tool_id or "", patched)
            step.inputs = patched
            trace.add_event(
                event_id=f"evt_repair_applied_{step.step_id}",
                event_type=EventType.REPAIR_APPLIED,
                actor="executor",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output={"repair_type": repair.repair_type.value, "result": retry_result},
            )
            return RepairApplyResult(
                applied=True,
                workflow=workflow,
                state_patch={step.expected_output or step.step_id: retry_result.get("payload")},
            )

        if repair.repair_type.value == "ask_user":
            pending = self._materialize_pending_interaction(workflow, step, repair)
            return RepairApplyResult(applied=False, blocked=True, pending_interaction=pending)

        return RepairApplyResult(applied=False, message=f"unsupported repair_type={repair.repair_type.value}")

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
        )

    def _build_error(
        self,
        step: WorkflowStep,
        trace: Trace,
        exc: Exception,
    ) -> ToolClawError:
        message = str(exc)
        category = ErrorCategory.BINDING_FAILURE if "missing required field" in message else ErrorCategory.ENVIRONMENT_FAILURE

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
    def _write_trace(trace: Trace, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")


from toolclaw.interaction.repair_updater import ResumePatch  # noqa: E402
