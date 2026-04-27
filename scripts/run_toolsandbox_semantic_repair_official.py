#!/usr/bin/env python3
"""Run ToolSandbox semantic-repair official benchmark variants."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

DEFAULT_SYSTEMS = "a2_planner,a3_full_interaction,a3_no_query,a3_noisy_user"


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except Exception:
        return str(path)


def _split_systems(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _source_manifest(source: Path) -> dict:
    candidates = [source.with_suffix(".manifest.json")]
    if source.name.endswith(".jsonl"):
        candidates.append(source.parent / (source.name[:-6] + ".manifest.json"))
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ToolSandbox semantic-repair official benchmark")
    parser.add_argument("--source", default=str(ROOT_DIR / "data" / "toolsandbox_semantic_repair_official_v1.jsonl"))
    parser.add_argument("--systems", default=DEFAULT_SYSTEMS)
    parser.add_argument("--num-runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", default="planner")
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    systems = _split_systems(args.systems)
    source_path = Path(args.source)
    source_manifest = _source_manifest(source_path)
    benchmark_name = str(source_manifest.get("dataset") or "toolsandbox_semantic_repair_official_v1")
    slice_policy_version = str(source_manifest.get("slice_policy_version") or benchmark_name)
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    bench_cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_toolsandbox_bench.py"),
        "--source",
        str(Path(args.source)),
        "--systems",
        ",".join(systems),
        "--mode",
        str(args.mode),
        "--num-runs",
        str(args.num_runs),
        "--outdir",
        str(outdir),
    ]
    if args.limit is not None:
        bench_cmd.extend(["--limit", str(args.limit)])
    completed = subprocess.run(bench_cmd, cwd=ROOT_DIR, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    score_cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "score_toolsandbox_semantic_repair_official.py"),
        "--dataset",
        str(Path(args.source)),
        "--comparison",
        str(outdir / "comparison.scored.csv"),
        "--outdir",
        str(outdir),
    ]
    completed = subprocess.run(score_cmd, cwd=ROOT_DIR, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    manifest_path = outdir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest.update(
        {
            "benchmark": benchmark_name,
            "source": _repo_relative(source_path),
            "systems": systems,
            "num_runs": int(args.num_runs),
            "slice_policy_version": slice_policy_version,
            "claim_ids": ["interaction_semantic_usefulness_mechanism"],
            "runner_script": _repo_relative(Path(__file__)),
            "score_script": _repo_relative(ROOT_DIR / "scripts" / "score_toolsandbox_semantic_repair_official.py"),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"outputs written under: {outdir}")
    print(f"claim summary: {outdir / 'claim_summary.json'}")
    print(f"report: {outdir / 'report.md'}")


if __name__ == "__main__":
    main()
