import json
from pathlib import Path

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.schemas.trace import EventType
from toolclaw.schemas.workflow import Workflow


def test_executor_runs_demo_workflow_and_writes_trace(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    output_file = tmp_path / "traces" / "run_success.json"

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_success_001",
        output_path=str(output_file),
    )

    assert trace.metrics.success is True
    assert output_file.exists()

    trace_payload = json.loads(output_file.read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in trace_payload["events"]]
    assert EventType.TOOL_CALL.value in event_types
    assert EventType.TOOL_RESULT.value in event_types
    assert EventType.STOP.value in event_types


def test_executor_triggers_repair_and_applies_backup_tool(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True
    output_file = tmp_path / "traces" / "run_repair.json"

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_repair_001",
        output_path=str(output_file),
        backup_tool_map={"write_tool": "backup_write_tool"},
    )

    assert trace.metrics.success is True

    trace_payload = json.loads(output_file.read_text(encoding="utf-8"))
    event_types = [evt["event_type"] for evt in trace_payload["events"]]
    assert EventType.REPAIR_TRIGGERED.value in event_types
    assert EventType.REPAIR_APPLIED.value in event_types
    assert EventType.STOP.value in event_types


def test_switch_tool_repair_updates_workflow_state(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    trace = SequentialExecutor().run(
        workflow=workflow,
        run_id="run_switch_update_001",
        output_path=str(tmp_path / "run_switch_update.json"),
        backup_tool_map={"write_tool": "backup_write_tool"},
    )

    assert trace.metrics.success is True
    assert workflow.execution_plan[1].tool_id == "backup_write_tool"
    write_binding = [b for b in workflow.tool_bindings if b.capability_id == "cap_write"][0]
    assert write_binding.primary_tool == "backup_write_tool"
    assert "write_tool" in write_binding.backup_tools
