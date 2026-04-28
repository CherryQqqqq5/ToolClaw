from __future__ import annotations

import json

from toolclaw.execution.completion_verifier import CompletionVerificationResult
from toolclaw.execution.final_response import FinalResponseSynthesizer
from toolclaw.schemas.trace import EventType, Trace
from toolclaw.schemas.workflow import ActionType, Workflow, WorkflowStep


def _workflow(goal: str = "Update the requested status.") -> Workflow:
    workflow = Workflow.demo()
    workflow.task.task_id = "final_response_test"
    workflow.task.user_goal = goal
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_update_state",
            tool_id="generic_state_tool",
            action_type=ActionType.TOOL_CALL,
            inputs={"status": "enabled"},
            expected_output="updated status",
        )
    ]
    return workflow


def test_final_response_synthesizer_generates_nonempty_runtime_response() -> None:
    workflow = _workflow()
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="generic_state_tool",
        output={"status": "success", "payload": "state value updated"},
    )

    result = FinalResponseSynthesizer().synthesize(
        workflow=workflow,
        trace=trace,
        state_values={"status": "enabled"},
        completion_verification=CompletionVerificationResult(completion_verified=True, confidence=0.8),
    )

    assert result.content
    assert result.policy_version == "generic_final_response_v1"
    assert result.used_gold is False
    assert "tool_results" in result.evidence_sources
    assert "update" in result.metadata["action_kind"]


def test_final_response_synthesizer_does_not_emit_scorer_gold() -> None:
    workflow = _workflow()
    workflow.metadata["milestones"] = ["SECRET_MILESTONE"]
    workflow.metadata["reference_result_summary"] = {"secret": "SECRET_REFERENCE"}
    workflow.execution_plan[0].inputs["official_milestone_mapping"] = "SECRET_MAPPING"
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="generic_state_tool",
        output={
            "status": "success",
            "payload": "state value updated",
            "reference_result_summary": "SECRET_REFERENCE",
            "scorer_gold_messages": ["SECRET_GOLD"],
        },
    )

    result = FinalResponseSynthesizer().synthesize(workflow=workflow, trace=trace, state_values={})
    serialized = json.dumps(result.to_dict())

    assert "SECRET_MILESTONE" not in serialized
    assert "SECRET_REFERENCE" not in serialized
    assert "SECRET_MAPPING" not in serialized
    assert "SECRET_GOLD" not in serialized


def test_final_response_synthesizer_uses_generic_action_templates() -> None:
    workflow = _workflow(goal="Send the requested message to the selected contact.")
    workflow.execution_plan[0].capability_id = "cap_send_message"
    workflow.execution_plan[0].tool_id = "generic_message_sender"
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="generic_message_sender",
        output={"status": "success", "payload": "sent message to selected contact"},
    )

    result = FinalResponseSynthesizer().synthesize(workflow=workflow, trace=trace, state_values={})

    assert "sent" in result.content.lower()


def test_final_response_synthesizer_prefers_last_tool_result_for_multistep_workflows() -> None:
    workflow = _workflow(goal="How many days is it till Christmas Day")
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_check",
            tool_id="get_current_timestamp",
            action_type=ActionType.TOOL_CALL,
            inputs={},
            expected_output="current_timestamp",
        ),
        WorkflowStep(
            step_id="step_02",
            capability_id="cap_retrieve",
            tool_id="search_holiday",
            action_type=ActionType.TOOL_CALL,
            inputs={"query": "How many days is it till Christmas Day"},
            expected_output="retrieved_info",
        ),
        WorkflowStep(
            step_id="step_03",
            capability_id="cap_retrieve",
            tool_id="timestamp_diff",
            action_type=ActionType.TOOL_CALL,
            inputs={},
            expected_output="timestamp_diff_result",
        ),
    ]
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result_01",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="get_current_timestamp",
        output={"status": "success", "payload": "current timestamp"},
    )
    trace.add_event(
        event_id="evt_result_02",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="search_holiday",
        output={"status": "success", "payload": "holiday lookup"},
    )
    trace.add_event(
        event_id="evt_result_03",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="timestamp_diff",
        output={"status": "success", "payload": "time difference between current timestamp and holiday lookup"},
    )

    result = FinalResponseSynthesizer().synthesize(workflow=workflow, trace=trace, state_values={})

    assert "time difference between current timestamp and holiday lookup" in result.content
    assert "How many days is it till Christmas Day" in result.content


def test_final_response_synthesizer_renders_typed_timestamp_diff_payload() -> None:
    workflow = _workflow(goal="How many days is it till Christmas Day")
    workflow.execution_plan[0].tool_id = "timestamp_diff"
    workflow.execution_plan[0].expected_output = "timestamp_diff_result"
    trace = Trace(run_id="run", workflow_id=workflow.workflow_id, task_id=workflow.task.task_id)
    trace.add_event(
        event_id="evt_result",
        event_type=EventType.TOOL_RESULT,
        actor="environment",
        tool_id="timestamp_diff",
        output={"status": "success", "payload": {"days": 242, "seconds": 18490}},
    )

    result = FinalResponseSynthesizer().synthesize(workflow=workflow, trace=trace, state_values={})

    assert "242 days and 18490 seconds" in result.content
