#!/usr/bin/env python3
"""Derive ToolSandbox mechanism-sensitive benchmark slices from frozen official data."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


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


def normalize_category(value: Any) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))


def load_samples(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"expected JSON list in {path}")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("all samples must be objects")
    return payload


def dump_samples(path: Path, samples: Sequence[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(list(samples), indent=2, ensure_ascii=False), encoding="utf-8")


def is_ground_truth_complete(sample: Dict[str, Any]) -> bool:
    return bool(sample.get("has_ground_truth_messages")) and bool(sample.get("has_ground_truth_milestones")) and bool(
        sample.get("has_ground_truth_tools")
    )


def strip_to_initial_observation(messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    first_user_idx = None
    for idx, message in enumerate(messages):
        if str(message.get("sender", "")).strip().lower() == "user":
            first_user_idx = idx
            break
    if first_user_idx is None:
        return list(messages), []
    kept = messages[: first_user_idx + 1]
    removed = messages[first_user_idx + 1 :]
    return kept, removed


PHONE_RE = re.compile(r"\+\d{6,}")
TIMESTAMP_RE = re.compile(r"^-?\d+(\.\d+)?$")


def infer_trigger(assistant_text: str) -> Tuple[str, str]:
    text = assistant_text.lower()
    if "approve" in text or "permission" in text:
        return "permission_query", "approved"
    if "low battery" in text:
        return "permission_query", "low_battery_mode"
    if "cellular" in text and "enable" in text:
        return "permission_query", "enable_cellular_service"
    if "wifi" in text and "enable" in text:
        return "permission_query", "enable_wifi"
    if "content" in text:
        return "missing_slot_query", "content"
    if "phone number" in text:
        return "missing_slot_query", "phone_number"
    if "time" in text or "date" in text:
        return "missing_slot_query", "time"
    return "user_reply", ""


def build_oracle_and_policy(removed: List[Dict[str, Any]], base_policy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    oracle_replies: List[Dict[str, Any]] = []
    missing_arg_values: Dict[str, Any] = dict(base_policy.get("missing_arg_values", {})) if isinstance(
        base_policy.get("missing_arg_values"), dict
    ) else {}
    approval_responses: Dict[str, Any] = dict(base_policy.get("approval_responses", {})) if isinstance(
        base_policy.get("approval_responses"), dict
    ) else {}
    tool_switch_hints: Dict[str, Any] = dict(base_policy.get("tool_switch_hints", {})) if isinstance(
        base_policy.get("tool_switch_hints"), dict
    ) else {}
    constraint_overrides: Dict[str, Any] = dict(base_policy.get("constraint_overrides", {})) if isinstance(
        base_policy.get("constraint_overrides"), dict
    ) else {}

    for idx, message in enumerate(removed):
        if str(message.get("sender", "")).strip().lower() != "user":
            continue
        user_reply = str(message.get("content", "") or "")
        prev_assistant = ""
        for j in range(idx - 1, -1, -1):
            if str(removed[j].get("sender", "")).strip().lower() == "assistant":
                prev_assistant = str(removed[j].get("content", "") or "")
                break
        trigger_type, slot = infer_trigger(prev_assistant)
        oracle_replies.append({"trigger_type": trigger_type, "slot": slot or None, "reply": user_reply})

        lower = user_reply.lower()
        if "yes" in lower or "yeah" in lower or "go ahead" in lower:
            constraint_overrides.setdefault("approved", True)
            missing_arg_values.setdefault("approved", True)
        if "no" in lower and "know" not in lower:
            constraint_overrides.setdefault("approved", False)
            missing_arg_values.setdefault("approved", False)

        phone_match = PHONE_RE.search(user_reply)
        if phone_match:
            missing_arg_values.setdefault("phone_number", phone_match.group(0))
            missing_arg_values.setdefault("recipient_phone_number", phone_match.group(0))

        if user_reply.strip():
            missing_arg_values.setdefault("content", user_reply.strip())
            missing_arg_values.setdefault("message_content", user_reply.strip())
            missing_arg_values.setdefault("reminder_content", user_reply.strip())

    for message in removed:
        if str(message.get("sender", "")).strip().lower() != "tool":
            continue
        raw = str(message.get("content", "") or "").strip()
        if TIMESTAMP_RE.fullmatch(raw):
            value: Any = float(raw) if "." in raw else int(raw)
            missing_arg_values.setdefault("timestamp", value)
            missing_arg_values.setdefault("reminder_timestamp", value)

    if any("cellular" in str(item.get("slot") or "") for item in oracle_replies):
        tool_switch_hints.setdefault("tool_id", "set_cellular_service_status")
        constraint_overrides.setdefault("enabled", True)
    if any("wifi" in str(item.get("slot") or "") for item in oracle_replies):
        tool_switch_hints.setdefault("tool_id", "set_wifi_status")
        constraint_overrides.setdefault("enabled", True)
    if any("low_battery_mode" in str(item.get("slot") or "") for item in oracle_replies):
        tool_switch_hints.setdefault("tool_id", "set_low_battery_mode_status")
        missing_arg_values.setdefault("enabled", False)

    policy = dict(base_policy)
    policy["mode"] = str(policy.get("mode") or "cooperative")
    policy["missing_arg_values"] = missing_arg_values
    policy["approval_responses"] = approval_responses
    policy["tool_switch_hints"] = tool_switch_hints
    policy["constraint_overrides"] = constraint_overrides
    return oracle_replies, policy


def build_interaction_live(sample: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(sample)
    messages = list(out.get("messages", []))
    kept, removed = strip_to_initial_observation(messages)
    out["messages"] = kept
    base_policy = dict(out.get("simulated_policy", {})) if isinstance(out.get("simulated_policy"), dict) else {"mode": "cooperative"}
    oracle, policy = build_oracle_and_policy(removed, base_policy)
    out["oracle_user_replies"] = oracle
    out["simulated_policy"] = policy
    return out


def build_reuse_pairs(source: Sequence[Dict[str, Any]], max_pairs_per_group: int) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {
        "reminder_date_time": [s for s in source if str(s.get("name", "")).startswith("add_reminder_content_and_date_and_time")],
        "reminder_week_time_location": [s for s in source if "add_reminder_content_and_week_delta_and_time_and_location" in str(s.get("name", ""))],
        "state_repair_permission": [s for s in source if str(s.get("name", "")).startswith("turn_on_") and "low_battery_mode" in str(s.get("name", ""))],
        "holiday_time": [s for s in source if str(s.get("name", "")).startswith("find_days_till_holiday")],
        "contact_edit": [s for s in source if str(s.get("name", "")).startswith("remove_contact_by_phone") or str(s.get("name", "")).startswith("modify_contact")],
    }
    out_pass1: List[Dict[str, Any]] = []
    out_pass2: List[Dict[str, Any]] = []
    for group_name, tasks in sorted(groups.items()):
        tasks_sorted = sorted(tasks, key=lambda item: str(item.get("name", "")))
        if len(tasks_sorted) < 2:
            continue
        pair_count = 0
        i = 0
        while i + 1 < len(tasks_sorted) and pair_count < max_pairs_per_group:
            warmup = tasks_sorted[i]
            eval_task = tasks_sorted[i + 1]
            if str(warmup.get("name", "")) == str(eval_task.get("name", "")):
                i += 1
                continue
            family_id = f"{group_name}__pair{pair_count:02d}"
            pass1 = copy.deepcopy(warmup)
            pass2 = copy.deepcopy(eval_task)
            pass1["name"] = f"{family_id}__pass1"
            pass2["name"] = f"{family_id}__pass2"
            pass1["reuse_family_id"] = family_id
            pass2["reuse_family_id"] = family_id
            pass1["reuse_pass_index"] = 1
            pass2["reuse_pass_index"] = 2
            pass1.setdefault("metadata", {})
            pass2.setdefault("metadata", {})
            if isinstance(pass1["metadata"], dict):
                pass1["metadata"]["reuse_family_id"] = family_id
                pass1["metadata"]["reuse_pass_index"] = 1
                pass1["metadata"]["base_sample_name"] = warmup.get("name")
            if isinstance(pass2["metadata"], dict):
                pass2["metadata"]["reuse_family_id"] = family_id
                pass2["metadata"]["reuse_pass_index"] = 2
                pass2["metadata"]["base_sample_name"] = eval_task.get("name")
            out_pass1.append(pass1)
            out_pass2.append(pass2)
            pair_count += 1
            i += 2
    return out_pass1 + out_pass2


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox benchmark slices")
    parser.add_argument("--in", dest="in_path", default="data/toolsandbox.formal.official.json", help="Input frozen dataset")
    parser.add_argument("--outdir", default="data/bench_slices", help="Output directory")
    parser.add_argument(
        "--interaction-strip-mode",
        choices=["oracle_remove_all_after_first_user", "keep_until_first_assistant_tool"],
        default="oracle_remove_all_after_first_user",
    )
    parser.add_argument("--interaction-oracle-sidecar", nargs="+", default=["oracle_user_replies", "simulated_policy_fill"])
    parser.add_argument("--noisy-bottom-quantile", type=float, default=0.2)
    parser.add_argument("--max-main-clean-count", type=int, default=None)
    parser.add_argument("--max-pairs-per-reuse-group", type=int, default=2)
    args = parser.parse_args()

    in_path = Path(args.in_path)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    frozen = load_samples(in_path)
    normalized_categories: Dict[str, List[str]] = {
        str(s.get("name", "")): [normalize_category(c) for c in (s.get("categories") or []) if normalize_category(c)]
        for s in frozen
    }

    # Main clean: exclude multi-turn + insufficient-information + bottom-quantile similarity + incomplete ground truth.
    sims = sorted(float(s.get("official_similarity", 0.0) or 0.0) for s in frozen)
    bottom_idx = max(0, int(math.floor(len(sims) * args.noisy_bottom_quantile)) - 1)
    bottom_threshold = sims[bottom_idx] if sims else -1.0

    main_clean: List[Dict[str, Any]] = []
    for sample in frozen:
        name = str(sample.get("name", ""))
        cats = set(normalized_categories.get(name, []))
        if not cats:
            continue
        if "multiple_user_turn" in cats or "insufficient_information" in cats:
            continue
        if not is_ground_truth_complete(sample):
            continue
        similarity = float(sample.get("official_similarity", 0.0) or 0.0)
        if similarity <= bottom_threshold:
            continue
        if not ({"single_user_turn", "state_dependency", "single_tool", "canonicalization", "multiple_tool"} & cats):
            continue
        main_clean.append(copy.deepcopy(sample))
    main_clean.sort(key=lambda s: str(s.get("name", "")))
    if args.max_main_clean_count is not None:
        main_clean = main_clean[: args.max_main_clean_count]

    # Skill distractor from main_clean with expanded candidate pool and expanded allow list.
    # Reason: planner path filters by tool_allow_list first; candidate_tools-only expansion
    # may be inert for actual binding/selection behavior.
    pool: List[str] = []
    for sample in main_clean:
        for tool in sample.get("candidate_tools", []) or []:
            if tool not in pool:
                pool.append(tool)
    skill_distractor: List[Dict[str, Any]] = []
    for sample in main_clean:
        out = copy.deepcopy(sample)
        out["candidate_tools"] = list(pool)
        out["tool_allow_list"] = list(pool)
        skill_distractor.append(out)
    skill_distractor.sort(key=lambda s: str(s.get("name", "")))

    # Interaction live.
    interaction_src = []
    for sample in frozen:
        name = str(sample.get("name", ""))
        cats = set(normalized_categories.get(name, []))
        if "multiple_user_turn" in cats or "insufficient_information" in cats:
            interaction_src.append(sample)
    interaction_live = [build_interaction_live(sample) for sample in sorted(interaction_src, key=lambda s: str(s.get("name", "")))]

    # Reuse persistent pairs.
    reuse_persistent = build_reuse_pairs(frozen, args.max_pairs_per_reuse_group)

    # Noisy stress: success + low similarity + complete ground truth + exclude protocol-dependent slices.
    noisy_candidates = []
    for sample in frozen:
        name = str(sample.get("name", ""))
        cats = set(normalized_categories.get(name, []))
        if "multiple_user_turn" in cats or "insufficient_information" in cats:
            continue
        if not is_ground_truth_complete(sample):
            continue
        summary = sample.get("result_summary", {})
        if not (isinstance(summary, dict) and bool(summary.get("success"))):
            continue
        noisy_candidates.append(sample)
    noisy_candidates = sorted(noisy_candidates, key=lambda s: float(s.get("official_similarity", 0.0) or 0.0))
    noisy_count = max(1, int(math.floor(len(noisy_candidates) * args.noisy_bottom_quantile))) if noisy_candidates else 0
    noisy_stress = [copy.deepcopy(s) for s in noisy_candidates[:noisy_count]]

    dump_samples(outdir / "main_clean.json", main_clean)
    dump_samples(outdir / "skill_distractor.json", skill_distractor)
    dump_samples(outdir / "interaction_live.json", interaction_live)
    dump_samples(outdir / "reuse_persistent.json", reuse_persistent)
    dump_samples(outdir / "noisy_stress.json", noisy_stress)

    print(f"input={in_path} total={len(frozen)}")
    print(f"main_clean={len(main_clean)}")
    print(f"skill_distractor={len(skill_distractor)}")
    print(f"interaction_live={len(interaction_live)}")
    print(f"reuse_persistent={len(reuse_persistent)}")
    print(f"noisy_stress={len(noisy_stress)}")


if __name__ == "__main__":
    main()

