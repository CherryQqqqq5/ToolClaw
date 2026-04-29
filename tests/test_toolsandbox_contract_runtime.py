from __future__ import annotations

import json

from toolclaw.schemas.workflow import ToolSpec, Workflow, WorkflowStep
from toolclaw.tools.mock_tools import ToolExecutionError
from toolclaw.tools.runtime import run_tool
from toolclaw.tools.toolsandbox_contract import run_toolsandbox_contract_tool


def _workflow() -> Workflow:
    workflow = Workflow.demo()
    workflow.metadata["benchmark"] = "toolsandbox"
    workflow.metadata["tool_execution_backend"] = "semantic_mock"
    workflow.metadata["messages"] = [
        {"sender": "user", "content": "What is my first text?"},
        {
            "sender": "tool",
            "content": str(
                [
                    {
                        "message_id": "msg_2",
                        "sender_phone_number": "+15550000002",
                        "recipient_phone_number": "+15550000001",
                        "content": "second visible message",
                        "creation_timestamp": 20.0,
                    },
                    {
                        "message_id": "msg_1",
                        "sender_phone_number": "+15550000003",
                        "recipient_phone_number": "+15550000001",
                        "content": "first visible message",
                        "creation_timestamp": 10.0,
                    },
                ]
            ),
        },
        {"sender": "assistant", "content": "SECRET_GOLD_FINAL_ANSWER"},
    ]
    workflow.metadata["reference_result_summary"] = {"content": "SECRET_GOLD_RESULT_SUMMARY"}
    workflow.metadata["official_milestone_contract"] = [{"content": "SECRET_GOLD_MILESTONE"}]
    workflow.context.candidate_tools = [
        ToolSpec(
            tool_id="search_messages",
            description="Search messages.",
            metadata={"execution_backend": "toolsandbox_contract"},
        )
    ]
    workflow.execution_plan = [
        WorkflowStep(
            step_id="step_01",
            capability_id="cap_search",
            tool_id="search_messages",
            inputs={"query": "first text"},
            expected_output="messages",
        )
    ]
    return workflow


def test_contract_runtime_returns_typed_search_message_records_without_gold_leakage() -> None:
    result = run_tool("search_messages", {"query": "first text"}, workflow=_workflow())

    assert result["status"] == "success"
    assert result["metadata"]["backend"] == "toolsandbox_contract"
    assert result["metadata"]["placeholder_payload"] is False
    assert result["metadata"]["domain_state_evidence_present"] is True
    assert result["payload"][0]["message_id"] == "msg_1"
    assert result["payload"][0]["content"] == "first visible message"
    serialized = json.dumps(result, sort_keys=True)
    assert "SECRET_GOLD" not in serialized
    assert "summary for:" not in serialized


def test_contract_runtime_modify_contact_requires_identifier_and_returns_state_patch() -> None:
    result = run_toolsandbox_contract_tool(
        "modify_contact",
        {"person_id": "person_1", "phone_number": "+15550001111"},
        workflow=_workflow(),
    )

    assert result["payload"]["person_id"] == "person_1"
    assert result["payload"]["phone_number"] == "+15550001111"
    assert result["payload"]["state_patch"]["operation"] == "modify_contact"
    assert result["state_patch"]["last_contact"]["person_id"] == "person_1"


def test_contract_runtime_fails_closed_without_required_mutation_inputs() -> None:
    try:
        run_toolsandbox_contract_tool("send_message_with_phone_number", {"content": "hello"}, workflow=_workflow())
    except ToolExecutionError as exc:
        assert "phone_number" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("send_message_with_phone_number should fail without a recipient phone number")
