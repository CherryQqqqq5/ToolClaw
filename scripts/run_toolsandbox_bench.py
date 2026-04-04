"""Prepare ToolSandbox-style samples, execute repeated runs, and aggregate benchmark outputs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
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


def _default_source() -> Path:
    candidates = [
        ROOT_DIR / "data" / "toolsandbox.formal.official.json",
        ROOT_DIR / "data" / "toolsandbox.formal.json",
        ROOT_DIR / "data" / "toolsandbox.sample.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


DEFAULT_SOURCE = _default_source()
DEFAULT_OFFICIAL_DATA_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox" / "data"


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
            "turn_efficiency": mean_or_zero(
                [float(record["score"]["metrics"].get("turn_efficiency", 0.0)) for record in category_records]
            ),
            "hallucination_avoidance": mean_or_zero(
                [float(record["score"]["metrics"].get("hallucination_avoidance", 0.0)) for record in category_records]
            ),
            "state_dependency_score": mean_or_zero(
                [float(record["score"]["metrics"].get("state_dependency_score", 0.0)) for record in category_records]
            ),
            "result_summary_coverage": mean_or_zero(
                [1.0 if record["score"]["diagnostics"].get("used_result_summary") else 0.0 for record in category_records]
            ),
            "reference_summary_coverage": mean_or_zero(
                [
                    1.0 if record["score"]["diagnostics"].get("reference_result_summary_available") else 0.0
                    for record in category_records
                ]
            ),
        }
    return summary


TOOLSANDBOX_GROUP_METRICS = [
    AggregateMetric("milestone_similarity"),
    AggregateMetric("milestone_coverage"),
    AggregateMetric("interaction_efficiency"),
    AggregateMetric("tool_efficiency"),
    AggregateMetric("turn_efficiency"),
    AggregateMetric("hallucination_avoidance"),
    AggregateMetric("state_dependency_score"),
    AggregateMetric("used_result_summary", source="diagnostics", label="result_summary_coverage"),
    AggregateMetric("reference_result_summary_available", source="diagnostics", label="reference_summary_coverage"),
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
        AggregateMetric("state_dependency_score"),
        AggregateMetric("used_result_summary", source="diagnostics", label="result_summary_coverage"),
        AggregateMetric("reference_result_summary_available", source="diagnostics", label="reference_summary_coverage"),
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
        help="Path to ToolSandbox-style JSON or JSONL source (defaults to formal ToolSandbox data when available)",
    )
    parser.add_argument(
        "--official-run-dir",
        default=None,
        help="Official ToolSandbox run directory, or 'latest' to auto-discover under data/external/ToolSandbox/data",
    )
    parser.add_argument(
        "--official-data-root",
        default=str(DEFAULT_OFFICIAL_DATA_ROOT),
        help="Root directory containing official ToolSandbox run directories for --official-run-dir auto-discovery",
    )
    parser.add_argument(
        "--result-source",
        default=None,
        help="Optional JSON/JSONL file or directory containing official ToolSandbox result summaries to merge before scoring",
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
    parser.add_argument(
        "--asset-registry-root",
        default=None,
        help="Optional root for file-backed reusable assets. Each benchmark repetition uses a separate subdirectory under this root.",
    )
    parser.add_argument(
        "--require-result-summary",
        action="store_true",
        help="Fail if the prepared ToolSandbox source does not include any merged result_summary / toolsandbox_result signal",
    )
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
    (outdir / "per_category_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_toolsandbox_report(scoreboard: Dict[str, Any], outdir: Path) -> None:
    lines = [
        "# ToolSandbox Benchmark Report",
        "",
        f"- source: `{scoreboard['source']}`",
        f"- normalized_taskset: `{scoreboard['normalized_taskset']}`",
        f"- samples: `{scoreboard['num_samples']}`",
        f"- runs: `{scoreboard['num_runs']}`",
        f"- systems: `{', '.join(scoreboard['systems'])}`",
        "",
        "## Aggregate",
        "",
        "| system | mean_success_rate | pass@k | consistency | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    per_system = scoreboard["per_system_summary"]
    for system, stats in per_system.items():
        lines.append(
            f"| {system} | {float(stats.get('mean_success_rate', 0.0)):.3f} | {float(stats.get('pass_at_k', 0.0)):.3f} | {float(stats.get('consistency', 0.0)):.3f} | {float(stats.get('milestone_similarity', 0.0)):.3f} | {float(stats.get('milestone_coverage', 0.0)):.3f} | {float(stats.get('state_dependency_score', 0.0)):.3f} | {float(stats.get('hallucination_avoidance', 0.0)):.3f} | {float(stats.get('tool_efficiency', 0.0)):.3f} | {float(stats.get('turn_efficiency', 0.0)):.3f} | {float(stats.get('used_result_summary', 0.0)):.3f} | {float(stats.get('reference_result_summary_available', 0.0)):.3f} |"
        )

    lines.extend(
        [
            "",
            "## Category Breakdown",
            "",
            "| system | category | rows | success_rate | milestone_similarity | milestone_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, stats in per_system.items():
        for category, category_stats in sorted(stats.get("per_category", {}).items()):
            lines.append(
                f"| {system} | {category} | {int(category_stats.get('num_rows', 0))} | {float(category_stats.get('success_rate', 0.0)):.3f} | {float(category_stats.get('milestone_similarity', 0.0)):.3f} | {float(category_stats.get('milestone_coverage', 0.0)):.3f} | {float(category_stats.get('state_dependency_score', 0.0)):.3f} | {float(category_stats.get('hallucination_avoidance', 0.0)):.3f} | {float(category_stats.get('tool_efficiency', 0.0)):.3f} | {float(category_stats.get('turn_efficiency', 0.0)):.3f} | {float(category_stats.get('result_summary_coverage', 0.0)):.3f} | {float(category_stats.get('reference_summary_coverage', 0.0)):.3f} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.",
            "- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.",
            "- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.",
            "- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.",
            "- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.",
        ]
    )
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _attach_current_result_summary(
    adapter: ToolSandboxAdapter,
    sample: Any,
    trace_path: Path,
    trace_payload: Dict[str, Any],
) -> Dict[str, Any]:
    metadata = trace_payload.setdefault("metadata", {})
    metadata["toolsandbox_result"] = adapter.build_proxy_result_summary(sample, trace_payload)
    metadata["toolsandbox_result_source"] = "toolclaw_proxy"
    reference_summary = adapter._extract_reference_result_summary(sample.raw_payload)
    if reference_summary:
        metadata["toolsandbox_reference_result"] = reference_summary
    trace_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
    return trace_payload


def _prepare_source_if_needed(source: str, result_source: str | None, prepared_dir: Path) -> Path:
    source_path = Path(source)
    if result_source is None and source_path.is_file():
        return source_path

    aligned_path = prepared_dir / "toolsandbox.aligned.jsonl"
    cmd: List[str] = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "prepare_toolsandbox_source.py"),
        "--source",
        str(source_path),
        "--out",
        str(aligned_path),
    ]
    if result_source is not None:
        cmd.extend(["--result-source", result_source])
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return aligned_path


def _prepare_source_from_official_run(official_run_dir: str, official_data_root: str, prepared_dir: Path) -> Path:
    aligned_path = prepared_dir / "toolsandbox.official.aligned.jsonl"
    cmd: List[str] = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "prepare_toolsandbox_official_run.py"),
        "--run-dir",
        official_run_dir,
        "--data-root",
        official_data_root,
        "--out",
        str(aligned_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return aligned_path


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    if args.official_run_dir is not None:
        source_for_adapter = _prepare_source_from_official_run(args.official_run_dir, args.official_data_root, prepared_dir)
    else:
        source_for_adapter = _prepare_source_if_needed(args.source, args.result_source, prepared_dir)

    adapter = ToolSandboxAdapter()
    samples = adapter.load_samples(str(source_for_adapter))
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
    if not samples:
        raise ValueError("No ToolSandbox samples loaded from source")
    if args.require_result_summary and not any(sample.raw_payload.get("result_summary") for sample in samples):
        raise ValueError("require-result-summary was set, but no ToolSandbox result_summary / toolsandbox_result was found")
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / TOOLSANDBOX_CONFIG.normalized_filename
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_records: List[Dict[str, Any]] = []
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        asset_registry_root = None
        if args.asset_registry_root:
            asset_registry_root = Path(args.asset_registry_root) / f"run_{run_index:02d}"
        invoke_run_eval(normalized_path, run_outdir, args.mode, systems, asset_registry_root=asset_registry_root)
        for row in load_run_rows(run_outdir / "comparison.csv"):
            trace_path = Path(row["trace_path"])
            trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
            sample = next(sample for sample in samples if sample.sample_id == row["task_id"])
            trace_payload = _attach_current_result_summary(adapter, sample, trace_path, trace_payload)
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
        source=str(source_for_adapter),
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
    _write_toolsandbox_report(scoreboard, outdir)

    print(f"prepared toolsandbox taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"scoreboard: {outdir / 'scoreboard.json'}")
    print(f"per-system summary: {outdir / 'per_system_summary.json'}")


if __name__ == "__main__":
    main()
