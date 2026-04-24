#!/usr/bin/env python3
"""Score ToolSandbox semantic-repair official slices."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except Exception:
        return str(path)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return float(mean(values)) if values else 0.0


def _float(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(str(value or "").strip() or 0.0)
    except ValueError:
        return 0.0


def _rounds(rows: List[Dict[str, str]], dataset_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rounds: List[Dict[str, Any]] = []
    for row in rows:
        trace_path = Path(row.get("trace_path", ""))
        if not trace_path.exists():
            continue
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
        dataset_row = dataset_by_id.get(str(row.get("task_id") or ""))
        if not dataset_row:
            continue
        for event in payload.get("events", []):
            if event.get("event_type") != "interaction_round_outcome":
                continue
            metadata = event.get("metadata", {}) if isinstance(event.get("metadata"), dict) else {}
            output = event.get("output", {}) if isinstance(event.get("output"), dict) else {}
            rounds.append(
                {
                    "task_id": row.get("task_id"),
                    "system": row.get("system"),
                    "slice_type": dataset_row.get("slice_type", ""),
                    "decoded_is_usable": bool(output.get("decoded_is_usable", metadata.get("decoded_is_usable", False))),
                    "target_alignment": _float(output.get("target_alignment", metadata.get("target_alignment", 0.0))),
                    "effective_patch": bool(output.get("effective_patch", metadata.get("effective_patch", False))),
                    "post_query_progress": bool(output.get("post_query_progress", metadata.get("post_query_progress", False))),
                    "interaction_round_useful": bool(output.get("interaction_round_useful", metadata.get("interaction_round_useful", False))),
                    "trace_path": _repo_relative(trace_path),
                }
            )
    return rounds


def _aggregate_rows(rows: List[Dict[str, str]], dataset_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        dataset_row = dataset_by_id.get(str(row.get("task_id") or ""))
        if not dataset_row:
            continue
        grouped[(str(row.get("system") or ""), str(dataset_row.get("slice_type") or ""))].append(row)
    result: Dict[str, Dict[str, Any]] = {}
    for (system, slice_type), group_rows in sorted(grouped.items()):
        key = f"{system}|{slice_type}"
        result[key] = {
            "system": system,
            "slice_type": slice_type,
            "num_rows": len(group_rows),
            "strict_scored_success": _mean(_float(row.get("strict_scored_success_rate", 0.0)) for row in group_rows),
            "execution_verified_success": _mean(_float(row.get("execution_verified_success_rate", 0.0)) for row in group_rows),
            "reply_usable_rate": _mean(_float(row.get("reply_usable_rate", 0.0)) for row in group_rows),
            "target_aligned_patch_rate": _mean(_float(row.get("target_aligned_patch_rate", 0.0)) for row in group_rows),
            "effective_patch_rate": _mean(_float(row.get("effective_patch_rate", 0.0)) for row in group_rows),
            "post_query_progress_rate": _mean(_float(row.get("post_query_progress_rate", 0.0)) for row in group_rows),
            "useful_interaction_round_rate": _mean(_float(row.get("useful_interaction_round_rate", 0.0)) for row in group_rows),
            "mean_user_queries": _mean(_float(row.get("mean_user_queries", 0.0)) for row in group_rows),
            "mean_tool_calls": _mean(_float(row.get("tool_calls", 0.0)) for row in group_rows),
        }
    return result


def _aggregate_rounds(rounds: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rounds:
        grouped[(str(row["system"]), str(row["slice_type"]))].append(row)
    result: Dict[str, Dict[str, Any]] = {}
    for (system, slice_type), group_rows in sorted(grouped.items()):
        key = f"{system}|{slice_type}"
        result[key] = {
            "num_rounds": len(group_rows),
            "reply_usable_rate": _mean(1.0 if row["decoded_is_usable"] else 0.0 for row in group_rows),
            "target_aligned_patch_rate": _mean(1.0 if row["target_alignment"] >= 0.5 else 0.0 for row in group_rows),
            "effective_patch_rate": _mean(1.0 if row["effective_patch"] else 0.0 for row in group_rows),
            "post_query_progress_rate": _mean(1.0 if row["post_query_progress"] else 0.0 for row in group_rows),
            "useful_interaction_round_rate": _mean(1.0 if row["interaction_round_useful"] else 0.0 for row in group_rows),
        }
    return result


def _paired_delta_summary(rows: List[Dict[str, str]], dataset_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    comparisons = {
        "a3_full_interaction_vs_a2_planner": ("a3_full_interaction", "a2_planner"),
        "a3_full_interaction_vs_a3_no_query": ("a3_full_interaction", "a3_no_query"),
        "a3_full_interaction_vs_a3_noisy_user": ("a3_full_interaction", "a3_noisy_user"),
    }
    by_key: Dict[Tuple[str, str, str], Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in rows:
        task_id = str(row.get("task_id") or "")
        dataset_row = dataset_by_id.get(task_id)
        if not dataset_row:
            continue
        slice_type = str(dataset_row.get("slice_type") or "")
        run_index = str(row.get("run_index") or "1")
        system = str(row.get("system") or "")
        by_key[(slice_type, task_id, run_index)][system] = row

    result: Dict[str, Any] = {
        "summary_version": "toolsandbox_semantic_repair_official_v1_paired_delta",
        "paired_key": ["task_id", "run_index"],
        "metric": "strict_scored_success_rate",
        "comparisons": {},
    }
    for comparison_name, (treatment, control) in comparisons.items():
        by_slice: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for (slice_type, task_id, run_index), system_rows in sorted(by_key.items()):
            if treatment not in system_rows or control not in system_rows:
                continue
            treatment_value = _float(system_rows[treatment].get("strict_scored_success_rate", 0.0))
            control_value = _float(system_rows[control].get("strict_scored_success_rate", 0.0))
            delta = treatment_value - control_value
            by_slice[slice_type].append(
                {
                    "task_id": task_id,
                    "run_index": run_index,
                    "treatment_value": treatment_value,
                    "control_value": control_value,
                    "delta": delta,
                }
            )
        comparison_summary: Dict[str, Any] = {
            "treatment": treatment,
            "control": control,
            "by_slice": {},
        }
        for slice_type, pairs in sorted(by_slice.items()):
            deltas = [float(pair["delta"]) for pair in pairs]
            comparison_summary["by_slice"][slice_type] = {
                "num_pairs": len(pairs),
                "wins": sum(1 for delta in deltas if delta > 0.0),
                "losses": sum(1 for delta in deltas if delta < 0.0),
                "ties": sum(1 for delta in deltas if delta == 0.0),
                "mean_delta": _mean(deltas),
                "task_count": len({str(pair["task_id"]) for pair in pairs}),
            }
        result["comparisons"][comparison_name] = comparison_summary
    return result


def _write_paired_delta_markdown(path: Path, paired_summary: Dict[str, Any]) -> None:
    lines = [
        "# ToolSandbox Semantic Repair Official v1 Paired Delta Summary",
        "",
        "Paired key: `(task_id, run_index)`.",
        "",
        "The repair-semantic-positive slice is the mechanism evidence. The probe-only control slice is a caveat: strict success there can be contract/probe-mediated and must not be interpreted as semantic repair.",
        "",
        "| comparison | slice | pairs | wins | losses | ties | mean_delta | task_count |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for comparison_name, comparison in sorted(paired_summary.get("comparisons", {}).items()):
        for slice_type, stats in sorted(comparison.get("by_slice", {}).items()):
            lines.append(
                f"| {comparison_name} | {slice_type} | {int(stats.get('num_pairs', 0))} | {int(stats.get('wins', 0))} | {int(stats.get('losses', 0))} | {int(stats.get('ties', 0))} | {float(stats.get('mean_delta', 0.0)):.3f} | {int(stats.get('task_count', 0))} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _claim_summary(
    row_summary: Dict[str, Dict[str, Any]],
    round_summary: Dict[str, Dict[str, Any]],
    systems_observed: List[str],
) -> Dict[str, Any]:
    expected = ["a2_planner", "a3_full_interaction", "a3_no_query", "a3_noisy_user"]
    protocol_complete = systems_observed == expected

    def row_stats(system: str, slice_type: str) -> Dict[str, Any]:
        return row_summary.get(f"{system}|{slice_type}", {})

    def round_stats(system: str, slice_type: str) -> Dict[str, Any]:
        return round_summary.get(f"{system}|{slice_type}", {})

    repair_full = row_stats("a3_full_interaction", "repair_semantic_positive")
    repair_no_query = row_stats("a3_no_query", "repair_semantic_positive")
    repair_noisy = row_stats("a3_noisy_user", "repair_semantic_positive")
    repair_planner = row_stats("a2_planner", "repair_semantic_positive")
    repair_full_round = round_stats("a3_full_interaction", "repair_semantic_positive")
    repair_noisy_round = round_stats("a3_noisy_user", "repair_semantic_positive")
    probe_full = row_stats("a3_full_interaction", "probe_only_control")
    probe_noisy = row_stats("a3_noisy_user", "probe_only_control")
    probe_planner = row_stats("a2_planner", "probe_only_control")
    probe_full_round = round_stats("a3_full_interaction", "probe_only_control")
    probe_noisy_round = round_stats("a3_noisy_user", "probe_only_control")

    semantic_supported = (
        protocol_complete
        and repair_full.get("strict_scored_success", 0.0) > repair_no_query.get("strict_scored_success", 0.0)
        and repair_full.get("strict_scored_success", 0.0) > repair_noisy.get("strict_scored_success", 0.0)
        and repair_full.get("strict_scored_success", 0.0) > repair_planner.get("strict_scored_success", 0.0)
        and repair_full_round.get("reply_usable_rate", 0.0) > 0.0
        and repair_full_round.get("target_aligned_patch_rate", 0.0) > 0.0
        and repair_full_round.get("effective_patch_rate", 0.0) > 0.0
        and repair_full_round.get("post_query_progress_rate", 0.0) > 0.0
        and repair_full_round.get("useful_interaction_round_rate", 0.0) > 0.0
        and repair_noisy_round.get("useful_interaction_round_rate", 0.0) <= 0.1
    )
    probe_caveat = (
        probe_full.get("strict_scored_success", 0.0) >= probe_planner.get("strict_scored_success", 0.0)
        and probe_noisy.get("strict_scored_success", 0.0) >= probe_planner.get("strict_scored_success", 0.0)
        and probe_full_round.get("useful_interaction_round_rate", 0.0) <= 0.1
        and probe_noisy_round.get("useful_interaction_round_rate", 0.0) <= 0.1
    )
    return {
        "summary_version": "toolsandbox_semantic_repair_official_v1",
        "systems_expected": expected,
        "systems_observed": systems_observed,
        "protocol_complete": protocol_complete,
        "semantic_repair_mechanism_supported": semantic_supported,
        "interaction_not_cheating_supported": (
            repair_noisy_round.get("useful_interaction_round_rate", 0.0) <= 0.1
            and repair_full_round.get("useful_interaction_round_rate", 0.0) > repair_noisy_round.get("useful_interaction_round_rate", 0.0)
        ),
        "probe_only_success_caveat_present": probe_caveat,
        "primary_result_ready": semantic_supported and protocol_complete,
        "repair_semantic_positive": {
            system: row_stats(system, "repair_semantic_positive")
            for system in expected
        },
        "probe_only_control": {
            system: row_stats(system, "probe_only_control")
            for system in expected
        },
        "repair_semantic_rounds": {
            system: round_stats(system, "repair_semantic_positive")
            for system in expected
        },
        "probe_only_rounds": {
            system: round_stats(system, "probe_only_control")
            for system in expected
        },
    }


def _write_report(
    path: Path,
    summary: Dict[str, Any],
    row_summary: Dict[str, Dict[str, Any]],
    round_summary: Dict[str, Dict[str, Any]],
    paired_summary: Dict[str, Any],
) -> None:
    lines = [
        "# ToolSandbox Semantic Repair Official v1",
        "",
        "## Claim Summary",
        "",
        "| verdict | value |",
        "|---|---:|",
    ]
    for key in (
        "protocol_complete",
        "semantic_repair_mechanism_supported",
        "interaction_not_cheating_supported",
        "probe_only_success_caveat_present",
        "primary_result_ready",
    ):
        lines.append(f"| {key} | {str(bool(summary.get(key))).lower()} |")
    lines.extend([
        "",
        "## Row-Level Slice Summary",
        "",
        "| system | slice | strict | verified | reply_usable | target_aligned | effective_patch | post_query_progress | useful_round | mean_user_queries | mean_tool_calls |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for key, stats in sorted(row_summary.items()):
        lines.append(
            f"| {stats.get('system')} | {stats.get('slice_type')} | {stats.get('strict_scored_success', 0.0):.3f} | {stats.get('execution_verified_success', 0.0):.3f} | {stats.get('reply_usable_rate', 0.0):.3f} | {stats.get('target_aligned_patch_rate', 0.0):.3f} | {stats.get('effective_patch_rate', 0.0):.3f} | {stats.get('post_query_progress_rate', 0.0):.3f} | {stats.get('useful_interaction_round_rate', 0.0):.3f} | {stats.get('mean_user_queries', 0.0):.3f} | {stats.get('mean_tool_calls', 0.0):.3f} |"
        )
    lines.extend([
        "",
        "## Round-Level Summary",
        "",
        "| system | slice | rounds | reply_usable | target_aligned | effective_patch | post_query_progress | useful_round |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for key, stats in sorted(round_summary.items()):
        system, slice_type = key.split("|", 1)
        lines.append(
            f"| {system} | {slice_type} | {int(stats.get('num_rounds', 0))} | {stats.get('reply_usable_rate', 0.0):.3f} | {stats.get('target_aligned_patch_rate', 0.0):.3f} | {stats.get('effective_patch_rate', 0.0):.3f} | {stats.get('post_query_progress_rate', 0.0):.3f} | {stats.get('useful_interaction_round_rate', 0.0):.3f} |"
        )
    lines.extend([
        "",
        "## Paired Delta Summary",
        "",
        "Paired deltas use `(task_id, run_index)` and strict scored success. The repair-semantic-positive slice is mechanism evidence; probe-only control is a contract/probe caveat.",
        "",
        "| comparison | slice | pairs | wins | losses | ties | mean_delta |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for comparison_name, comparison in sorted(paired_summary.get("comparisons", {}).items()):
        for slice_type, stats in sorted(comparison.get("by_slice", {}).items()):
            lines.append(
                f"| {comparison_name} | {slice_type} | {int(stats.get('num_pairs', 0))} | {int(stats.get('wins', 0))} | {int(stats.get('losses', 0))} | {int(stats.get('ties', 0))} | {float(stats.get('mean_delta', 0.0)):.3f} |"
            )
    lines.extend([
        "",
        "See `paired_delta_summary.md` and `paired_delta_summary.json` for the standalone paired evidence artifact.",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score ToolSandbox semantic-repair official outputs")
    parser.add_argument("--dataset")
    parser.add_argument("--comparison")
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def _resolve_input_paths(args: argparse.Namespace, outdir: Path) -> Tuple[Path, Path]:
    manifest_path = outdir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    dataset = args.dataset or manifest.get("dataset") or "data/toolsandbox_semantic_repair_official_v1.jsonl"
    comparison = args.comparison or manifest.get("comparison_scored") or str(outdir / "comparison.scored.csv")
    return Path(dataset), Path(comparison)


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    dataset_path, comparison_path = _resolve_input_paths(args, outdir)
    dataset = _read_jsonl(dataset_path)
    dataset_by_id = {str(row.get("task_id") or row.get("name")): row for row in dataset}
    scored_rows = _read_csv(comparison_path)
    filtered_rows = [row for row in scored_rows if str(row.get("task_id") or "") in dataset_by_id]
    interaction_rounds_path = outdir / "interaction_rounds.jsonl"
    rounds = _rounds(filtered_rows, dataset_by_id)
    if not rounds and interaction_rounds_path.exists():
        # Paper-facing bundles intentionally omit raw traces. Preserve the
        # already-materialized round summary input when re-scoring such bundles.
        rounds = _read_jsonl(interaction_rounds_path)
    interaction_rounds_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rounds) + ("\n" if rounds else ""),
        encoding="utf-8",
    )
    row_summary = _aggregate_rows(filtered_rows, dataset_by_id)
    round_summary = _aggregate_rounds(rounds)
    paired_summary = _paired_delta_summary(filtered_rows, dataset_by_id)
    (outdir / "paired_delta_summary.json").write_text(json.dumps(paired_summary, indent=2), encoding="utf-8")
    _write_paired_delta_markdown(outdir / "paired_delta_summary.md", paired_summary)
    slice_summary = {
        "summary_version": "toolsandbox_semantic_repair_official_v1",
        "row_level": row_summary,
        "round_level": round_summary,
        "paired_delta_path": _repo_relative(outdir / "paired_delta_summary.json"),
    }
    (outdir / "slice_summary.json").write_text(json.dumps(slice_summary, indent=2), encoding="utf-8")
    systems_observed = sorted({str(row.get("system") or "") for row in filtered_rows})
    claim_summary = _claim_summary(row_summary, round_summary, systems_observed)
    claim_summary["paired_delta_summary_path"] = _repo_relative(outdir / "paired_delta_summary.json")
    (outdir / "claim_summary.json").write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")
    _write_report(outdir / "report.md", claim_summary, row_summary, round_summary, paired_summary)

    manifest_path = outdir / "experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest.update(
        {
            "benchmark": "toolsandbox_semantic_repair_official_v1",
            "dataset": _repo_relative(dataset_path),
            "comparison_scored": _repo_relative(comparison_path),
            "slice_summary_path": _repo_relative(outdir / "slice_summary.json"),
            "paired_delta_summary_path": _repo_relative(outdir / "paired_delta_summary.json"),
            "paired_delta_summary_md_path": _repo_relative(outdir / "paired_delta_summary.md"),
            "claim_summary_path": _repo_relative(outdir / "claim_summary.json"),
            "interaction_rounds_path": _repo_relative(outdir / "interaction_rounds.jsonl"),
            "report_path": _repo_relative(outdir / "report.md"),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
