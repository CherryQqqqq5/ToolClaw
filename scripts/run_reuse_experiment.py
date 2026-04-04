"""Run a dedicated second-run reuse experiment over a repeated task family."""

from __future__ import annotations

import argparse
import csv
import json
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
    parser = argparse.ArgumentParser(description="Run second-run reuse experiment for A3 vs A4")
    parser.add_argument("--taskset", type=existing_json_path, required=True, help="Path to JSON taskset")
    parser.add_argument("--outdir", default="outputs/reuse_experiment", help="Output directory")
    parser.add_argument(
        "--systems",
        default="a3_interaction,a4_reuse",
        help="Comma-separated systems to compare. Defaults to a3_interaction,a4_reuse",
    )
    return parser.parse_args()


def build_repeated_taskset(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    repeated: List[Dict[str, Any]] = []
    for pass_index in (1, 2):
        for task in tasks:
            cloned = deepcopy(task)
            original_id = str(
                task.get("task_id")
                or task.get("sample_id")
                or task.get("name")
                or task.get("scenario_id")
                or task.get("id")
            )
            cloned["task_id"] = f"{original_id}__pass{pass_index}"
            metadata = dict(cloned.get("metadata", {}))
            metadata["reuse_family_id"] = original_id
            metadata["reuse_pass_index"] = pass_index
            cloned["metadata"] = metadata
            repeated.append(cloned)
    return repeated


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def repeat_family_key(task_id: str) -> str:
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id


def summarize_pass(rows: List[Dict[str, str]]) -> Dict[str, float]:
    success_rate = mean(1.0 if row["success"] == "True" else 0.0 for row in rows) if rows else 0.0
    avg_tool_calls = mean(float(row["tool_calls"]) for row in rows) if rows else 0.0
    avg_user_turns = mean(float(row["user_turns"]) for row in rows) if rows else 0.0
    fail_stop_rate = mean(0.0 if row["success"] == "True" else 1.0 for row in rows) if rows else 0.0
    return {
        "num_rows": float(len(rows)),
        "success_rate": success_rate,
        "avg_tool_calls": avg_tool_calls,
        "avg_user_turns": avg_user_turns,
        "fail_stop_rate": fail_stop_rate,
    }


def write_report(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolClaw Reuse Experiment",
        "",
        "| system | pass | rows | success_rate | avg_tool_calls | avg_user_turns | fail_stop_rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for system, system_summary in summary["per_system"].items():
        for pass_index in (1, 2):
            stats = system_summary[f"pass_{pass_index}"]
            lines.append(
                f"| {system} | {pass_index} | {int(stats['num_rows'])} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['fail_stop_rate']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## Second-Run Delta",
            "",
            "| system | success_rate | avg_tool_calls | avg_user_turns | fail_stop_rate |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for system, system_summary in summary["per_system"].items():
        delta = system_summary["second_run_delta"]
        lines.append(
            f"| {system} | {delta['success_rate']:+.3f} | {delta['avg_tool_calls']:+.2f} | {delta['avg_user_turns']:+.2f} | {delta['fail_stop_rate']:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Per-Family First-vs-Second-Run",
            "",
            "| system | repeat_family | pass_1_success | pass_2_success | pass_2_reused_artifact | second_run_improvement |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for system, family_rows in sorted(summary["per_family"].items()):
        for repeat_family, stats in sorted(family_rows.items()):
            lines.append(
                f"| {system} | {repeat_family} | {stats['pass_1_success']:.3f} | {stats['pass_2_success']:.3f} | {stats['pass_2_reused_artifact']:.3f} | {stats['second_run_improvement']:.3f} |"
            )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    tasks = json.loads(args.taskset.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("taskset JSON must be a list of task objects")

    repeated_taskset = build_repeated_taskset(tasks)
    repeated_path = prepared_dir / "repeated_taskset.json"
    repeated_path.write_text(json.dumps(repeated_taskset, indent=2), encoding="utf-8")

    run_eval_outdir = outdir / "run_eval"
    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_eval.py"),
        "--taskset",
        str(repeated_path),
        "--outdir",
        str(run_eval_outdir),
        "--systems",
        args.systems,
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={"PYTHONPATH": str(SRC_DIR), **dict(**__import__("os").environ)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    rows = load_rows(run_eval_outdir / "comparison.csv")
    systems = sorted({row["system"] for row in rows})
    per_system: Dict[str, Any] = {}
    per_family: Dict[str, Dict[str, Any]] = {}
    for system in systems:
        system_rows = [row for row in rows if row["system"] == system]
        pass_1_rows = [row for row in system_rows if row["task_id"].endswith("__pass1")]
        pass_2_rows = [row for row in system_rows if row["task_id"].endswith("__pass2")]
        pass_1 = summarize_pass(pass_1_rows)
        pass_2 = summarize_pass(pass_2_rows)
        per_system[system] = {
            "pass_1": pass_1,
            "pass_2": pass_2,
            "second_run_delta": {
                "success_rate": pass_2["success_rate"] - pass_1["success_rate"],
                "avg_tool_calls": pass_2["avg_tool_calls"] - pass_1["avg_tool_calls"],
                "avg_user_turns": pass_2["avg_user_turns"] - pass_1["avg_user_turns"],
                "fail_stop_rate": pass_2["fail_stop_rate"] - pass_1["fail_stop_rate"],
            },
        }
        family_summary: Dict[str, Any] = {}
        families = sorted({repeat_family_key(row["task_id"]) for row in system_rows})
        for family in families:
            family_pass_1 = next((row for row in system_rows if repeat_family_key(row["task_id"]) == family and row["task_id"].endswith("__pass1")), None)
            family_pass_2 = next((row for row in system_rows if repeat_family_key(row["task_id"]) == family and row["task_id"].endswith("__pass2")), None)
            if family_pass_1 is None or family_pass_2 is None:
                continue
            family_summary[family] = {
                "pass_1_success": 1.0 if family_pass_1["success"] == "True" else 0.0,
                "pass_2_success": 1.0 if family_pass_2["success"] == "True" else 0.0,
                "pass_2_reused_artifact": 1.0 if family_pass_2.get("reused_artifact") == "True" else 0.0,
                "second_run_improvement": float(family_pass_2.get("second_run_improvement", 0.0)),
            }
        per_family[system] = family_summary

    summary = {
        "taskset": str(args.taskset.resolve()),
        "systems": systems,
        "num_seed_tasks": len(tasks),
        "num_repeated_tasks": len(repeated_taskset),
        "per_system": per_system,
        "per_family": per_family,
        "run_eval_outdir": str(run_eval_outdir.resolve()),
    }
    summary_path = outdir / "reuse_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(summary, outdir / "reuse_report.md")

    print(f"wrote: {summary_path}")
    print(f"wrote: {outdir / 'reuse_report.md'}")


if __name__ == "__main__":
    main()
