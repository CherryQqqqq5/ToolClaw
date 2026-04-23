#!/usr/bin/env python3
"""Derive a versioned ToolSandbox persistent-reuse paired dataset."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Tuple


PASS_RE = re.compile(r"^(?P<family>.+)__pass(?P<idx>[12])$")


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return ""


def _load_json(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected JSON list in {path}")
    return [row for row in payload if isinstance(row, dict)]


def _canonical_id(task: Dict[str, Any]) -> str:
    for key in ("task_id", "name", "sample_id", "scenario_id", "id"):
        value = task.get(key)
        if value:
            return str(value)
    raise ValueError("task object missing id/name")


def _metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    metadata = task.get("metadata", {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def _signature_key(task: Dict[str, Any]) -> str:
    tools = task.get("candidate_tools") or task.get("tool_allow_list") or []
    if not isinstance(tools, list):
        tools = []
    categories = task.get("normalized_categories") or task.get("categories") or []
    if not isinstance(categories, list):
        categories = []
    tool_key = ",".join(sorted(str(item) for item in tools))
    category_key = ",".join(sorted(str(item).lower().replace(" ", "_") for item in categories))
    return f"tools={tool_key}|categories={category_key}"


def _stage_task(task: Dict[str, Any], *, family_id: str, pass_index: int, stage: str) -> Dict[str, Any]:
    staged = deepcopy(task)
    staged_id = f"{family_id}__pass{pass_index}_{'compile' if pass_index == 1 else 'eval'}"
    staged["task_id"] = staged_id
    staged["name"] = staged_id
    staged["reuse_family_id"] = family_id
    staged["reuse_pass_index"] = pass_index
    metadata = _metadata(staged)
    metadata.update(
        {
            "reuse_family_id": family_id,
            "reuse_pass_index": pass_index,
            "reuse_stage": stage,
            "reuse_persistent_v1": True,
            "contamination_guard": {
                "allow_compile": pass_index == 1,
                "stage": stage,
                "paired_family_id": family_id,
            },
        }
    )
    staged["metadata"] = metadata
    return staged


def _pair_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    family_to_pass: Dict[str, Dict[int, Dict[str, Any]]] = {}
    errors: List[str] = []
    for row in rows:
        name = _canonical_id(row)
        match = PASS_RE.match(name)
        if not match:
            continue
        family = str(match.group("family"))
        pass_index = int(match.group("idx"))
        family_to_pass.setdefault(family, {})[pass_index] = row

    dataset: List[Dict[str, Any]] = []
    for family_id, pass_map in sorted(family_to_pass.items()):
        if 1 not in pass_map or 2 not in pass_map:
            errors.append(f"{family_id}: missing pass1 or pass2")
            continue
        pass1 = pass_map[1]
        pass2 = pass_map[2]
        same_messages = pass1.get("messages") == pass2.get("messages")
        same_candidates = pass1.get("candidate_tools") == pass2.get("candidate_tools")
        anti_leakage_passed = not (same_messages and same_candidates)
        dataset.append(
            {
                "family_id": family_id,
                "signature_key": _signature_key(pass1),
                "source_pass1_id": _canonical_id(pass1),
                "source_pass2_id": _canonical_id(pass2),
                "pair_type": "exact_or_matched_signature",
                "pass1_compile": _stage_task(pass1, family_id=family_id, pass_index=1, stage="pass1_compile"),
                "pass2_eval": _stage_task(pass2, family_id=family_id, pass_index=2, stage="pass2_eval"),
                "anti_leakage": {
                    "same_messages": same_messages,
                    "same_candidate_tools": same_candidates,
                    "passed": anti_leakage_passed,
                },
                "manual_label_status": "auto_seeded_from_toolsandbox_reuse_persistent",
            }
        )
    return dataset, errors


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=True, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox persistent-reuse v1 dataset")
    parser.add_argument("--source", default="data/bench_slices/reuse_persistent.json")
    parser.add_argument("--out", default="data/toolsandbox_reuse_persistent_v1.jsonl")
    parser.add_argument("--manifest", default="data/toolsandbox_reuse_persistent_v1.manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    dataset, errors = _pair_rows(_load_json(source))
    out = Path(args.out)
    manifest_path = Path(args.manifest)
    _write_jsonl(out, dataset)
    manifest = {
        "dataset": str(out),
        "source": str(source),
        "source_commit": _git_commit(),
        "pair_rule": "group rows named {family}__pass1/2 from data/bench_slices/reuse_persistent.json",
        "signature_key": "sorted candidate tools plus normalized categories",
        "family_count": len(dataset),
        "row_count": len(dataset),
        "anti_leakage_passed": all(row["anti_leakage"]["passed"] for row in dataset),
        "statistical_claim_allowed": len(dataset) >= 20,
        "statistical_claim_note": (
            "family_count < 20; report effect sizes and paired CIs, not strong significance claims"
            if len(dataset) < 20
            else "family_count >= 20"
        ),
        "expansion_attempted": True,
        "expansion_added": 0,
        "expansion_note": "v1 uses the existing curated ToolSandbox reuse_persistent slice as the paper-safe source.",
        "errors": errors,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote: {out}")
    print(f"wrote: {manifest_path}")


if __name__ == "__main__":
    main()
