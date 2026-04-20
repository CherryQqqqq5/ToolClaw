#!/usr/bin/env python3
"""Aggregate BFCL official evaluation and ToolClaw diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import BFCLAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score BFCL benchmark outputs")
    parser.add_argument("--outdir", required=True, help="BFCL benchmark outdir from run_bfcl_bench.py")
    parser.add_argument("--official-eval", choices=["true", "false"], default="true", help="Whether to run the official BFCL evaluator")
    parser.add_argument("--toolclaw-diagnostics", choices=["true", "false"], default="true", help="Whether to compute ToolClaw diagnostics")
    parser.add_argument("--official-evaluator-script", default=None, help="Optional override for the official evaluator wrapper script")
    return parser.parse_args()


def _bool_from_flag(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _key(row: Dict[str, Any]) -> Tuple[int, str, str]:
    return (int(row.get("run_index", 0) or 0), str(row.get("task_id") or ""), str(row.get("system") or ""))


def _suite_name_for_track(track: str) -> str:
    if track == "fc_core":
        return "bfcl_fc_core"
    if track == "agentic_ext":
        return "bfcl_agentic_ext"
    if track == "full_v4":
        return "bfcl_full_v4"
    return "bfcl"


def _load_task_lookup(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return {}
    return {str(task.get("task_id") or ""): task for task in payload if isinstance(task, dict)}


def _discover_official_evaluator(manifest: Dict[str, Any], override: str | None) -> Path | None:
    if override:
        path = Path(override)
        return path if path.exists() else None
    source_manifest = manifest.get("source_manifest")
    if source_manifest:
        path = ROOT_DIR / source_manifest
        if path.exists():
            payload = _load_json(path)
            script = str(payload.get("official_evaluator_script") or "").strip()
            if script:
                candidate = (ROOT_DIR / script) if not Path(script).is_absolute() else Path(script)
                if candidate.exists():
                    return candidate
    return None


def _run_official_evaluator(
    *,
    evaluator_script: Path | None,
    normalized_taskset: Path,
    comparison_raw: Path,
    outdir: Path,
    official_requested: bool,
) -> Tuple[Dict[Tuple[int, str, str], Dict[str, Any]], List[Dict[str, Any]]]:
    if not official_requested:
        return {}, [{"stratum": "all", "reason": "official_eval_disabled", "paper_safe": False}]
    if evaluator_script is None:
        return {}, [{"stratum": "all", "reason": "official_evaluator_unavailable", "paper_safe": False}]

    with tempfile.TemporaryDirectory(prefix="toolclaw_bfcl_eval_") as tmp:
        output_path = Path(tmp) / "official_eval.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(evaluator_script),
                "--prepared-taskset",
                str(normalized_taskset),
                "--comparison",
                str(comparison_raw),
                "--out",
                str(output_path),
            ],
            cwd=ROOT_DIR,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not output_path.exists():
            return {}, [{"stratum": "all", "reason": "official_evaluator_failed", "paper_safe": False, "stderr": completed.stderr.strip()}]
        payload = _load_json(output_path)

    results: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    for row in payload.get("results", []):
        if not isinstance(row, dict):
            continue
        results[_key(row)] = {
            "success": float(row.get("success", 0.0)),
            "tool_selection_correctness": float(row.get("tool_selection_correctness", 0.0)),
            "argument_correctness": float(row.get("argument_correctness", 0.0)),
            "structure_correctness": float(row.get("structure_correctness", 0.0)),
            "paper_safe": bool(row.get("paper_safe", False)),
            "unsupported_reasons": list(row.get("unsupported_reasons", [])) if isinstance(row.get("unsupported_reasons"), list) else [],
        }
    unsupported = list(payload.get("unsupported_strata", [])) if isinstance(payload.get("unsupported_strata"), list) else []
    return results, unsupported


def _toolclaw_row_scores(
    *,
    adapter: BFCLAdapter,
    row: Dict[str, str],
    task_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    task = task_lookup[row["task_id"]]
    sample = adapter.load_samples_from_tasks([task])[0]
    trace_path = Path(row["trace_path"])
    if not trace_path.is_absolute():
        trace_path = ROOT_DIR / row["trace_path"]
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    score = adapter.score_trace(sample, trace_payload)
    return {
        "binder_selection_match": float(score.metrics.get("binder_selection_match", 0.0)),
        "tool_sequence_match": float(score.metrics.get("tool_sequence_match", 0.0)),
        "parameter_fill_ratio": float(score.metrics.get("parameter_fill_ratio", 0.0)),
        "policy_format_compliance": float(score.metrics.get("policy_format_compliance", 0.0)),
        "repair_overhead": float(score.metrics.get("repair_overhead", 0.0)),
    }


def _mean(items: Iterable[float]) -> float:
    values = list(items)
    if not values:
        return 0.0
    return float(mean(values))


def _aggregate(rows: List[Dict[str, Any]], metric_keys: List[str]) -> Dict[str, Dict[str, float]]:
    per_system: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        per_system.setdefault(str(row["system"]), []).append(row)
    summary: Dict[str, Dict[str, float]] = {}
    for system, system_rows in per_system.items():
        summary[system] = {
            "num_rows": float(len(system_rows)),
            **{key: _mean(float(row.get(key, 0.0)) for row in system_rows) for key in metric_keys},
        }
    return summary


def _paper_safe_for_fc_core(rows: List[Dict[str, Any]], unsupported: List[Dict[str, Any]]) -> bool:
    if unsupported:
        return False
    if not rows:
        return False
    return all(bool(row.get("official_bfcl_eval_paper_safe")) for row in rows)


def _claim_summary(
    *,
    suite: str,
    track: str,
    official_scoreboard: Dict[str, Any],
    toolclaw_diagnostics: Dict[str, Any],
    scored_rows: List[Dict[str, Any]],
    unsupported: List[Dict[str, Any]],
) -> Dict[str, Any]:
    official_metrics = official_scoreboard.get("per_system", {})
    if track == "fc_core":
        claim_id = "planner_binding_headline"
        paper_safe = _paper_safe_for_fc_core(scored_rows, unsupported)
        interpretation = "BFCL fc_core is paper-safe only when the official evaluator covers all included strata."
    else:
        claim_id = "bfcl_agentic_supporting"
        paper_safe = False
        interpretation = "BFCL agentic extension is supporting-only and must not be used as the planner/binder headline claim."
    return {
        "suite": suite,
        "status": "completed",
        "track": track,
        "paper_safe_for_claim": paper_safe,
        "official_bfcl_eval": official_metrics,
        "toolclaw_diagnostics": toolclaw_diagnostics.get("per_system", {}),
        "unsupported_strata": unsupported,
        "claims": [
            {
                "claim_id": claim_id,
                "paper_safe_for_claim": paper_safe,
                "metric_snapshot": official_metrics,
                "interpretation": interpretation,
            }
        ],
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    manifest_path = outdir / "experiment_manifest.json"
    comparison_raw_path = outdir / "comparison.raw.csv"
    if not manifest_path.exists() or not comparison_raw_path.exists():
        raise FileNotFoundError("Expected BFCL raw outputs are missing")

    manifest = _load_json(manifest_path)
    normalized_taskset = ROOT_DIR / manifest["normalized_taskset"] if not Path(manifest["normalized_taskset"]).is_absolute() else Path(manifest["normalized_taskset"])
    rows = _load_csv(comparison_raw_path)
    task_lookup = _load_task_lookup(normalized_taskset)
    adapter = BFCLAdapter()

    evaluator_script = _discover_official_evaluator(manifest, args.official_evaluator_script)
    official_results, unsupported = _run_official_evaluator(
        evaluator_script=evaluator_script,
        normalized_taskset=normalized_taskset,
        comparison_raw=comparison_raw_path,
        outdir=outdir,
        official_requested=_bool_from_flag(args.official_eval),
    )

    scored_rows: List[Dict[str, Any]] = []
    for row in rows:
        official = official_results.get(
            (int(row.get("run_index", "0") or 0), row["task_id"], row["system"]),
            {
                "success": 0.0,
                "tool_selection_correctness": 0.0,
                "argument_correctness": 0.0,
                "structure_correctness": 0.0,
                "paper_safe": False,
                "unsupported_reasons": ["official_evaluator_unavailable"],
            },
        )
        diagnostics = (
            _toolclaw_row_scores(adapter=adapter, row=row, task_lookup=task_lookup)
            if _bool_from_flag(args.toolclaw_diagnostics)
            else {
                "binder_selection_match": 0.0,
                "tool_sequence_match": 0.0,
                "parameter_fill_ratio": 0.0,
                "policy_format_compliance": 0.0,
                "repair_overhead": 0.0,
            }
        )
        scored_rows.append(
            {
                **row,
                "official_bfcl_eval_success": float(official["success"]),
                "official_bfcl_eval_tool_selection_correctness": float(official["tool_selection_correctness"]),
                "official_bfcl_eval_argument_correctness": float(official["argument_correctness"]),
                "official_bfcl_eval_structure_correctness": float(official["structure_correctness"]),
                "official_bfcl_eval_paper_safe": bool(official["paper_safe"]),
                "official_bfcl_eval_unsupported_reasons": json.dumps(official.get("unsupported_reasons", [])),
                "toolclaw_diagnostics_binder_selection_match": diagnostics["binder_selection_match"],
                "toolclaw_diagnostics_tool_sequence_match": diagnostics["tool_sequence_match"],
                "toolclaw_diagnostics_parameter_fill_ratio": diagnostics["parameter_fill_ratio"],
                "toolclaw_diagnostics_policy_format_compliance": diagnostics["policy_format_compliance"],
                "toolclaw_diagnostics_repair_overhead": diagnostics["repair_overhead"],
            }
        )

    comparison_scored_path = outdir / "comparison.scored.csv"
    _write_csv(scored_rows, comparison_scored_path)

    official_scoreboard = {
        "benchmark": "bfcl",
        "track": manifest.get("track"),
        "namespace": "official_bfcl_eval",
        "per_system": _aggregate(
            scored_rows,
            [
                "official_bfcl_eval_success",
                "official_bfcl_eval_tool_selection_correctness",
                "official_bfcl_eval_argument_correctness",
                "official_bfcl_eval_structure_correctness",
            ],
        ),
        "unsupported_strata": unsupported,
    }
    toolclaw_diagnostics = {
        "benchmark": "bfcl",
        "track": manifest.get("track"),
        "namespace": "toolclaw_diagnostics",
        "per_system": _aggregate(
            scored_rows,
            [
                "toolclaw_diagnostics_binder_selection_match",
                "toolclaw_diagnostics_tool_sequence_match",
                "toolclaw_diagnostics_parameter_fill_ratio",
                "toolclaw_diagnostics_policy_format_compliance",
                "toolclaw_diagnostics_repair_overhead",
            ],
        ),
    }
    claim_summary = _claim_summary(
        suite=_suite_name_for_track(str(manifest.get("track") or "")),
        track=str(manifest.get("track") or ""),
        official_scoreboard=official_scoreboard,
        toolclaw_diagnostics=toolclaw_diagnostics,
        scored_rows=scored_rows,
        unsupported=unsupported,
    )

    (outdir / "official_scoreboard.json").write_text(json.dumps(official_scoreboard, indent=2), encoding="utf-8")
    (outdir / "toolclaw_diagnostics.json").write_text(json.dumps(toolclaw_diagnostics, indent=2), encoding="utf-8")
    (outdir / "claim_summary.json").write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")

    manifest["comparison_scored_path"] = _display_path(comparison_scored_path)
    manifest["official_scoreboard_path"] = _display_path(outdir / "official_scoreboard.json")
    manifest["toolclaw_diagnostics_path"] = _display_path(outdir / "toolclaw_diagnostics.json")
    manifest["claim_summary_path"] = _display_path(outdir / "claim_summary.json")
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"official_scoreboard: {outdir / 'official_scoreboard.json'}")
    print(f"toolclaw_diagnostics: {outdir / 'toolclaw_diagnostics.json'}")
    print(f"claim_summary: {outdir / 'claim_summary.json'}")


if __name__ == "__main__":
    main()
