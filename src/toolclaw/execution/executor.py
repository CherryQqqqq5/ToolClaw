from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

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
from toolclaw.schemas.trace import EventType, RunMetadata, RunMode, Trace
from toolclaw.schemas.workflow import Workflow, WorkflowStep
from toolclaw.tools.mock_tools import ToolExecutionError, run_mock_tool


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

        for idx, step in enumerate(workflow.execution_plan, start=1):
            tracker.set_current_step(step.step_id)
            pending = [s.step_id for s in workflow.execution_plan[idx:]]
            trace.add_snapshot(snapshot_id=f"snap_{idx:02d}_start", **tracker.snapshot(pending_steps=pending))

            ok = self._run_step(workflow, step, trace, tracker, backup_tool_map)
            if not ok:
                trace.add_event(
                    event_id="evt_stop_failed",
                    event_type=EventType.STOP,
                    actor="executor",
                    output={"status": "failed", "reason": "step_execution_failed"},
                )
                trace.finalize(success=False, total_steps=len(workflow.execution_plan))
                self._write_trace(trace, output_path)
                return trace

        trace.add_event(
            event_id="evt_stop_success",
            event_type=EventType.STOP,
            actor="executor",
            output={"status": "success", "reason": "success_criteria_satisfied"},
        )
        trace.finalize(success=True, total_steps=len(workflow.execution_plan))
        self._write_trace(trace, output_path)
        return trace

    def _run_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        trace: Trace,
        tracker: StateTracker,
        backup_tool_map: Dict[str, str],
    ) -> bool:
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
            tracker.mark_completed(step.step_id)
            tracker.state_values[step.expected_output or step.step_id] = result.get("payload")
            return True
        except ToolExecutionError as exc:
            tracker.mark_failed(step.step_id)
            error = self._build_error(workflow, trace, step, exc, tracker)
            backup_tool_id = backup_tool_map.get(step.tool_id or "")
            repair = self.recovery_engine.plan_repair(error, backup_tool_id=backup_tool_id)
            trace.add_event(
                event_id=f"evt_repair_triggered_{step.step_id}",
                event_type=EventType.REPAIR_TRIGGERED,
                actor="recovery_engine",
                step_id=step.step_id,
                tool_id=step.tool_id,
                output=repair.to_dict(),
            )

            if repair.repair_type.value == "switch_tool" and backup_tool_id:
                retry_result = run_mock_tool(backup_tool_id, dict(step.inputs))
                trace.add_event(
                    event_id=f"evt_repair_applied_{step.step_id}",
                    event_type=EventType.REPAIR_APPLIED,
                    actor="executor",
                    step_id=step.step_id,
                    tool_id=backup_tool_id,
                    output={"repair_type": repair.repair_type.value, "result": retry_result},
                )
                tracker.mark_completed(step.step_id)
                tracker.state_values[step.expected_output or step.step_id] = retry_result.get("payload")
                return True

            if repair.repair_type.value == "rebind_args":
                patched = dict(step.inputs)
                if "target_path" not in patched:
                    patched["target_path"] = "outputs/reports/recovered_report.txt"
                retry_result = run_mock_tool(step.tool_id or "", patched)
                trace.add_event(
                    event_id=f"evt_repair_applied_{step.step_id}",
                    event_type=EventType.REPAIR_APPLIED,
                    actor="executor",
                    step_id=step.step_id,
                    tool_id=step.tool_id,
                    output={"repair_type": repair.repair_type.value, "result": retry_result},
                )
                tracker.mark_completed(step.step_id)
                tracker.state_values[step.expected_output or step.step_id] = retry_result.get("payload")
                return True

            return False

    def _build_error(
        self,
        workflow: Workflow,
        trace: Trace,
        step: WorkflowStep,
        exc: Exception,
        tracker: StateTracker,
    ) -> ToolClawError:
        message = str(exc)
        category = (
            ErrorCategory.BINDING_FAILURE
            if "missing required field" in message
            else ErrorCategory.ENVIRONMENT_FAILURE
        )

        return ToolClawError(
            error_id=f"err_{step.step_id}",
            run_id=trace.run_id,
            workflow_id=workflow.workflow_id,
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
                state_values=dict(tracker.state_values),
                policy_flags={"approval_pending": False},
            ),
            recoverability=Recoverability(
                recoverable=True,
                requires_user_input=False,
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
