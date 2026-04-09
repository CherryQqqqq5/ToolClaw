#!/usr/bin/env python3
"""Sweep planner/interaction budgets and summarize the success-budget frontier."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def existing_json_path(value: str) -> Path:
    path = Path(value)
    if not path.exists() or not path.is_file():
        raise argparse.ArgumentTypeError(f"taskset file not found: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run budget sweeps over ToolClaw evaluation tasksets")
    parser.add_argument("--taskset", type=existing_json_path, required=True, help="Path to JSON taskset")
    parser.add_argument("--outdir", default="outputs/budget_sweep", help="Output directory")
    parser.add_argument("--systems", default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse", help="Systems to evaluate")
    parser.add_argument("--mode", default="planner", choices=["demo", "planner"], help="Workflow mode")
    return parser.parse_args()


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _canonical_task_id(task: Dict[str, Any]) -> str:
    for key in ("task_id", "sample_id", "name", "scenario_id", "id"):
        value = task.get(key)
        if value:
            return str(value)
    raise KeyError("task object must include one of: task_id, sample_id, name, scenario_id, id")


def _with_budget(taskset: List[Dict[str, Any]], key: str, value: int) -> List[Dict[str, Any]]:
    cloned = deepcopy(taskset)
    for task in cloned:
        constraints = dict(task.get("constraints", {}))
        constraints[key] = value
        task["constraints"] = constraints
    return cloned


def _run_eval(taskset_path: Path, outdir: Path, systems: str, mode: str) -> None:
    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_eval.py"),
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--systems",
        systems,
        "--mode",
        mode,
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _aggregate(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    systems = sorted({row["system"] for row in rows})
    summary: Dict[str, Dict[str, float]] = {}
    for system in systems:
        system_rows = [row for row in rows if row["system"] == system]
        summary[system] = {
            "num_rows": float(len(system_rows)),
            "success_rate": mean(1.0 if row["success"] == "True" else 0.0 for row in system_rows) if system_rows else 0.0,
            "avg_tool_calls": mean(float(row["tool_calls"]) for row in system_rows) if system_rows else 0.0,
            "avg_user_turns": mean(float(row["user_turns"]) for row in system_rows) if system_rows else 0.0,
            "avg_repair_actions": mean(float(row["repair_actions"]) for row in system_rows) if system_rows else 0.0,
            "avg_recovery_budget_used": mean(float(row.get("recovery_budget_used", 0.0)) for row in system_rows) if system_rows else 0.0,
            "budget_violation_rate": mean(1.0 if row.get("budget_violation") == "True" else 0.0 for row in system_rows) if system_rows else 0.0,
        }
    return summary


def _write_report(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolClaw Budget Sweep",
        "",
        f"- taskset: `{summary['taskset']}`",
        "",
        "## Frontier",
        "",
        "| sweep | value | system | success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_recovery_budget_used | budget_violation_rate |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for sweep_name, sweep_rows in summary["sweeps"].items():
        for point in sweep_rows:
            for system, stats in sorted(point["per_system"].items()):
                lines.append(
                    f"| {sweep_name} | {point['value']} | {system} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['avg_recovery_budget_used']:.2f} | {stats['budget_violation_rate']:.3f} |"
                )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    taskset = json.loads(args.taskset.read_text(encoding="utf-8"))
    if not isinstance(taskset, list):
        raise ValueError("taskset JSON must be a list of task objects")

    sweep_values = {
        "max_user_turns": [0, 1, 2],
        "max_repair_attempts": [0, 1, 2],
        "max_tool_calls": [2, 3, 4],
    }

    sweeps: Dict[str, Any] = {}
    for sweep_key, values in sweep_values.items():
        points: List[Dict[str, Any]] = []
        for value in values:
            taskset_with_budget = _with_budget(taskset, sweep_key, value)
            taskset_path = prepared_dir / f"{sweep_key}_{value}.json"
            taskset_path.write_text(json.dumps(taskset_with_budget, indent=2), encoding="utf-8")
            run_outdir = outdir / sweep_key / f"value_{value}"
            _run_eval(taskset_path, run_outdir, args.systems, args.mode)
            rows = _load_rows(run_outdir / "comparison.csv")
            points.append(
                {
                    "value": value,
                    "taskset_path": str(taskset_path.resolve()),
                    "run_outdir": str(run_outdir.resolve()),
                    "per_system": _aggregate(rows),
                }
            )
        sweeps[sweep_key] = points

    summary = {
        "taskset": str(args.taskset.resolve()),
        "systems": [item.strip() for item in args.systems.split(",") if item.strip()],
        "mode": args.mode,
        "sweeps": sweeps,
    }
    summary_path = outdir / "budget_sweep_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(summary, outdir / "budget_sweep_report.md")
    print(f"wrote: {summary_path}")
    print(f"wrote: {outdir / 'budget_sweep_report.md'}")


if __name__ == "__main__":
    main()
