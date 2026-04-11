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
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Sequence

from toolclaw.benchmarks.proxy_env import benchmark_proxy_env
from toolclaw.benchmarks.task_annotations import file_sha256, payload_sha256, sample_id_checksum

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


def invoke_run_eval(
    taskset_path: Path,
    run_outdir: Path,
    mode: str,
    systems: List[str],
    *,
    asset_registry_root: Optional[Path] = None,
) -> None:
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
    if asset_registry_root is not None:
        cmd.extend(["--asset-registry-root", str(asset_registry_root)])
    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env=benchmark_proxy_env({**os.environ, "PYTHONPATH": str(SRC_DIR)}),
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
            primary_failtax = next(
                (
                    str(record["row"].get("primary_failtax"))
                    for record in sample_records
                    if str(record["row"].get("primary_failtax") or "").strip()
                ),
                "recovery",
            )
            sample_stats: Dict[str, Any] = {
                "scenario": sample.scenario if sample is not None else "unknown",
                "primary_failtax": primary_failtax,
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
                metric_value = mean_or_zero(values)
                sample_stats[metric.key] = metric_value
                if metric.column_label != metric.key:
                    sample_stats[metric.column_label] = metric_value
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
            "per_failtax": _group_sample_summary(per_sample, "primary_failtax"),
        }
        for metric in config.aggregate_metrics:
            metric_value = mean_or_zero([float(item.get(metric.key, 0.0)) for item in per_sample.values()])
            system_stats[metric.key] = metric_value
            if metric.column_label != metric.key:
                system_stats[metric.column_label] = metric_value
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
                "row": dict(record["row"]),
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
        metric_values = " | ".join(f"{_summary_metric_value(stats, metric):.3f}" for metric in config.aggregate_metrics)
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
            metric_values = " | ".join(f"{_summary_metric_value(group_stats, metric):.3f}" for metric in metrics)
            lines.append(
                f"| {system} | {group_name} | {int(group_stats['num_rows'])} | {group_stats['success_rate']:.3f} | {metric_values} |"
            )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_csv_rows(rows: Sequence[Dict[str, Any]], out_path: Path) -> None:
    if not rows:
        out_path.write_text("", encoding="utf-8")
        return

    first_row = rows[0]
    fieldnames = list(first_row.keys())
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_combined_run_rows(run_entries: Sequence[Dict[str, Any]], out_path: Path) -> None:
    rows: List[Dict[str, Any]] = []
    for entry in run_entries:
        row = dict(entry.get("row", {}))
        row["run_index"] = entry.get("run_index", 0)
        ordered_row = {"run_index": row.pop("run_index")}
        ordered_row.update(row)
        rows.append(ordered_row)
    write_csv_rows(rows, out_path)


def _group_sample_summary(per_sample: Dict[str, Dict[str, Any]], key: str) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for sample_stats in per_sample.values():
        group_name = str(sample_stats.get(key) or "unknown")
        grouped.setdefault(group_name, []).append(sample_stats)
    summary: Dict[str, Dict[str, float]] = {}
    for group_name, items in grouped.items():
        summary[group_name] = {
            "num_rows": float(len(items)),
            "success_rate": mean_or_zero([float(item.get("success_rate", 0.0)) for item in items]),
            "pass_at_k": mean_or_zero([float(item.get("pass_at_k", 0.0)) for item in items]),
            "consistency": mean_or_zero([float(item.get("consistency", 0.0)) for item in items]),
        }
    return summary


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
    run_entries: Optional[Sequence[Dict[str, Any]]] = None,
    comparison_filename: Optional[str] = "comparison.csv",
    latest_comparison_filename: Optional[str] = "latest_run_comparison.csv",
    extra_output_writers: Optional[Callable[[Dict[str, Any], Path], None]] = None,
    experiment_metadata: Optional[Dict[str, Any]] = None,
    archive_files: Optional[Sequence[Path]] = None,
) -> None:
    latest_run_outdir = outdir / "runs" / f"run_{num_runs:02d}"
    latest_comparison = latest_run_outdir / "comparison.csv"
    latest_report = latest_run_outdir / "report.md"
    if comparison_filename is not None:
        if run_entries:
            write_combined_run_rows(run_entries, outdir / comparison_filename)
        elif latest_comparison.exists():
            shutil.copy2(latest_comparison, outdir / comparison_filename)
    if latest_comparison_filename is not None and latest_comparison.exists():
        shutil.copy2(latest_comparison, outdir / latest_comparison_filename)
    if latest_report.exists():
        shutil.copy2(latest_report, outdir / "report.md")
        shutil.copy2(latest_report, outdir / "latest_run_report.md")

    scoreboard_path = outdir / "scoreboard.json"
    scoreboard_path.write_text(json.dumps(scoreboard, indent=2), encoding="utf-8")

    per_system_summary_path = outdir / "per_system_summary.json"
    per_system_summary_path.write_text(json.dumps(scoreboard["per_system_summary"], indent=2), encoding="utf-8")
    write_system_markdown(scoreboard["per_system_summary"], outdir / "per_system_summary.md", config)
    if extra_output_writers is not None:
        extra_output_writers(scoreboard["per_system_summary"], outdir)

    sample_ids = sorted({str(entry.get("task_id", "")) for entry in scoreboard.get("runs", []) if entry.get("task_id")})
    archive_hashes = {
        str(Path(candidate).resolve()): file_sha256(Path(candidate))
        for candidate in archive_files or []
        if Path(candidate).exists() and Path(candidate).is_file()
    }
    config_hash = payload_sha256({key: value for key, value in archive_hashes.items() if value is not None}) if archive_hashes else None
    git_commit = _git_commit()
    source_hash = file_sha256(Path(source)) if Path(source).exists() else None
    normalized_hash = file_sha256(normalized_path)
    sample_checksum = sample_id_checksum(sample_ids)

    manifest = {
        "benchmark": benchmark_name,
        "source": str(Path(source).resolve()),
        "source_sha256": source_hash,
        "normalized_taskset": str(normalized_path.resolve()),
        "normalized_taskset_sha256": normalized_hash,
        "sample_count": scoreboard["num_samples"],
        "sample_id_checksum": sample_checksum,
        "mode": mode,
        "systems": list(systems),
        "num_runs": num_runs,
        "git_commit": git_commit,
        "config_sha256": config_hash,
        "scoreboard_path": str(scoreboard_path.resolve()),
        "per_system_summary_path": str(per_system_summary_path.resolve()),
    }
    (prepared_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive_dir = outdir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_files: List[str] = []
    for candidate in archive_files or []:
        path = Path(candidate)
        if not path.exists() or not path.is_file():
            continue
        destination = archive_dir / path.name
        shutil.copy2(path, destination)
        archived_files.append(str(destination.resolve()))

    experiment_manifest = {
        "benchmark": benchmark_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(Path(source).resolve()),
        "source_sha256": source_hash,
        "normalized_taskset": str(normalized_path.resolve()),
        "normalized_taskset_sha256": normalized_hash,
        "mode": mode,
        "systems": list(systems),
        "num_runs": num_runs,
        "sample_id_checksum": sample_checksum,
        "git_commit": git_commit,
        "config_sha256": config_hash,
        "scoreboard_path": str(scoreboard_path.resolve()),
        "report_path": str((outdir / "report.md").resolve()) if (outdir / "report.md").exists() else None,
        "comparison_path": str((outdir / comparison_filename).resolve()) if comparison_filename and (outdir / comparison_filename).exists() else None,
        "per_system_summary_path": str(per_system_summary_path.resolve()),
        "archived_files": archived_files,
        "archive_hashes": archive_hashes,
        "experiment_metadata": dict(experiment_metadata or {}),
    }
    write_experiment_manifest(outdir, experiment_manifest)
    footer = (
        f"Results generated from commit {git_commit}."
        if git_commit
        else "Results generated from a workspace without a resolved git commit."
    )
    for report_candidate in (outdir / "report.md", outdir / "latest_run_report.md"):
        _append_report_footer(report_candidate, footer)

    if not keep_normalized_taskset:
        temp_copy = Path(tempfile.gettempdir()) / f"toolclaw_{benchmark_name}_{os.getpid()}.json"
        temp_copy.write_text(normalized_path.read_text(encoding="utf-8"), encoding="utf-8")


def write_experiment_manifest(outdir: Path, manifest: Dict[str, Any]) -> None:
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def update_experiment_manifest(
    outdir: Path,
    *,
    updates: Optional[Dict[str, Any]] = None,
    metadata_updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    manifest_path = outdir / "experiment_manifest.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if updates:
        manifest.update(updates)
    if metadata_updates:
        metadata = dict(manifest.get("experiment_metadata", {}))
        metadata.update(metadata_updates)
        manifest["experiment_metadata"] = metadata
    write_experiment_manifest(outdir, manifest)
    return manifest


def _append_report_footer(report_path: Path, footer: str) -> None:
    if not report_path.exists():
        return
    body = report_path.read_text(encoding="utf-8")
    footer_line = f"_ {footer} _"
    if footer_line in body:
        return
    report_path.write_text(body.rstrip() + f"\n\n{footer_line}\n", encoding="utf-8")


def _extract_stat(score_payload: Dict[str, Any], metric: AggregateMetric) -> float:
    if metric.source == "diagnostics":
        value = score_payload.get("diagnostics", {}).get(metric.key, 0.0)
    else:
        value = score_payload.get("metrics", {}).get(metric.key, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _summary_metric_value(summary_payload: Dict[str, Any], metric: AggregateMetric) -> float:
    value = summary_payload.get(metric.key)
    if value is None and metric.column_label != metric.key:
        value = summary_payload.get(metric.column_label)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _git_commit() -> Optional[str]:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip()
    return commit or None
