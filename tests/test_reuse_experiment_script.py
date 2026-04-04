import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_reuse_experiment_script_generates_summary(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "reuse_eval_001",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool"],
        }
    ]
    taskset_path = tmp_path / "reuse_taskset.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "reuse_out"
    cmd = [
        sys.executable,
        "scripts/run_reuse_experiment.py",
        "--taskset",
        str(taskset_path),
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

    summary_path = outdir / "reuse_summary.json"
    report_path = outdir / "reuse_report.md"
    repeated_path = outdir / "prepared" / "repeated_taskset.json"

    assert summary_path.exists()
    assert report_path.exists()
    assert repeated_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["num_seed_tasks"] == 1
    assert summary["num_repeated_tasks"] == 2
    assert set(summary["systems"]) == {"a3_interaction", "a4_reuse"}
    assert "per_family" in summary
    assert "reuse_eval_001" in summary["per_family"]["a4_reuse"]

    report = report_path.read_text(encoding="utf-8")
    assert "ToolClaw Reuse Experiment" in report
    assert "Second-Run Delta" in report
    assert "Per-Family First-vs-Second-Run" in report
