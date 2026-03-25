from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from toolclaw.schemas.trace import EventType, RunMetadata, RunMode, Trace
from toolclaw.schemas.workflow import Workflow
from toolclaw.tools.mock_tools import ToolExecutionError, run_mock_tool


def run_baseline(workflow: Workflow, run_id: str, output_path: Path) -> Tuple[Trace, str]:
    """Run workflow without repair/recovery (first error fails run)."""
    trace = Trace(
        run_id=run_id,
        workflow_id=workflow.workflow_id,
        task_id=workflow.task.task_id,
        metadata=RunMetadata(model_name="baseline_executor", mode=RunMode.BASELINE),
    )

    trace.add_event(
        event_id="evt_000",
        event_type=EventType.PLAN_GENERATED,
        actor="baseline_executor",
        output={"steps": len(workflow.execution_plan)},
    )

    stop_reason = "success_criteria_satisfied"
    for step in workflow.execution_plan:
        trace.add_event(
            event_id=f"evt_call_{step.step_id}",
            event_type=EventType.TOOL_CALL,
            actor="baseline_executor",
            step_id=step.step_id,
            tool_id=step.tool_id,
            tool_args=step.inputs,
        )

        try:
            result = run_mock_tool(step.tool_id or "", dict(step.inputs))
        except ToolExecutionError as exc:
            stop_reason = f"step_failed:{step.step_id}:{exc}"
            trace.add_event(
                event_id=f"evt_stop_failed_{step.step_id}",
                event_type=EventType.STOP,
                actor="baseline_executor",
                step_id=step.step_id,
                output={"status": "failed", "reason": stop_reason},
            )
            trace.finalize(success=False, total_steps=len(workflow.execution_plan))
            _write_trace(trace, output_path)
            return trace, stop_reason

        trace.add_event(
            event_id=f"evt_result_{step.step_id}",
            event_type=EventType.TOOL_RESULT,
            actor="environment",
            step_id=step.step_id,
            tool_id=step.tool_id,
            output=result,
        )

    trace.add_event(
        event_id="evt_stop_success",
        event_type=EventType.STOP,
        actor="baseline_executor",
        output={"status": "success", "reason": stop_reason},
    )
    trace.finalize(success=True, total_steps=len(workflow.execution_plan))
    _write_trace(trace, output_path)
    return trace, stop_reason


def _write_trace(trace: Trace, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")
