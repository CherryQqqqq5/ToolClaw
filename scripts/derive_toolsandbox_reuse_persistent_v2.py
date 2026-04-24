#!/usr/bin/env python3
"""Derive a stricter ToolSandbox persistent-reuse v2 paired dataset."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    except Exception:
        return ""


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _categories(row: Dict[str, Any]) -> List[str]:
    categories = row.get("pass2_eval", {}).get("categories") or []
    if not isinstance(categories, list):
        return []
    return [str(item).strip().lower().replace(" ", "_") for item in categories if str(item).strip()]


def _priority(row: Dict[str, Any]) -> tuple[int, str]:
    family_id = str(row.get("family_id") or "")
    categories = set(_categories(row))
    headroom_candidate = 0
    if "state_dependency" in categories:
        headroom_candidate -= 20
    if "multiple_user_turn" in categories or "insufficient_information" in categories:
        headroom_candidate -= 10
    if "canonicalization" in categories:
        headroom_candidate += 10
    if family_id.startswith("state_repair_permission__"):
        headroom_candidate -= 20
    return (headroom_candidate, family_id)


def _augment(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    categories = _categories(item)
    item["family_priority"] = {
        "headroom_candidate": "state_dependency" in categories or "multiple_user_turn" in categories or "insufficient_information" in categories,
        "category_tags": categories,
    }
    item["manual_label_status"] = "auto_seeded_v2_prioritized"
    return item


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox persistent-reuse v2 dataset")
    parser.add_argument("--source", default="data/toolsandbox_reuse_persistent_v1.jsonl")
    parser.add_argument("--out", default="data/toolsandbox_reuse_persistent_v2.jsonl")
    parser.add_argument("--manifest", default="data/toolsandbox_reuse_persistent_v2.manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    rows = [_augment(row) for row in _read_jsonl(source)]
    rows.sort(key=_priority)
    out = Path(args.out)
    manifest_path = Path(args.manifest)
    _write_jsonl(out, rows)
    manifest = {
        "dataset": str(out),
        "source": str(source),
        "source_commit": _git_commit(),
        "version": "toolsandbox_reuse_persistent_v2",
        "pair_rule": "inherits paired families from v1 and reorders families to prioritize cost-headroom candidates",
        "family_count": len(rows),
        "headroom_candidate_count": sum(1 for row in rows if row.get("family_priority", {}).get("headroom_candidate")),
        "statistical_claim_allowed": len(rows) >= 20,
        "statistical_claim_note": (
            "family_count < 20; report effect sizes and paired CIs, not strong significance claims"
            if len(rows) < 20
            else "family_count >= 20"
        ),
        "selection_policy": {
            "prioritize": [
                "state_dependency",
                "multiple_user_turn",
                "insufficient_information",
            ],
            "deprioritize": [
                "canonicalization",
            ],
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote: {out}")
    print(f"wrote: {manifest_path}")


if __name__ == "__main__":
    main()
