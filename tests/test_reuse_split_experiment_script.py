import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_reuse_split_experiment_script_generates_summary(tmp_path: Path) -> None:
    train_taskset = [
        {
            "task_id": "reuse_train_001",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool"],
            "categories": ["State Dependency", "Multiple Tool Call"],
            "ideal_turn_count": 2,
            "ideal_tool_calls": 2,
            "metadata": {"task_family": "t4_repeated_reusable"},
        }
    ]
    eval_taskset = [
        {
            "task_id": "reuse_eval_heldout_001",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool"],
            "categories": ["State Dependency", "Multiple Tool Call"],
            "ideal_turn_count": 2,
            "ideal_tool_calls": 2,
            "metadata": {"task_family": "t4_repeated_reusable"},
        }
    ]
    train_path = tmp_path / "train_taskset.json"
    eval_path = tmp_path / "eval_taskset.json"
    train_path.write_text(json.dumps(train_taskset), encoding="utf-8")
    eval_path.write_text(json.dumps(eval_taskset), encoding="utf-8")

    outdir = tmp_path / "reuse_split_out"
    cmd = [
        sys.executable,
        "scripts/run_reuse_split_experiment.py",
        "--train-taskset",
        str(train_path),
        "--eval-taskset",
        str(eval_path),
        "--outdir",
        str(outdir),
    ]
    completed = subprocess.run(
        cmd,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    summary_path = outdir / "reuse_split_summary.json"
    report_path = outdir / "reuse_split_report.md"
    assert summary_path.exists()
    assert report_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["num_train_tasks"] == 1
    assert summary["num_eval_tasks"] == 1
    assert set(summary["train_systems"]) == {"a4_reuse"}
    assert set(summary["eval_systems"]) == {"a3_interaction", "a4_reuse"}
    assert "a4_vs_a3_delta" in summary
    assert "t4_repeated_reusable" in summary["eval_per_family"]["a4_reuse"]

    report = report_path.read_text(encoding="utf-8")
    assert "ToolClaw Reuse Split Experiment" in report
    assert "Eval Aggregate" in report
    assert "Eval Delta (A4 Reuse vs A3 Interaction)" in report
