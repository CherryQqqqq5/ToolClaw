"""Thin wrapper for running the ToolClaw executor in tau-style experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.schemas.trace import Trace
from toolclaw.schemas.workflow import Workflow


def run_toolclaw_lite(
    workflow: Workflow,
    run_id: str,
    output_path: Path,
    backup_tool_map: Optional[Dict[str, str]] = None,
) -> Tuple[Trace, str]:
    executor = SequentialExecutor()
    trace = executor.run(
        workflow=workflow,
        run_id=run_id,
        output_path=str(output_path),
        backup_tool_map=backup_tool_map or {},
    )

    stop_reason = "unknown"
    for event in reversed(trace.events):
        if event.event_type.value == "stop":
            if isinstance(event.output, dict):
                stop_reason = str(event.output.get("reason", "unknown"))
            break
    return trace, stop_reason
