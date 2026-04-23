#!/usr/bin/env python3
"""Derive a ToolSandbox interaction-live mechanism dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]


CATEGORY_ALIASES = {
    "single/multiple tool call": "multiple_tool",
    "single tool": "single_tool",
    "single tool call": "single_tool",
    "multiple tool": "multiple_tool",
    "multiple tool call": "multiple_tool",
    "multi tool": "multiple_tool",
    "single/multiple user turn": "multiple_user_turn",
    "single user turn": "single_user_turn",
    "multiple user turn": "multiple_user_turn",
    "multi user turn": "multiple_user_turn",
    "state dependency": "state_dependency",
    "canonicalization": "canonicalization",
    "insufficient information": "insufficient_information",
}


def _normalize_category(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", " ")
    return CATEGORY_ALIASES.get(text, text.replace(" ", "_"))


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
        return [dict(row) for row in payload["samples"] if isinstance(row, dict)]
    raise ValueError("source must be a JSON list, JSON object with samples, or JSONL")


def _sample_id(row: Dict[str, Any], idx: int) -> str:
    return str(row.get("sample_id") or row.get("task_id") or row.get("name") or row.get("id") or f"sample_{idx:05d}")


def _categories(row: Dict[str, Any]) -> List[str]:
    raw = row.get("normalized_categories") or row.get("categories") or []
    if not isinstance(raw, list):
        raw = []
    normalized = [_normalize_category(item) for item in raw if str(item).strip()]
    metadata = row.get("metadata", {})
    if isinstance(metadata, dict) and isinstance(metadata.get("toolsandbox_categories"), list):
        normalized.extend(_normalize_category(item) for item in metadata["toolsandbox_categories"] if str(item).strip())
    return sorted(set(normalized))


def _slice_type(categories: Iterable[str]) -> Optional[str]:
    category_set = set(categories)
    if "state_dependency" in category_set:
        return "repair_semantic_primary"
    if {"multiple_user_turn", "insufficient_information"}.intersection(category_set):
        return "probe_only_control"
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except Exception:
        return ""


def _trace_candidates(trace_root: Optional[Path], task_id: str) -> List[Path]:
    if trace_root is None or not trace_root.exists():
        return []
    return sorted(
        path
        for path in trace_root.rglob("*.json")
        if task_id in path.name and "a3_full_interaction" in path.name
    )


def _trace_gold(trace_root: Optional[Path], task_id: str) -> Dict[str, Any]:
    for path in _trace_candidates(trace_root, task_id):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        events = list(payload.get("events", []))
        user_query = next((event for event in events if event.get("event_type") == "user_query"), {})
        outcome = next((event for event in events if event.get("event_type") == "interaction_round_outcome"), {})
        query_meta = dict(user_query.get("metadata", {}).get("query_metadata", {})) if isinstance(user_query, dict) else {}
        answer_patch = dict(outcome.get("metadata", {}).get("answer_patch", {})) if isinstance(outcome, dict) else {}
        reply_meta = dict(outcome.get("metadata", {}).get("reply_metadata", {})) if isinstance(outcome, dict) else {}
        patch_targets = query_meta.get("patch_targets")
        if not isinstance(patch_targets, dict):
            patch_targets = reply_meta.get("patch_targets")
        if not isinstance(patch_targets, dict):
            patch_targets = {str(key): str(key) for key in answer_patch.get("expected_patch_targets", []) if str(key)}
        query_policy = query_meta.get("query_policy", {}) if isinstance(query_meta.get("query_policy"), dict) else {}
        outcome_metadata = outcome.get("metadata", {}) if isinstance(outcome, dict) else {}
        outcome_output = outcome.get("output", {}) if isinstance(outcome, dict) else {}
        return {
            "trace_path": str(path),
            "expected_query_type": str(query_policy.get("question_type") or reply_meta.get("expected_answer_type") or ""),
            "expected_patch_targets": dict(patch_targets),
            "suggested_values": dict(query_meta.get("suggested_values", {})) if isinstance(query_meta.get("suggested_values"), dict) else {},
            "expected_effect_scope": str(answer_patch.get("effect_scope") or "none"),
            "gold_effective_patch": bool(answer_patch.get("effective_patch", False)),
            "gold_post_query_progress": bool(
                outcome_output.get("post_query_progress", outcome_metadata.get("post_query_progress", False))
            ),
            "gold_decoded_signal": {
                "intent_type": str(reply_meta.get("decoded_intent_type") or ""),
                "slot_updates": dict(reply_meta.get("decoded_slot_updates", {})) if isinstance(reply_meta.get("decoded_slot_updates"), dict) else {},
                "approvals": dict(reply_meta.get("decoded_approvals", {})) if isinstance(reply_meta.get("decoded_approvals"), dict) else {},
                "control_updates": dict(reply_meta.get("decoded_control_updates", {})) if isinstance(reply_meta.get("decoded_control_updates"), dict) else {},
                "expected_targets": list(reply_meta.get("expected_targets", [])) if isinstance(reply_meta.get("expected_targets"), list) else list(patch_targets.keys()),
            },
        }
    return {
        "trace_path": "",
        "expected_query_type": "",
        "expected_patch_targets": {},
        "suggested_values": {},
        "expected_effect_scope": "none",
        "gold_effective_patch": False,
        "gold_post_query_progress": False,
        "gold_decoded_signal": {
            "intent_type": "",
            "slot_updates": {},
            "approvals": {},
            "control_updates": {},
            "expected_targets": [],
        },
    }


def _oracle_payload(row: Dict[str, Any], trace_gold: Dict[str, Any]) -> Dict[str, Any]:
    patch_targets = trace_gold["expected_patch_targets"]
    suggested_values = trace_gold.get("suggested_values", {})
    signal = trace_gold.get("gold_decoded_signal", {})
    gold_slots = signal.get("slot_updates", {}) if isinstance(signal, dict) and isinstance(signal.get("slot_updates"), dict) else {}
    gold_approvals = signal.get("approvals", {}) if isinstance(signal, dict) and isinstance(signal.get("approvals"), dict) else {}
    gold_controls = signal.get("control_updates", {}) if isinstance(signal, dict) and isinstance(signal.get("control_updates"), dict) else {}
    payload: Dict[str, Any] = {}
    for key in patch_targets:
        key_text = str(key)
        if key_text in gold_slots:
            payload[key_text] = gold_slots[key_text]
        elif key_text in gold_approvals:
            payload[key_text] = gold_approvals[key_text]
        elif key_text in gold_controls:
            payload[key_text] = gold_controls[key_text]
        elif key_text == "approved":
            payload[key_text] = True
        elif key_text == "tool_id":
            payload[key_text] = suggested_values.get("tool_id") or "backup_write_tool"
        elif key_text in suggested_values:
            payload[key_text] = suggested_values[key_text]
        elif key_text == "target_path":
            payload[key_text] = row.get("target_path") or f"outputs/toolsandbox/reports/{_sample_id(row, 0)}.txt"
        else:
            payload[key_text] = f"oracle_{key_text}"
    return payload


def _oracle_replies(row: Dict[str, Any], trace_gold: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = _oracle_payload(row, trace_gold)
    if not payload:
        return []
    return [
        {
            "trigger_type": "permission_query" if "approved" in payload else "missing_slot_query",
            "slot": next((key for key in payload if key != "approved"), next(iter(payload), "")),
            "reply": json.dumps(payload, sort_keys=True),
            "payload": payload,
        }
    ]


def _negative_replies(trace_gold: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        "noisy_user": {"raw_text": "I don't know", "payload": {"raw_text": "I don't know"}},
        "irrelevant_user": {"raw_text": "irrelevant answer", "payload": {"raw_text": "irrelevant answer"}},
        "wrong_parameter_user": {"raw_text": "wrong parameter", "payload": {"input_patch": {"value": "wrong_parameter"}}},
        "partial_user": {"raw_text": "partial answer", "payload": {"approved": True} if "approved" in trace_gold["expected_patch_targets"] else {}},
    }


def derive(source: Path, trace_root: Optional[Path]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    output_rows: List[Dict[str, Any]] = []
    source_rows = _load_rows(source)
    for idx, row in enumerate(source_rows, start=1):
        categories = _categories(row)
        slice_type = _slice_type(categories)
        if slice_type is None:
            continue
        task_id = _sample_id(row, idx)
        trace_gold = _trace_gold(trace_root, task_id)
        derived = dict(row)
        derived["task_id"] = task_id
        derived["source_task_id"] = task_id
        derived["slice_type"] = slice_type
        derived["categories"] = categories
        derived["expected_query_type"] = trace_gold["expected_query_type"]
        derived["expected_patch_targets"] = trace_gold["expected_patch_targets"]
        derived["expected_effect_scope"] = trace_gold["expected_effect_scope"]
        derived["oracle_user_replies"] = _oracle_replies(row, trace_gold)
        derived["negative_user_replies"] = _negative_replies(trace_gold)
        derived["gold_decoded_signal"] = trace_gold["gold_decoded_signal"]
        derived["gold_effective_patch"] = trace_gold["gold_effective_patch"]
        derived["gold_post_query_progress"] = trace_gold["gold_post_query_progress"]
        derived["gold_has_useful_interaction"] = bool(trace_gold["gold_effective_patch"] and trace_gold["gold_post_query_progress"])
        derived["manual_label_status"] = "auto_seeded"
        derived.setdefault("metadata", {})
        if isinstance(derived["metadata"], dict):
            derived["metadata"]["interaction_live_trace_path"] = trace_gold["trace_path"]
            derived["metadata"]["interaction_live_slice_type"] = slice_type
        output_rows.append(derived)

    output_rows.sort(
        key=lambda row: (
            0 if row.get("slice_type") == "repair_semantic_primary" else 1,
            0 if row.get("gold_has_useful_interaction") else 1,
            str(row.get("task_id") or ""),
        )
    )
    manifest = {
        "dataset": "toolsandbox_interaction_live_v1",
        "source": str(source),
        "source_sha256": _file_sha256(source),
        "trace_root": str(trace_root) if trace_root else "",
        "git_commit": _git_commit(),
        "selection_rule": {
            "repair_semantic_primary": "normalized categories include state_dependency",
            "probe_only_control": "normalized categories include multiple_user_turn or insufficient_information, unless state_dependency is present",
        },
        "counts": {
            "total": len(output_rows),
            "repair_semantic_primary": sum(1 for row in output_rows if row.get("slice_type") == "repair_semantic_primary"),
            "probe_only_control": sum(1 for row in output_rows if row.get("slice_type") == "probe_only_control"),
            "auto_seeded": sum(1 for row in output_rows if row.get("manual_label_status") == "auto_seeded"),
            "with_oracle_reply": sum(1 for row in output_rows if row.get("oracle_user_replies")),
            "with_trace_gold": sum(1 for row in output_rows if row.get("metadata", {}).get("interaction_live_trace_path")),
            "with_useful_interaction_gold": sum(1 for row in output_rows if row.get("gold_has_useful_interaction")),
        },
    }
    return output_rows, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox interaction-live dataset")
    parser.add_argument("--source", default=str(ROOT_DIR / "data" / "toolsandbox.formal.official.json"))
    parser.add_argument("--trace-root", default="")
    parser.add_argument("--out", default=str(ROOT_DIR / "data" / "toolsandbox_interaction_live_v1.jsonl"))
    parser.add_argument("--manifest", default=str(ROOT_DIR / "data" / "toolsandbox_interaction_live_v1.manifest.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    trace_root = Path(args.trace_root) if str(args.trace_root).strip() else None
    rows, manifest = derive(source, trace_root)
    out_path = Path(args.out)
    manifest_path = Path(args.manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {out_path} rows={len(rows)}")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
