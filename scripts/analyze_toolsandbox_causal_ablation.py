#!/usr/bin/env python3
"""Analyze ToolSandbox interaction causality and HTGP structural ablations."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List


SYSTEMS = (
    "a1_recovery",
    "a2_planner",
    "a3_full_interaction",
    "a3_no_query",
    "a3_noisy_user",
)


def _float(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    text = str(value or "").strip().lower()
    if text in {"true", "yes"}:
        return 1.0
    if text in {"false", "no", ""}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _mean(rows: Iterable[Dict[str, Any]], key: str) -> float:
    values = [_float(row.get(key, 0.0)) for row in rows]
    return float(mean(values)) if values else 0.0


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _system_rows(rows: List[Dict[str, str]], system: str) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("system") == system]


def _system_summary(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for system in sorted({row.get("system", "unknown") for row in rows}):
        system_rows = _system_rows(rows, system)
        summary[system] = {
            "rows": float(len(system_rows)),
            "strict_scored_success": _mean(system_rows, "strict_scored_success_rate"),
            "execution_verified_success": _mean(system_rows, "execution_verified_success_rate"),
            "raw_execution_success": _mean(system_rows, "raw_execution_success_rate"),
            "repair_scored_success": _mean(system_rows, "repair_scored_success_rate"),
            "interaction_contract_satisfied": _mean(system_rows, "interaction_contract_satisfied"),
            "mean_user_queries": _mean(system_rows, "mean_user_queries"),
            "repair_user_queries": _mean(system_rows, "repair_user_queries"),
            "probe_user_queries": _mean(system_rows, "probe_user_queries"),
            "milestone_similarity": _mean(system_rows, "milestone_similarity"),
            "state_dependency_score": _mean(system_rows, "state_dependency_score"),
        }
    return summary


def _failtax_summary(scoreboard: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, float]]]:
    result: Dict[str, Dict[str, Dict[str, float]]] = {}
    per_system = scoreboard.get("per_system_summary", {})
    if not isinstance(per_system, dict):
        return result
    for system, stats in per_system.items():
        if not isinstance(stats, dict):
            continue
        failtax_map = stats.get("per_failtax", {})
        if not isinstance(failtax_map, dict):
            continue
        result[str(system)] = {
            str(bucket): {
                "success_rate": _float(bucket_stats.get("success_rate", 0.0)),
                "error_rate": 1.0 - _float(bucket_stats.get("success_rate", 0.0)),
                "num_rows": _float(bucket_stats.get("num_rows", 0.0)),
            }
            for bucket, bucket_stats in failtax_map.items()
            if isinstance(bucket_stats, dict)
        }
    return result


def _metric(summary: Dict[str, Dict[str, float]], system: str, key: str) -> float:
    return float(summary.get(system, {}).get(key, 0.0))


def _failtax_metric(failtax: Dict[str, Dict[str, Dict[str, float]]], system: str, bucket: str, key: str) -> float:
    return float(failtax.get(system, {}).get(bucket, {}).get(key, 0.0))


def analyze(rows: List[Dict[str, str]], scoreboard: Dict[str, Any]) -> Dict[str, Any]:
    system_summary = _system_summary(rows)
    failtax = _failtax_summary(scoreboard)

    full_strict = _metric(system_summary, "a3_full_interaction", "strict_scored_success")
    no_query_strict = _metric(system_summary, "a3_no_query", "strict_scored_success")
    no_query_exec = _metric(system_summary, "a3_no_query", "execution_verified_success")
    planner_exec = _metric(system_summary, "a2_planner", "execution_verified_success")
    noisy_strict = _metric(system_summary, "a3_noisy_user", "strict_scored_success")
    planner_strict = _metric(system_summary, "a2_planner", "strict_scored_success")

    ordering_a1 = _failtax_metric(failtax, "a1_recovery", "ordering", "success_rate")
    ordering_a2 = _failtax_metric(failtax, "a2_planner", "ordering", "success_rate")
    state_a1 = _failtax_metric(failtax, "a1_recovery", "state", "success_rate")
    state_a2 = _failtax_metric(failtax, "a2_planner", "state", "success_rate")

    verdicts = {
        "interaction_query_contribution_supported": full_strict > no_query_strict,
        "no_query_repair_mechanism_supported": no_query_exec > planner_exec,
        "interaction_not_cheating_supported": full_strict > noisy_strict and noisy_strict <= planner_strict + 0.05,
        "htgp_structural_reduction_supported": (
            ordering_a2 >= ordering_a1
            and state_a2 >= state_a1
            and (ordering_a2 > ordering_a1 or state_a2 > state_a1)
        ),
    }

    risk_flags: List[str] = []
    if full_strict <= no_query_strict:
        risk_flags.append("query_ablation_no_drop")
    if noisy_strict > planner_strict + 0.05:
        risk_flags.append("noisy_user_above_planner")
    if not verdicts["htgp_structural_reduction_supported"]:
        risk_flags.append("htgp_structural_claim_not_supported")

    return {
        "systems_expected": list(SYSTEMS),
        "systems_observed": sorted(system_summary),
        "system_summary": system_summary,
        "failtax_summary": failtax,
        "verdicts": verdicts,
        "risk_flags": risk_flags,
        "comparisons": {
            "exp1_full_vs_no_query": {
                "a3_full_interaction_strict": full_strict,
                "a3_no_query_strict": no_query_strict,
                "a3_no_query_execution_verified": no_query_exec,
                "a2_planner_execution_verified": planner_exec,
            },
            "exp2_full_vs_noisy": {
                "a3_full_interaction_strict": full_strict,
                "a3_noisy_user_strict": noisy_strict,
                "a2_planner_strict": planner_strict,
            },
            "exp3_htgp_structural": {
                "a1_recovery_ordering_success": ordering_a1,
                "a2_planner_ordering_success": ordering_a2,
                "a1_recovery_state_success": state_a1,
                "a2_planner_state_success": state_a2,
                "a1_recovery_milestone_similarity": _metric(system_summary, "a1_recovery", "milestone_similarity"),
                "a2_planner_milestone_similarity": _metric(system_summary, "a2_planner", "milestone_similarity"),
                "a1_recovery_state_dependency_score": _metric(system_summary, "a1_recovery", "state_dependency_score"),
                "a2_planner_state_dependency_score": _metric(system_summary, "a2_planner", "state_dependency_score"),
            },
        },
    }


def _write_report(summary: Dict[str, Any], out_path: Path) -> None:
    lines = [
        "# ToolSandbox Causal Ablation Report",
        "",
        "## Verdicts",
        "",
        "| verdict | value |",
        "|---|---:|",
    ]
    for key, value in sorted(summary.get("verdicts", {}).items()):
        lines.append(f"| {key} | {str(bool(value)).lower()} |")
    lines.extend(["", "## System Summary", ""])
    lines.append(
        "| system | strict_scored_success | execution_verified_success | raw_execution_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for system, stats in sorted(summary.get("system_summary", {}).items()):
        lines.append(
            f"| {system} | {stats.get('strict_scored_success', 0.0):.3f} | {stats.get('execution_verified_success', 0.0):.3f} | {stats.get('raw_execution_success', 0.0):.3f} | {stats.get('repair_scored_success', 0.0):.3f} | {stats.get('interaction_contract_satisfied', 0.0):.3f} | {stats.get('mean_user_queries', 0.0):.3f} |"
        )
    lines.extend(["", "## Risk Flags", ""])
    risk_flags = list(summary.get("risk_flags", []))
    if risk_flags:
        lines.extend(f"- `{flag}`" for flag in risk_flags)
    else:
        lines.append("- none")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze ToolSandbox interaction causality ablations")
    parser.add_argument("--comparison", required=True, help="Path to comparison.scored.csv")
    parser.add_argument("--scoreboard", required=True, help="Path to scoreboard.json")
    parser.add_argument("--outdir", required=True, help="Directory for causal_claim_summary.json and causal_claim_report.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison_path = Path(args.comparison)
    scoreboard_path = Path(args.scoreboard)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summary = analyze(
        rows=_read_csv(comparison_path),
        scoreboard=json.loads(scoreboard_path.read_text(encoding="utf-8")),
    )
    (outdir / "causal_claim_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(summary, outdir / "causal_claim_report.md")


if __name__ == "__main__":
    main()
