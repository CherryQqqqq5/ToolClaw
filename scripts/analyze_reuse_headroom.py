#!/usr/bin/env python3
"""Analyze high-headroom exact or near-match reuse cases from a ToolClaw outdir."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.reuse_headroom_analysis import analyze_outdir, render_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze high-headroom exact or near-match reuse cases")
    parser.add_argument("--outdir", required=True, help="Benchmark output directory containing comparison csv files")
    parser.add_argument("--taskset", default=None, help="Optional taskset/prepared JSON used to recover reuse families")
    parser.add_argument("--left-system", default="a3_interaction", help="Reference system name")
    parser.add_argument("--right-system", default="a4_reuse", help="Candidate system name")
    parser.add_argument(
        "--focus-tiers",
        default="exact_match_reuse,same_family_transfer_reuse",
        help="Comma-separated reuse tiers to focus on",
    )
    parser.add_argument("--json-out", default=None, help="Optional path for JSON output")
    parser.add_argument("--md-out", default=None, help="Optional path for Markdown output")
    return parser.parse_args()


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
    taskset_path = Path(args.taskset) if args.taskset else None
    focus_tiers = [item.strip() for item in str(args.focus_tiers).split(",") if item.strip()]
    analysis = analyze_outdir(
        outdir,
        left_system=args.left_system,
        right_system=args.right_system,
        taskset_path=taskset_path,
        focus_tiers=focus_tiers,
    )
    json_out = Path(args.json_out) if args.json_out else outdir / "reuse_headroom_analysis.json"
    md_out = Path(args.md_out) if args.md_out else outdir / "reuse_headroom_analysis.md"
    json_out = _write_with_fallback(json_out, json.dumps(analysis, indent=2), outdir=outdir)
    md_out = _write_with_fallback(md_out, render_markdown(analysis), outdir=outdir)
    print(f"json: {json_out}")
    print(f"markdown: {md_out}")


if __name__ == "__main__":
    main()
