#!/usr/bin/env python3
"""
Aggregate official ToolSandbox runs under data/agent_*/result_summary.json.

Typical layout (cwd = repo root when using run_toolsandbox_official.sh):
  data/agent_<agent>_<user>_<MM_DD_YYYY_HH_MM_SS>/result_summary.json

Each file usually contains one row in per_scenario_results (single --scenarios run).

This tool:
  - Restricts analysis to scenario names listed in a safe-subset file (one name per line).
  - Dedupes by scenario name, keeping the newest result by file mtime (configurable).
  - Applies the same pass rule as paper notes: no exception_type/traceback, milestone_similarity >= thresh.

Examples:
  python3 scripts/analyze_toolsandbox_official_subset.py \\
    --safe-list outputs/official_subset/safe_scenarios.txt \\
    --data-root data

  python3 scripts/analyze_toolsandbox_official_subset.py \\
    --safe-list outputs/official_subset/safe_scenarios.txt \\
    --since 2026-04-14T23:00:00 \\
    --out-csv outputs/official_subset/safe_subset_scored.csv \\
    --out-failures outputs/official_subset/safe_subset_failures.tsv
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    run_dir: Path
    result_path: Path
    mtime: float
    milestone_similarity: Optional[float]
    similarity: Optional[float]
    exception_type: Any
    traceback: Any
    turn_count: Any
    minefield_similarity: Any
    pass_ok: bool
    pass_reason: str


def parse_since(value: str) -> datetime:
    raw = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"invalid --since {value!r}; use e.g. 2026-04-14T23:00:00 or 2026-04-14"
    )


def load_safe_scenarios(path: Path) -> List[str]:
    if not path.is_file():
        raise FileNotFoundError(f"safe list not found: {path}")
    names: List[str] = []
    seen: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line not in seen:
            seen.add(line)
            names.append(line)
    return names


def is_pass(row: Dict[str, Any], *, thresh: float) -> Tuple[bool, str]:
    ex = row.get("exception_type")
    if ex not in (None, "", []):
        return False, f"exception_type={ex!r}"
    tb = row.get("traceback")
    if tb not in (None, "", []):
        return False, "traceback_set"
    ms = row.get("milestone_similarity")
    if ms is None:
        ms = row.get("similarity")
    try:
        score = float(ms)
    except (TypeError, ValueError):
        return False, "missing_similarity"
    if score < thresh:
        return False, f"below_thresh({score:.6g}<{thresh})"
    return True, "ok"


def iter_result_files(data_root: Path) -> Iterable[Path]:
    for path in sorted(data_root.glob("agent_*/result_summary.json")):
        if path.is_file():
            yield path


def collect_rows(
    *,
    data_root: Path,
    since: Optional[datetime],
) -> List[Tuple[Path, float, List[Dict[str, Any]]]]:
    """Return list of (result_path, mtime, per_scenario_results rows) filtered by since."""
    out: List[Tuple[Path, float, List[Dict[str, Any]]]] = []
    since_ts = since.timestamp() if since else None
    for result_path in iter_result_files(data_root):
        mtime = result_path.stat().st_mtime
        if since_ts is not None and mtime < since_ts:
            continue
        try:
            doc = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows = doc.get("per_scenario_results") or []
        if not isinstance(rows, list):
            continue
        out.append((result_path, mtime, rows))
    return out


def build_scenario_results(
    bundles: List[Tuple[Path, float, List[Dict[str, Any]]]],
    *,
    safe_set: Set[str],
    thresh: float,
) -> Dict[str, ScenarioResult]:
    """Map scenario name -> best ScenarioResult (newest result_summary by file mtime)."""
    best: Dict[str, ScenarioResult] = {}

    for result_path, mtime, rows in bundles:
        run_dir = result_path.parent
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("scenario_name") or row.get("scenario")
            if not name or str(name) not in safe_set:
                continue
            scenario = str(name)
            ok, reason = is_pass(row, thresh=thresh)
            ms = row.get("milestone_similarity")
            sim = row.get("similarity")
            sr = ScenarioResult(
                scenario=scenario,
                run_dir=run_dir,
                result_path=result_path,
                mtime=mtime,
                milestone_similarity=float(ms) if ms is not None else None,
                similarity=float(sim) if sim is not None else None,
                exception_type=row.get("exception_type"),
                traceback=row.get("traceback"),
                turn_count=row.get("turn_count"),
                minefield_similarity=row.get("minefield_similarity"),
                pass_ok=ok,
                pass_reason=reason,
            )
            prev = best.get(scenario)
            if prev is None or mtime > prev.mtime:
                best[scenario] = sr
    return best


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score official ToolSandbox runs restricted to a safe scenario list.",
    )
    parser.add_argument(
        "--safe-list",
        type=Path,
        default=Path("outputs/official_subset/safe_scenarios.txt"),
        help="Text file: one scenario name per line (# comments allowed).",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Directory containing agent_*/result_summary.json (default: data).",
    )
    parser.add_argument(
        "--since",
        type=parse_since,
        default=None,
        help="Only include result_summary.json with mtime >= this (local time), e.g. 2026-04-14T23:00:00",
    )
    parser.add_argument(
        "--thresh",
        type=float,
        default=0.95,
        help="Pass if milestone_similarity (else similarity) >= thresh (default 0.95).",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=None,
        help="Optional CSV path for per-scenario rows (safe subset only).",
    )
    parser.add_argument(
        "--out-failures",
        type=Path,
        default=None,
        help="Optional TSV of failed scenarios in safe subset (for debugging / code iteration).",
    )
    parser.add_argument(
        "--out-missing",
        type=Path,
        default=None,
        help="Optional text file listing safe scenarios with no matching result under data-root.",
    )
    parser.add_argument(
        "--include-missing-in-failures",
        action="store_true",
        help="With --out-failures, append one row per missing scenario (pass_reason=not_found).",
    )
    args = parser.parse_args()

    ordered_safe = load_safe_scenarios(args.safe_list)
    safe_set = set(ordered_safe)

    bundles = collect_rows(data_root=args.data_root, since=args.since)
    best = build_scenario_results(bundles, safe_set=safe_set, thresh=args.thresh)

    present = set(best.keys())
    missing = [s for s in ordered_safe if s not in present]

    passed = sum(1 for s in ordered_safe if s in best and best[s].pass_ok)
    passed_in_found = sum(1 for s in present if best[s].pass_ok)
    n = len(ordered_safe)
    scored = len(present)

    print(f"safe_list: {args.safe_list.resolve()}")
    print(f"data_root: {args.data_root.resolve()}")
    print(f"since: {args.since}")
    print(f"thresh: {args.thresh}")
    print(f"safe_count: {n}  found_in_data: {scored}  missing: {len(missing)}")
    print(f"pass (on full safe list, missing count as not pass): {passed}/{n}  rate: {passed/n:.4f}" if n else "pass: n/a")
    if scored:
        print(f"pass (among found only): {passed_in_found}/{scored}  rate: {passed_in_found/scored:.4f}")

    if args.out_missing is not None:
        args.out_missing.parent.mkdir(parents=True, exist_ok=True)
        args.out_missing.write_text("\n".join(missing) + ("\n" if missing else ""), encoding="utf-8")
        print(f"wrote missing ({len(missing)}): {args.out_missing}")

    if args.out_csv:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "scenario",
            "pass_ok",
            "pass_reason",
            "milestone_similarity",
            "similarity",
            "exception_type",
            "turn_count",
            "minefield_similarity",
            "run_dir",
            "result_path",
            "mtime_iso",
        ]
        with args.out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for name in ordered_safe:
                if name not in best:
                    continue
                sr = best[name]
                w.writerow(
                    {
                        "scenario": sr.scenario,
                        "pass_ok": sr.pass_ok,
                        "pass_reason": sr.pass_reason,
                        "milestone_similarity": sr.milestone_similarity,
                        "similarity": sr.similarity,
                        "exception_type": sr.exception_type,
                        "turn_count": sr.turn_count,
                        "minefield_similarity": sr.minefield_similarity,
                        "run_dir": str(sr.run_dir),
                        "result_path": str(sr.result_path),
                        "mtime_iso": datetime.fromtimestamp(sr.mtime).isoformat(timespec="seconds"),
                    }
                )
        print(f"wrote csv: {args.out_csv}")

    if args.out_failures:
        args.out_failures.parent.mkdir(parents=True, exist_ok=True)
        with args.out_failures.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(
                [
                    "scenario",
                    "pass_reason",
                    "milestone_similarity",
                    "similarity",
                    "exception_type",
                    "turn_count",
                    "result_path",
                ]
            )
            for name in ordered_safe:
                if name not in best:
                    continue
                sr = best[name]
                if sr.pass_ok:
                    continue
                w.writerow(
                    [
                        sr.scenario,
                        sr.pass_reason,
                        sr.milestone_similarity,
                        sr.similarity,
                        sr.exception_type,
                        sr.turn_count,
                        sr.result_path,
                    ]
                )
            if args.include_missing_in_failures:
                for name in missing:
                    w.writerow([name, "not_found", "", "", "", "", ""])
        print(f"wrote failures: {args.out_failures}")


if __name__ == "__main__":
    main()
