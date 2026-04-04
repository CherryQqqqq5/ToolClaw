#!/usr/bin/env python3
"""Build a fixed ToolSandbox formal dataset JSON directly from an official ToolSandbox run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from prepare_toolsandbox_official_run import (
    DEFAULT_DATA_ROOT,
    iter_aligned_rows,
    load_result_summary,
    resolve_run_dir,
)

DISPLAY_CATEGORY_NAMES = {
    "single_tool": "Single Tool",
    "multiple_tool": "Multiple Tool Call",
    "single_user_turn": "Single User Turn",
    "multiple_user_turn": "Multiple User Turn",
    "state_dependency": "State Dependency",
    "canonicalization": "Canonicalization",
    "insufficient_information": "Insufficient Information",
    "three_distraction_tools": "Three Distraction Tools",
    "ten_distraction_tools": "Ten Distraction Tools",
    "all_tools_available": "All Tools Available",
    "tool_description_scrambled": "Tool Description Scrambled",
    "tool_name_scrambled": "Tool Name Scrambled",
    "arg_description_scrambled": "Arg Description Scrambled",
    "arg_type_scrambled": "Arg Type Scrambled",
    "arg_name_scrambled": "Arg Name Scrambled",
    "no_distraction_tools": "No Distraction Tools",
}
AUGMENTATION_MARKERS = (
    "3_distraction_tools",
    "10_distraction_tools",
    "all_tools",
    "tool_description_scrambled",
    "tool_name_scrambled",
    "arg_description_scrambled",
    "arg_type_scrambled",
    "arg_name_scrambled",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a ToolClaw formal ToolSandbox dataset from an official ToolSandbox run")
    parser.add_argument(
        "--official-run-dir",
        default="latest",
        help="Official ToolSandbox run directory, or 'latest' to auto-discover under the data root",
    )
    parser.add_argument(
        "--official-data-root",
        default=str(DEFAULT_DATA_ROOT),
        help="Root directory containing official ToolSandbox run directories",
    )
    parser.add_argument(
        "--out",
        default="data/toolsandbox.formal.official.json",
        help="Output JSON path for the formal dataset",
    )
    parser.add_argument(
        "--exclude-augmented",
        action="store_true",
        help="Exclude distraction/scrambled-tool augmentations to form a cleaner core benchmark set",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples after sorting and filtering")
    return parser.parse_args()


def to_display_category(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    normalized = str(raw_value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split()).replace(" ", "_")
    return DISPLAY_CATEGORY_NAMES.get(normalized, str(raw_value))


def is_augmented(row: Dict[str, Any]) -> bool:
    name = str(row.get("sample_id") or "")
    if any(marker in name for marker in AUGMENTATION_MARKERS):
        return True
    for category in row.get("categories", []):
        normalized = str(category).strip().lower().replace("-", " ").replace("_", " ")
        normalized = " ".join(normalized.split()).replace(" ", "_")
        if normalized in DISPLAY_CATEGORY_NAMES and normalized not in {
            "single_tool",
            "multiple_tool",
            "single_user_turn",
            "multiple_user_turn",
            "state_dependency",
            "canonicalization",
            "insufficient_information",
            "no_distraction_tools",
        }:
            return True
    return False


def infer_execution_scenario(row: Dict[str, Any]) -> str | None:
    categories = {str(category).strip().lower().replace("-", " ").replace("_", " ") for category in row.get("categories", [])}
    if "insufficient information" in categories:
        return "environment_failure"
    return None


def infer_simulated_policy(row: Dict[str, Any]) -> Dict[str, Any] | None:
    categories = {str(category).strip().lower().replace("-", " ").replace("_", " ") for category in row.get("categories", [])}
    if "multiple user turn" in categories or "insufficient information" in categories:
        return {"mode": "cooperative"}
    return None


def aligned_row_to_formal_record(row: Dict[str, Any]) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "name": row["sample_id"],
        "query": row.get("query") or row["sample_id"],
        "messages": list(row.get("messages", [])),
        "tool_allow_list": list(row.get("tool_allow_list", [])),
        "candidate_tools": list(row.get("candidate_tools", [])),
        "categories": [to_display_category(category) for category in row.get("categories", [])],
        "milestones": list(row.get("milestones", [])),
        "ideal_turn_count": row.get("ideal_turn_count"),
        "ideal_tool_calls": row.get("ideal_tool_calls"),
        "result_summary": dict(row.get("result_summary", {})),
        "metadata": dict(row.get("metadata", {})),
    }
    execution_scenario = infer_execution_scenario(row)
    if execution_scenario is not None:
        record["execution_scenario"] = execution_scenario
    simulated_policy = infer_simulated_policy(row)
    if simulated_policy is not None:
        record["simulated_policy"] = simulated_policy
    return record


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args.official_run_dir, Path(args.official_data_root))
    result_summary = load_result_summary(run_dir)
    rows = list(iter_aligned_rows(run_dir, result_summary))
    if args.exclude_augmented:
        rows = [row for row in rows if not is_augmented(row)]
    rows.sort(key=lambda row: str(row.get("sample_id") or ""))
    if args.limit is not None:
        rows = rows[: args.limit]
    if not rows:
        raise RuntimeError("no ToolSandbox rows available after filtering")
    records = [aligned_row_to_formal_record(row) for row in rows]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"official ToolSandbox run: {run_dir}")
    print(f"wrote formal dataset: {out_path}")
    print(f"total samples: {len(records)}")


if __name__ == "__main__":
    main()
