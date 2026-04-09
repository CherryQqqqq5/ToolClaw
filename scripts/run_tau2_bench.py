"""Prepare tau2-bench samples and run phase-2 slices, reuse, and budget sweeps."""

from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import json
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

from toolclaw.benchmarks.adapters import BenchmarkSample, Tau2BenchAdapter
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
        AggregateMetric("safe_abort_rate"),
        AggregateMetric("policy_compliance_success_rate"),
        AggregateMetric("state_repair_success_rate"),
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
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples after slicing")
    parser.add_argument("--smoke", action="store_true", help="Run a small smoke slice (min(limit, 10))")
    parser.add_argument("--num-runs", type=int, default=1, help="Repeat runs to estimate pass^k and consistency")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep the normalized taskset JSON file")
    parser.add_argument(
        "--slice-by",
        choices=["failtax", "scenario", "task_family"],
        default=None,
        help="Optional slicing axis before normalization",
    )
    parser.add_argument(
        "--slice-values",
        default="",
        help="Comma-separated slice values; for failtax, use values such as state or recovery",
    )
    parser.add_argument(
        "--reuse-second-run",
        action="store_true",
        help="Duplicate each selected sample into pass1/pass2 tasks so A4 can consume first-run assets on the paired second run",
    )
    parser.add_argument(
        "--budget-sweep",
        action="store_true",
        help="Run max_user_turns/max_repair_attempts/max_tool_calls sweeps instead of the standard repeated-run aggregate",
    )
    parser.add_argument("--asset-registry-root", default=None, help="Optional root directory for persistent per-run asset registries")
    parser.add_argument("--user-turn-values", default="0,1,2", help="Sweep values for max_user_turns")
    parser.add_argument("--repair-attempt-values", default="0,1,2", help="Sweep values for max_repair_attempts")
    parser.add_argument("--tool-call-values", default="2,3,4", help="Sweep values for max_tool_calls")
    return parser.parse_args()


def _parse_int_values(raw: str) -> List[int]:
    values: List[int] = []
    for item in str(raw).split(","):
        item = item.strip()
        if not item:
            continue
        values.append(int(item))
    return values


def _sample_task(adapter: Tau2BenchAdapter, sample: BenchmarkSample) -> Dict[str, Any]:
    return adapter.to_eval_task(sample)


def _matches_slice(task: Dict[str, Any], *, slice_by: str | None, slice_values: Sequence[str]) -> bool:
    if not slice_by or not slice_values:
        return True
    normalized_values = {value.strip().lower() for value in slice_values if value.strip()}
    if not normalized_values:
        return True
    if slice_by == "failtax":
        observed = {str(task.get("primary_failtax") or "").strip().lower()}
        observed.update(str(item).strip().lower() for item in task.get("failtaxes", []) if str(item).strip())
        return bool(observed & normalized_values)
    if slice_by == "scenario":
        return str(task.get("scenario") or "").strip().lower() in normalized_values
    if slice_by == "task_family":
        return str(task.get("task_family") or "").strip().lower() in normalized_values
    return True


def _slice_samples(
    adapter: Tau2BenchAdapter,
    samples: Sequence[BenchmarkSample],
    *,
    slice_by: str | None,
    slice_values: Sequence[str],
) -> List[BenchmarkSample]:
    if not slice_by:
        return list(samples)
    return [sample for sample in samples if _matches_slice(_sample_task(adapter, sample), slice_by=slice_by, slice_values=slice_values)]


def _reuse_ready_samples(samples: Sequence[BenchmarkSample]) -> List[BenchmarkSample]:
    if any(sample.raw_payload.get("reuse_pass_index") for sample in samples):
        return list(samples)
    augmented: List[BenchmarkSample] = []
    for sample in samples:
        family_id = str(
            sample.raw_payload.get("reuse_family_id")
            or sample.raw_payload.get("task_family")
            or sample.sample_id
        )
        for pass_index in (1, 2):
            raw = deepcopy(sample.raw_payload)
            raw["sample_id"] = f"{sample.sample_id}__pass{pass_index}"
            raw["reuse_family_id"] = family_id
            raw["reuse_pass_index"] = pass_index
            metadata = dict(raw.get("metadata", {}))
            metadata["reuse_family_id"] = family_id
            metadata["reuse_pass_index"] = pass_index
            raw["metadata"] = metadata
            augmented.append(
                BenchmarkSample(
                    sample_id=str(raw["sample_id"]),
                    raw_payload=raw,
                    scenario=sample.scenario,
                    metadata=dict(sample.metadata),
                )
            )
    return augmented


def _load_budget_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _budget_summary(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
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


def _write_budget_report(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Tau2-Bench Budget Sweep",
        "",
        f"- source: `{summary['source']}`",
        f"- mode: `{summary['mode']}`",
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


def _run_budget_sweep(
    *,
    tasks: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
    systems: Sequence[str],
    prepared_dir: Path,
    outdir: Path,
) -> None:
    prepared_dir.mkdir(parents=True, exist_ok=True)
    sweep_values = {
        "max_user_turns": _parse_int_values(args.user_turn_values),
        "max_repair_attempts": _parse_int_values(args.repair_attempt_values),
        "max_tool_calls": _parse_int_values(args.tool_call_values),
    }

    sweeps: Dict[str, Any] = {}
    for sweep_key, values in sweep_values.items():
        points: List[Dict[str, Any]] = []
        for value in values:
            taskset = deepcopy(list(tasks))
            for task in taskset:
                constraints = dict(task.get("constraints", {}))
                constraints[sweep_key] = value
                task["constraints"] = constraints
            taskset_path = prepared_dir / f"{sweep_key}_{value}.json"
            taskset_path.write_text(json.dumps(taskset, indent=2), encoding="utf-8")
            run_outdir = outdir / sweep_key / f"value_{value}"
            base_asset_root = Path(args.asset_registry_root) if args.asset_registry_root else (outdir / "asset_registry")
            asset_registry_root = (base_asset_root / sweep_key / f"value_{value}") if (args.reuse_second_run or args.asset_registry_root) else None
            invoke_run_eval(taskset_path, run_outdir, args.mode, list(systems), asset_registry_root=asset_registry_root)
            rows = _load_budget_rows(run_outdir / "comparison.csv")
            points.append(
                {
                    "value": value,
                    "taskset_path": str(taskset_path.resolve()),
                    "run_outdir": str(run_outdir.resolve()),
                    "per_system": _budget_summary(rows),
                }
            )
        sweeps[sweep_key] = points

    summary = {
        "source": str(Path(args.source).resolve()),
        "systems": list(systems),
        "mode": args.mode,
        "slice_by": args.slice_by,
        "slice_values": [value.strip() for value in args.slice_values.split(",") if value.strip()],
        "reuse_second_run": bool(args.reuse_second_run),
        "sweeps": sweeps,
    }
    summary_path = outdir / "budget_sweep_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_budget_report(summary, outdir / "budget_sweep_report.md")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    adapter = Tau2BenchAdapter()
    samples = adapter.load_samples(args.source)
    systems = normalize_systems(args.systems)
    slice_values = [value.strip() for value in args.slice_values.split(",") if value.strip()]
    samples = _slice_samples(adapter, samples, slice_by=args.slice_by, slice_values=slice_values)
    if args.limit is not None:
        samples = samples[: args.limit]
    if args.smoke:
        samples = samples[: min(len(samples), 10)]
    if args.reuse_second_run:
        samples = _reuse_ready_samples(samples)
    if not samples:
        raise ValueError("No tau2-bench samples loaded from source after slicing")

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / TAU2_CONFIG.normalized_filename
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")

    cli_config = {
        "source": str(Path(args.source).resolve()),
        "mode": args.mode,
        "systems": systems,
        "limit": args.limit,
        "smoke": bool(args.smoke),
        "num_runs": args.num_runs,
        "slice_by": args.slice_by,
        "slice_values": slice_values,
        "reuse_second_run": bool(args.reuse_second_run),
        "budget_sweep": bool(args.budget_sweep),
        "user_turn_values": args.user_turn_values,
        "repair_attempt_values": args.repair_attempt_values,
        "tool_call_values": args.tool_call_values,
    }
    cli_config_path = prepared_dir / "tau2_cli_config.json"
    cli_config_path.write_text(json.dumps(cli_config, indent=2), encoding="utf-8")

    if args.budget_sweep:
        _run_budget_sweep(
            tasks=normalized_tasks,
            args=args,
            systems=systems,
            prepared_dir=prepared_dir / "budget_sweep",
            outdir=outdir,
        )
        print(f"prepared tau2-bench taskset: {normalized_path}")
        print(f"budget sweep summary: {outdir / 'budget_sweep_summary.json'}")
        print(f"budget sweep report: {outdir / 'budget_sweep_report.md'}")
        return

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_records: List[Dict[str, Any]] = []
    base_asset_registry_root = Path(args.asset_registry_root) if args.asset_registry_root else (outdir / "asset_registry")
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        run_asset_registry_root = base_asset_registry_root / f"run_{run_index:02d}" if (args.reuse_second_run or args.asset_registry_root) else None
        invoke_run_eval(normalized_path, run_outdir, args.mode, systems, asset_registry_root=run_asset_registry_root)
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
        run_entries=scoreboard.get("runs"),
        experiment_metadata={
            "slice_by": args.slice_by,
            "slice_values": slice_values,
            "reuse_second_run": bool(args.reuse_second_run),
            "budget_sweep": False,
            "config_file": str(cli_config_path.resolve()),
        },
        archive_files=[cli_config_path, Path(args.source)],
    )

    print(f"prepared tau2-bench taskset: {normalized_path}")
    print(f"outputs written under: {outdir}")
    print(f"scoreboard: {outdir / 'scoreboard.json'}")
    print(f"per-system summary: {outdir / 'per_system_summary.json'}")


if __name__ == "__main__":
    main()
