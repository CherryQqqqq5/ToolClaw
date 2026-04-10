"""Baseline runner that executes the workflow without repair or interaction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from toolclaw.schemas.trace import EventType, RunMetadata, RunMode, Trace
from toolclaw.schemas.workflow import Workflow
from toolclaw.tools.mock_tools import ToolExecutionError
from toolclaw.tools.runtime import run_tool


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
    trace.metadata.run_manifest["tool_runtime_backend"] = str(workflow.metadata.get("tool_execution_backend", "mock"))

    stop_reason = "success_criteria_satisfied"
    state_values: Dict[str, Any] = {}
    for step in workflow.execution_plan:
        _inject_step_state_failures(step=step, state_values=state_values)
        state_failure = _state_failure_message(step=step, state_values=state_values)
        if state_failure is not None:
            stop_reason = f"step_failed:{step.step_id}:{state_failure}"
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

        tool_args = _materialize_tool_args(step=step, state_values=state_values)
        trace.add_event(
            event_id=f"evt_call_{step.step_id}",
            event_type=EventType.TOOL_CALL,
            actor="baseline_executor",
            step_id=step.step_id,
            tool_id=step.tool_id,
            tool_args=tool_args,
        )

        try:
            result = run_tool(step.tool_id or "", dict(tool_args), workflow=workflow)
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
        state_values[step.expected_output or step.step_id] = result.get("payload")
        _clear_state_slot_flags(state_values, [step.expected_output or step.step_id])

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


def _materialize_tool_args(*, step, state_values: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = dict(step.inputs)
    state_bindings = step.metadata.get("state_bindings", {})
    if isinstance(state_bindings, dict):
        for input_key, state_key in state_bindings.items():
            if state_key in state_values:
                tool_args[str(input_key)] = state_values[state_key]
    return tool_args


def _inject_step_state_failures(*, step, state_values: Dict[str, Any]) -> None:
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


def _state_failure_message(*, step, state_values: Dict[str, Any]) -> str | None:
    required_slots = [str(item) for item in step.metadata.get("required_state_slots", []) if str(item)]
    stale_slots = [str(item) for item in state_values.get("__stale_state_slots__", []) if str(item)]
    missing_slots = [slot for slot in required_slots if slot not in state_values or state_values.get(slot) in {None, ""}]
    stale_required = [slot for slot in required_slots if slot in stale_slots]
    if not missing_slots and not stale_required:
        return None
    parts = []
    if missing_slots:
        parts.append(f"missing required state slot(s): {', '.join(missing_slots)}")
    if stale_required:
        parts.append(f"stale state slot(s): {', '.join(stale_required)}")
    return "; ".join(parts)


def _clear_state_slot_flags(state_values: Dict[str, Any], slots: list[str]) -> None:
    slot_set = {str(slot) for slot in slots if str(slot)}
    if not slot_set:
        return
    stale = [str(item) for item in state_values.get("__stale_state_slots__", []) if str(item)]
    missing = [str(item) for item in state_values.get("__missing_assets__", []) if str(item)]
    if stale:
        state_values["__stale_state_slots__"] = [slot for slot in stale if slot not in slot_set]
    if missing:
        state_values["__missing_assets__"] = [slot for slot in missing if slot not in slot_set]
