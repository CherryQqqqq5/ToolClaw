#!/usr/bin/env python3
"""Run a targeted Tau2-style before/after study for compound approval+repair."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.tau2_compound_approval_repair import run_compound_ablation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run targeted Tau2 compound approval+repair before/after ablation")
    parser.add_argument(
        "--outdir",
        default="/tmp/tau2_compound_approval_repair_ablation",
        help="Directory for traces and summary artifacts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    analysis = run_compound_ablation(outdir)
    print(f"json: {outdir / 'tau2_compound_approval_repair_ablation.json'}")
    print(f"markdown: {outdir / 'tau2_compound_approval_repair_ablation.md'}")
    print(f"headline: {analysis['headline']}")


if __name__ == "__main__":
    main()
