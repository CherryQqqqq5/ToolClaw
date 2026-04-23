#!/usr/bin/env python3
"""Score ToolSandbox persistent reuse as a paired second-run benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Tuple


PRIMARY_REDUCTION_METRICS = ("repair_reduction", "turn_reduction", "tool_call_reduction", "wall_clock_reduction")


def _float(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(str(value or "0").strip())
    except ValueError:
        return 0.0


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return float(mean(values)) if values else 0.0


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _success(row: Dict[str, str]) -> float:
    return 1.0 if _bool(row.get("success")) else 0.0


def _family(row: Dict[str, str]) -> str:
    return str(row.get("reuse_target_family") or row.get("family_id") or row.get("task_id", "").split("__pass", 1)[0])


def _aggregate(rows: List[Dict[str, str]]) -> Dict[str, float]:
    if not rows:
        return {
            "rows": 0.0,
            "success_rate": 0.0,
            "avg_tool_calls": 0.0,
            "avg_user_turns": 0.0,
            "avg_repair_actions": 0.0,
            "avg_wall_clock_ms": 0.0,
            "reuse_hit_rate": 0.0,
            "correct_source_match_rate": 0.0,
            "success_per_user_turn": 0.0,
            "success_per_repair_attempt": 0.0,
        }
    reuse_rows = [row for row in rows if _bool(row.get("reused_artifact"))]
    exact_reuse_rows = [
        row
        for row in reuse_rows
        if str(row.get("reuse_tier") or "").strip() == "exact_match_reuse"
    ]
    transfer_reuse_rows = [
        row
        for row in reuse_rows
        if str(row.get("reuse_tier") or "").strip() == "cross_family_transfer_reuse"
    ]
    correct_reuse_rows = [
        row
        for row in reuse_rows
        if str(row.get("reuse_source_family") or "") and str(row.get("reuse_source_family") or "") == str(row.get("reuse_target_family") or "")
    ]
    successes = sum(_success(row) for row in rows)
    user_turns = sum(_float(row.get("user_turns")) for row in rows)
    repairs = sum(_float(row.get("repair_actions")) for row in rows)
    return {
        "rows": float(len(rows)),
        "success_rate": _mean(_success(row) for row in rows),
        "avg_tool_calls": _mean(_float(row.get("tool_calls")) for row in rows),
        "avg_user_turns": _mean(_float(row.get("user_turns")) for row in rows),
        "avg_repair_actions": _mean(_float(row.get("repair_actions")) for row in rows),
        "avg_wall_clock_ms": _mean(_float(row.get("wall_clock_ms")) for row in rows),
        "reuse_hit_rate": _mean(1.0 if _bool(row.get("reused_artifact")) else 0.0 for row in rows),
        "exact_reuse_hit_rate": float(len(exact_reuse_rows) / len(rows)),
        "transfer_reuse_hit_rate": float(len(transfer_reuse_rows) / len(rows)),
        "correct_source_match_rate": float(len(correct_reuse_rows) / len(reuse_rows)) if reuse_rows else 0.0,
        "success_per_user_turn": float(successes / user_turns) if user_turns else float(successes),
        "success_per_repair_attempt": float(successes / repairs) if repairs else float(successes),
    }


def _pair_effects(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in rows:
        if str(row.get("stage")) != "pass2_eval":
            continue
        grouped[(str(row.get("run_index") or "1"), _family(row))][str(row.get("system"))] = row

    effects: List[Dict[str, Any]] = []
    for (run_index, family), arm_rows in sorted(grouped.items()):
        warm = arm_rows.get("a4_reuse_warm")
        cold = arm_rows.get("a4_reuse_cold")
        a3 = arm_rows.get("a3_interaction")
        sham = arm_rows.get("a4_reuse_sham")
        if not warm or not cold:
            continue
        item = {
            "run_index": run_index,
            "family_id": family,
            "warm_success": _success(warm),
            "cold_success": _success(cold),
            "a3_success": _success(a3) if a3 else 0.0,
            "sham_success": _success(sham) if sham else 0.0,
            "warm_reused_artifact": 1.0 if _bool(warm.get("reused_artifact")) else 0.0,
            "sham_reused_artifact": 1.0 if sham and _bool(sham.get("reused_artifact")) else 0.0,
            "warm_correct_source_match": 1.0
            if _bool(warm.get("reused_artifact"))
            and str(warm.get("reuse_source_family") or "") == str(warm.get("reuse_target_family") or "")
            else 0.0,
            "second_run_success_delta": _success(warm) - _success(cold),
            "repair_reduction": _float(cold.get("repair_actions")) - _float(warm.get("repair_actions")),
            "turn_reduction": _float(cold.get("user_turns")) - _float(warm.get("user_turns")),
            "tool_call_reduction": _float(cold.get("tool_calls")) - _float(warm.get("tool_calls")),
            "wall_clock_reduction": _float(cold.get("wall_clock_ms")) - _float(warm.get("wall_clock_ms")),
        }
        if a3:
            item.update(
                {
                    "warm_vs_a3_success_delta": _success(warm) - _success(a3),
                    "warm_vs_a3_repair_reduction": _float(a3.get("repair_actions")) - _float(warm.get("repair_actions")),
                    "warm_vs_a3_turn_reduction": _float(a3.get("user_turns")) - _float(warm.get("user_turns")),
                    "warm_vs_a3_tool_call_reduction": _float(a3.get("tool_calls")) - _float(warm.get("tool_calls")),
                }
            )
        if sham:
            item.update(
                {
                    "warm_vs_sham_success_delta": _success(warm) - _success(sham),
                    "warm_vs_sham_repair_reduction": _float(sham.get("repair_actions")) - _float(warm.get("repair_actions")),
                    "warm_vs_sham_turn_reduction": _float(sham.get("user_turns")) - _float(warm.get("user_turns")),
                    "warm_vs_sham_tool_call_reduction": _float(sham.get("tool_calls")) - _float(warm.get("tool_calls")),
                }
            )
        effects.append(item)
    return effects


def _bootstrap_ci(values: List[float], *, seed: int = 13, iterations: int = 2000) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
        means.append(mean(sample))
    means.sort()
    low_idx = int(0.025 * (len(means) - 1))
    high_idx = int(0.975 * (len(means) - 1))
    return {
        "mean": float(mean(values)),
        "median": float(median(values)),
        "ci_low": float(means[low_idx]),
        "ci_high": float(means[high_idx]),
    }


def _sign_test(values: List[float]) -> Dict[str, float]:
    positives = sum(1 for value in values if value > 0)
    negatives = sum(1 for value in values if value < 0)
    n = positives + negatives
    if n == 0:
        return {"n": 0.0, "positive": float(positives), "negative": float(negatives), "p_value_two_sided": 1.0}
    k = min(positives, negatives)
    prob = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return {"n": float(n), "positive": float(positives), "negative": float(negatives), "p_value_two_sided": min(1.0, 2.0 * prob)}


def _stat_tests(effects: List[Dict[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for metric in ("second_run_success_delta", *PRIMARY_REDUCTION_METRICS):
        values = [float(item.get(metric, 0.0) or 0.0) for item in effects]
        result[metric] = {
            **_bootstrap_ci(values),
            "sign_test": _sign_test(values),
        }
    return result


def _claim_summary(
    *,
    rows: List[Dict[str, str]],
    effects: List[Dict[str, Any]],
    stats: Dict[str, Any],
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    pass2_rows = [row for row in rows if str(row.get("stage")) == "pass2_eval"]
    by_system = {system: _aggregate([row for row in pass2_rows if row.get("system") == system]) for system in sorted({row.get("system", "") for row in pass2_rows})}
    warm = by_system.get("a4_reuse_warm", {})
    cold = by_system.get("a4_reuse_cold", {})
    sham = by_system.get("a4_reuse_sham", {})
    reductions = {metric: float(stats.get(metric, {}).get("mean", 0.0) or 0.0) for metric in PRIMARY_REDUCTION_METRICS}
    ci_ok = any(float(stats.get(metric, {}).get("ci_low", 0.0) or 0.0) >= -0.05 for metric in PRIMARY_REDUCTION_METRICS)
    any_reduction = any(value > 0.0 for value in reductions.values())
    success_guard = float(warm.get("success_rate", 0.0) or 0.0) >= float(cold.get("success_rate", 0.0) or 0.0) - 0.02
    gate_failures: List[str] = []
    if not bool(manifest.get("registry_preflight_passed", False)):
        gate_failures.append("registry_preflight_failed")
    if float(warm.get("reuse_hit_rate", 0.0) or 0.0) < 0.50:
        gate_failures.append("warm_reuse_hit_rate_below_0.50")
    if float(warm.get("correct_source_match_rate", 0.0) or 0.0) < 0.90:
        gate_failures.append("warm_correct_source_match_rate_below_0.90")
    if float(sham.get("reuse_hit_rate", 0.0) or 0.0) > 0.05:
        gate_failures.append("sham_false_positive_rate_above_0.05")
    if not any_reduction:
        gate_failures.append("no_positive_primary_cost_reduction")
    if not ci_ok:
        gate_failures.append("primary_reduction_ci_lower_bound_negative")
    if not success_guard:
        gate_failures.append("warm_success_below_cold_guard")
    paper_safe = (
        bool(manifest.get("registry_preflight_passed", False))
        and float(warm.get("reuse_hit_rate", 0.0) or 0.0) >= 0.50
        and float(warm.get("correct_source_match_rate", 0.0) or 0.0) >= 0.90
        and float(sham.get("reuse_hit_rate", 0.0) or 0.0) <= 0.05
        and any_reduction
        and ci_ok
        and success_guard
    )
    return {
        "paper_safe_reuse_evidence": paper_safe,
        "strong_second_run_claim_supported": paper_safe and bool(manifest.get("statistical_claim_allowed", False)),
        "mechanism_evidence_only": not paper_safe or not bool(manifest.get("statistical_claim_allowed", False)),
        "registry_preflight_passed": bool(manifest.get("registry_preflight_passed", False)),
        "family_count": int(manifest.get("family_count", 0) or 0),
        "statistical_claim_allowed": bool(manifest.get("statistical_claim_allowed", False)),
        "warm_reuse_hit_rate": float(warm.get("reuse_hit_rate", 0.0) or 0.0),
        "warm_correct_source_match_rate": float(warm.get("correct_source_match_rate", 0.0) or 0.0),
        "sham_false_positive_rate": float(sham.get("reuse_hit_rate", 0.0) or 0.0),
        "reuse_false_positive_rate": float(sham.get("reuse_hit_rate", 0.0) or 0.0),
        "warm_exact_reuse_hit_rate": float(warm.get("exact_reuse_hit_rate", 0.0) or 0.0),
        "warm_transfer_reuse_hit_rate": float(warm.get("transfer_reuse_hit_rate", 0.0) or 0.0),
        "sham_exact_reuse_hit_rate": float(sham.get("exact_reuse_hit_rate", 0.0) or 0.0),
        "sham_transfer_reuse_hit_rate": float(sham.get("transfer_reuse_hit_rate", 0.0) or 0.0),
        "gate_failures": gate_failures,
        "a4_reuse_warm": warm,
        "a4_reuse_cold": cold,
        "a4_reuse_sham": sham,
        "reductions_mean": reductions,
        "success_guard_passed": success_guard,
        "primary_reduction_present": any_reduction,
        "paired_effect_count": len(effects),
    }


def _write_report(path: Path, summary: Dict[str, Any], effects_summary: Dict[str, Any], stats: Dict[str, Any]) -> None:
    lines = [
        "# ToolSandbox Reuse Persistent V1 Report",
        "",
        "## Claim Summary",
        "",
        "| verdict | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        if isinstance(value, bool):
            lines.append(f"| {key} | {str(value).lower()} |")
    if summary.get("gate_failures"):
        lines.extend(["", "Gate failures:", ""])
        for reason in summary.get("gate_failures", []):
            lines.append(f"- `{reason}`")
    lines.extend(["", "## Pass2 Systems", ""])
    lines.append("| system | success | tool_calls | user_turns | repair_actions | reuse_hit | exact_hit | transfer_hit | correct_source_match |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for system, stats_row in sorted(effects_summary.get("pass2_by_system", {}).items()):
        lines.append(
            f"| {system} | {stats_row.get('success_rate', 0.0):.3f} | {stats_row.get('avg_tool_calls', 0.0):.2f} | {stats_row.get('avg_user_turns', 0.0):.2f} | {stats_row.get('avg_repair_actions', 0.0):.2f} | {stats_row.get('reuse_hit_rate', 0.0):.3f} | {stats_row.get('exact_reuse_hit_rate', 0.0):.3f} | {stats_row.get('transfer_reuse_hit_rate', 0.0):.3f} | {stats_row.get('correct_source_match_rate', 0.0):.3f} |"
        )
    lines.extend(["", "## Paired Reductions", ""])
    lines.append("| metric | mean | median | ci_low | ci_high | sign_p |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for metric, metric_stats in stats.items():
        sign = metric_stats.get("sign_test", {})
        lines.append(
            f"| {metric} | {metric_stats.get('mean', 0.0):.3f} | {metric_stats.get('median', 0.0):.3f} | {metric_stats.get('ci_low', 0.0):.3f} | {metric_stats.get('ci_high', 0.0):.3f} | {sign.get('p_value_two_sided', 1.0):.4f} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score ToolSandbox persistent reuse outputs")
    parser.add_argument("--dataset", default="")
    parser.add_argument("--comparison", default="")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--official-eval", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--toolclaw-diagnostics", default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    manifest_path = outdir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    dataset_path = Path(args.dataset or manifest.get("source") or "")
    comparison_path = Path(args.comparison or outdir / "comparison.scored.csv")
    if not dataset_path.exists():
        raise FileNotFoundError(f"reuse persistent dataset not found: {dataset_path}")
    _read_jsonl(dataset_path)
    rows = _read_csv(comparison_path)
    effects = _pair_effects(rows)
    _write_jsonl(outdir / "reuse_pair_effects.jsonl", effects)
    pass2_rows = [row for row in rows if str(row.get("stage")) == "pass2_eval"]
    effect_summary = {
        "pass2_by_system": {
            system: _aggregate([row for row in pass2_rows if row.get("system") == system])
            for system in sorted({row.get("system", "") for row in pass2_rows})
        },
        "paired_effect_count": len(effects),
    }
    (outdir / "reuse_effect_summary.json").write_text(json.dumps(effect_summary, indent=2), encoding="utf-8")
    stats = _stat_tests(effects)
    (outdir / "reuse_stat_tests.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    summary = _claim_summary(rows=rows, effects=effects, stats=stats, manifest=manifest)
    (outdir / "claim_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(outdir / "report.md", summary, effect_summary, stats)


if __name__ == "__main__":
    main()
