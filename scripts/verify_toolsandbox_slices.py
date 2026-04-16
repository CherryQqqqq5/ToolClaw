#!/usr/bin/env python3
"""Verify ToolSandbox derived slices for structural and protocol correctness."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from scripts.run_eval import build_workflow_from_task


def load_json(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must be a JSON list")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} contains non-object rows")
    return payload


def normalize_sender(value: Any) -> str:
    return str(value or "").strip().lower()


def require(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def first_non_system_sender(messages: Sequence[Dict[str, Any]]) -> str:
    for message in messages:
        sender = normalize_sender(message.get("sender"))
        if sender != "system":
            return sender
    return ""


def validate_common(slice_name: str, rows: Sequence[Dict[str, Any]], errors: List[str]) -> None:
    names = [str(row.get("name", "")) for row in rows]
    require(all(name for name in names), f"{slice_name}: empty name found", errors)
    require(len(set(names)) == len(names), f"{slice_name}: duplicate task names detected", errors)

    for row in rows:
        name = str(row.get("name", ""))
        messages = row.get("messages", [])
        require(isinstance(messages, list) and len(messages) > 0, f"{slice_name}:{name}: messages must be non-empty list", errors)
        if isinstance(messages, list) and messages:
            require(
                first_non_system_sender(messages) == "user",
                f"{slice_name}:{name}: first non-system sender must be user",
                errors,
            )
        allow = row.get("tool_allow_list", [])
        cand = row.get("candidate_tools", [])
        require(isinstance(allow, list), f"{slice_name}:{name}: tool_allow_list must be list", errors)
        require(isinstance(cand, list), f"{slice_name}:{name}: candidate_tools must be list", errors)
        if isinstance(allow, list) and isinstance(cand, list):
            missing = [tool for tool in allow if tool not in cand]
            require(not missing, f"{slice_name}:{name}: tool_allow_list not subset of candidate_tools: {missing}", errors)
        milestones = row.get("milestones", [])
        require(isinstance(milestones, list) and len(milestones) > 0, f"{slice_name}:{name}: milestones must be non-empty list", errors)
        ref = row.get("reference_result_summary")
        require(isinstance(ref, dict) and bool(ref), f"{slice_name}:{name}: reference_result_summary must be non-empty dict", errors)
        metadata = row.get("metadata", {})
        require(isinstance(metadata, dict), f"{slice_name}:{name}: metadata must be dict", errors)
        if isinstance(metadata, dict):
            require(bool(metadata.get("source")), f"{slice_name}:{name}: metadata.source missing", errors)


def validate_interaction_live(rows: Sequence[Dict[str, Any]], errors: List[str]) -> None:
    for row in rows:
        name = str(row.get("name", ""))
        messages = row.get("messages", [])
        if not isinstance(messages, list) or not messages:
            continue
        first_user = None
        for idx, message in enumerate(messages):
            if normalize_sender(message.get("sender")) == "user":
                first_user = idx
                break
        require(first_user is not None, f"interaction_live:{name}: no user message", errors)
        if first_user is not None:
            trailing = messages[first_user + 1 :]
            require(len(trailing) == 0, f"interaction_live:{name}: stripped messages still contain post-user turns", errors)
        oracle = row.get("oracle_user_replies")
        require(isinstance(oracle, list) and len(oracle) > 0, f"interaction_live:{name}: oracle_user_replies missing/empty", errors)
        sp = row.get("simulated_policy")
        require(isinstance(sp, dict), f"interaction_live:{name}: simulated_policy missing", errors)
        if isinstance(sp, dict):
            require(bool(sp.get("mode")), f"interaction_live:{name}: simulated_policy.mode missing", errors)
            mav = sp.get("missing_arg_values", {})
            if isinstance(mav, dict):
                leakage_keys = {"content", "message_content", "reminder_content", "timestamp", "reminder_timestamp", "time", "location"}
                leaked = sorted(k for k in mav.keys() if str(k) in leakage_keys)
                require(not leaked, f"interaction_live:{name}: potential answer leakage keys in missing_arg_values: {leaked}", errors)


PASS_RE = re.compile(r"^(?P<family>.+)__pass(?P<idx>[12])$")


def validate_reuse(rows: Sequence[Dict[str, Any]], errors: List[str]) -> None:
    family_to_pass: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for row in rows:
        name = str(row.get("name", ""))
        match = PASS_RE.match(name)
        require(match is not None, f"reuse_persistent:{name}: name must follow {{family}}__pass1/2", errors)
        if match is None:
            continue
        family = str(match.group("family"))
        idx = int(match.group("idx"))
        family_to_pass.setdefault(family, {})[idx] = row
    for family, pass_map in family_to_pass.items():
        require(1 in pass_map and 2 in pass_map, f"reuse_persistent:{family}: missing pass1 or pass2", errors)
        if 1 in pass_map and 2 in pass_map:
            a = pass_map[1]
            b = pass_map[2]
            same_messages = a.get("messages") == b.get("messages")
            same_candidates = a.get("candidate_tools") == b.get("candidate_tools")
            require(not (same_messages and same_candidates), f"reuse_persistent:{family}: pass1/pass2 appear identical", errors)


def validate_noisy_stress(rows: Sequence[Dict[str, Any]], errors: List[str]) -> None:
    for row in rows:
        name = str(row.get("name", ""))
        require(bool(row.get("has_ground_truth_messages")), f"noisy_stress:{name}: has_ground_truth_messages not true", errors)
        require(bool(row.get("has_ground_truth_milestones")), f"noisy_stress:{name}: has_ground_truth_milestones not true", errors)
        require(bool(row.get("has_ground_truth_tools")), f"noisy_stress:{name}: has_ground_truth_tools not true", errors)
        summary = row.get("result_summary", {})
        require(isinstance(summary, dict) and bool(summary.get("success")), f"noisy_stress:{name}: result_summary.success must be true", errors)


def _workflow_signature(task: Dict[str, Any]) -> Tuple[int, Tuple[str, ...], Tuple[str, ...]]:
    workflow = build_workflow_from_task(task, mode="planner")
    steps = tuple(str(step.tool_id or "") for step in workflow.execution_plan)
    candidates = []
    for node in workflow.workflow_graph.nodes:
        candidates.extend([str(t) for t in node.tool_candidates])
    return len(workflow.execution_plan), steps, tuple(candidates)


def validate_skill_effective(main_rows: Sequence[Dict[str, Any]], skill_rows: Sequence[Dict[str, Any]], errors: List[str]) -> None:
    by_name_main = {str(row.get("name", "")): row for row in main_rows}
    by_name_skill = {str(row.get("name", "")): row for row in skill_rows}
    common = sorted(set(by_name_main).intersection(by_name_skill))
    require(bool(common), "skill_distractor: no overlap with main_clean for diagnostics", errors)
    if not common:
        return

    pool_sizes = [len(row.get("candidate_tools", []) or []) for row in skill_rows]
    base_sizes = [len(row.get("candidate_tools", []) or []) for row in main_rows if str(row.get("name", "")) in by_name_skill]
    require(mean(pool_sizes) > mean(base_sizes), "skill_distractor: candidate_tools did not expand on average", errors)
    # skill_distractor protocol: keep allow list unchanged from main_clean.
    for name in common:
        main_allow = by_name_main[name].get("tool_allow_list", []) or []
        skill_allow = by_name_skill[name].get("tool_allow_list", []) or []
        require(main_allow == skill_allow, f"skill_distractor:{name}: tool_allow_list changed; should remain identical to main_clean", errors)

    changed = 0
    # Check first up to 20 overlapping tasks.
    for name in common[:20]:
        m = by_name_main[name]
        s = by_name_skill[name]
        sig_m = _workflow_signature(m)
        sig_s = _workflow_signature(s)
        if sig_m != sig_s:
            changed += 1
    # Keep this as a warning-like soft check by printing only.
    if changed == 0:
        print("warning: skill_distractor diagnostics found no workflow signature change in first 20 tasks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify derived ToolSandbox slices")
    parser.add_argument("--slices-dir", default="data/bench_slices", help="Directory containing generated slice JSON files")
    args = parser.parse_args()

    slices_dir = Path(args.slices_dir)
    expected = {
        "main_clean": slices_dir / "main_clean.json",
        "skill_distractor": slices_dir / "skill_distractor.json",
        "interaction_live": slices_dir / "interaction_live.json",
        "reuse_persistent": slices_dir / "reuse_persistent.json",
        "noisy_stress": slices_dir / "noisy_stress.json",
    }

    errors: List[str] = []
    loaded: Dict[str, List[Dict[str, Any]]] = {}
    for name, path in expected.items():
        require(path.exists(), f"missing slice file: {path}", errors)
        if path.exists():
            loaded[name] = load_json(path)

    for name, rows in loaded.items():
        validate_common(name, rows, errors)

    if "interaction_live" in loaded:
        validate_interaction_live(loaded["interaction_live"], errors)
    if "reuse_persistent" in loaded:
        validate_reuse(loaded["reuse_persistent"], errors)
    if "noisy_stress" in loaded:
        validate_noisy_stress(loaded["noisy_stress"], errors)
    if "main_clean" in loaded and "skill_distractor" in loaded:
        validate_skill_effective(loaded["main_clean"], loaded["skill_distractor"], errors)

    for name, rows in loaded.items():
        print(f"{name}: {len(rows)}")

    if errors:
        print("verification failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("verification passed")


if __name__ == "__main__":
    main()

