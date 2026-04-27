#!/usr/bin/env python3
"""Derive a narrow ToolSandbox semantic-repair official slice."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]

PRIMARY_TASK_IDS = (
    "turn_on_cellular_low_battery_mode",
    "turn_on_cellular_low_battery_mode_implicit",
    "turn_on_location_low_battery_mode",
    "turn_on_location_low_battery_mode_implicit",
    "turn_on_wifi_low_battery_mode",
    "turn_on_wifi_low_battery_mode_implicit",
)

PROBE_CONTROL_TASK_IDS = (
    "add_reminder_content_and_date_and_time_multiple_user_turn",
    "add_reminder_content_and_week_delta_and_time_multiple_user_turn",
    "find_days_till_holiday_multiple_user_turn",
    "search_message_with_recency_latest_multiple_user_turn",
    "remove_contact_by_phone_no_remove_contact_insufficient_information",
    "remove_contact_by_phone_no_remove_contact_insufficient_information_alt",
)


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    except Exception:
        return ""


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except Exception:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_source(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected JSON list in {path}")
    return [dict(item) for item in payload if isinstance(item, dict)]


def _load_comparison(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _task_id(row: Dict[str, Any]) -> str:
    for key in ("task_id", "name", "sample_id", "id"):
        value = row.get(key)
        if value:
            return str(value)
    raise ValueError("task missing id/name")


def _best_row(
    rows: Iterable[Dict[str, str]],
    *,
    task_id: str,
    system: str,
) -> Optional[Dict[str, str]]:
    candidates = [row for row in rows if row.get("task_id") == task_id and row.get("system") == system]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            float(row.get("useful_interaction_round_rate", 0.0) or 0.0),
            float(row.get("reply_usable_rate", 0.0) or 0.0),
            float(row.get("strict_scored_success_rate", 0.0) or 0.0),
        ),
    )


def _load_trace(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _trace_gold(trace_path: Path) -> Dict[str, Any]:
    payload = _load_trace(trace_path)
    events = list(payload.get("events", []))
    user_query = next((event for event in events if event.get("event_type") == "user_query"), {})
    outcome = next((event for event in events if event.get("event_type") == "interaction_round_outcome"), {})
    query_meta = dict(user_query.get("metadata", {}).get("query_metadata", {})) if isinstance(user_query, dict) else {}
    answer_patch = dict(outcome.get("metadata", {}).get("answer_patch", {})) if isinstance(outcome, dict) else {}
    reply_meta = dict(outcome.get("metadata", {}).get("reply_metadata", {})) if isinstance(outcome, dict) else {}
    output = dict(outcome.get("output", {})) if isinstance(outcome, dict) else {}
    patch_targets = query_meta.get("patch_targets")
    if not isinstance(patch_targets, dict):
        patch_targets = reply_meta.get("patch_targets")
    if not isinstance(patch_targets, dict):
        patch_targets = {str(key): str(key) for key in answer_patch.get("expected_patch_targets", []) if str(key)}
    return {
        "expected_query_type": str(query_meta.get("question_type") or reply_meta.get("expected_answer_type") or ""),
        "expected_patch_targets": dict(patch_targets),
        "expected_effect_scope": str(answer_patch.get("effect_scope") or "none"),
        "gold_target_aligned_patch": float(output.get("target_alignment", reply_meta.get("target_alignment", 0.0)) or 0.0) >= 0.5,
        "gold_effective_patch": bool(answer_patch.get("effective_patch", False) or output.get("effective_patch", False)),
        "gold_post_query_progress": bool(output.get("post_query_progress", False)),
        "gold_decoded_signal": {
            "intent_type": str(reply_meta.get("decoded_intent_type") or ""),
            "slot_updates": dict(reply_meta.get("decoded_slot_updates", {})) if isinstance(reply_meta.get("decoded_slot_updates"), dict) else {},
            "approvals": dict(reply_meta.get("decoded_approvals", {})) if isinstance(reply_meta.get("decoded_approvals"), dict) else {},
            "control_updates": dict(reply_meta.get("decoded_control_updates", {})) if isinstance(reply_meta.get("decoded_control_updates"), dict) else {},
            "expected_targets": list(reply_meta.get("expected_targets", [])) if isinstance(reply_meta.get("expected_targets"), list) else list(patch_targets.keys()),
        },
    }


def _categories(row: Dict[str, Any]) -> List[str]:
    raw = row.get("categories") or row.get("normalized_categories") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item).strip()]


def _conversation_prefix(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    user_indices = [
        idx
        for idx, message in enumerate(messages)
        if str(message.get("sender", "")).strip().lower() == "user"
    ]
    if len(user_indices) < 2:
        return list(messages), []
    second_user_idx = user_indices[1]
    return list(messages[:second_user_idx]), list(messages[second_user_idx:])


def _oracle_replies(
    removed_messages: List[Dict[str, Any]],
    *,
    expected_query_type: str,
    patch_targets: Dict[str, Any],
    gold_signal: Dict[str, Any],
) -> List[Dict[str, Any]]:
    replies: List[Dict[str, Any]] = []
    trigger_type = "permission_query" if "permission" in expected_query_type or "approval" in expected_query_type else "missing_slot_query"
    slot = "approved" if trigger_type == "permission_query" else next(iter(patch_targets.keys()), "")
    payload: Dict[str, Any] = {}
    slot_updates = gold_signal.get("slot_updates", {}) if isinstance(gold_signal.get("slot_updates"), dict) else {}
    approvals = gold_signal.get("approvals", {}) if isinstance(gold_signal.get("approvals"), dict) else {}
    control_updates = gold_signal.get("control_updates", {}) if isinstance(gold_signal.get("control_updates"), dict) else {}
    if slot_updates:
        payload.update(slot_updates)
    if approvals:
        payload.update(approvals)
    if control_updates:
        payload.update(control_updates)
    for message in removed_messages:
        if str(message.get("sender", "")).strip().lower() != "user":
            continue
        raw_text = str(message.get("content", "") or "").strip()
        if not raw_text:
            continue
        replies.append(
            {
                "trigger_type": trigger_type,
                "slot": slot or None,
                "reply": raw_text,
                "payload": dict(payload) if payload else None,
            }
        )
    return replies


def _derive_row(
    source_row: Dict[str, Any],
    *,
    slice_type: str,
    comparison_rows: List[Dict[str, str]],
    metadata_key: str,
    manual_label_suffix: str,
) -> Dict[str, Any]:
    task_id = _task_id(source_row)
    result = dict(source_row)
    result["task_id"] = task_id
    result["source_task_id"] = task_id
    result["slice_type"] = slice_type
    result["categories"] = _categories(source_row)
    full_row = _best_row(comparison_rows, task_id=task_id, system="a3_full_interaction")
    no_query_row = _best_row(comparison_rows, task_id=task_id, system="a3_no_query")
    noisy_row = _best_row(comparison_rows, task_id=task_id, system="a3_noisy_user")
    if full_row is None:
        raise ValueError(f"missing a3_full_interaction evidence for {task_id}")
    trace_path = Path(full_row["trace_path"])
    trace_gold = _trace_gold(trace_path)
    result["expected_query_type"] = trace_gold["expected_query_type"]
    result["expected_patch_targets"] = trace_gold["expected_patch_targets"]
    result["expected_effect_scope"] = trace_gold["expected_effect_scope"]
    result["gold_target_aligned_patch"] = bool(trace_gold["gold_target_aligned_patch"])
    result["gold_effective_patch"] = bool(trace_gold["gold_effective_patch"])
    result["gold_post_query_progress"] = bool(trace_gold["gold_post_query_progress"])
    result["gold_decoded_signal"] = trace_gold["gold_decoded_signal"]
    messages = list(result.get("messages", [])) if isinstance(result.get("messages"), list) else []
    kept_messages, removed_messages = _conversation_prefix(messages)
    if kept_messages:
        result["messages"] = kept_messages
    oracle_replies = _oracle_replies(
        removed_messages,
        expected_query_type=result["expected_query_type"],
        patch_targets=result["expected_patch_targets"],
        gold_signal=result["gold_decoded_signal"],
    )
    if oracle_replies:
        result["oracle_user_replies"] = oracle_replies
    if slice_type == "repair_semantic_positive":
        result["scenario"] = "state_failure"
        result["execution_scenario"] = "state_failure"
        result["state_failure_mode"] = "resume_state_loss"
    result["manual_label_status"] = (
        f"human_verified_trace_review_{manual_label_suffix}"
        if slice_type == "repair_semantic_positive"
        else f"trace_verified_probe_only_control_{manual_label_suffix}"
    )
    result.setdefault("metadata", {})
    if isinstance(result["metadata"], dict):
        result["metadata"][metadata_key] = {
            "slice_type": slice_type,
            "selection_basis": (
                "trace-backed useful interaction candidate"
                if slice_type == "repair_semantic_positive"
                else "probe-only contract/control task"
            ),
            "history_truncated_before_withheld_user_reply": bool(oracle_replies),
            "trace_path": _repo_relative(trace_path),
            "a3_full_strict_scored_success": float(full_row.get("strict_scored_success_rate", 0.0) or 0.0),
            "a3_no_query_strict_scored_success": float(no_query_row.get("strict_scored_success_rate", 0.0) or 0.0) if no_query_row else None,
            "a3_noisy_user_strict_scored_success": float(noisy_row.get("strict_scored_success_rate", 0.0) or 0.0) if noisy_row else None,
        }
    return result


def derive(
    source: Path,
    comparison: Path,
    *,
    dataset_name: str = "toolsandbox_semantic_repair_official_v1",
    slice_policy_version: Optional[str] = None,
    metadata_key: Optional[str] = None,
    manual_label_suffix: str = "20260424",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    slice_policy_version = slice_policy_version or dataset_name
    metadata_key = metadata_key or dataset_name
    source_rows = _load_source(source)
    comparison_rows = _load_comparison(comparison)
    source_by_id = {_task_id(row): row for row in source_rows}
    missing = [
        task_id
        for task_id in list(PRIMARY_TASK_IDS) + list(PROBE_CONTROL_TASK_IDS)
        if task_id not in source_by_id
    ]
    if missing:
        raise ValueError(f"source missing expected tasks: {missing}")
    dataset: List[Dict[str, Any]] = []
    for task_id in PRIMARY_TASK_IDS:
        dataset.append(_derive_row(source_by_id[task_id], slice_type="repair_semantic_positive", comparison_rows=comparison_rows, metadata_key=metadata_key, manual_label_suffix=manual_label_suffix))
    for task_id in PROBE_CONTROL_TASK_IDS:
        dataset.append(_derive_row(source_by_id[task_id], slice_type="probe_only_control", comparison_rows=comparison_rows, metadata_key=metadata_key, manual_label_suffix=manual_label_suffix))
    manifest = {
        "dataset": dataset_name,
        "source": _repo_relative(source),
        "source_sha256": _sha256(source),
        "evidence_comparison": _repo_relative(comparison),
        "git_commit": _git_commit(),
        "slice_policy_version": slice_policy_version,
        "selection_rule": {
            "repair_semantic_positive": "human-reviewed task ids with trace-backed target_aligned/effective_patch/post_query_progress signals",
            "probe_only_control": "multiple_user_turn / insufficient_information control tasks with query/contract behavior but no useful repair signal",
        },
        "reviewed_primary_task_ids": list(PRIMARY_TASK_IDS),
        "probe_control_task_ids": list(PROBE_CONTROL_TASK_IDS),
        "row_count": len(dataset),
        "counts_by_slice": {
            "repair_semantic_positive": len(PRIMARY_TASK_IDS),
            "probe_only_control": len(PROBE_CONTROL_TASK_IDS),
        },
    }
    return dataset, manifest


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive a narrow ToolSandbox semantic-repair official dataset")
    parser.add_argument("--source", default="data/toolsandbox.formal.official.json")
    parser.add_argument(
        "--comparison",
        default="outputs/paper_final_freeze_20260423/toolsandbox_interaction_causality_formal/comparison.scored.csv",
    )
    parser.add_argument("--out", default="data/toolsandbox_semantic_repair_official_v1.jsonl")
    parser.add_argument("--manifest", default="data/toolsandbox_semantic_repair_official_v1.manifest.json")
    parser.add_argument("--dataset-name", default="toolsandbox_semantic_repair_official_v1")
    parser.add_argument("--slice-policy-version", default=None)
    parser.add_argument("--metadata-key", default=None)
    parser.add_argument("--manual-label-suffix", default="20260424")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset, manifest = derive(
        Path(args.source),
        Path(args.comparison),
        dataset_name=args.dataset_name,
        slice_policy_version=args.slice_policy_version,
        metadata_key=args.metadata_key,
        manual_label_suffix=args.manual_label_suffix,
    )
    out_path = Path(args.out)
    manifest_path = Path(args.manifest)
    _write_jsonl(out_path, dataset)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote: {out_path}")
    print(f"wrote: {manifest_path}")


if __name__ == "__main__":
    main()
