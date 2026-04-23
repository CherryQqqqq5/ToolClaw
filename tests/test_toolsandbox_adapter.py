import json

from toolclaw.benchmarks.adapters import BenchmarkSample, ToolSandboxAdapter


def test_toolsandbox_adapter_loads_samples_and_extracts_categories(tmp_path) -> None:
    source = tmp_path / "toolsandbox.json"
    source.write_text(
        json.dumps(
            [
                {
                    "name": "toolsandbox_001",
                    "messages": [{"sender": "user", "recipient": "agent", "content": "Book lunch and confirm the address"}],
                    "tool_allow_list": ["search_restaurant", "book_restaurant"],
                    "categories": ["Multiple Tool Call", "State Dependency"],
                }
            ]
        ),
        encoding="utf-8",
    )

    adapter = ToolSandboxAdapter()
    samples = adapter.load_samples(str(source))
    eval_task = adapter.to_eval_task(samples[0])

    assert len(samples) == 1
    assert samples[0].sample_id == "toolsandbox_001"
    assert samples[0].scenario == "multiple_tool"
    assert eval_task["query"] == "Book lunch and confirm the address"
    assert eval_task["metadata"]["toolsandbox_categories"] == ["multiple_tool", "state_dependency"]


def test_toolsandbox_adapter_build_request_uses_allow_list_and_message_query() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_002",
        raw_payload={
            "messages": [{"sender": "user", "recipient": "agent", "content": "Find Alex and message the ETA"}],
            "tool_allow_list": ["find_contact", "send_message"],
            "categories": ["Multiple User Turn", "Insufficient Information"],
            "milestones": ["find contact", "ask clarification", "send message"],
        },
    )

    request = adapter.build_request(sample)

    assert request.task.user_goal == "Find Alex and message the ETA"
    assert [tool.tool_id for tool in request.context.candidate_tools] == ["find_contact", "send_message"]
    assert request.context.candidate_tools[0].metadata["execution_backend"] == "semantic_mock"
    assert request.hints.user_style["benchmark"] == "toolsandbox"
    assert request.hints.user_style["requires_interaction"] is True
    assert request.hints.user_style["categories"] == ["multiple_user_turn", "insufficient_information"]
    assert request.hints.user_style["milestones"] == ["find contact", "ask clarification", "send message"]
    assert request.hints.user_style["tool_allow_list"] == ["find_contact", "send_message"]


def test_toolsandbox_adapter_scores_similarity_coverage_and_hallucination_avoidance() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_003",
        raw_payload={
            "categories": ["State Dependency", "Multiple Tool Call"],
            "tool_allow_list": ["search_mail", "send_mail"],
            "milestones": ["locate thread", "draft response", "send response"],
            "ideal_turn_count": 4,
            "ideal_tool_calls": 2,
            "result_summary": {"similarity": 0.1},
        },
    )
    trace_payload = {
        "metrics": {"success": False, "tool_calls": 3},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 0.9,
                "milestone_mapping": [0, 1, None],
                "turn_count": 5,
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {"event_type": "tool_call", "tool_id": "search_mail"},
            {"event_type": "tool_call", "tool_id": "send_mail"},
            {"event_type": "tool_call", "tool_id": "unexpected_tool"},
            {"event_type": "user_query"},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["execution_verified_success"] == 0.0
    assert score.metrics["proxy_summary_success"] == 0.0
    assert score.metrics["milestone_similarity"] == 0.9
    assert score.metrics["milestone_coverage"] == 2 / 3
    assert score.metrics["tool_efficiency"] < 1.0
    assert score.metrics["turn_efficiency"] < 1.0
    assert score.metrics["hallucination_avoidance"] == 0.0
    assert score.metrics["state_dependency_score"] == 0.9
    assert score.diagnostics["used_result_summary"] is True
    assert score.diagnostics["result_summary_source"] == "toolclaw_proxy"
    assert score.diagnostics["reference_result_summary_available"] is True


def test_toolsandbox_adapter_ignores_external_reference_summary_when_trace_summary_missing() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_004",
        raw_payload={
            "categories": ["State Dependency"],
            "milestones": ["disable wifi", "confirm wifi disabled"],
            "result_summary": {
                "similarity": 0.99,
                "milestone_mapping": [0, 1],
                "turn_count": 2,
            },
        },
    )
    trace_payload = {
        "metrics": {"success": False, "tool_calls": 1},
        "events": [
            {"event_type": "tool_call", "tool_id": "set_wifi_status"},
            {"event_type": "tool_result", "tool_id": "set_wifi_status"},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["milestone_similarity"] == 0.5
    assert score.metrics["milestone_coverage"] == 0.5
    assert score.diagnostics["used_result_summary"] is True
    assert score.diagnostics["result_summary_source"] == "toolclaw_proxy"
    assert score.diagnostics["reference_result_summary_available"] is True


def test_toolsandbox_adapter_strips_proxy_only_success_when_no_milestones_are_verified() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_proxy_only_001",
        raw_payload={
            "categories": ["State Dependency"],
            "milestones": [],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "matched_milestones": 0,
                "source": "toolclaw_proxy",
            }
        },
        "events": [{"event_type": "tool_result", "tool_id": "set_wifi_status"}],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["execution_verified_success"] == 0.0
    assert score.metrics["proxy_summary_success"] == 0.0
    assert score.metrics["milestone_similarity"] == 0.0
    assert score.metrics["milestone_coverage"] == 0.0
    assert score.metrics["state_dependency_score"] == 0.0
    assert score.diagnostics["result_summary_source"] == "toolclaw_proxy"


def test_toolsandbox_adapter_does_not_fallback_to_demo_tools_for_empty_tool_space() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_empty_tools_001",
        raw_payload={
            "messages": [{"sender": "user", "recipient": "agent", "content": "Do the thing."}],
            "candidate_tools": [],
            "tool_allow_list": [],
        },
    )

    request = adapter.build_request(sample)
    eval_task = adapter.to_eval_task(sample)

    assert request.context.candidate_tools == []
    assert eval_task["candidate_tools"] == []


def test_toolsandbox_adapter_preserves_execution_controls_in_eval_task() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_controls_001",
        raw_payload={
            "query": "Retrieve the compliance notes and write the approved report.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the compliance notes and write the approved report."}],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search"},
                {"tool_id": "write_tool", "description": "Write"},
            ],
            "tool_allow_list": ["search_tool", "write_tool"],
            "execution_scenario": "state_failure",
            "state_failure_mode": "wrong_write_target",
            "backup_tool_map": {"write_tool": "backup_write_tool"},
            "reuse_family_id": "reuse_case_001",
            "reuse_pass_index": 2,
            "wrong_target_path": "outputs/reports/shadow.txt",
            "reuse_override_inputs": {"cap_write": ["target_path"]},
        },
    )

    eval_task = adapter.to_eval_task(sample)

    assert eval_task["scenario"] == "state_failure"
    assert eval_task["state_failure_mode"] == "wrong_write_target"
    assert eval_task["backup_tool_map"] == {"write_tool": "backup_write_tool"}
    assert eval_task["reuse_family_id"] == "reuse_case_001"
    assert eval_task["reuse_pass_index"] == 2
    assert eval_task["wrong_target_path"] == "outputs/reports/shadow.txt"
    assert eval_task["reuse_override_inputs"] == {"cap_write": ["target_path"]}
    assert eval_task["tool_execution_backend"] == "semantic_mock"


def test_toolsandbox_adapter_proxy_capability_prefers_write_over_retrieval_words_in_writer_description() -> None:
    adapter = ToolSandboxAdapter()
    raw = {
        "candidate_tools": [
            {"tool_id": "write_tool", "description": "Standard writer used after retrieval once the retrieved summary is available."}
        ]
    }

    capability = adapter._infer_proxy_tool_capability(raw, "write_tool")

    assert capability == "write"


def test_toolsandbox_adapter_proxy_capability_prefers_write_over_state_update_wording() -> None:
    adapter = ToolSandboxAdapter()
    raw = {
        "candidate_tools": [
            {"tool_id": "write_tool", "description": "Primary writer for board update reports after retrieval."}
        ]
    }

    capability = adapter._infer_proxy_tool_capability(raw, "write_tool")

    assert capability == "write"


def test_toolsandbox_adapter_rejects_verified_success_when_write_target_path_is_wrong() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_reuse_family_001__pass2",
        raw_payload={
            "categories": ["Multiple Tool Call", "Insufficient Information"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search"},
                {"tool_id": "write_tool", "description": "Write"},
            ],
            "milestones": ["retrieve handoff summary", "prepare report", "write report"],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 2},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0, 1, 2],
                "turn_count": 4,
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {"event_type": "tool_call", "tool_id": "search_tool", "tool_args": {"query": "Retrieve the same customer handoff summary again and write the matching support handoff report."}},
            {"event_type": "tool_call", "tool_id": "write_tool", "tool_args": {"target_path": "outputs/toolsandbox/reports/toolsandbox_env_backup_001.txt"}},
            {"event_type": "tool_result", "tool_id": "write_tool"},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["execution_verified_success"] == 0.0
    assert score.metrics["proxy_summary_success"] == 1.0
    assert score.metrics["write_target_verified"] == 0.0
    assert score.diagnostics["expected_target_path"] == "outputs/toolsandbox/reports/toolsandbox_reuse_family_001__pass2.txt"
    assert score.diagnostics["observed_target_path"] == "outputs/toolsandbox/reports/toolsandbox_env_backup_001.txt"


def test_proxy_progress_signals_count_distinct_write_tools_for_planner_sensitive_depth() -> None:
    adapter = ToolSandboxAdapter()
    raw = {
        "categories": ["Multiple Tool Call", "State Dependency"],
        "candidate_tools": [
            {"tool_id": "search_tool", "description": "Retrieve and summarize the board update details."},
            {"tool_id": "archive_write_tool", "description": "Read-only archive writer for historical snapshots only."},
            {"tool_id": "write_tool", "description": "Standard primary writer for the final board update report."},
        ],
        "milestones": ["retrieve board update summary", "prune archive writer", "save final board update report"],
        "ideal_tool_calls": 2,
    }
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 3},
        "events": [
            {"event_type": "tool_call", "tool_id": "search_tool"},
            {"event_type": "tool_call", "tool_id": "archive_write_tool", "tool_args": {"target_path": "outputs/tmp/archive.txt"}},
            {"event_type": "tool_call", "tool_id": "write_tool", "tool_args": {"target_path": "outputs/tmp/final.txt"}},
        ],
    }
    signals = adapter._proxy_progress_signals(raw, trace_payload)
    # retrieve + two distinct write tools + success_bonus (progress_base >= 2)
    assert signals >= 4


def test_write_target_verification_accepts_normalized_relative_paths() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_path_norm_001",
        raw_payload={
            "target_path": "outputs/toolsandbox/reports/toolsandbox_path_norm_001.txt",
            "categories": ["State Dependency"],
            "milestones": ["write"],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0],
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {
                "event_type": "tool_call",
                "tool_id": "write_tool",
                "tool_args": {"target_path": "./outputs/toolsandbox/reports/toolsandbox_path_norm_001.txt"},
            },
        ],
    }
    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["write_target_verified"] == 1.0
    assert score.metrics["execution_verified_success"] == 1.0


def test_toolsandbox_adapter_distinguishes_probe_only_interaction_from_repair_interaction() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_probe_only_001",
        raw_payload={
            "categories": ["Multiple User Turn", "Insufficient Information"],
            "milestones": ["ask", "complete"],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0, 1],
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {
                "event_type": "user_query",
                "metadata": {
                    "query_metadata": {"interaction_probe": True},
                },
            },
            {
                "event_type": "user_reply",
                "metadata": {
                    "reply_metadata": {"interaction_probe": True, "decoded_intent_type": "interaction_probe"},
                },
            },
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["execution_verified_success"] == 1.0
    assert score.metrics["strict_scored_success"] == 1.0
    assert score.metrics["interaction_contract_satisfied"] == 1.0
    assert score.metrics["repair_interaction_satisfied"] == 0.0
    assert score.metrics["repair_scored_success"] == 0.0
    assert score.diagnostics["probe_user_queries"] == 1
    assert score.diagnostics["repair_user_queries"] == 0
    assert score.diagnostics["probe_user_replies"] == 1
    assert score.diagnostics["repair_user_replies"] == 0


def test_toolsandbox_adapter_counts_non_probe_interaction_as_repair_success() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_repair_only_001",
        raw_payload={
            "categories": ["Multiple User Turn", "Insufficient Information"],
            "milestones": ["ask", "complete"],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0, 1],
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {
                "event_type": "user_query",
                "metadata": {
                    "query_metadata": {"patch_targets": {"time": "step.inputs.time"}},
                },
            },
            {
                "event_type": "user_reply",
                "metadata": {
                    "reply_metadata": {"decoded_intent_type": "slot_fill", "decoded_slot_updates": {"time": "tomorrow 9am"}},
                },
            },
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["execution_verified_success"] == 1.0
    assert score.metrics["interaction_contract_satisfied"] == 1.0
    assert score.metrics["repair_interaction_satisfied"] == 1.0
    assert score.metrics["repair_scored_success"] == 1.0
    assert score.diagnostics["probe_user_queries"] == 0
    assert score.diagnostics["repair_user_queries"] == 1


def test_toolsandbox_adapter_accepts_approval_request_as_interaction_contract() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_approval_contract_001",
        raw_payload={
            "categories": ["Multiple User Turn"],
            "milestones": ["approve", "complete"],
            "constraints": {"requires_user_approval": True},
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0, 1],
                "source": "toolclaw_proxy",
            }
        },
        "events": [
            {
                "event_type": "approval_request",
                "output": {"expected_answer_type": "approval"},
            },
            {
                "event_type": "approval_response",
                "output": {"approved": True},
            },
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["execution_verified_success"] == 1.0
    assert score.metrics["interaction_contract_satisfied"] == 1.0
    assert score.metrics["strict_scored_success"] == 1.0
    assert score.metrics["repair_interaction_satisfied"] == 1.0
    assert score.diagnostics["approval_requests"] == 1
    assert score.diagnostics["approval_responses"] == 1


def test_toolsandbox_adapter_keeps_execution_verified_separate_from_interaction_gate() -> None:
    adapter = ToolSandboxAdapter()
    sample = BenchmarkSample(
        sample_id="toolsandbox_gate_split_001",
        raw_payload={
            "categories": ["Multiple User Turn"],
            "milestones": ["ask", "complete"],
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 1},
        "metadata": {
            "toolsandbox_result": {
                "similarity": 1.0,
                "milestone_mapping": [0, 1],
                "source": "toolclaw_proxy",
            }
        },
        "events": [],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["execution_verified_success"] == 1.0
    assert score.metrics["interaction_contract_satisfied"] == 0.0
    assert score.metrics["strict_scored_success"] == 0.0
