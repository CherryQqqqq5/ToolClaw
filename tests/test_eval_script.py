import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_eval_script_generates_csv_and_report(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_success_001",
            "scenario": "success",
            "query": "target document summary",
            "target_path": "outputs/reports/task_success_001.txt",
        },
        {
            "task_id": "task_env_001",
            "scenario": "environment_failure",
            "query": "target document summary",
            "target_path": "outputs/reports/task_env_001.txt",
            "backup_tool_map": {"write_tool": "backup_write_tool"},
        },
    ]
    taskset_path = tmp_path / "taskset.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
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

    csv_path = outdir / "comparison.csv"
    report_path = outdir / "report.md"
    assert csv_path.exists()
    assert report_path.exists()

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 4
    systems = {row["system"] for row in rows}
    assert systems == {"baseline", "toolclaw_lite"}

    report = report_path.read_text(encoding="utf-8")
    assert "ToolClaw Phase-1 Evaluation Report" in report
    assert "Delta (ToolClaw-lite vs Baseline)" in report
    assert "Scenario Breakdown" in report


def test_run_eval_script_with_planner_mode(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_success_planner_001",
            "scenario": "success",
            "query": "retrieve and write report",
        }
    ]
    taskset_path = tmp_path / "taskset_planner.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_planner"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--mode",
        "planner",
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
    assert (outdir / "comparison.csv").exists()


def test_run_eval_script_missing_taskset_shows_clear_error(tmp_path: Path) -> None:
    outdir = tmp_path / "eval_out_missing"
    missing_path = tmp_path / "does_not_exist.json"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(missing_path),
        "--outdir",
        str(outdir),
    ]
    completed = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "taskset file not found" in completed.stderr
    assert "data/eval_tasks.sample.json" in completed.stderr


def test_run_eval_script_placeholder_taskset_uses_sample() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    outdir = repo_root / "outputs" / "eval_placeholder_test"
    if outdir.exists():
        for child in outdir.glob("*"):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                for nested in child.glob("*"):
                    if nested.is_file():
                        nested.unlink()
                child.rmdir()
        outdir.rmdir()

    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        "path/to/taskset.json",
        "--outdir",
        str(outdir),
    ]
    completed = subprocess.run(
        cmd,
        cwd=repo_root,
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "using sample taskset" in completed.stderr
    assert (outdir / "comparison.csv").exists()
    assert (outdir / "report.md").exists()
