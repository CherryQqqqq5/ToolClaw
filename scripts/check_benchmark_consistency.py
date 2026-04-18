"""Validate benchmark output consistency across aggregate files and comparison rows."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check benchmark output consistency")
    parser.add_argument("--outdir", required=True, help="Benchmark output directory")
    parser.add_argument("--expected-systems", default=None, help="Comma-separated expected systems list")
    parser.add_argument("--expected-source", default=None, help="Expected source path recorded in experiment_manifest.json")
    parser.add_argument("--expected-config", default=None, help="Expected config file path recorded in experiment_manifest.json")
    parser.add_argument("--expected-model-version", default=None, help="Expected model version recorded in experiment_manifest.json")
    parser.add_argument("--expected-num-runs", type=int, default=None, help="Expected number of repeated runs")
    parser.add_argument("--expected-budget-note", default=None, help="Expected budget note recorded in experiment_manifest.json")
    return parser.parse_args()


def _normalize_csv_categories(raw_value: str) -> List[str]:
    value = (raw_value or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [part.strip() for part in value.split(";") if part.strip()]
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _bool_from_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _resolve_path(value: str | None) -> str | None:
    if not value:
        return None
    return str(Path(value).resolve())


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv_rows(path: Path) -> List[Dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def _comparison_path(outdir: Path) -> Path:
    scored = outdir / "comparison.scored.csv"
    if scored.exists():
        return scored
    raw = outdir / "comparison.csv"
    if raw.exists():
        return raw
    raise FileNotFoundError(f"comparison file not found under {outdir}")


def _check_systems(
    scoreboard: Dict[str, Any],
    per_system: Dict[str, Any],
    manifest: Dict[str, Any],
    expected_systems: Sequence[str] | None,
    errors: List[str],
) -> None:
    scoreboard_systems = list(scoreboard.get("systems", []))
    per_system_keys = list(per_system.keys())
    manifest_systems = list(manifest.get("systems", []))
    if scoreboard_systems != per_system_keys:
        errors.append("system names/order mismatch between scoreboard.json and per_system_summary.json")
    if manifest_systems != scoreboard_systems:
        errors.append("system names/order mismatch between experiment_manifest.json and scoreboard.json")
    if expected_systems is not None and list(expected_systems) != scoreboard_systems:
        errors.append("system names/order mismatch between expected CLI systems and scoreboard.json")


def _check_rows(
    rows: Sequence[Dict[str, str]],
    scoreboard: Dict[str, Any],
    per_system: Dict[str, Any],
    errors: List[str],
) -> None:
    systems = list(scoreboard.get("systems", []))
    num_samples = int(scoreboard.get("num_samples", 0))
    num_runs = int(scoreboard.get("num_runs", 0))
    expected_row_count = len(systems) * num_samples * num_runs
    if len(rows) != expected_row_count:
        errors.append(f"comparison row count mismatch: expected {expected_row_count}, got {len(rows)}")

    task_ids = {row["task_id"] for row in rows}
    if len(task_ids) != num_samples:
        errors.append(f"task count mismatch: scoreboard.num_samples={num_samples}, rows={len(task_ids)}")

    observed_run_indices = sorted({int(row.get("run_index", "0")) for row in rows})
    expected_run_indices = list(range(1, num_runs + 1))
    if observed_run_indices != expected_run_indices:
        errors.append(f"run count mismatch: expected run indices {expected_run_indices}, got {observed_run_indices}")

    observed_systems = [system for system in systems if any(row["system"] == system for row in rows)]
    if observed_systems != systems:
        errors.append("system set mismatch between comparison rows and scoreboard.json")

    rows_by_system: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_system[row["system"]].append(row)
    benchmark_success_by_system: Dict[str, List[float]] = defaultdict(list)
    raw_runs = scoreboard.get("runs", [])
    if isinstance(raw_runs, list):
        for run in raw_runs:
            if not isinstance(run, dict):
                continue
            system = str(run.get("system") or "").strip()
            score_payload = run.get("score", {})
            if not system or not isinstance(score_payload, dict) or "success" not in score_payload:
                continue
            benchmark_success_by_system[system].append(1.0 if _bool_from_value(score_payload.get("success")) else 0.0)
    for system in systems:
        system_rows = rows_by_system.get(system, [])
        if benchmark_success_by_system.get(system):
            success_rate = sum(benchmark_success_by_system[system]) / len(benchmark_success_by_system[system])
        else:
            success_count = sum(1 for row in system_rows if _bool_from_value(row.get("success", "False")))
            success_rate = success_count / len(system_rows) if system_rows else 0.0
        summary_rate = float(per_system.get(system, {}).get("mean_success_rate", -1.0))
        if abs(success_rate - summary_rate) > 1e-9:
            errors.append(
                f"success rate mismatch for {system}: comparison={success_rate:.6f}, per_system_summary={summary_rate:.6f}"
            )


def _check_category_summary(
    outdir: Path,
    rows: Sequence[Dict[str, str]],
    errors: List[str],
) -> None:
    per_category_path = outdir / "per_category_summary.json"
    if not per_category_path.exists():
        return

    per_category = _load_json(per_category_path)
    category_counts: Dict[tuple[str, str], int] = defaultdict(int)
    category_success: Dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        categories = _normalize_csv_categories(row.get("categories", ""))
        if not categories:
            continue
        success = _bool_from_value(row.get("success", "False"))
        for category in categories:
            key = (row["system"], category)
            category_counts[key] += 1
            category_success[key] += int(success)

    for system, category_map in per_category.items():
        if not isinstance(category_map, dict):
            errors.append(f"per_category_summary.json malformed for system {system}")
            continue
        for category, stats in category_map.items():
            key = (system, category)
            expected_rows = category_counts.get(key, 0)
            if expected_rows == 0:
                errors.append(f"category slice mismatch for {system}/{category}: summary exists but comparison rows are missing")
                continue
            expected_success_rate = category_success[key] / expected_rows
            summary_rows = int(float(stats.get("num_rows", 0)))
            summary_success_rate = float(stats.get("success_rate", -1.0))
            if summary_rows != expected_rows:
                errors.append(
                    f"category row count mismatch for {system}/{category}: comparison={expected_rows}, summary={summary_rows}"
                )
            if abs(expected_success_rate - summary_success_rate) > 1e-9:
                errors.append(
                    f"category success rate mismatch for {system}/{category}: comparison={expected_success_rate:.6f}, summary={summary_success_rate:.6f}"
                )


def _check_manifest(
    manifest: Dict[str, Any],
    outdir: Path,
    comparison_path: Path,
    expected_source: str | None,
    expected_config: str | None,
    expected_model_version: str | None,
    expected_num_runs: int | None,
    expected_budget_note: str | None,
    errors: List[str],
) -> None:
    metadata = manifest.get("experiment_metadata", {})
    manifest_comparison = manifest.get("comparison_path")
    if comparison_path.exists() and not manifest_comparison:
        errors.append("manifest comparison_path is null even though comparison output exists")
    if manifest_comparison and _resolve_path(manifest_comparison) != _resolve_path(str(comparison_path)):
        errors.append("manifest comparison_path does not match the benchmark comparison file")
    for field_name in ("comparison_raw_path", "comparison_scored_path"):
        field_value = manifest.get(field_name)
        if field_value and not Path(field_value).exists():
            errors.append(f"manifest {field_name} points to a missing file")
    if expected_source is not None and _resolve_path(manifest.get("source")) != _resolve_path(expected_source):
        errors.append("manifest source does not match expected CLI source")
    if expected_config is not None and _resolve_path(metadata.get("config_file")) != _resolve_path(expected_config):
        errors.append("manifest config_file does not match expected CLI config")
    if expected_model_version is not None and str(metadata.get("model_version")) != expected_model_version:
        errors.append("manifest model_version does not match expected CLI model version")
    if expected_num_runs is not None and int(manifest.get("num_runs", -1)) != expected_num_runs:
        errors.append("manifest num_runs does not match expected CLI num_runs")
    if expected_budget_note is not None and str(metadata.get("budget_note")) != expected_budget_note:
        errors.append("manifest budget_note does not match expected CLI budget note")


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    scoreboard_path = outdir / "scoreboard.json"
    per_system_path = outdir / "per_system_summary.json"
    manifest_path = outdir / "experiment_manifest.json"
    comparison_path = _comparison_path(outdir)

    required_paths = [scoreboard_path, per_system_path, manifest_path, comparison_path]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        print("CONSISTENCY CHECK: FAILED")
        for path in missing:
            print(f"- missing required artifact: {path}")
        raise SystemExit(1)

    scoreboard = _load_json(scoreboard_path)
    per_system = _load_json(per_system_path)
    manifest = _load_json(manifest_path)
    rows = _load_csv_rows(comparison_path)
    expected_systems = [item.strip() for item in args.expected_systems.split(",") if item.strip()] if args.expected_systems else None

    errors: List[str] = []
    _check_systems(scoreboard, per_system, manifest, expected_systems, errors)
    _check_rows(rows, scoreboard, per_system, errors)
    _check_category_summary(outdir, rows, errors)
    _check_manifest(
        manifest,
        outdir,
        comparison_path,
        args.expected_source,
        args.expected_config,
        args.expected_model_version,
        args.expected_num_runs,
        args.expected_budget_note,
        errors,
    )

    print(f"outdir: {outdir.resolve()}")
    print(f"comparison: {comparison_path.resolve()}")
    print(f"systems: {', '.join(scoreboard.get('systems', []))}")
    print(f"num_samples: {scoreboard.get('num_samples')}")
    print(f"num_runs: {scoreboard.get('num_runs')}")
    print(f"source: {manifest.get('source')}")
    print(f"config_file: {manifest.get('experiment_metadata', {}).get('config_file')}")
    print(f"model_version: {manifest.get('experiment_metadata', {}).get('model_version')}")

    if errors:
        print("CONSISTENCY CHECK: FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("CONSISTENCY CHECK: PASSED")


if __name__ == "__main__":
    main()
