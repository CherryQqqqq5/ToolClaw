#!/usr/bin/env python3
"""Analyze task-level A3 vs A4 regressions inside a prepared ToolSandbox output directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.reuse_regression_analysis import analyze_outdir, render_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze A3 vs A4 reuse regressions from a ToolSandbox benchmark outdir")
    parser.add_argument("--outdir", required=True, help="Benchmark output directory containing comparison.scored.csv, comparison.raw.csv, or comparison.csv")
    parser.add_argument("--left-system", default="a3_interaction", help="Reference system name")
    parser.add_argument("--right-system", default="a4_reuse", help="Candidate system name")
    parser.add_argument("--json-out", default=None, help="Optional path for the JSON analysis output")
    parser.add_argument("--md-out", default=None, help="Optional path for the Markdown analysis output")
    return parser.parse_args()


def _default_output_path(outdir: Path, filename: str) -> Path:
    return outdir / filename


def _write_with_fallback(path: Path, content: str, *, outdir: Path) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
    except PermissionError:
        fallback_dir = Path("/tmp") / "toolclaw_analysis_outputs" / outdir.name
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / path.name
        fallback_path.write_text(content, encoding="utf-8")
        return fallback_path


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    analysis = analyze_outdir(outdir, left_system=args.left_system, right_system=args.right_system)
    json_out = Path(args.json_out) if args.json_out else _default_output_path(outdir, "a3_vs_a4_reuse_failure_analysis.json")
    md_out = Path(args.md_out) if args.md_out else _default_output_path(outdir, "a3_vs_a4_reuse_failure_analysis.md")
    json_out = _write_with_fallback(json_out, json.dumps(analysis, indent=2), outdir=outdir)
    md_out = _write_with_fallback(md_out, render_markdown(analysis), outdir=outdir)
    print(f"json: {json_out}")
    print(f"markdown: {md_out}")


if __name__ == "__main__":
    main()
