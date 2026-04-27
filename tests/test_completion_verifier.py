from __future__ import annotations

import json
from pathlib import Path

from toolclaw.execution.completion_verifier import CompletionVerifier
from toolclaw.execution.executor import SequentialExecutor
from toolclaw.schemas.trace import EventType, Trace
from toolclaw.schemas.workflow import ActionType, Workflow, WorkflowStep


def _workflow() -> Workflow:
    workflow = Workflow.demo()
    workflow.task.task_id = "completion_verifier_test"
    workflow.task.user_goal = "Write a report."
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_write",
            tool_id="write_tool",
            action_type=ActionType.TOOL_CALL,
            inputs={"target_path": "outputs/reports/completion_verifier_test.txt", "content": "done"},
            expected_output="report_artifact",
        )
    ]
    return workflow


def test_completion_verifier_passes_concrete_tool_result() -> None:
    workflow = _workflow()
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="write_tool",
        output={"status": "success", "payload": "created report artifact with task-relevant content"},
    )

    result = CompletionVerifier().verify(workflow=workflow, trace=trace, state_values={"report_artifact": "created"})

    assert result.completion_verified is True
    assert result.recommended_action == "finalize"
    assert result.metadata["gold_free"] is True


def test_completion_verifier_flags_missing_runtime_evidence() -> None:
    workflow = _workflow()
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)

    result = CompletionVerifier().verify(workflow=workflow, trace=trace, state_values={})

    assert result.completion_verified is False
    assert "successful_tool_result" in result.missing_evidence
    assert result.recommended_action == "repair"


def test_completion_verifier_flags_ambiguous_goal_without_user_query() -> None:
    workflow = _workflow()
    workflow.task.user_goal = "Remind me to buy milk"
    workflow.metadata["messages"] = [
        {"sender": "system", "content": "Don't make assumptions. Ask for clarification if a user request is ambiguous."},
        {"sender": "user", "content": "Remind me to buy milk"},
    ]
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="write_tool",
        output={"status": "success", "payload": "created report artifact with task-relevant content"},
    )

    result = CompletionVerifier().verify(workflow=workflow, trace=trace, state_values={"report_artifact": "created"})

    assert result.completion_verified is False
    assert "user_clarification_for_ambiguous_goal" in result.missing_evidence
    assert result.recommended_action == "ask_user"


def test_completion_verifier_does_not_expose_scorer_gold() -> None:
    workflow = _workflow()
    workflow.metadata["milestones"] = ["SECRET_MILESTONE"]
    workflow.metadata["toolsandbox_reference_result"] = {"secret": "SECRET_REFERENCE"}
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="write_tool",
        output={"status": "success", "payload": "created report artifact with task-relevant content"},
    )

    payload = CompletionVerifier().verify(workflow=workflow, trace=trace, state_values={"report_artifact": "created"}).to_dict()

    serialized = json.dumps(payload)
    assert "SECRET_MILESTONE" not in serialized
    assert "SECRET_REFERENCE" not in serialized


def test_executor_records_completion_verifier_without_changing_success(tmp_path: Path) -> None:
    workflow = _workflow()
    out = tmp_path / "trace.json"

    outcome = SequentialExecutor().run_until_blocked(workflow=workflow, run_id="run_completion_verifier", output_path=str(out))
    payload = json.loads(out.read_text(encoding="utf-8"))
    event_types = [event["event_type"] for event in payload["events"]]

    assert outcome.success is True
    assert payload["metrics"]["success"] is True
    assert "completion_verification" in event_types
    assert "final_response_synthesized" in event_types
    assert event_types.index("completion_verification") < event_types.index("final_response_synthesized") < event_types.index("stop")
    completion = next(event for event in payload["events"] if event["event_type"] == "completion_verification")
    final_response = next(event for event in payload["events"] if event["event_type"] == "final_response_synthesized")
    stop = next(event for event in payload["events"] if event["event_type"] == "stop")
    assert "completion_verified" in completion["output"]
    assert "recommended_action" in completion["output"]
    assert final_response["output"]["content"]
    assert stop["output"]["final_response"] == final_response["output"]["content"]
