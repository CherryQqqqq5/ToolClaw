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
    assert request.hints.user_style["benchmark"] == "toolsandbox"
    assert request.hints.user_style["requires_interaction"] is True
    assert request.hints.user_style["categories"] == ["multiple_user_turn", "insufficient_information"]


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
            "result_summary": {
                "similarity": 0.9,
                "milestone_mapping": [0, 1, None],
                "turn_count": 5,
            },
        },
    )
    trace_payload = {
        "metrics": {"success": False, "tool_calls": 3},
        "events": [
            {"event_type": "tool_call", "tool_id": "search_mail"},
            {"event_type": "tool_call", "tool_id": "send_mail"},
            {"event_type": "tool_call", "tool_id": "unexpected_tool"},
            {"event_type": "user_query"},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["milestone_similarity"] == 0.9
    assert score.metrics["milestone_coverage"] == 2 / 3
    assert score.metrics["tool_efficiency"] < 1.0
    assert score.metrics["turn_efficiency"] < 1.0
    assert score.metrics["hallucination_avoidance"] == 0.0
    assert score.metrics["state_dependency_score"] == 0.9
    assert score.diagnostics["used_result_summary"] is True
