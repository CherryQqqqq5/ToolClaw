#!/usr/bin/env python3
"""Run and score the ToolSandbox interaction-live mechanism benchmark."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"


DEFAULT_SYSTEMS = (
    "a2_planner,"
    "a3_no_query,"
    "a3_full_interaction_oracle,"
    "a3_full_interaction_noisy,"
    "a3_full_interaction_irrelevant,"
    "a3_full_interaction_wrong_parameter,"
    "a3_full_interaction_partial"
)


def _split_systems(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _copy_required_outputs(outdir: Path) -> None:
    raw = outdir / "comparison.raw.csv"
    scored = outdir / "comparison.scored.csv"
    if not raw.exists() or not scored.exists():
        raise FileNotFoundError("run_toolsandbox_bench did not produce comparison.raw.csv and comparison.scored.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ToolSandbox interaction-live benchmark")
    parser.add_argument("--source", default=str(ROOT_DIR / "data" / "toolsandbox_interaction_live_v1.jsonl"))
    parser.add_argument("--systems", default=DEFAULT_SYSTEMS)
    parser.add_argument("--num-runs", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mode", default="planner")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    systems = _split_systems(args.systems)
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
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    completed = subprocess.run(bench_cmd, cwd=ROOT_DIR, env=env, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    _copy_required_outputs(outdir)
    score_cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "score_toolsandbox_interaction_live.py"),
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
            "benchmark": "toolsandbox_interaction_live_v1",
            "source": str(Path(args.source)),
            "systems": systems,
            "num_runs": int(args.num_runs),
            "runner_script": str(Path(__file__).resolve()),
            "score_script": str(ROOT_DIR / "scripts" / "score_toolsandbox_interaction_live.py"),
            "interaction_rounds_path": str((outdir / "interaction_rounds.jsonl").resolve()),
            "interaction_effectiveness_summary_path": str((outdir / "interaction_effectiveness_summary.json").resolve()),
            "extraction_prf_path": str((outdir / "extraction_prf.json").resolve()),
            "interaction_live_claim_summary_path": str((outdir / "claim_summary.json").resolve()),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"outputs written under: {outdir}")
    print(f"claim summary: {outdir / 'claim_summary.json'}")
    print(f"report: {outdir / 'report.md'}")


if __name__ == "__main__":
    main()
