import json

from toolclaw.benchmarks.adapters import BenchmarkSample, TauBenchAdapter


def test_tau_adapter_loads_json_list_and_builds_eval_task(tmp_path) -> None:
    source = tmp_path / "tau.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau_001",
                    "query": "retrieve and write report",
                    "scenario": "success",
                    "candidate_tools": ["search_tool", "write_tool"],
                }
            ]
        ),
        encoding="utf-8",
    )

    adapter = TauBenchAdapter()
    samples = adapter.load_samples(str(source))
    eval_task = adapter.to_eval_task(samples[0])

    assert len(samples) == 1
    assert eval_task["task_id"] == "tau_001"
    assert eval_task["query"] == "retrieve and write report"


def test_tau_adapter_build_request_uses_candidate_tools(tmp_path) -> None:
    source = tmp_path / "tau.jsonl"
    source.write_text(
        json.dumps(
            {
                "sample_id": "tau_002",
                "instruction": "find and save",
                "candidate_tools": [{"tool_id": "search_tool", "description": "search"}, {"tool_id": "write_tool", "description": "write"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    adapter = TauBenchAdapter()
    sample = adapter.load_samples(str(source))[0]
    request = adapter.build_request(sample)

    assert request.task.task_id == "tau_002"
    assert len(request.context.candidate_tools) == 2


def test_tau_adapter_scores_rule_following_and_interaction_quality() -> None:
    adapter = TauBenchAdapter()
    sample = BenchmarkSample(
        sample_id="tau_003",
        scenario="policy_failure",
        raw_payload={
            "constraints": {"requires_user_approval": True, "forbidden_actions": ["delete"]},
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 2, "repair_actions": 1},
        "events": [
            {"event_type": "tool_call", "tool_id": "search_tool"},
            {"event_type": "repair_triggered", "output": {"repair_type": "request_approval"}},
            {"event_type": "approval_request"},
            {"event_type": "approval_response"},
            {"event_type": "stop", "output": {"reason": "success_criteria_satisfied"}},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.metrics["rule_following"] > 0.5
    assert score.metrics["interaction_quality"] > 0.5
