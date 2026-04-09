import json

from toolclaw.benchmarks.adapters import BenchmarkSample, Tau2BenchAdapter


def test_tau2_adapter_loads_samples_and_builds_eval_task(tmp_path) -> None:
    source = tmp_path / "tau2.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau2_001",
                    "scenario": "binding_failure",
                    "query": "retrieve and write report",
                    "simulated_policy": {"mode": "cooperative", "missing_arg_values": {"target_path": "outputs/x.txt"}},
                }
            ]
        ),
        encoding="utf-8",
    )

    adapter = Tau2BenchAdapter()
    samples = adapter.load_samples(str(source))
    eval_task = adapter.to_eval_task(samples[0])

    assert len(samples) == 1
    assert eval_task["task_id"] == "tau2_001"
    assert eval_task["scenario"] == "binding_failure"
    assert eval_task["metadata"]["requires_interaction"] is True
    assert eval_task["simulated_policy"]["mode"] == "cooperative"


def test_tau2_adapter_preserves_phase2_fields() -> None:
    adapter = Tau2BenchAdapter()
    sample = BenchmarkSample(
        sample_id="tau2_state_001",
        scenario="state_failure",
        raw_payload={
            "query": "retrieve and write report",
            "primary_failtax": "state",
            "failtaxes": ["state", "recovery"],
            "task_family": "t1_static_recovery",
            "state_slots": ["retrieved_info"],
            "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
            "gold_recovery_class": "patch_state_then_retry",
            "budget_profile": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
            "constraints": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
            "reuse_override_inputs": {"cap_write": ["target_path"]},
            "wrong_target_path": "outputs/wrong.txt",
        },
    )

    eval_task = adapter.to_eval_task(sample)

    assert eval_task["primary_failtax"] == "state"
    assert eval_task["task_family"] == "t1_static_recovery"
    assert eval_task["state_slots"] == ["retrieved_info"]
    assert eval_task["expected_recovery_path"] == "patch_state_then_retry"
    assert eval_task["budget_profile"]["max_user_turns"] == 1
    assert eval_task["reuse_override_inputs"] == {"cap_write": ["target_path"]}
    assert eval_task["wrong_target_path"] == "outputs/wrong.txt"


def test_tau2_adapter_build_request_uses_interaction_hints() -> None:
    adapter = Tau2BenchAdapter()
    sample = BenchmarkSample(
        sample_id="tau2_002",
        scenario="environment_failure",
        raw_payload={
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool", "backup_write_tool"],
            "simulated_policy": {"mode": "cooperative"},
        },
    )

    request = adapter.build_request(sample)

    assert request.task.task_id == "tau2_002"
    assert request.hints.user_style["benchmark"] == "tau2_bench"
    assert request.hints.user_style["requires_interaction"] is True
    assert request.hints.user_style["scenario"] == "environment_failure"
    assert request.hints.user_style["primary_failtax"] == "recovery"


def test_tau2_adapter_scores_interaction_and_repair_metrics() -> None:
    adapter = Tau2BenchAdapter()
    sample = BenchmarkSample(
        sample_id="tau2_003",
        scenario="binding_failure",
        raw_payload={
            "expected_user_turns": 1,
            "expected_repairs": 1,
            "simulated_policy": {"mode": "cooperative"},
        },
    )
    trace_payload = {
        "metrics": {"success": True, "tool_calls": 2, "repair_actions": 1},
        "events": [
            {"event_type": "user_query"},
            {"event_type": "user_reply"},
            {"event_type": "repair_triggered", "output": {"repair_type": "ask_user"}},
            {"event_type": "stop", "output": {"reason": "success_criteria_satisfied"}},
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is True
    assert score.metrics["interactive_correction"] >= 2.0
    assert score.metrics["interaction_efficiency"] > 0.0
    assert score.metrics["repair_salvage"] == 1.0
    assert score.metrics["repair_efficiency"] > 0.0
