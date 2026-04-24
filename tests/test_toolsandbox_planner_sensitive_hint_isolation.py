import json

from toolclaw.benchmarks.adapters import ToolSandboxAdapter


def _sample():
    adapter = ToolSandboxAdapter()
    row = json.loads(open("data/toolsandbox_planner_sensitive_v1.jsonl", encoding="utf-8").readline())
    return adapter, adapter._make_sample(row, 1)


def test_scorer_gold_does_not_enter_planning_request_hints():
    adapter, sample = _sample()
    request = adapter.build_request(sample)
    hints_text = json.dumps(request.hints.user_style, sort_keys=True)
    for leaked_key in ToolSandboxAdapter.PLANNER_SENSITIVE_GOLD_KEYS:
        assert leaked_key not in hints_text
    assert request.hints.user_style["planner_sensitive_protocol"] == "planner_sensitive_v1"
    assert request.hints.user_style["tool_allow_list"] == []
    assert request.hints.user_style["milestones"] == []
    assert request.hints.user_style["ideal_tool_calls"] is None
    assert request.context.candidate_tools


def test_scorer_gold_does_not_enter_eval_task_metadata_or_benchmark_hints():
    adapter, sample = _sample()
    eval_task = adapter.to_eval_task(sample)
    task_text = json.dumps(eval_task, sort_keys=True)
    metadata_text = json.dumps(eval_task["metadata"], sort_keys=True)
    for leaked_key in ToolSandboxAdapter.PLANNER_SENSITIVE_GOLD_KEYS:
        assert leaked_key not in task_text
        assert leaked_key not in metadata_text
    assert eval_task["metadata"]["planner_sensitive_protocol"] == "planner_sensitive_v1"
    assert eval_task["tool_allow_list"] == []
    assert eval_task["milestones"] == []
    assert eval_task["ideal_tool_calls"] is None
    assert "benchmark_hints" not in eval_task["metadata"]
