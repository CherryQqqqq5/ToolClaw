import json
import importlib.util
from pathlib import Path

from toolclaw.benchmarks.adapters import ToolSandboxAdapter


_SCORER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "score_toolsandbox_planner_sensitive.py"
_SPEC = importlib.util.spec_from_file_location("score_toolsandbox_planner_sensitive", _SCORER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_SCORER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SCORER)
detect_hint_leakage = _SCORER.detect_hint_leakage


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


def test_ordered_structure_leakage_detected_but_individual_tool_ids_allowed():
    source_row = {
        "planner_visible": {
            "candidate_tools": [
                {"tool_id": "source_lookup"},
                {"tool_id": "summary_builder"},
                {"tool_id": "report_writer"},
            ]
        },
        "scorer_gold": {
            "expected_capability_order": ["cap_retrieve", "cap_summarize", "cap_write"],
            "expected_dependency_edges": [["cap_retrieve", "cap_summarize"], ["cap_summarize", "cap_write"]],
            "expected_tool_sequence": ["source_lookup", "summary_builder", "report_writer"],
        },
    }
    clean = detect_hint_leakage({"metadata": {"candidate_tool_id": "source_lookup"}}, {}, source_row)
    assert clean["leakage_detected"] is False

    leaked = detect_hint_leakage(
        {"metadata": {"task_annotations": {"debug_order": ["cap_retrieve", "cap_summarize", "cap_write"]}}},
        {},
        source_row,
    )
    assert leaked["ordered_gold_structure_leakage_detected"] is True
    assert leaked["leakage_detected"] is True
