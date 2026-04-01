"""Prepare tau-bench samples, execute repeated runs, and aggregate scoreboard outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import TauBenchAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and run tau-bench through ToolClaw")
    parser.add_argument("--source", required=True, help="Path to tau-bench JSON or JSONL sample file")
    parser.add_argument("--outdir", default="outputs/tau_bench", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    parser.add_argument(
        "--systems",
        default="baseline,toolclaw_lite",
        help="Comma-separated systems to run: baseline,planning,skill,policy,interactive,toolclaw_lite",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke slice (min(limit, 10))")
    parser.add_argument("--num-runs", type=int, default=1, help="Repeat runs to estimate pass^k and consistency")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep the normalized taskset JSON file")
    return parser.parse_args()


def _normalize_systems(raw_systems: str) -> List[str]:
    return [item.strip() for item in raw_systems.split(",") if item.strip()]


def _invoke_run_eval(taskset_path: Path, run_outdir: Path, mode: str, systems: List[str]) -> None:
    cmd: List[str] = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_eval.py"),
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(run_outdir),
        "--mode",
        mode,
        "--systems",
        ",".join(systems),
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _load_run_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return float(mean(values))


def _outcome_signature(score: Dict[str, Any], row: Dict[str, str]) -> str:
    metrics = score.get("metrics", {})
    diagnostics = score.get("diagnostics", {})
    return json.dumps(
        {
            "success": bool(score.get("success")),
            "stop_reason": row.get("stop_reason", "unknown"),
            "tool_calls": row.get("tool_calls", "0"),
            "rule_following": round(float(metrics.get("rule_following", 0.0)), 4),
            "interaction_quality": round(float(metrics.get("interaction_quality", 0.0)), 4),
            "scenario": diagnostics.get("scenario", row.get("scenario", "unknown")),
        },
        sort_keys=True,
    )


def _build_scoreboard(
    adapter: TauBenchAdapter,
    samples: List[Any],
    systems: List[str],
    run_records: List[Dict[str, Any]],
    args: argparse.Namespace,
    normalized_path: Path,
) -> Dict[str, Any]:
    sample_by_id = {sample.sample_id: sample for sample in samples}
    per_system_summary: Dict[str, Any] = {}

    for system in systems:
        system_records = [record for record in run_records if record["system"] == system]
        sample_ids = sorted({record["task_id"] for record in system_records})
        per_sample: Dict[str, Any] = {}
        for sample_id in sample_ids:
            sample_records = [record for record in system_records if record["task_id"] == sample_id]
            successes = [1.0 if record["score"]["success"] else 0.0 for record in sample_records]
            rule_following = [float(record["score"]["metrics"].get("rule_following", 0.0)) for record in sample_records]
            interaction_quality = [float(record["score"]["metrics"].get("interaction_quality", 0.0)) for record in sample_records]
            repair_overhead = [float(record["score"]["metrics"].get("repair_overhead", 0.0)) for record in sample_records]
            tool_efficiency = [float(record["score"]["metrics"].get("tool_efficiency", 0.0)) for record in sample_records]
            signatures = [_outcome_signature(record["score"], record["row"]) for record in sample_records]
            consistency = 1.0 if len(signatures) <= 1 else max(signatures.count(sig) for sig in set(signatures)) / len(signatures)
            per_sample[sample_id] = {
                "scenario": sample_by_id[sample_id].scenario if sample_id in sample_by_id else "unknown",
                "num_runs": len(sample_records),
                "success_rate": _mean(successes),
                "pass_at_k": 1.0 if any(successes) else 0.0,
                "consistency": consistency,
                "rule_following": _mean(rule_following),
                "interaction_quality": _mean(interaction_quality),
                "tool_efficiency": _mean(tool_efficiency),
                "repair_overhead": _mean(repair_overhead),
                "distinct_outcomes": len(set(signatures)),
                "stop_reasons": [record["row"].get("stop_reason", "unknown") for record in sample_records],
            }

        per_system_summary[system] = {
            "num_samples": len(per_sample),
            "num_runs": args.num_runs,
            "mean_success_rate": _mean([item["success_rate"] for item in per_sample.values()]),
            "pass_at_k": _mean([item["pass_at_k"] for item in per_sample.values()]),
            "consistency": _mean([item["consistency"] for item in per_sample.values()]),
            "rule_following": _mean([item["rule_following"] for item in per_sample.values()]),
            "interaction_quality": _mean([item["interaction_quality"] for item in per_sample.values()]),
            "tool_efficiency": _mean([item["tool_efficiency"] for item in per_sample.values()]),
            "repair_overhead": _mean([item["repair_overhead"] for item in per_sample.values()]),
            "per_sample": per_sample,
        }

    return {
        "benchmark": adapter.benchmark_name,
        "source": str(Path(args.source).resolve()),
        "normalized_taskset": str(normalized_path.resolve()),
        "mode": args.mode,
        "systems": systems,
        "num_samples": len(samples),
        "num_runs": args.num_runs,
        "smoke": bool(args.smoke),
        "per_system_summary": per_system_summary,
        "runs": [
            {
                "run_index": record["run_index"],
                "system": record["system"],
                "task_id": record["task_id"],
                "success": bool(record["score"]["success"]),
                "trace_path": record["row"]["trace_path"],
                "score": record["score"],
            }
            for record in run_records
        ],
    }


def _write_per_system_markdown(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Tau-Bench Per-System Summary",
        "",
        "| system | samples | runs | mean_success_rate | pass@k | consistency | rule_following | interaction_quality | tool_efficiency | repair_overhead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, stats in summary.items():
        lines.append(
            f"| {system} | {stats['num_samples']} | {stats['num_runs']} | {stats['mean_success_rate']:.3f} | {stats['pass_at_k']:.3f} | {stats['consistency']:.3f} | {stats['rule_following']:.3f} | {stats['interaction_quality']:.3f} | {stats['tool_efficiency']:.3f} | {stats['repair_overhead']:.3f} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    adapter = TauBenchAdapter()
    samples = adapter.load_samples(args.source)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
    if not samples:
        raise ValueError("No tau-bench samples loaded from source")
    systems = _normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / "tau_bench.normalized.json"
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_records: List[Dict[str, Any]] = []
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        _invoke_run_eval(normalized_path, run_outdir, args.mode, systems)
        for row in _load_run_rows(run_outdir / "comparison.csv"):
            trace_payload = json.loads(Path(row["trace_path"]).read_text(encoding="utf-8"))
            sample = next(sample for sample in samples if sample.sample_id == row["task_id"])
            score = adapter.score_trace(sample, trace_payload)
            run_records.append(
                {
                    "run_index": run_index,
                    "system": row["system"],
                    "task_id": row["task_id"],
                    "row": row,
                    "score": {
                        "benchmark": score.benchmark,
                        "sample_id": score.sample_id,
                        "success": score.success,
                        "metrics": score.metrics,
                        "diagnostics": score.diagnostics,
                    },
                }
            )

    latest_run_outdir = runs_root / f"run_{args.num_runs:02d}"
    latest_comparison = latest_run_outdir / "comparison.csv"
    latest_report = latest_run_outdir / "report.md"
    if latest_comparison.exists():
        shutil.copy2(latest_comparison, outdir / "comparison.csv")
    if latest_report.exists():
        shutil.copy2(latest_report, outdir / "report.md")

    scoreboard = _build_scoreboard(adapter, samples, systems, run_records, args, normalized_path)
    scoreboard_path = outdir / "scoreboard.json"
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")

    per_system_summary_path = outdir / "per_system_summary.json"
    per_system_summary_path.write_text(json.dumps(scoreboard["per_system_summary"], indent=2), encoding="utf-8")
    _write_per_system_markdown(scoreboard["per_system_summary"], outdir / "per_system_summary.md")

    manifest = {
        "benchmark": "tau_bench",
        "source": str(Path(args.source).resolve()),
        "normalized_taskset": str(normalized_path.resolve()),
        "sample_count": len(samples),
        "mode": args.mode,
        "systems": systems,
        "num_runs": args.num_runs,
        "scoreboard_path": str(scoreboard_path.resolve()),
        "per_system_summary_path": str(per_system_summary_path.resolve()),
    }
    (prepared_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not args.keep_normalized_taskset:
        temp_copy = Path(tempfile.gettempdir()) / f"toolclaw_tau_bench_{os.getpid()}.json"
        temp_copy.write_text(normalized_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"prepared tau-bench taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"scoreboard: {scoreboard_path}")
    print(f"per-system summary: {per_system_summary_path}")


if __name__ == "__main__":
    main()
