#!/usr/bin/env python3
"""Derive ToolSandbox planner-sensitive benchmark data."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List


FAMILIES = {
    "retrieve_summarize_write": {
        "order": ["cap_retrieve", "cap_summarize", "cap_write"],
        "edges": [["cap_retrieve", "cap_summarize"], ["cap_summarize", "cap_write"]],
        "tools": [
            ("source_lookup", "Retrieve relevant source records before composing an answer.", ["retrieve", "source"]),
            ("summary_builder", "Summarize retrieved records into a concise synthesis.", ["summarize"]),
            ("report_writer", "Write the final summarized report to the target artifact.", ["write", "report"]),
            ("preference_toggler", "Distractor that updates a user preference state.", ["state", "distractor"]),
            ("message_sender", "Distractor that sends a notification message.", ["message", "distractor"]),
        ],
        "expected_tools": ["source_lookup", "summary_builder", "report_writer"],
        "required": {"cap_summarize": ["cap_retrieve"], "cap_write": ["cap_summarize"]},
        "query": "Retrieve the project notes for {topic}, summarize the risk items, then write the summary to {target}.",
    },
    "check_modify_verify": {
        "order": ["cap_check", "cap_modify", "cap_verify"],
        "edges": [["cap_check", "cap_modify"], ["cap_modify", "cap_verify"]],
        "tools": [
            ("state_checker", "Check current configuration and detect whether a change is required.", ["check", "state"]),
            ("state_modifier", "Modify the configuration after the check determines the target patch.", ["modify", "patch"]),
            ("change_verifier", "Verify the modified configuration satisfies the requested condition.", ["verify"]),
            ("archive_reader", "Distractor that reads archived information.", ["retrieve", "distractor"]),
            ("brief_writer", "Distractor that writes a human-readable brief.", ["write", "distractor"]),
        ],
        "expected_tools": ["state_checker", "state_modifier", "change_verifier"],
        "required": {"cap_modify": ["cap_check"], "cap_verify": ["cap_modify"]},
        "query": "Check whether {topic} is misconfigured, modify only the failing setting, and verify the final state.",
    },
    "branch_select_execute": {
        "order": ["cap_retrieve", "cap_select", "cap_modify", "cap_verify"],
        "edges": [["cap_retrieve", "cap_select"], ["cap_select", "cap_modify"], ["cap_modify", "cap_verify"]],
        "tools": [
            ("context_retriever", "Retrieve the latest state needed before choosing a branch.", ["retrieve", "context"]),
            ("branch_selector", "Select the correct branch based on retrieved state.", ["branch", "select"]),
            ("branch_executor", "Execute the selected branch-specific change.", ["modify", "execute"]),
            ("result_verifier", "Verify the branch execution produced the requested result.", ["verify"]),
            ("summary_builder", "Distractor that summarizes text but cannot execute branches.", ["summarize", "distractor"]),
        ],
        "expected_tools": ["context_retriever", "branch_selector", "branch_executor", "result_verifier"],
        "required": {"cap_select": ["cap_retrieve"], "cap_modify": ["cap_select"], "cap_verify": ["cap_modify"]},
        "query": "Inspect {topic}, select the matching branch, execute that branch, and verify the outcome.",
    },
    "multi_source_merge_write": {
        "order": ["cap_retrieve", "cap_merge", "cap_write"],
        "edges": [["cap_retrieve", "cap_merge"], ["cap_merge", "cap_write"]],
        "tools": [
            ("primary_source_fetcher", "Retrieve the primary source needed for the merge.", ["retrieve", "source"]),
            ("secondary_source_fetcher", "Retrieve secondary evidence for the merge.", ["retrieve", "source"]),
            ("source_merger", "Merge multiple retrieved sources into one synthesized state.", ["merge", "synthesize"]),
            ("merged_report_writer", "Write the merged source synthesis to the target artifact.", ["write", "report"]),
            ("state_modifier", "Distractor that modifies application state without merging sources.", ["modify", "distractor"]),
        ],
        "expected_tools": ["primary_source_fetcher", "secondary_source_fetcher", "source_merger", "merged_report_writer"],
        "required": {"cap_merge": ["cap_retrieve"], "cap_write": ["cap_merge"]},
        "query": "Collect primary and secondary evidence for {topic}, merge the evidence, and write the merged report to {target}.",
    },
}


TOPICS = [
    "billing",
    "calendar",
    "travel",
    "device",
    "contacts",
    "messages",
    "inventory",
    "support",
    "security",
    "compliance",
    "onboarding",
    "renewals",
]


VERSION_FAMILY_COUNTS = {
    "v1": {family: 6 for family in FAMILIES},
    "v2": {
        "retrieve_summarize_write": 9,
        "check_modify_verify": 11,
        "branch_select_execute": 11,
        "multi_source_merge_write": 11,
    },
}


def tool_specs(raw_tools: List[tuple[str, str, List[str]]]) -> List[Dict[str, Any]]:
    return [
        {
            "tool_id": tool_id,
            "description": description,
            "semantic_tags": tags,
        }
        for tool_id, description, tags in raw_tools
    ]


def make_row(family: str, index: int, *, version: str) -> Dict[str, Any]:
    spec = FAMILIES[family]
    topic = TOPICS[index % len(TOPICS)]
    target = f"outputs/planner_sensitive/{family}_{index + 1:02d}.txt"
    protocol = f"planner_sensitive_{version}"
    rng = random.Random(f"{family}:{index}:{protocol}")
    candidates = tool_specs(spec["tools"])
    rng.shuffle(candidates)
    task_id = f"planner_sensitive_{family}_{index + 1:02d}"
    return {
        "task_id": task_id,
        "family": family,
        "task_family": family,
        "slice_type": "planner_sensitive_primary",
        "planner_sensitive_protocol": protocol,
        "planner_visible": {
            "query": spec["query"].format(topic=topic, target=target),
            "target_path": target,
            "messages": [
                {
                    "sender": "user",
                    "recipient": "agent",
                    "content": spec["query"].format(topic=topic, target=target),
                }
            ],
            "candidate_tools": candidates,
            "categories": ["planner_sensitive", "multiple_tool", "state_dependency"],
            "constraints": {
                "max_tool_calls": max(len(spec["expected_tools"]) + 2, 5),
                "max_user_turns": 1,
                "max_repair_attempts": 1,
            },
            "ideal_turn_count": 1,
            "metadata": {
                "planner_sensitive_public_family": family,
                "tool_execution_backend": "semantic_mock",
            },
        },
        "scorer_gold": {
            "expected_capability_order": list(spec["order"]),
            "expected_dependency_edges": list(spec["edges"]),
            "expected_tool_sequence": list(spec["expected_tools"]),
            "required_state_slots_by_step": dict(spec["required"]),
            "forbidden_shortcuts": [
                "single_tool_fast_path",
                "milestone_order_hint",
                "ideal_tool_calls_one",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox planner-sensitive data")
    parser.add_argument("--version", choices=["v1", "v2"], default="v1")
    parser.add_argument("--out", default=None)
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()
    protocol = f"planner_sensitive_{args.version}"
    dataset = f"toolsandbox_planner_sensitive_{args.version}"
    out = args.out or f"data/{dataset}.jsonl"
    manifest_out = args.manifest or f"data/{dataset}.manifest.json"

    rows: List[Dict[str, Any]] = []
    family_counts = VERSION_FAMILY_COUNTS[args.version]
    for family, count in family_counts.items():
        for index in range(count):
            rows.append(make_row(family, index, version=args.version))

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    manifest = {
        "dataset": dataset,
        "protocol": protocol,
        "source": "synthetic planner-sensitive protocol derived from ToolSandbox adapter semantics",
        "sample_count": len(rows),
        "family_counts": family_counts,
        "planner_visible_keys": ["query", "target_path", "messages", "candidate_tools", "categories", "constraints", "ideal_turn_count", "metadata"],
        "scorer_gold_keys": [
            "expected_capability_order",
            "expected_dependency_edges",
            "expected_tool_sequence",
            "required_state_slots_by_step",
            "forbidden_shortcuts",
        ],
        "anti_leakage_policy": {
            "scorer_gold_not_planner_visible": True,
            "no_single_tool_primary_samples": True,
            "no_ideal_tool_calls_one": True,
            "milestones_hidden_from_planner": True,
            "candidate_tools_shuffled": True,
            "distractor_tools_per_task": True,
        },
        "paper_claim_policy": "planner structural mechanism remains pending; v2 may become mechanism supporting/candidate only if all formal gates pass",
    }
    if args.version == "v2":
        manifest["promotion_gates"] = {
            "source_task_count_ge_40": True,
            "family_positive_count_ge_3": True,
            "planner_bypass_known_rate_ge_0_90": True,
            "known_row_planner_bypass_rate_le_0_25": True,
            "ordered_gold_structure_leakage_detected": False,
            "retrieve_summarize_write_positive_win_cap": "25-30%",
        }
    manifest_path = Path(manifest_out)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote: {out_path}")
    print(f"wrote: {manifest_path}")


if __name__ == "__main__":
    main()
