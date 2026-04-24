import csv
import json
import subprocess
import sys
from pathlib import Path


def _write_csv(path: Path, rows):
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_planner_sensitive_scorer_handles_proxy_order_and_missing_trace(tmp_path):
    source = tmp_path / "source.jsonl"
    trace = tmp_path / "trace_a2.json"
    trace.write_text(
        json.dumps(
            {
                "metadata": {"planner_mode": "planner"},
                "events": [
                    {"event_type": "tool_call", "tool_id": "source_lookup"},
                    {"event_type": "tool_call", "tool_id": "summary_builder"},
                    {"event_type": "tool_call", "tool_id": "report_writer"},
                ],
            }
        ),
        encoding="utf-8",
    )
    source_row = {
        "task_id": "planner_sensitive_test",
        "family": "retrieve_summarize_write",
        "planner_sensitive_protocol": "planner_sensitive_v1",
        "planner_visible": {
            "query": "Retrieve, summarize, and write.",
            "candidate_tools": [
                {"tool_id": "report_writer", "description": "Write final report.", "semantic_tags": ["write"]},
                {"tool_id": "source_lookup", "description": "Retrieve source.", "semantic_tags": ["retrieve"]},
                {"tool_id": "summary_builder", "description": "Summarize source.", "semantic_tags": ["summarize"]},
            ],
        },
        "scorer_gold": {
            "expected_capability_order": ["cap_retrieve", "cap_summarize", "cap_write"],
            "expected_dependency_edges": [["cap_retrieve", "cap_summarize"], ["cap_summarize", "cap_write"]],
            "expected_tool_sequence": ["source_lookup", "summary_builder", "report_writer"],
            "required_state_slots_by_step": {"cap_summarize": ["cap_retrieve"], "cap_write": ["cap_summarize"]},
            "forbidden_shortcuts": [],
        },
    }
    source.write_text(json.dumps(source_row) + "\n", encoding="utf-8")
    comparison = tmp_path / "comparison.scored.csv"
    _write_csv(
        comparison,
        [
            {
                "run_index": "1",
                "task_id": "planner_sensitive_test",
                "system": "a1_recovery",
                "strict_scored_success": "0",
                "raw_success": "0",
                "trace_path": str(tmp_path / "missing_a1.json"),
                "tool_calls": "1",
                "stop_reason": "failed",
            },
            {
                "run_index": "1",
                "task_id": "planner_sensitive_test",
                "system": "a2_planner",
                "strict_scored_success": "1",
                "raw_success": "1",
                "trace_path": str(trace),
                "tool_calls": "3",
                "stop_reason": "success_criteria_satisfied",
            },
        ],
    )
    outdir = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            "scripts/score_toolsandbox_planner_sensitive.py",
            "--source",
            str(source),
            "--comparison",
            str(comparison),
            "--outdir",
            str(outdir),
        ],
        check=True,
    )
    summary = json.loads((outdir / "planner_sensitive_summary.json").read_text(encoding="utf-8"))
    assert summary["paired_wins_losses_ties"]["wins"] == 1
    assert summary["deltas"]["a2_minus_a1_success_delta"] == 1.0
    assert summary["per_system"]["a1_recovery"]["trace_missing_count"] == 1
    assert summary["per_system"]["a2_planner"]["planner_bypass_rate"] in ("unknown", 0.0)
    leakage = json.loads((outdir / "hint_leakage_report.json").read_text(encoding="utf-8"))
    assert leakage["leakage_detected"] is False


def test_hint_leakage_audit_flags_gold_key_in_trace_metadata(tmp_path):
    source = tmp_path / "source.jsonl"
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"metadata": {"expected_tool_sequence": ["source_lookup"]}, "events": []}), encoding="utf-8")
    source_row = {
        "task_id": "planner_sensitive_leak",
        "family": "retrieve_summarize_write",
        "planner_sensitive_protocol": "planner_sensitive_v1",
        "planner_visible": {"query": "x", "candidate_tools": [{"tool_id": "source_lookup"}]},
        "scorer_gold": {
            "expected_capability_order": ["cap_retrieve"],
            "expected_dependency_edges": [],
            "expected_tool_sequence": ["source_lookup"],
            "required_state_slots_by_step": {},
            "forbidden_shortcuts": [],
        },
    }
    source.write_text(json.dumps(source_row) + "\n", encoding="utf-8")
    comparison = tmp_path / "comparison.scored.csv"
    _write_csv(
        comparison,
        [
            {
                "run_index": "1",
                "task_id": "planner_sensitive_leak",
                "system": "a2_planner",
                "strict_scored_success": "1",
                "trace_path": str(trace),
                "tool_calls": "1",
                "stop_reason": "success_criteria_satisfied",
            }
        ],
    )
    outdir = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            "scripts/score_toolsandbox_planner_sensitive.py",
            "--source",
            str(source),
            "--comparison",
            str(comparison),
            "--outdir",
            str(outdir),
        ],
        check=True,
    )
    leakage = json.loads((outdir / "hint_leakage_report.json").read_text(encoding="utf-8"))
    assert leakage["leakage_detected"] is True
