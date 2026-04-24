#!/usr/bin/env python3
"""Derive a small Tau2 dual-control family bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]


NON_INTERACTIVE_IDS = {
    "tau2_binding_auto_001",
    "tau2_state_stale_slot_001",
    "tau2_state_checkpoint_resume_001",
    "tau2_state_wrong_write_target_001",
}

MUST_INTERACT_IDS = {
    "tau2_approval_gate_001",
    "tau2_dual_control_001",
    "tau2_interaction_failure_001",
    "tau2_policy_abort_001",
}

COMPOUND_IDS = {
    "tau2_binding_plus_approval_001",
}


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    except Exception:
        return ""


def _read_json(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected list in {path}")
    return [row for row in payload if isinstance(row, dict)]


def _annotate(row: Dict[str, Any], *, family_slice: str, source_file: str) -> Dict[str, Any]:
    item = dict(row)
    item["family_slice"] = family_slice
    item["source_file"] = source_file
    metadata = dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {}
    metadata.update(
        {
            "tau2_dual_control_family_v1": True,
            "family_slice": family_slice,
            "source_file": source_file,
        }
    )
    item["metadata"] = metadata
    return item


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive tau2 dual-control family v1 dataset")
    parser.add_argument("--formal-source", default="data/tau2_bench.formal.json")
    parser.add_argument("--approval-source", default="data/tau2_bench.approval_only.json")
    parser.add_argument("--binding-approval-source", default="data/tau2_bench.binding_plus_approval_only.json")
    parser.add_argument("--out", default="data/tau2_dual_control_family_v1.json")
    parser.add_argument("--manifest", default="data/tau2_dual_control_family_v1.manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for source_path in (Path(args.formal_source), Path(args.approval_source), Path(args.binding_approval_source)):
        source_rows = _read_json(source_path)
        for row in source_rows:
            sample_id = str(row.get("sample_id") or "")
            if not sample_id or sample_id in seen:
                continue
            if sample_id in NON_INTERACTIVE_IDS:
                rows.append(_annotate(row, family_slice="non_interactive_solvable", source_file=str(source_path)))
                seen.add(sample_id)
            elif sample_id in MUST_INTERACT_IDS:
                rows.append(_annotate(row, family_slice="must_interact_approval", source_file=str(source_path)))
                seen.add(sample_id)
            elif sample_id in COMPOUND_IDS:
                rows.append(_annotate(row, family_slice="compound_approval_plus_repair", source_file=str(source_path)))
                seen.add(sample_id)

    out = Path(args.out)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    manifest = {
        "dataset": str(out),
        "source_commit": _git_commit(),
        "family_counts": {
            "non_interactive_solvable": sum(1 for row in rows if row.get("family_slice") == "non_interactive_solvable"),
            "must_interact_approval": sum(1 for row in rows if row.get("family_slice") == "must_interact_approval"),
            "compound_approval_plus_repair": sum(1 for row in rows if row.get("family_slice") == "compound_approval_plus_repair"),
        },
        "boundary_note": "compound slice is still sparse; use as boundary/supporting evidence, not headline",
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote: {out}")
    print(f"wrote: {args.manifest}")


if __name__ == "__main__":
    main()
