#!/usr/bin/env python3
"""Run BFCL benchmark execution only, leaving scoring to score_bfcl_outputs.py."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import BFCLAdapter
from toolclaw.benchmarks.runner_utils import invoke_run_eval, load_run_rows, normalize_systems


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute BFCL benchmark runs without scoring")
    parser.add_argument("--source", required=True, help="Aligned BFCL JSONL or a directory containing aligned track files")
    parser.add_argument("--outdir", default="outputs/bfcl_bench", help="Output directory")
    parser.add_argument("--track", choices=["fc_core", "agentic_ext", "full_v4"], default="fc_core", help="BFCL protocol track")
    parser.add_argument("--official-eval", choices=["true", "false"], default="true", help="Whether official BFCL evaluation is requested")
    parser.add_argument("--toolclaw-diagnostics", choices=["true", "false"], default="true", help="Whether ToolClaw diagnostics should be computed later")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    parser.add_argument("--systems", default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse", help="Comma-separated systems")
    parser.add_argument("--num-runs", type=int, default=1, help="Number of repeated runs")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Preserve prepared taskset")
    return parser.parse_args()


def _bool_from_flag(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _resolve_display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _resolve_source(raw_source: str, track: str) -> Path:
    path = Path(raw_source)
    if path.is_dir():
        if track == "fc_core":
            return path / "bfcl_v4.fc_core.aligned.jsonl"
        if track == "agentic_ext":
            return path / "bfcl_v4.agentic_ext.aligned.jsonl"
        return path
    return path


def _load_manifest_for_source(source_path: Path) -> Path | None:
    manifest_parent = source_path if source_path.is_dir() else source_path.parent
    manifest_path = manifest_parent / "manifest.json"
    return manifest_path if manifest_path.exists() else None


def _load_samples_for_track(adapter: BFCLAdapter, source_path: Path, track: str) -> Sequence[Any]:
    if not source_path.is_dir():
        return adapter.load_samples(str(source_path))
    if track != "full_v4":
        raise FileNotFoundError(f"BFCL aligned source not found: {source_path}")

    merged_samples: List[Any] = []
    for filename in ("bfcl_v4.fc_core.aligned.jsonl", "bfcl_v4.agentic_ext.aligned.jsonl"):
        candidate = source_path / filename
        if not candidate.exists():
            raise FileNotFoundError(f"BFCL aligned source not found: {candidate}")
        merged_samples.extend(adapter.load_samples(str(candidate)))
    return merged_samples


def _task_lookup(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(task.get("task_id") or ""): task for task in tasks if str(task.get("task_id") or "")}


def _json_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _enrich_row(row: Dict[str, str], *, run_index: int, task: Dict[str, Any]) -> Dict[str, Any]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    expected_structure = task.get("expected_call_structure", metadata.get("expected_call_structure", {}))
    return {
        "run_index": run_index,
        **row,
        "bfcl_track": str(metadata.get("bfcl_track") or ""),
        "bfcl_group": str(metadata.get("bfcl_group") or ""),
        "bfcl_language": str(metadata.get("bfcl_language") or ""),
        "bfcl_call_pattern": str(metadata.get("bfcl_call_pattern") or ""),
        "official_evaluator_supported": str(bool(metadata.get("official_evaluator_supported"))),
        "expected_call_structure": _json_value(expected_structure),
        "candidate_tools": _json_value(task.get("candidate_tools", [])),
    }


def _write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    source_path = _resolve_source(args.source, args.track)
    if not source_path.exists():
        raise FileNotFoundError(f"BFCL aligned source not found: {source_path}")

    adapter = BFCLAdapter()
    samples = list(_load_samples_for_track(adapter, source_path, args.track))
    if not samples:
        raise ValueError(f"No BFCL samples loaded from source: {source_path}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    prepared_dir = outdir / "prepared"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    systems = normalize_systems(args.systems)

    normalized_tasks = [adapter.to_eval_task(sample) for sample in samples]
    normalized_path = prepared_dir / "bfcl.normalized.json"
    normalized_path.write_text(json.dumps(normalized_tasks, indent=2), encoding="utf-8")
    task_lookup = _task_lookup(normalized_tasks)

    runs_root = outdir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    raw_rows: List[Dict[str, Any]] = []
    for run_index in range(1, args.num_runs + 1):
        run_outdir = runs_root / f"run_{run_index:02d}"
        invoke_run_eval(normalized_path, run_outdir, args.mode, systems)
        for row in load_run_rows(run_outdir / "comparison.csv"):
            raw_rows.append(_enrich_row(row, run_index=run_index, task=task_lookup[row["task_id"]]))

    raw_comparison_path = outdir / "comparison.raw.csv"
    _write_csv(raw_rows, raw_comparison_path)
    if (runs_root / f"run_{args.num_runs:02d}" / "report.md").exists():
        shutil.copy2(runs_root / f"run_{args.num_runs:02d}" / "report.md", outdir / "report.md")
        shutil.copy2(runs_root / f"run_{args.num_runs:02d}" / "report.md", outdir / "latest_run_report.md")

    source_manifest_path = _load_manifest_for_source(source_path)
    manifest = {
        "benchmark": "bfcl",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "track": args.track,
        "source": _resolve_display_path(source_path),
        "source_manifest": _resolve_display_path(source_manifest_path) if source_manifest_path else None,
        "normalized_taskset": _resolve_display_path(normalized_path),
        "comparison_path": _resolve_display_path(raw_comparison_path),
        "systems": systems,
        "num_runs": args.num_runs,
        "experiment_metadata": {
            "runner_script": _resolve_display_path(Path(__file__)),
            "official_eval_requested": _bool_from_flag(args.official_eval),
            "toolclaw_diagnostics_requested": _bool_from_flag(args.toolclaw_diagnostics),
            "mode": args.mode,
            "raw_only": True,
        },
    }
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not args.keep_normalized_taskset:
        # BFCL scoring needs the prepared taskset, so do nothing. The flag is kept for CLI parity.
        pass

    print(f"prepared bfcl taskset: {normalized_path}")
    print(f"raw comparison: {raw_comparison_path}")
    print(f"manifest: {outdir / 'experiment_manifest.json'}")


if __name__ == "__main__":
    main()
