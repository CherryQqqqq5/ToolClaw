"""Prepare ToolSandbox-style samples, execute repeated runs, and aggregate benchmark outputs."""

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

from toolclaw.benchmarks.adapters import ToolSandboxAdapter
from toolclaw.benchmarks.runner_utils import (
    AggregateMetric,
    BenchmarkScriptConfig,
    aggregate_records,
    finalize_outputs,
    invoke_run_eval,
    load_run_rows,
    mean_or_zero,
    normalize_systems,
    score_to_payload,
    write_group_markdown,
)


DEFAULT_SOURCE = ROOT_DIR / "data" / "toolsandbox.sample.json"


def _category_breakdown(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        categories = record["score"]["diagnostics"].get("categories", [])
        if not categories:
            categories = [record["row"].get("scenario", "toolsandbox")]
        for category in categories:
            grouped.setdefault(str(category), []).append(record)

    summary: Dict[str, Dict[str, float]] = {}
    for category, category_records in grouped.items():
        summary[category] = {
            "num_rows": float(len(category_records)),
            "success_rate": mean_or_zero([1.0 if record["score"]["success"] else 0.0 for record in category_records]),
            "milestone_similarity": mean_or_zero(
                [float(record["score"]["metrics"].get("milestone_similarity", 0.0)) for record in category_records]
            ),
            "milestone_coverage": mean_or_zero(
                [float(record["score"]["metrics"].get("milestone_coverage", 0.0)) for record in category_records]
            ),
            "interaction_efficiency": mean_or_zero(
                [float(record["score"]["metrics"].get("interaction_efficiency", 0.0)) for record in category_records]
            ),
            "tool_efficiency": mean_or_zero(
                [float(record["score"]["metrics"].get("tool_efficiency", 0.0)) for record in category_records]
            ),
            "hallucination_avoidance": mean_or_zero(
                [float(record["score"]["metrics"].get("hallucination_avoidance", 0.0)) for record in category_records]
            ),
        }
    return summary


TOOLSANDBOX_GROUP_METRICS = [
    AggregateMetric("milestone_similarity"),
    AggregateMetric("milestone_coverage"),
    AggregateMetric("interaction_efficiency"),
    AggregateMetric("tool_efficiency"),
    AggregateMetric("hallucination_avoidance"),
]


TOOLSANDBOX_CONFIG = BenchmarkScriptConfig(
    benchmark_name="toolsandbox",
    normalized_filename="toolsandbox.normalized.json",
    system_summary_title="ToolSandbox Per-System Summary",
    aggregate_metrics=[
        AggregateMetric("milestone_similarity"),
        AggregateMetric("milestone_coverage"),
        AggregateMetric("interaction_efficiency"),
        AggregateMetric("tool_efficiency"),
        AggregateMetric("turn_efficiency"),
        AggregateMetric("hallucination_avoidance"),
    ],
    signature_builder=lambda score, row: json.dumps(
        {
            "success": bool(score.get("success")),
            "stop_reason": row.get("stop_reason", "unknown"),
            "tool_calls": row.get("tool_calls", "0"),
            "milestone_similarity": round(float(score.get("metrics", {}).get("milestone_similarity", 0.0)), 4),
            "hallucination_avoidance": round(float(score.get("metrics", {}).get("hallucination_avoidance", 0.0)), 4),
            "primary_category": score.get("diagnostics", {}).get("primary_category", row.get("scenario", "unknown")),
        },
        sort_keys=True,
    ),
    sample_extra_builder=lambda sample: {
        "categories": list(sample.metadata.get("toolsandbox_categories", [])),
    },
    system_extra_builder=lambda records: {
        "per_category": _category_breakdown(records),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and run ToolSandbox-style benchmark slices through ToolClaw")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Path to ToolSandbox-style JSON or JSONL sample file (defaults to data/toolsandbox.sample.json)",
    )
    parser.add_argument("--outdir", default="outputs/toolsandbox_bench", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    parser.add_argument(
        "--systems",
        default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
        help="Comma-separated systems to run: a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke slice (min(limit, 10))")
    parser.add_argument("--num-runs", type=int, default=1, help="Repeat runs to estimate pass@k and consistency")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep the normalized taskset JSON file")
    return parser.parse_args()


def _write_toolsandbox_artifacts(summary: Dict[str, Any], outdir: Path) -> None:
    write_group_markdown(
        summary,
        outdir / "per_category_summary.md",
        title="ToolSandbox Category Summary",
        group_key="per_category",
        metrics=TOOLSANDBOX_GROUP_METRICS,
    )


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    adapter = ToolSandboxAdapter()
    samples = adapter.load_samples(args.source)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
    if not samples:
        raise ValueError("No ToolSandbox samples loaded from source")
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / TOOLSANDBOX_CONFIG.normalized_filename
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
        config=TOOLSANDBOX_CONFIG,
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
        benchmark_name=TOOLSANDBOX_CONFIG.benchmark_name,
        source=args.source,
        normalized_path=normalized_path,
        mode=args.mode,
        systems=systems,
        num_runs=args.num_runs,
        scoreboard=scoreboard,
        config=TOOLSANDBOX_CONFIG,
        keep_normalized_taskset=args.keep_normalized_taskset,
        extra_output_writers=_write_toolsandbox_artifacts,
    )

    print(f"prepared toolsandbox taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"scoreboard: {outdir / 'scoreboard.json'}")
    print(f"per-system summary: {outdir / 'per_system_summary.json'}")


if __name__ == "__main__":
    main()
