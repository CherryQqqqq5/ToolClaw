"""Prepare tau2-bench samples, execute repeated runs, and aggregate interaction-focused outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import Tau2BenchAdapter
from toolclaw.benchmarks.runner_utils import (
    AggregateMetric,
    BenchmarkScriptConfig,
    aggregate_records,
    finalize_outputs,
    invoke_run_eval,
    load_run_rows,
    normalize_systems,
    score_to_payload,
)


DEFAULT_SOURCE = ROOT_DIR / "data" / "tau2_bench.sample.json"


TAU2_CONFIG = BenchmarkScriptConfig(
    benchmark_name="tau2_bench",
    normalized_filename="tau2_bench.normalized.json",
    system_summary_title="Tau2-Bench Per-System Summary",
    aggregate_metrics=[
        AggregateMetric("interactive_correction"),
        AggregateMetric("interaction_efficiency"),
        AggregateMetric("repair_salvage"),
        AggregateMetric("repair_efficiency"),
        AggregateMetric("approval_following"),
        AggregateMetric("tool_efficiency"),
    ],
    signature_builder=lambda score, row: json.dumps(
        {
            "success": bool(score.get("success")),
            "stop_reason": row.get("stop_reason", "unknown"),
            "interactive_correction": round(float(score.get("metrics", {}).get("interactive_correction", 0.0)), 4),
            "interaction_efficiency": round(float(score.get("metrics", {}).get("interaction_efficiency", 0.0)), 4),
            "repair_salvage": round(float(score.get("metrics", {}).get("repair_salvage", 0.0)), 4),
            "scenario": score.get("diagnostics", {}).get("scenario", row.get("scenario", "unknown")),
        },
        sort_keys=True,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and run tau2-bench through ToolClaw")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Path to tau2-bench JSON or JSONL sample file (defaults to data/tau2_bench.sample.json)",
    )
    parser.add_argument("--outdir", default="outputs/tau2_bench", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    parser.add_argument(
        "--systems",
        default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
        help="Comma-separated systems to run: a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke slice (min(limit, 10))")
    parser.add_argument("--num-runs", type=int, default=1, help="Repeat runs to estimate pass^k and consistency")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep the normalized taskset JSON file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    adapter = Tau2BenchAdapter()
    samples = adapter.load_samples(args.source)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
    if not samples:
        raise ValueError("No tau2-bench samples loaded from source")
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / TAU2_CONFIG.normalized_filename
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_records: List[Dict[str, Any]] = []
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        invoke_run_eval(normalized_path, run_outdir, args.mode, systems)
        for row in load_run_rows(run_outdir / "comparison.csv"):
            trace_payload = json.loads(Path(row["trace_path"]).read_text(encoding="utf-8"))
            sample = next(sample for sample in samples if sample.sample_id == row["task_id"])
            run_records.append(
                {
                    "run_index": run_index,
                    "system": row["system"],
                    "task_id": row["task_id"],
                    "row": row,
                    "score": score_to_payload(adapter.score_trace(sample, trace_payload)),
                }
            )

    scoreboard = aggregate_records(
        config=TAU2_CONFIG,
        adapter=adapter,
        samples=samples,
        systems=systems,
        run_records=run_records,
        source=args.source,
        mode=args.mode,
        normalized_path=normalized_path,
        num_runs=args.num_runs,
        smoke=args.smoke,
    )
    finalize_outputs(
        outdir=outdir,
        prepared_dir=prepared_dir,
        benchmark_name=TAU2_CONFIG.benchmark_name,
        source=args.source,
        normalized_path=normalized_path,
        mode=args.mode,
        systems=systems,
        num_runs=args.num_runs,
        scoreboard=scoreboard,
        config=TAU2_CONFIG,
        keep_normalized_taskset=args.keep_normalized_taskset,
    )

    print(f"prepared tau2-bench taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"scoreboard: {outdir / 'scoreboard.json'}")
    print(f"per-system summary: {outdir / 'per_system_summary.json'}")


if __name__ == "__main__":
    main()
