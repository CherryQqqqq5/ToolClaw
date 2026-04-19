"""Stratified analysis for exact-vs-transfer reuse on ToolClaw benchmark outputs."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple


REUSE_TIERS: Tuple[str, ...] = (
    "exact_match_reuse",
    "same_family_transfer_reuse",
    "cross_family_transfer_reuse",
    "unresolved_transfer_reuse",
)
HIGHER_IS_BETTER = {
    "success",
    "execution_verified_success",
    "interaction_efficiency",
    "tool_efficiency",
    "turn_efficiency",
    "state_dependency_score",
}
LOWER_IS_BETTER = {"tool_calls", "repair_actions", "user_turns"}


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze_outdir(
    outdir: Path,
    *,
    left_system: str = "a3_interaction",
    right_system: str = "a4_reuse",
    taskset_path: Optional[Path] = None,
) -> Dict[str, Any]:
    comparison_path = _discover_comparison_path(outdir)
    resolved_taskset = taskset_path or _discover_taskset_path(outdir)
    task_lookup = _load_task_lookup(resolved_taskset) if resolved_taskset else {}
    rows = [_enrich_row(row, outdir=outdir, task_lookup=task_lookup) for row in load_csv_rows(comparison_path)]
    paired = _paired_rows(rows, left_system=left_system, right_system=right_system)

    tier_summary: Dict[str, Dict[str, Any]] = {}
    nonreuse_cases = 0
    for left_row, right_row in paired:
        if not right_row["_reused_artifact_bool"]:
            nonreuse_cases += 1
            continue
        tier = str(right_row["_reuse_tier"] or "unresolved_transfer_reuse")
        stats = tier_summary.setdefault(
            tier,
            {
                "tier": tier,
                "paired_cases": 0,
                "unique_tasks": set(),
                "a3_success": [],
                "a4_success": [],
                "delta_success": [],
                "delta_tool_calls": [],
                "delta_repair_actions": [],
                "delta_user_turns": [],
                "delta_interaction_efficiency": [],
                "delta_tool_efficiency": [],
                "delta_turn_efficiency": [],
                "delta_execution_verified_success": [],
                "delta_state_dependency_score": [],
            },
        )
        stats["paired_cases"] += 1
        stats["unique_tasks"].add(right_row["task_id"])
        _append_delta(stats["a3_success"], _metric_value(left_row, "success"))
        _append_delta(stats["a4_success"], _metric_value(right_row, "success"))
        _append_pair_delta(stats["delta_success"], left_row, right_row, "success")
        _append_pair_delta(stats["delta_tool_calls"], left_row, right_row, "tool_calls")
        _append_pair_delta(stats["delta_repair_actions"], left_row, right_row, "repair_actions")
        _append_pair_delta(stats["delta_user_turns"], left_row, right_row, "user_turns")
        _append_pair_delta(stats["delta_interaction_efficiency"], left_row, right_row, "interaction_efficiency")
        _append_pair_delta(stats["delta_tool_efficiency"], left_row, right_row, "tool_efficiency")
        _append_pair_delta(stats["delta_turn_efficiency"], left_row, right_row, "turn_efficiency")
        _append_pair_delta(stats["delta_execution_verified_success"], left_row, right_row, "execution_verified_success")
        _append_pair_delta(stats["delta_state_dependency_score"], left_row, right_row, "state_dependency_score")

    summarized_tiers = [_finalize_tier_stats(stats) for _, stats in sorted(tier_summary.items(), key=lambda item: REUSE_TIERS.index(item[0]) if item[0] in REUSE_TIERS else 99)]
    recommendation = _recommendation(summarized_tiers)
    return {
        "outdir": str(outdir),
        "comparison_path": str(comparison_path),
        "taskset_path": str(resolved_taskset) if resolved_taskset else "",
        "left_system": left_system,
        "right_system": right_system,
        "nonreuse_case_count": nonreuse_cases,
        "tier_summary": summarized_tiers,
        "recommendation": recommendation,
    }


def render_markdown(analysis: Dict[str, Any]) -> str:
    lines = [
        "# Reuse Strata Analysis",
        "",
        f"- outdir: `{analysis['outdir']}`",
        f"- comparison: `{analysis['comparison_path']}`",
    ]
    if analysis.get("taskset_path"):
        lines.append(f"- taskset: `{analysis['taskset_path']}`")
    lines.extend(
        [
            f"- left_system: `{analysis['left_system']}`",
            f"- right_system: `{analysis['right_system']}`",
            f"- nonreuse paired cases: `{analysis['nonreuse_case_count']}`",
            "",
            "## Tier Summary",
            "",
            "| tier | paired_cases | unique_tasks | a3_success | a4_success | delta_success | delta_tool_calls | delta_repair_actions | delta_user_turns | delta_interaction_efficiency |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for stats in analysis.get("tier_summary", []):
        lines.append(
            f"| {stats['tier']} | {stats['paired_cases']} | {stats['unique_tasks']} | {stats['a3_success']:.3f} | {stats['a4_success']:.3f} | {stats['delta_success']:+.3f} | {stats['delta_tool_calls']:+.3f} | {stats['delta_repair_actions']:+.3f} | {stats['delta_user_turns']:+.3f} | {stats['delta_interaction_efficiency']:+.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- headline: **{analysis['recommendation']['headline']}**",
            f"- framing: {analysis['recommendation']['paper_framing']}",
            f"- evidence: {analysis['recommendation']['rationale']}",
        ]
    )
    return "\n".join(lines)


def _discover_comparison_path(outdir: Path) -> Path:
    for candidate in ("comparison.scored.csv", "comparison.raw.csv", "comparison.csv"):
        path = outdir / candidate
        if path.exists():
            return path
    raise FileNotFoundError(f"no comparison csv found under {outdir}")


def _discover_taskset_path(outdir: Path) -> Optional[Path]:
    manifest_path = outdir / "experiment_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("normalized_taskset", "taskset", "comparison_taskset"):
            candidate = payload.get(key)
            if candidate and Path(candidate).exists():
                return Path(candidate)
    for parent in (outdir, outdir.parent):
        prepared_dir = parent / "prepared"
        if prepared_dir.exists():
            for candidate in sorted(prepared_dir.glob("*.json")):
                return candidate
    return None


def _load_task_lookup(taskset_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if taskset_path is None or not taskset_path.exists():
        return {}
    payload = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return {}
    lookup: Dict[str, Dict[str, Any]] = {}
    for task in payload:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if task_id:
            lookup[task_id] = task
    return lookup


def _resolve_trace_path(outdir: Path, raw_path: str) -> Path:
    path = Path(str(raw_path or "").strip())
    if path.is_absolute():
        return path
    return outdir / path


def _load_trace_reuse_provenance(outdir: Path, raw_path: str) -> Dict[str, Any]:
    if not str(raw_path or "").strip():
        return {}
    path = _resolve_trace_path(outdir, raw_path)
    if not path.exists() or path.is_dir():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    provenance = metadata.get("reuse_provenance", {})
    return provenance if isinstance(provenance, dict) else {}


def _task_reuse_family(task_id: str, task: Dict[str, Any]) -> str:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_family_id"):
        return str(metadata["reuse_family_id"]).strip()
    if task.get("reuse_family_id"):
        return str(task["reuse_family_id"]).strip()
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return ""


def _semantic_family(family: str) -> str:
    value = str(family or "").strip()
    if not value:
        return ""
    value = re.sub(r"__pair\d+$", "", value)
    value = re.sub(r"_\d+$", "", value)
    return value


def _classify_tier(
    *,
    reused_artifact: bool,
    reuse_mode: str,
    target_family: str,
    source_family: str,
    target_semantic_family: str,
    source_semantic_family: str,
) -> str:
    if not reused_artifact:
        return "none"
    if source_family and target_family:
        if source_family == target_family:
            return "exact_match_reuse"
        if source_semantic_family and target_semantic_family and source_semantic_family == target_semantic_family:
            return "same_family_transfer_reuse"
        return "cross_family_transfer_reuse"
    if reuse_mode == "exact_reuse":
        return "exact_match_reuse"
    return "unresolved_transfer_reuse"


def _enrich_row(
    row: Dict[str, str],
    *,
    outdir: Path,
    task_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    enriched: Dict[str, Any] = dict(row)
    task_id = str(row.get("task_id") or "").strip()
    task = task_lookup.get(task_id, {})
    trace_provenance = _load_trace_reuse_provenance(outdir, row.get("trace_path", ""))
    reused_artifact = _bool_value(row.get("reused_artifact"))
    target_family = str(row.get("reuse_target_family") or trace_provenance.get("reuse_target_family") or _task_reuse_family(task_id, task))
    target_semantic_family = str(
        row.get("reuse_target_semantic_family")
        or trace_provenance.get("reuse_target_semantic_family")
        or _semantic_family(target_family)
    )
    source_family = str(row.get("reuse_source_family") or trace_provenance.get("reuse_source_family") or "")
    source_semantic_family = str(
        row.get("reuse_source_semantic_family")
        or trace_provenance.get("reuse_source_semantic_family")
        or _semantic_family(source_family)
    )
    reuse_mode = str(row.get("reuse_mode") or trace_provenance.get("reuse_mode") or ("unknown_reuse" if reused_artifact else "none"))
    reuse_tier = str(
        row.get("reuse_tier")
        or trace_provenance.get("reuse_tier")
        or _classify_tier(
            reused_artifact=reused_artifact,
            reuse_mode=reuse_mode,
            target_family=target_family,
            source_family=source_family,
            target_semantic_family=target_semantic_family,
            source_semantic_family=source_semantic_family,
        )
    )
    enriched["_run_index"] = int(row.get("run_index", 1) or 1)
    enriched["_reused_artifact_bool"] = reused_artifact
    enriched["_reuse_mode"] = reuse_mode
    enriched["_reuse_tier"] = reuse_tier
    enriched["_reuse_target_family"] = target_family
    enriched["_reuse_source_family"] = source_family
    enriched["_reuse_target_semantic_family"] = target_semantic_family
    enriched["_reuse_source_semantic_family"] = source_semantic_family
    return enriched


def _paired_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    left_system: str,
    right_system: str,
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    grouped: Dict[Tuple[int, str], Dict[str, Dict[str, Any]]] = {}
    for row in rows:
        key = (int(row.get("_run_index", 1) or 1), str(row.get("task_id") or ""))
        grouped.setdefault(key, {})[str(row.get("system") or "")] = row
    paired: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for key in sorted(grouped):
        row_map = grouped[key]
        if left_system in row_map and right_system in row_map:
            paired.append((row_map[left_system], row_map[right_system]))
    return paired


def _metric_value(row: Dict[str, Any], metric: str) -> Optional[float]:
    if metric not in row:
        return None
    raw = row.get(metric)
    if metric == "success":
        return 1.0 if _bool_value(raw) else 0.0
    return _float_value(raw)


def _append_delta(values: List[float], value: Optional[float]) -> None:
    if value is not None:
        values.append(value)


def _append_pair_delta(values: List[float], left_row: Dict[str, Any], right_row: Dict[str, Any], metric: str) -> None:
    left_value = _metric_value(left_row, metric)
    right_value = _metric_value(right_row, metric)
    if left_value is None or right_value is None:
        return
    values.append(right_value - left_value)


def _mean_or_zero(values: List[float]) -> float:
    return mean(values) if values else 0.0


def _finalize_tier_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tier": stats["tier"],
        "paired_cases": int(stats["paired_cases"]),
        "unique_tasks": len(stats["unique_tasks"]),
        "a3_success": _mean_or_zero(stats["a3_success"]),
        "a4_success": _mean_or_zero(stats["a4_success"]),
        "delta_success": _mean_or_zero(stats["delta_success"]),
        "delta_tool_calls": _mean_or_zero(stats["delta_tool_calls"]),
        "delta_repair_actions": _mean_or_zero(stats["delta_repair_actions"]),
        "delta_user_turns": _mean_or_zero(stats["delta_user_turns"]),
        "delta_interaction_efficiency": _mean_or_zero(stats["delta_interaction_efficiency"]),
        "delta_tool_efficiency": _mean_or_zero(stats["delta_tool_efficiency"]),
        "delta_turn_efficiency": _mean_or_zero(stats["delta_turn_efficiency"]),
        "delta_execution_verified_success": _mean_or_zero(stats["delta_execution_verified_success"]),
        "delta_state_dependency_score": _mean_or_zero(stats["delta_state_dependency_score"]),
    }


def _tier_beneficial(stats: Dict[str, Any]) -> bool:
    if stats["delta_success"] > 1e-9:
        return True
    if stats["delta_success"] < -1e-9:
        return False
    for metric in ("delta_tool_calls", "delta_repair_actions", "delta_user_turns"):
        if stats.get(metric, 0.0) < -1e-9:
            return True
        if stats.get(metric, 0.0) > 1e-9:
            return False
    for metric in ("delta_interaction_efficiency", "delta_tool_efficiency", "delta_turn_efficiency", "delta_execution_verified_success", "delta_state_dependency_score"):
        if stats.get(metric, 0.0) > 1e-9:
            return True
        if stats.get(metric, 0.0) < -1e-9:
            return False
    return False


def _recommendation(tier_summary: List[Dict[str, Any]]) -> Dict[str, str]:
    by_tier = {entry["tier"]: entry for entry in tier_summary}
    exact_good = _tier_beneficial(by_tier["exact_match_reuse"]) if "exact_match_reuse" in by_tier else False
    same_good = _tier_beneficial(by_tier["same_family_transfer_reuse"]) if "same_family_transfer_reuse" in by_tier else False
    cross_good = _tier_beneficial(by_tier["cross_family_transfer_reuse"]) if "cross_family_transfer_reuse" in by_tier else False
    unresolved = by_tier.get("unresolved_transfer_reuse")

    if exact_good and not same_good and not cross_good:
        return {
            "headline": "exact-match benefit only",
            "paper_framing": "Write reuse as a safe reusable execution prior under matched task signatures, not as broad transfer.",
            "rationale": "Exact-match reuse shows positive paired deltas, while transfer tiers do not show stable gains.",
        }
    if (exact_good or same_good) and not cross_good:
        return {
            "headline": "matched-or-near-matched reuse only",
            "paper_framing": "Frame reuse as a safe reusable execution prior under matched or near-matched task signatures.",
            "rationale": "Benefit is confined to exact and/or same-family transfer; cross-family transfer is not yet supported by stable gains.",
        }
    if cross_good:
        return {
            "headline": "cross-family transfer evidence present",
            "paper_framing": "Broader transfer claims are supportable, but should still be qualified by the observed tier-specific deltas.",
            "rationale": "Cross-family transfer shows positive paired deltas instead of merely triggering reuse.",
        }
    if unresolved and unresolved["paired_cases"] > 0:
        return {
            "headline": "transfer provenance still under-resolved",
            "paper_framing": "Avoid broad reuse claims until source-family provenance is fully surfaced in the benchmark outputs.",
            "rationale": "Some reused cases cannot yet be placed into same-family vs cross-family transfer from the available trace metadata.",
        }
    return {
        "headline": "no stable reuse gain",
        "paper_framing": "Do not pitch reuse as a general capability gain yet; use the tier breakdown to target admission-control fixes first.",
        "rationale": "None of the reuse tiers show a stable positive paired delta against A3.",
    }


def _bool_value(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _float_value(value: Any) -> Optional[float]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.lower() in {"true", "false"}:
        return 1.0 if text.lower() == "true" else 0.0
    try:
        return float(text)
    except ValueError:
        return None
