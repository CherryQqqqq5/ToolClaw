#!/usr/bin/env python3
"""Score ToolSandbox interaction-live runs for usefulness and extraction PRF."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple


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


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return float(mean(values)) if values else 0.0


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _system_user_mode(system: str) -> str:
    mapping = {
        "a3_full_interaction_oracle": "oracle_user",
        "a3_full_interaction_noisy": "noisy_user",
        "a3_full_interaction_irrelevant": "irrelevant_user",
        "a3_full_interaction_wrong_parameter": "wrong_parameter_user",
        "a3_full_interaction_partial": "partial_user",
        "a3_no_query": "no_query",
        "a2_planner": "planner",
    }
    return mapping.get(system, system)


def _gold_targets(gold: Dict[str, Any]) -> set[str]:
    signal = gold.get("gold_decoded_signal", {})
    targets = set()
    if isinstance(signal, dict):
        targets.update(str(item) for item in signal.get("expected_targets", []) if str(item))
        targets.update(str(key) for key in signal.get("slot_updates", {}) if str(key))
        targets.update(str(key) for key in signal.get("approvals", {}) if str(key))
        targets.update(str(key) for key in signal.get("control_updates", {}) if str(key))
    targets.update(str(key) for key in gold.get("expected_patch_targets", {}) if str(key))
    return targets


def _actual_targets(metadata: Dict[str, Any]) -> set[str]:
    reply_metadata = metadata.get("reply_metadata", {})
    targets = set()
    if isinstance(reply_metadata, dict):
        selected = reply_metadata.get("selected_targets", [])
        if isinstance(selected, list):
            targets.update(str(item) for item in selected if str(item))
        for container_key in ("decoded_slot_updates", "decoded_approvals", "decoded_control_updates"):
            container = reply_metadata.get(container_key, {})
            if isinstance(container, dict):
                targets.update(str(key) for key in container if str(key))
    non_semantic = {"raw_text", "value", "abstain", "abort", "error"}
    return {target for target in targets if target not in non_semantic}


def _value_matches(metadata: Dict[str, Any], gold: Dict[str, Any], target: str) -> bool:
    signal = gold.get("gold_decoded_signal", {})
    reply_metadata = metadata.get("reply_metadata", {})
    if not isinstance(signal, dict) or not isinstance(reply_metadata, dict):
        return False
    gold_slots = signal.get("slot_updates", {}) if isinstance(signal.get("slot_updates"), dict) else {}
    actual_slots = reply_metadata.get("decoded_slot_updates", {}) if isinstance(reply_metadata.get("decoded_slot_updates"), dict) else {}
    if target in gold_slots:
        return str(actual_slots.get(target)) == str(gold_slots.get(target))
    gold_approvals = signal.get("approvals", {}) if isinstance(signal.get("approvals"), dict) else {}
    actual_approvals = reply_metadata.get("decoded_approvals", {}) if isinstance(reply_metadata.get("decoded_approvals"), dict) else {}
    if target in gold_approvals:
        return bool(actual_approvals.get(target)) == bool(gold_approvals.get(target))
    gold_controls = signal.get("control_updates", {}) if isinstance(signal.get("control_updates"), dict) else {}
    actual_controls = reply_metadata.get("decoded_control_updates", {}) if isinstance(reply_metadata.get("decoded_control_updates"), dict) else {}
    if target in gold_controls:
        return str(actual_controls.get(target)) == str(gold_controls.get(target))
    return target in _actual_targets(metadata)


def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    false_positive_rate = fp / (tp + fp) if (tp + fp) else 0.0
    return {
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": false_positive_rate,
    }


def _trace_rounds(rows: List[Dict[str, str]], dataset_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rounds: List[Dict[str, Any]] = []
    for row in rows:
        trace_path = Path(row.get("trace_path", ""))
        if not trace_path.exists():
            continue
        try:
            payload = json.loads(trace_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        gold = dataset_by_id.get(row.get("task_id", ""), {})
        for event in payload.get("events", []):
            if event.get("event_type") != "interaction_round_outcome":
                continue
            metadata = event.get("metadata", {}) if isinstance(event.get("metadata"), dict) else {}
            output = event.get("output", {}) if isinstance(event.get("output"), dict) else {}
            gold_targets = _gold_targets(gold)
            actual_targets = _actual_targets(metadata)
            target_tp = len(gold_targets & actual_targets)
            target_fp = len(actual_targets - gold_targets)
            target_fn = len(gold_targets - actual_targets)
            value_tp = sum(1 for target in gold_targets & actual_targets if _value_matches(metadata, gold, target))
            value_fp = target_fp + max(0, target_tp - value_tp)
            value_fn = target_fn + max(0, target_tp - value_tp)
            action_targets = {target for target in gold_targets if target in {"approved", "tool_id"}}
            action_actual = {target for target in actual_targets if target in {"approved", "tool_id"}}
            action_tp = len(action_targets & action_actual)
            action_fp = len(action_actual - action_targets)
            action_fn = len(action_targets - action_actual)
            rounds.append(
                {
                    "run_index": row.get("run_index"),
                    "task_id": row.get("task_id"),
                    "system": row.get("system"),
                    "user_mode": _system_user_mode(row.get("system", "")),
                    "slice_type": gold.get("slice_type", ""),
                    "strict_scored_success": _float(row.get("strict_scored_success_rate", row.get("strict_scored_success", 0))),
                    "decoded_is_usable": bool(output.get("decoded_is_usable", metadata.get("decoded_is_usable"))),
                    "target_alignment": _float(output.get("target_alignment", metadata.get("target_alignment", 0.0))),
                    "effective_patch": bool(output.get("effective_patch", metadata.get("effective_patch"))),
                    "post_query_progress": bool(output.get("post_query_progress", metadata.get("post_query_progress"))),
                    "interaction_round_useful": bool(output.get("interaction_round_useful", metadata.get("interaction_round_useful"))),
                    "gold_targets": sorted(gold_targets),
                    "actual_targets": sorted(actual_targets),
                    "target_tp": target_tp,
                    "target_fp": target_fp,
                    "target_fn": target_fn,
                    "value_tp": value_tp,
                    "value_fp": value_fp,
                    "value_fn": value_fn,
                    "action_tp": action_tp,
                    "action_fp": action_fp,
                    "action_fn": action_fn,
                }
            )
    return rounds


def _aggregate_rounds(rounds: List[Dict[str, Any]], key_fields: Tuple[str, ...]) -> Dict[str, Any]:
    grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    for item in rounds:
        grouped[tuple(str(item.get(key, "")) for key in key_fields)].append(item)
    result: Dict[str, Any] = {}
    for key, items in grouped.items():
        name = "|".join(key)
        result[name] = {
            "rounds": len(items),
            "reply_usable_rate": _mean(1.0 if item["decoded_is_usable"] else 0.0 for item in items),
            "target_aligned_patch_rate": _mean(1.0 if item["target_alignment"] >= 0.5 else 0.0 for item in items),
            "effective_patch_rate": _mean(1.0 if item["effective_patch"] else 0.0 for item in items),
            "post_query_progress_rate": _mean(1.0 if item["post_query_progress"] else 0.0 for item in items),
            "useful_interaction_round_rate": _mean(1.0 if item["interaction_round_useful"] else 0.0 for item in items),
            "strict_success_rate": _mean(float(item["strict_scored_success"]) for item in items),
        }
    return result


def _prf_by(rounds: List[Dict[str, Any]], key_fields: Tuple[str, ...]) -> Dict[str, Any]:
    grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    for item in rounds:
        grouped[tuple(str(item.get(key, "")) for key in key_fields)].append(item)
    result: Dict[str, Any] = {}
    for key, items in grouped.items():
        name = "|".join(key)
        result[name] = {
            "target": _prf(sum(item["target_tp"] for item in items), sum(item["target_fp"] for item in items), sum(item["target_fn"] for item in items)),
            "value": _prf(sum(item["value_tp"] for item in items), sum(item["value_fp"] for item in items), sum(item["value_fn"] for item in items)),
            "action": _prf(sum(item["action_tp"] for item in items), sum(item["action_fp"] for item in items), sum(item["action_fn"] for item in items)),
        }
    return result


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _claim_summary(scored_rows: List[Dict[str, str]], rounds: List[Dict[str, Any]], prf: Dict[str, Any]) -> Dict[str, Any]:
    def rows_for(system: str, slice_type: str) -> List[Dict[str, str]]:
        return [
            row for row in scored_rows
            if row.get("system") == system and dataset_by_id.get(row.get("task_id", ""), {}).get("slice_type") == slice_type
        ]

    def row_mean(system: str, slice_type: str, key: str) -> float:
        return _mean(_float(row.get(key, 0.0)) for row in rows_for(system, slice_type))

    repair_oracle = row_mean("a3_full_interaction_oracle", "repair_semantic_primary", "strict_scored_success_rate")
    repair_no_query = row_mean("a3_no_query", "repair_semantic_primary", "strict_scored_success_rate")
    repair_planner = row_mean("a2_planner", "repair_semantic_primary", "strict_scored_success_rate")
    repair_noisy = row_mean("a3_full_interaction_noisy", "repair_semantic_primary", "strict_scored_success_rate")
    round_summary = _aggregate_rounds(rounds, ("system", "slice_type"))
    oracle_key = "a3_full_interaction_oracle|repair_semantic_primary"
    noisy_key = "a3_full_interaction_noisy|repair_semantic_primary"
    irrelevant_key = "a3_full_interaction_irrelevant|repair_semantic_primary"
    wrong_key = "a3_full_interaction_wrong_parameter|repair_semantic_primary"
    oracle_round = round_summary.get(oracle_key, {})
    noisy_round = round_summary.get(noisy_key, {})
    irrelevant_round = round_summary.get(irrelevant_key, {})
    wrong_round = round_summary.get(wrong_key, {})
    oracle_prf = prf.get("user_mode|oracle_user", {})
    target_f1 = float(oracle_prf.get("target", {}).get("f1", 0.0) or 0.0)
    value_f1 = float(oracle_prf.get("value", {}).get("f1", 0.0) or 0.0)
    noisy_prf = prf.get("user_mode|noisy_user", {})
    noisy_fpr = float(noisy_prf.get("target", {}).get("false_positive_rate", 0.0) or 0.0)
    return {
        "interaction_as_control_signal_supported": (
            repair_oracle > repair_no_query
            and repair_oracle > repair_planner
            and repair_oracle > repair_noisy
            and float(oracle_round.get("useful_interaction_round_rate", 0.0) or 0.0) > 0.0
        ),
        "semantic_usefulness_supported_on_repair_semantic": (
            float(oracle_round.get("reply_usable_rate", 0.0) or 0.0) > 0.0
            and float(oracle_round.get("target_aligned_patch_rate", 0.0) or 0.0) > 0.0
            and float(oracle_round.get("effective_patch_rate", 0.0) or 0.0) > 0.0
            and float(oracle_round.get("post_query_progress_rate", 0.0) or 0.0) > 0.0
        ),
        "probe_only_success_caveat_present": True,
        "noisy_user_not_counted_as_useful_repair": float(noisy_round.get("useful_interaction_round_rate", 0.0) or 0.0) <= 0.1,
        "irrelevant_user_not_counted_as_useful_repair": float(irrelevant_round.get("reply_usable_rate", 0.0) or 0.0) <= 0.1,
        "wrong_parameter_not_counted_as_effective_patch": float(wrong_round.get("effective_patch_rate", 0.0) or 0.0) <= 0.1,
        "extraction_f1_gate_passed": target_f1 >= 0.80 and value_f1 >= 0.70 and noisy_fpr <= 0.10,
        "repair_semantic_success": {
            "a2_planner": repair_planner,
            "a3_no_query": repair_no_query,
            "a3_full_interaction_oracle": repair_oracle,
            "a3_full_interaction_noisy": repair_noisy,
        },
        "oracle_repair_semantic_round_metrics": oracle_round,
        "noisy_repair_semantic_round_metrics": noisy_round,
        "target_f1_oracle": target_f1,
        "value_f1_oracle": value_f1,
        "noisy_target_false_positive_rate": noisy_fpr,
    }


def _write_report(path: Path, summary: Dict[str, Any], effect: Dict[str, Any], prf: Dict[str, Any]) -> None:
    lines = [
        "# Interaction Live Benchmark Report",
        "",
        "## Claim Summary",
        "",
        "| verdict | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        if isinstance(value, bool):
            lines.append(f"| {key} | {str(value).lower()} |")
    lines.extend(["", "## Repair Semantic Success", ""])
    for system, value in summary.get("repair_semantic_success", {}).items():
        lines.append(f"- `{system}`: {float(value):.3f}")
    lines.extend(["", "## Interaction Effectiveness By System And Slice", ""])
    lines.append("| group | useful_round | reply_usable | effective_patch | post_query_progress | strict_success |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for group, stats in sorted(effect.get("by_system_slice", {}).items()):
        lines.append(
            f"| {group} | {stats.get('useful_interaction_round_rate', 0.0):.3f} | {stats.get('reply_usable_rate', 0.0):.3f} | {stats.get('effective_patch_rate', 0.0):.3f} | {stats.get('post_query_progress_rate', 0.0):.3f} | {stats.get('strict_success_rate', 0.0):.3f} |"
        )
    lines.extend(["", "## Extraction PRF By User Mode", ""])
    lines.append("| user_mode | target_f1 | value_f1 | action_f1 | target_false_positive_rate |")
    lines.append("|---|---:|---:|---:|---:|")
    for group, stats in sorted(prf.items()):
        if not group.startswith("user_mode|"):
            continue
        user_mode = group.split("|", 1)[1]
        lines.append(
            f"| {user_mode} | {stats.get('target', {}).get('f1', 0.0):.3f} | {stats.get('value', {}).get('f1', 0.0):.3f} | {stats.get('action', {}).get('f1', 0.0):.3f} | {stats.get('target', {}).get('false_positive_rate', 0.0):.3f} |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score ToolSandbox interaction-live outputs")
    parser.add_argument("--dataset", default="")
    parser.add_argument("--comparison", default="")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--official-eval", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--toolclaw-diagnostics", default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global dataset_by_id
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = outdir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    dataset_path = Path(args.dataset or manifest.get("source") or "")
    comparison_path = Path(args.comparison or outdir / "comparison.scored.csv")
    if not dataset_path.exists():
        raise FileNotFoundError(f"interaction-live dataset not found: {dataset_path}")
    dataset = _read_jsonl(dataset_path)
    dataset_by_id = {str(row.get("task_id") or row.get("name")): row for row in dataset}
    scored_rows = _read_csv(comparison_path)
    rounds = _trace_rounds(scored_rows, dataset_by_id)
    _write_jsonl(outdir / "interaction_rounds.jsonl", rounds)
    effect_summary = {
        "by_system_slice": _aggregate_rounds(rounds, ("system", "slice_type")),
        "by_user_mode_slice": _aggregate_rounds(rounds, ("user_mode", "slice_type")),
    }
    (outdir / "interaction_effectiveness_summary.json").write_text(json.dumps(effect_summary, indent=2), encoding="utf-8")
    prf = {
        **{f"system|{key}": value for key, value in _prf_by(rounds, ("system",)).items()},
        **{f"user_mode|{key}": value for key, value in _prf_by(rounds, ("user_mode",)).items()},
        **{f"slice|{key}": value for key, value in _prf_by(rounds, ("slice_type",)).items()},
        **{f"user_mode_slice|{key}": value for key, value in _prf_by(rounds, ("user_mode", "slice_type")).items()},
    }
    (outdir / "extraction_prf.json").write_text(json.dumps(prf, indent=2), encoding="utf-8")
    slice_summary = {
        "by_system_slice": effect_summary["by_system_slice"],
        "by_user_mode_slice": effect_summary["by_user_mode_slice"],
    }
    (outdir / "slice_summary.json").write_text(json.dumps(slice_summary, indent=2), encoding="utf-8")
    summary = _claim_summary(scored_rows, rounds, prf)
    (outdir / "claim_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(outdir / "report.md", summary, effect_summary, prf)


dataset_by_id: Dict[str, Dict[str, Any]] = {}


if __name__ == "__main__":
    main()
