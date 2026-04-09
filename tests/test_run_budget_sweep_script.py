import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_budget_sweep_script_generates_summary(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "budget_sweep_001",
            "scenario": "environment_failure",
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool", "backup_write_tool"],
            "simulated_policy": {"mode": "cooperative", "tool_switch_hints": {"tool_id": "backup_write_tool"}},
        }
    ]
    taskset_path = tmp_path / "budget_sweep.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "budget_sweep_out"
    completed = subprocess.run(
        [sys.executable, "scripts/run_budget_sweep.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a3_interaction,a4_reuse"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    summary_path = outdir / "budget_sweep_summary.json"
    report_path = outdir / "budget_sweep_report.md"
    assert summary_path.exists()
    assert report_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert set(summary["sweeps"]) == {"max_user_turns", "max_repair_attempts", "max_tool_calls"}
    assert len(summary["sweeps"]["max_user_turns"]) == 3

    report = report_path.read_text(encoding="utf-8")
    assert "ToolClaw Budget Sweep" in report
    assert "Frontier" in report
