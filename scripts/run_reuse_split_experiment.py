#!/usr/bin/env python3
"""Run a two-stage reuse experiment with compile/eval splits over persistent assets."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Sequence

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
    parser = argparse.ArgumentParser(description="Run ToolClaw reuse train/eval split experiment")
    parser.add_argument("--train-taskset", type=existing_json_path, required=True, help="Train/compile split JSON taskset")
    parser.add_argument("--eval-taskset", type=existing_json_path, required=True, help="Held-out eval split JSON taskset")
    parser.add_argument("--outdir", default="outputs/reuse_split_experiment", help="Output directory")
    parser.add_argument("--train-systems", default="a4_reuse", help="Systems to run on the compile split")
    parser.add_argument("--eval-systems", default="a3_interaction,a4_reuse", help="Systems to compare on the eval split")
    parser.add_argument("--asset-registry-root", default=None, help="Persistent registry root shared across train/eval stages")
    return parser.parse_args()


def _run_eval(taskset_path: Path, outdir: Path, systems: str, asset_registry_root: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_eval.py"),
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--systems",
        systems,
        "--asset-registry-root",
        str(asset_registry_root),
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


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _canonical_task_id(task: Dict[str, Any]) -> str:
    for key in ("task_id", "sample_id", "name", "scenario_id", "id"):
        value = task.get(key)
        if value:
            return str(value)
    raise KeyError("task object must include one of: task_id, sample_id, name, scenario_id, id")


def _normalized_categories(task: Dict[str, Any]) -> List[str]:
    categories: List[str] = []
    raw_categories = task.get("categories")
    if isinstance(raw_categories, list):
        for item in raw_categories:
            normalized = str(item).strip().lower().replace(" ", "_")
            if normalized and normalized not in categories:
                categories.append(normalized)
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict):
        raw_meta_categories = metadata.get("toolsandbox_categories")
        if isinstance(raw_meta_categories, list):
            for item in raw_meta_categories:
                normalized = str(item).strip().lower().replace(" ", "_")
                if normalized and normalized not in categories:
                    categories.append(normalized)
    return categories


def _expected_turn_count(task: Dict[str, Any]) -> int:
    for key in ("ideal_turn_count", "expected_turn_count"):
        value = task.get(key)
        if value is not None:
            try:
                return max(int(value), 1)
            except (TypeError, ValueError):
                continue
    if "multiple_user_turn" in _normalized_categories(task):
        return 4
    return 2


def _expected_tool_calls(task: Dict[str, Any]) -> int:
    for key in ("ideal_tool_calls", "expected_tool_calls"):
        value = task.get(key)
        if value is not None:
            try:
                return max(int(value), 1)
            except (TypeError, ValueError):
                continue
    categories = _normalized_categories(task)
    if "multiple_tool" in categories or "state_dependency" in categories:
        return 2
    return 1


def _trace_turn_count(trace_path: Path) -> int:
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    visible_events = {"user_query", "user_reply", "tool_call", "tool_result"}
    return sum(1 for event in payload.get("events", []) if event.get("event_type") in visible_events)


def _efficiency_score(observed: int, expected: int, step_penalty: float) -> float:
    if observed <= max(expected, 1):
        return 1.0
    return max(0.0, 1.0 - step_penalty * (observed - max(expected, 1)))


def _augment_eval_row(row: Dict[str, str], task_index: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    task = task_index[row["task_id"]]
    turn_count = _trace_turn_count(Path(row["trace_path"]))
    expected_turns = _expected_turn_count(task)
    expected_tool_calls = _expected_tool_calls(task)
    return {
        **row,
        "turn_count": turn_count,
        "expected_turn_count": expected_turns,
        "expected_tool_calls": expected_tool_calls,
        "tool_efficiency": _efficiency_score(int(row["tool_calls"]), expected_tool_calls, step_penalty=0.15),
        "turn_efficiency": _efficiency_score(turn_count, expected_turns, step_penalty=0.2),
    }


def _aggregate_eval_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    if not rows:
        return {
            "num_rows": 0.0,
            "success_rate": 0.0,
            "avg_tool_calls": 0.0,
            "avg_user_turns": 0.0,
            "avg_repair_actions": 0.0,
            "avg_repair_triggered": 0.0,
            "avg_token_cost": 0.0,
            "avg_wall_clock_ms": 0.0,
            "tool_efficiency": 0.0,
            "turn_efficiency": 0.0,
            "reuse_usage_rate": 0.0,
        }
    return {
        "num_rows": float(len(rows)),
        "success_rate": mean(1.0 if row["success"] == "True" else 0.0 for row in rows),
        "avg_tool_calls": mean(float(row["tool_calls"]) for row in rows),
        "avg_user_turns": mean(float(row["user_turns"]) for row in rows),
        "avg_repair_actions": mean(float(row["repair_actions"]) for row in rows),
        "avg_repair_triggered": mean(float(row["repair_triggered"]) for row in rows),
        "avg_token_cost": mean(float(row.get("token_cost", 0.0)) for row in rows),
        "avg_wall_clock_ms": mean(float(row.get("wall_clock_ms", 0.0)) for row in rows),
        "tool_efficiency": mean(float(row["tool_efficiency"]) for row in rows),
        "turn_efficiency": mean(float(row["turn_efficiency"]) for row in rows),
        "reuse_usage_rate": mean(1.0 if row.get("reused_artifact") == "True" else 0.0 for row in rows),
    }


def _delta(right: Dict[str, float], left: Dict[str, float]) -> Dict[str, float]:
    keys = (
        "success_rate",
        "avg_tool_calls",
        "avg_user_turns",
        "avg_repair_actions",
        "avg_repair_triggered",
        "avg_token_cost",
        "avg_wall_clock_ms",
        "tool_efficiency",
        "turn_efficiency",
        "reuse_usage_rate",
    )
    return {key: float(right.get(key, 0.0)) - float(left.get(key, 0.0)) for key in keys}


def _write_report(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolClaw Reuse Split Experiment",
        "",
        f"- train_taskset: `{summary['train_taskset']}`",
        f"- eval_taskset: `{summary['eval_taskset']}`",
        f"- asset_registry_root: `{summary['asset_registry_root']}`",
        "",
        "## Eval Aggregate",
        "",
        "| system | rows | success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_repair_triggered | avg_token_cost | avg_wall_clock_ms | tool_efficiency | turn_efficiency | reuse_usage_rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, stats in sorted(summary["eval_per_system"].items()):
        lines.append(
            f"| {system} | {int(stats['num_rows'])} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['avg_repair_triggered']:.2f} | {stats['avg_token_cost']:.3f} | {stats['avg_wall_clock_ms']:.1f} | {stats['tool_efficiency']:.3f} | {stats['turn_efficiency']:.3f} | {stats['reuse_usage_rate']:.3f} |"
        )

    if summary.get("a4_vs_a3_delta"):
        delta = summary["a4_vs_a3_delta"]
        lines.extend(
            [
                "",
                "## Eval Delta (A4 Reuse vs A3 Interaction)",
                "",
                "| metric | delta |",
                "|---|---:|",
            ]
        )
        for key in (
            "success_rate",
            "avg_tool_calls",
            "avg_user_turns",
            "avg_repair_actions",
            "avg_repair_triggered",
            "avg_token_cost",
            "avg_wall_clock_ms",
            "tool_efficiency",
            "turn_efficiency",
            "reuse_usage_rate",
        ):
            lines.append(f"| {key} | {float(delta.get(key, 0.0)):+.3f} |")

    lines.extend(
        [
            "",
            "## Eval Family Breakdown",
            "",
            "| system | task_family | rows | success_rate | avg_tool_calls | avg_user_turns | tool_efficiency | turn_efficiency | reuse_usage_rate |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, family_map in sorted(summary["eval_per_family"].items()):
        for family, stats in sorted(family_map.items()):
            lines.append(
                f"| {system} | {family} | {int(stats['num_rows'])} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['tool_efficiency']:.3f} | {stats['turn_efficiency']:.3f} | {stats['reuse_usage_rate']:.3f} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    asset_registry_root = Path(args.asset_registry_root) if args.asset_registry_root else (outdir / "asset_registry")

    train_outdir = outdir / "train_compile"
    eval_outdir = outdir / "eval_compare"
    _run_eval(args.train_taskset, train_outdir, args.train_systems, asset_registry_root)
    _run_eval(args.eval_taskset, eval_outdir, args.eval_systems, asset_registry_root)

    train_tasks = json.loads(args.train_taskset.read_text(encoding="utf-8"))
    eval_tasks = json.loads(args.eval_taskset.read_text(encoding="utf-8"))
    if not isinstance(train_tasks, list) or not isinstance(eval_tasks, list):
        raise ValueError("train/eval tasksets must be JSON lists")
    eval_task_index = {_canonical_task_id(task): task for task in eval_tasks}

    eval_rows = [
        _augment_eval_row(row, eval_task_index)
        for row in _load_rows(eval_outdir / "comparison.csv")
    ]
    systems = sorted({row["system"] for row in eval_rows})
    eval_per_system = {
        system: _aggregate_eval_rows([row for row in eval_rows if row["system"] == system])
        for system in systems
    }
    eval_per_family: Dict[str, Dict[str, Dict[str, float]]] = {}
    for system in systems:
        family_rows = [row for row in eval_rows if row["system"] == system]
        family_keys = sorted({row["task_family"] for row in family_rows})
        eval_per_family[system] = {
            family: _aggregate_eval_rows([row for row in family_rows if row["task_family"] == family])
            for family in family_keys
        }

    a4_vs_a3_delta = None
    if "a3_interaction" in eval_per_system and "a4_reuse" in eval_per_system:
        a4_vs_a3_delta = _delta(eval_per_system["a4_reuse"], eval_per_system["a3_interaction"])

    summary = {
        "train_taskset": str(args.train_taskset.resolve()),
        "eval_taskset": str(args.eval_taskset.resolve()),
        "asset_registry_root": str(asset_registry_root.resolve()),
        "train_systems": [item.strip() for item in args.train_systems.split(",") if item.strip()],
        "eval_systems": [item.strip() for item in args.eval_systems.split(",") if item.strip()],
        "num_train_tasks": len(train_tasks),
        "num_eval_tasks": len(eval_tasks),
        "train_outdir": str(train_outdir.resolve()),
        "eval_outdir": str(eval_outdir.resolve()),
        "eval_per_system": eval_per_system,
        "eval_per_family": eval_per_family,
        "a4_vs_a3_delta": a4_vs_a3_delta,
    }
    (outdir / "reuse_split_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(summary, outdir / "reuse_split_report.md")
    print(f"wrote: {outdir / 'reuse_split_summary.json'}")
    print(f"wrote: {outdir / 'reuse_split_report.md'}")


if __name__ == "__main__":
    main()
