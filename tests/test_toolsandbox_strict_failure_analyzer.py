from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_script():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_toolsandbox_strict_failures.py"
    spec = importlib.util.spec_from_file_location("analyze_toolsandbox_strict_failures", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _trace(path: Path, events):
    path.write_text(json.dumps({"events": events, "metrics": {"success": True}}), encoding="utf-8")


def test_raw_success_strict_fail_classifies_interaction_gap(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {"event_type": "tool_call", "tool_id": "write_tool", "output": None},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task_interaction",
            "system": "s4_reuse_overlay",
            "failure_type": "multiple_user_turn",
            "primary_failtax": "selection",
            "failtaxes": '["selection", "recovery"]',
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "stop_reason": "success_criteria_satisfied",
            "repair_user_queries": "0",
            "trace_path": str(trace),
        }
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    assert summary["failure_row_count"] == 1
    assert summary["unique_failed_task_count"] == 1
    assert summary["raw_success_but_strict_fail_count"] == 1
    record = summary["records"][0]
    assert record["failure_category"] == "interaction_trigger_or_decoder_gap"
    assert record["error_subtype"] == "multiple_user_turn_no_user_query"
    assert record["candidate_owning_layer"] == "s3_interaction_overlay"


def test_trace_evidence_extracts_repair_and_missing_metadata(tmp_path: Path) -> None:
    module = _load_script()
    payload = {
        "events": [
            {
                "event_type": "repair_triggered",
                "output": {
                    "repair_type": "ask_user",
                    "metadata": {"missing_input_keys": ["phone"]},
                    "actions": [
                        {
                            "metadata": {
                                "missing_targets": ["email"],
                                "state_slot": "contact",
                            }
                        }
                    ],
                    "interaction": {"expected_answer_type": "email"},
                },
                "metadata": {
                    "state_context": {"missing_assets": ["profile"]},
                },
            },
            {
                "event_type": "repair_failed",
                "output": {"reason": "no concrete value"},
            },
        ]
    }

    evidence = module.extract_trace_evidence(payload)

    assert evidence["repair_type_chosen"] == "ask_user"
    assert evidence["repair_applied"] is False
    assert "no concrete value" in evidence["repair_blocked"]
    assert evidence["missing_input_keys"] == ["phone", "email"]
    assert evidence["state_context"]["missing_assets"] == ["contact", "profile"]
    assert "email" in evidence["raw_message_pattern"]


def test_first_failed_layer_from_paired_system_rows(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(trace, [{"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}}])
    rows = [
        {"run_index": "1", "task_id": "task", "system": "s0_baseline", "strict_scored_success": "True"},
        {"run_index": "1", "task_id": "task", "system": "s1_recovery", "strict_scored_success": "True"},
        {"run_index": "1", "task_id": "task", "system": "s2_planner_overlay", "strict_scored_success": "False"},
        {"run_index": "1", "task_id": "task", "system": "s3_interaction_overlay", "strict_scored_success": "False"},
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "state_failure",
            "primary_failtax": "state",
            "failtaxes": '["state"]',
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    assert summary["records"][0]["first_failed_layer"] == "s2_planner_overlay"
    assert summary["failure_category_counts"]["state_precondition_gap"] == 1


def test_analyzer_maps_completion_verifier_to_subcause(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {
                "event_type": "completion_verification",
                "output": {
                    "completion_verified": False,
                    "missing_evidence": ["user_clarification_for_ambiguous_goal"],
                    "recommended_action": "ask_user",
                },
            },
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "multiple_user_turn",
            "primary_failtax": "selection",
            "failtaxes": '["selection"]',
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    assert summary["records"][0]["failure_subcause"] == "missing_interaction_gap"
    assert summary["failure_subcause_counts"]["missing_interaction_gap"] == 1


def test_analyzer_reports_final_response_contract_subcause(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {"event_type": "final_response_synthesized", "output": {"content": "I completed the requested task."}},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied", "final_response": "I completed the requested task."}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "multiple_user_turn",
            "primary_failtax": "selection",
            "failtaxes": '["selection"]',
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "False",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    assert summary["final_response_present_count"] == 1
    assert summary["records"][0]["failure_subcause"] == "interaction_contract_still_blocked"


def test_analyzer_reports_final_response_absent_subcause(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(trace, [{"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}}])
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "single_tool",
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    assert summary["final_response_absent_count"] == 1
    assert summary["records"][0]["failure_subcause"] == "final_response_absent"


def test_workflow_residual_detects_missing_mutating_action_after_clock_only(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {
                "event_type": "tool_call",
                "tool_id": "get_current_timestamp",
                "tool_args": {"query": "Remind me to buy milk tomorrow at 5PM"},
            },
            {
                "event_type": "tool_result",
                "tool_id": "get_current_timestamp",
                "output": {"status": "success", "payload": "current timestamp"},
            },
            {"event_type": "final_response_synthesized", "output": {"content": "I created the reminder."}},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "canonicalization",
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    record = summary["records"][0]
    assert record["workflow_residual"] == "missing_action_step"
    assert summary["workflow_residual_counts"]["missing_action_step"] == 1
    assert record["semantic_payload_placeholder"] is False
    assert record["domain_state_evidence_present"] is False


def test_workflow_residual_detects_placeholder_search_summary(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {
                "event_type": "tool_call",
                "tool_id": "search_messages",
                "tool_args": {"query": "Find the latest message from Alex"},
            },
            {
                "event_type": "tool_result",
                "tool_id": "search_messages",
                "output": {"status": "success", "payload": "summary for: Find the latest message from Alex"},
            },
            {"event_type": "final_response_synthesized", "output": {"content": "I found the message."}},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "canonicalization",
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    record = summary["records"][0]
    assert record["workflow_residual"] == "summary_not_field_evidence"
    assert record["semantic_payload_placeholder"] is True
    assert record["placeholder_tool_ids"] == ["search_messages"]
    assert record["domain_state_evidence_present"] is False


def test_workflow_residual_detects_mutation_without_state_delta(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {
                "event_type": "tool_call",
                "tool_id": "modify_contact",
                "tool_args": {"person_id": "person_1", "phone_number": "555-0101"},
            },
            {
                "event_type": "tool_result",
                "tool_id": "modify_contact",
                "output": {"status": "success", "payload": "tool modify_contact executed successfully"},
            },
            {"event_type": "final_response_synthesized", "output": {"content": "I updated the contact."}},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "canonicalization",
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    record = summary["records"][0]
    assert record["workflow_residual"] == "missing_state_diff"
    assert record["semantic_payload_placeholder"] is True
    assert record["placeholder_tool_ids"] == ["modify_contact"]
    assert record["domain_state_evidence_present"] is False


def test_workflow_residual_keeps_typed_payload_as_rendering_gap(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _trace(
        trace,
        [
            {
                "event_type": "tool_call",
                "tool_id": "search_messages",
                "tool_args": {"query": "latest message from Alex"},
            },
            {
                "event_type": "tool_result",
                "tool_id": "search_messages",
                "output": {
                    "status": "success",
                    "payload": [{"message_id": "msg_1", "content": "Bring the report", "sender_person_id": "person_1"}],
                },
            },
            {"event_type": "final_response_synthesized", "output": {"content": "Bring the report"}},
            {"event_type": "stop", "output": {"status": "success", "reason": "success_criteria_satisfied"}},
        ],
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "failure_type": "canonicalization",
            "strict_scored_success": "False",
            "raw_execution_success": "True",
            "execution_verified_success": "True",
            "interaction_contract_satisfied": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": str(trace),
        },
    ]

    summary = module.build_taxonomy(rows, repo_root=tmp_path)

    record = summary["records"][0]
    assert record["workflow_residual"] == "pure_final_rendering"
    assert record["semantic_payload_placeholder"] is False
    assert record["domain_state_evidence_present"] is True
