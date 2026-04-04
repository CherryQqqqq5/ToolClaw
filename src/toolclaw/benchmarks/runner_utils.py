"""Shared helpers for benchmark scripts that reuse run_eval.py and aggregate scoreboards."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence


ROOT_DIR = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT_DIR / "src"


@dataclass(frozen=True)
class AggregateMetric:
    key: str
    source: str = "metrics"
    label: Optional[str] = None

    @property
    def column_label(self) -> str:
        return self.label or self.key


@dataclass(frozen=True)
class BenchmarkScriptConfig:
    benchmark_name: str
    normalized_filename: str
    system_summary_title: str
    aggregate_metrics: Sequence[AggregateMetric]
    signature_builder: Callable[[Dict[str, Any], Dict[str, str]], str]
    sample_extra_builder: Optional[Callable[[Any], Dict[str, Any]]] = None
    system_extra_builder: Optional[Callable[[List[Dict[str, Any]]], Dict[str, Any]]] = None


def normalize_systems(raw_systems: str) -> List[str]:
    return [item.strip() for item in raw_systems.split(",") if item.strip()]


def invoke_run_eval(taskset_path: Path, run_outdir: Path, mode: str, systems: List[str]) -> None:
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


def load_run_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mean_or_zero(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(mean(values))


def score_to_payload(score: Any) -> Dict[str, Any]:
    return {
        "benchmark": score.benchmark,
        "sample_id": score.sample_id,
        "success": score.success,
        "metrics": score.metrics,
        "diagnostics": score.diagnostics,
    }


def aggregate_records(
    *,
    config: BenchmarkScriptConfig,
    adapter: Any,
    samples: Sequence[Any],
    systems: Sequence[str],
    run_records: List[Dict[str, Any]],
    source: str,
    mode: str,
    normalized_path: Path,
    num_runs: int,
    smoke: bool,
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
            signatures = [config.signature_builder(record["score"], record["row"]) for record in sample_records]
            consistency = 1.0 if len(signatures) <= 1 else max(signatures.count(sig) for sig in set(signatures)) / len(signatures)
            sample = sample_by_id.get(sample_id)
            sample_stats: Dict[str, Any] = {
                "scenario": sample.scenario if sample is not None else "unknown",
                "num_runs": len(sample_records),
                "success_rate": mean_or_zero(successes),
                "pass_at_k": 1.0 if any(successes) else 0.0,
                "consistency": consistency,
                "distinct_outcomes": len(set(signatures)),
                "stop_reasons": [record["row"].get("stop_reason", "unknown") for record in sample_records],
            }
            for metric in config.aggregate_metrics:
                values = [
                    _extract_stat(record["score"], metric)
                    for record in sample_records
                ]
                sample_stats[metric.key] = mean_or_zero(values)
            if sample is not None and config.sample_extra_builder is not None:
                sample_stats.update(config.sample_extra_builder(sample))
            per_sample[sample_id] = sample_stats

        system_stats: Dict[str, Any] = {
            "num_samples": len(per_sample),
            "num_runs": num_runs,
            "mean_success_rate": mean_or_zero([item["success_rate"] for item in per_sample.values()]),
            "pass_at_k": mean_or_zero([item["pass_at_k"] for item in per_sample.values()]),
            "consistency": mean_or_zero([item["consistency"] for item in per_sample.values()]),
            "per_sample": per_sample,
        }
        for metric in config.aggregate_metrics:
            system_stats[metric.key] = mean_or_zero([float(item.get(metric.key, 0.0)) for item in per_sample.values()])
        if config.system_extra_builder is not None:
            system_stats.update(config.system_extra_builder(system_records))
        per_system_summary[system] = system_stats

    return {
        "benchmark": adapter.benchmark_name,
        "source": str(Path(source).resolve()),
        "normalized_taskset": str(normalized_path.resolve()),
        "mode": mode,
        "systems": list(systems),
        "num_samples": len(samples),
        "num_runs": num_runs,
        "smoke": bool(smoke),
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


def write_system_markdown(summary: Dict[str, Any], out_path: Path, config: BenchmarkScriptConfig) -> None:
    metric_headers = [metric.column_label for metric in config.aggregate_metrics]
    header = "| system | samples | runs | mean_success_rate | pass@k | consistency | " + " | ".join(metric_headers) + " |"
    separator = "|---|---:|---:|---:|---:|---:|" + "---:|" * len(metric_headers)
    lines = [f"# {config.system_summary_title}", "", header, separator]
    for system, stats in summary.items():
        metric_values = " | ".join(f"{float(stats.get(metric.key, 0.0)):.3f}" for metric in config.aggregate_metrics)
        lines.append(
            f"| {system} | {stats['num_samples']} | {stats['num_runs']} | {stats['mean_success_rate']:.3f} | {stats['pass_at_k']:.3f} | {stats['consistency']:.3f} | {metric_values} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_group_markdown(
    grouped_summary: Dict[str, Any],
    out_path: Path,
    *,
    title: str,
    group_key: str,
    metrics: Sequence[AggregateMetric],
) -> None:
    metric_headers = [metric.column_label for metric in metrics]
    header = "| system | " + group_key + " | rows | success_rate | " + " | ".join(metric_headers) + " |"
    separator = "|---|---|---:|---:|" + "---:|" * len(metric_headers)
    lines = [f"# {title}", "", header, separator]
    for system, stats in grouped_summary.items():
        groups = stats.get(group_key, {})
        for group_name, group_stats in sorted(groups.items()):
            metric_values = " | ".join(f"{float(group_stats.get(metric.key, 0.0)):.3f}" for metric in metrics)
            lines.append(
                f"| {system} | {group_name} | {int(group_stats['num_rows'])} | {group_stats['success_rate']:.3f} | {metric_values} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def finalize_outputs(
    *,
    outdir: Path,
    prepared_dir: Path,
    benchmark_name: str,
    source: str,
    normalized_path: Path,
    mode: str,
    systems: Sequence[str],
    num_runs: int,
    scoreboard: Dict[str, Any],
    config: BenchmarkScriptConfig,
    keep_normalized_taskset: bool,
    extra_output_writers: Optional[Callable[[Dict[str, Any], Path], None]] = None,
) -> None:
    latest_run_outdir = outdir / "runs" / f"run_{num_runs:02d}"
    latest_comparison = latest_run_outdir / "comparison.csv"
    latest_report = latest_run_outdir / "report.md"
    if latest_comparison.exists():
        shutil.copy2(latest_comparison, outdir / "comparison.csv")
    if latest_report.exists():
        shutil.copy2(latest_report, outdir / "report.md")

    scoreboard_path = outdir / "scoreboard.json"
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")

    per_system_summary_path = outdir / "per_system_summary.json"
    per_system_summary_path.write_text(json.dumps(scoreboard["per_system_summary"], indent=2), encoding="utf-8")
    write_system_markdown(scoreboard["per_system_summary"], outdir / "per_system_summary.md", config)
    if extra_output_writers is not None:
        extra_output_writers(scoreboard["per_system_summary"], outdir)

    manifest = {
        "benchmark": benchmark_name,
        "source": str(Path(source).resolve()),
        "normalized_taskset": str(normalized_path.resolve()),
        "sample_count": scoreboard["num_samples"],
        "mode": mode,
        "systems": list(systems),
        "num_runs": num_runs,
        "scoreboard_path": str(scoreboard_path.resolve()),
        "per_system_summary_path": str(per_system_summary_path.resolve()),
    }
    (prepared_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not keep_normalized_taskset:
        temp_copy = Path(tempfile.gettempdir()) / f"toolclaw_{benchmark_name}_{os.getpid()}.json"
        temp_copy.write_text(normalized_path.read_text(encoding="utf-8"), encoding="utf-8")


def _extract_stat(score_payload: Dict[str, Any], metric: AggregateMetric) -> float:
    if metric.source == "diagnostics":
        value = score_payload.get("diagnostics", {}).get(metric.key, 0.0)
    else:
        value = score_payload.get("metrics", {}).get(metric.key, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
