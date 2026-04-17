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


APPROVE_RE = re.compile(r"\b(yes|yeah|yep|go ahead|please do|sure|ok)\b", re.I)
DENY_RE = re.compile(r"\b(no|don't|do not|stop)\b", re.I)


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


def build_oracle_and_policy(
    removed: List[Dict[str, Any]],
    base_policy: Dict[str, Any],
    *,
    enable_policy_fill: bool,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Build sidecar oracle and strict (non-leaky) simulated policy.

    IMPORTANT:
    - Never fill content/time/location slots from removed user replies.
    - Only fill approval-oriented and tool-switch hints when clearly implied.
    """
    oracle_replies: List[Dict[str, Any]] = []
    missing_arg_values: Dict[str, Any] = {}
    approval_responses: Dict[str, Any] = dict(base_policy.get("approval_responses", {})) if isinstance(
        base_policy.get("approval_responses"), dict
    ) else {}
    tool_switch_hints: Dict[str, Any] = {}
    constraint_overrides: Dict[str, Any] = {}

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

        if not enable_policy_fill:
            continue
        # Strict fill: only approval-like state; never content/time/location values.
        if trigger_type == "permission_query":
            if APPROVE_RE.search(user_reply):
                constraint_overrides.setdefault("approved", True)
                missing_arg_values.setdefault("approved", True)
            elif DENY_RE.search(user_reply):
                constraint_overrides.setdefault("approved", False)
                missing_arg_values.setdefault("approved", False)
            slot_text = str(slot or "").lower()
            if "cellular" in slot_text:
                tool_switch_hints.setdefault("tool_id", "set_cellular_service_status")
            if "wifi" in slot_text:
                tool_switch_hints.setdefault("tool_id", "set_wifi_status")
            if "low_battery_mode" in slot_text:
                tool_switch_hints.setdefault("tool_id", "set_low_battery_mode_status")

    policy = dict(base_policy)
    policy["mode"] = str(policy.get("mode") or "cooperative")
    if enable_policy_fill:
        policy["missing_arg_values"] = missing_arg_values
        policy["approval_responses"] = approval_responses
        policy["tool_switch_hints"] = tool_switch_hints
        policy["constraint_overrides"] = constraint_overrides
    else:
        policy.pop("missing_arg_values", None)
        policy.pop("approval_responses", None)
        policy.pop("tool_switch_hints", None)
        policy.pop("constraint_overrides", None)
    return oracle_replies, policy


def build_interaction_live(
    sample: Dict[str, Any],
    *,
    strip_mode: str,
    sidecar_flags: Sequence[str],
) -> Dict[str, Any]:
    out = copy.deepcopy(sample)
    messages = list(out.get("messages", []))
    kept, removed = strip_to_initial_observation(messages)
    if strip_mode == "keep_until_first_assistant_tool":
        # Keep first assistant/tool pair after initial user to preserve minimal execution context.
        first_user_idx = None
        for idx, message in enumerate(messages):
            if str(message.get("sender", "")).strip().lower() == "user":
                first_user_idx = idx
                break
        if first_user_idx is not None:
            end = first_user_idx + 1
            while end < len(messages):
                sender = str(messages[end].get("sender", "")).strip().lower()
                if sender in {"assistant", "tool"}:
                    end += 1
                    continue
                break
            kept = messages[:end]
            removed = messages[end:]
    out["messages"] = kept
    base_policy = dict(out.get("simulated_policy", {})) if isinstance(out.get("simulated_policy"), dict) else {"mode": "cooperative"}
    enable_policy_fill = "simulated_policy_fill" in set(sidecar_flags)
    oracle, policy = build_oracle_and_policy(removed, base_policy, enable_policy_fill=enable_policy_fill)
    if "oracle_user_replies" in set(sidecar_flags):
        out["oracle_user_replies"] = oracle
    else:
        out.pop("oracle_user_replies", None)
    out["simulated_policy"] = policy
    return out


def build_reuse_pairs(
    source: Sequence[Dict[str, Any]],
    normalized_categories: Dict[str, List[str]],
    max_pairs_per_group: int,
) -> List[Dict[str, Any]]:
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
        # Semantic pairing: prefer pass1 from clean single-turn tasks;
        # prefer pass2 from similar family but non-identical tasks, with _alt as eval if available.
        warmup_pool = []
        eval_pool = []
        for t in tasks_sorted:
            name = str(t.get("name", ""))
            cats = set(normalized_categories.get(name, []))
            is_multi = "multiple_user_turn" in cats or "insufficient_information" in cats
            if not is_multi:
                warmup_pool.append(t)
            if not is_multi and ("_alt" in name or "implicit" in name):
                eval_pool.append(t)
        if not warmup_pool:
            warmup_pool = [t for t in tasks_sorted if "multiple_user_turn" not in set(normalized_categories.get(str(t.get("name", "")), []))]
        if not eval_pool:
            eval_pool = [t for t in tasks_sorted if t not in warmup_pool[:1]] or list(tasks_sorted)

        pair_count = 0
        used_names = set()
        for warmup in warmup_pool:
            if pair_count >= max_pairs_per_group:
                break
            eval_task = None
            for candidate in eval_pool:
                if str(candidate.get("name", "")) == str(warmup.get("name", "")):
                    continue
                if str(candidate.get("name", "")) in used_names:
                    continue
                eval_task = candidate
                break
            if eval_task is None:
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
            used_names.add(str(warmup.get("name", "")))
            used_names.add(str(eval_task.get("name", "")))
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
    parser.add_argument("--interaction-strict-bottom-quantile", type=float, default=0.2)
    args = parser.parse_args()

    in_path = Path(args.in_path)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    frozen = load_samples(in_path)
    normalized_categories: Dict[str, List[str]] = {
        str(s.get("name", "")): [normalize_category(c) for c in (s.get("categories") or []) if normalize_category(c)]
        for s in frozen
    }

    # Main clean candidates first, then compute quantile within this candidate set.
    main_clean_candidates: List[Dict[str, Any]] = []
    for sample in frozen:
        name = str(sample.get("name", ""))
        cats = set(normalized_categories.get(name, []))
        if not cats:
            continue
        if "multiple_user_turn" in cats or "insufficient_information" in cats:
            continue
        if not is_ground_truth_complete(sample):
            continue
        if not ({"single_user_turn", "state_dependency", "single_tool", "canonicalization", "multiple_tool"} & cats):
            continue
        main_clean_candidates.append(copy.deepcopy(sample))
    candidate_sims = sorted(float(s.get("official_similarity", 0.0) or 0.0) for s in main_clean_candidates)
    cand_bottom_idx = max(0, int(math.floor(len(candidate_sims) * args.noisy_bottom_quantile)) - 1)
    cand_bottom_threshold = candidate_sims[cand_bottom_idx] if candidate_sims else -1.0
    main_clean: List[Dict[str, Any]] = []
    for sample in main_clean_candidates:
        similarity = float(sample.get("official_similarity", 0.0) or 0.0)
        if similarity <= cand_bottom_threshold:
            continue
        main_clean.append(sample)
    main_clean.sort(key=lambda s: str(s.get("name", "")))
    if args.max_main_clean_count is not None:
        main_clean = main_clean[: args.max_main_clean_count]

    # Skill distractor: expand candidate_tools only; keep execution allow-list unchanged.
    pool: List[str] = []
    for sample in main_clean:
        for tool in sample.get("candidate_tools", []) or []:
            if tool not in pool:
                pool.append(tool)
    skill_distractor: List[Dict[str, Any]] = []
    for sample in main_clean:
        out = copy.deepcopy(sample)
        out["candidate_tools"] = list(pool)
        skill_distractor.append(out)
    skill_distractor.sort(key=lambda s: str(s.get("name", "")))

    # Interaction live.
    interaction_src = []
    for sample in frozen:
        name = str(sample.get("name", ""))
        cats = set(normalized_categories.get(name, []))
        if "multiple_user_turn" in cats or "insufficient_information" in cats:
            interaction_src.append(sample)
    interaction_live_extended = [
        build_interaction_live(
            sample,
            strip_mode=args.interaction_strip_mode,
            sidecar_flags=args.interaction_oracle_sidecar,
        )
        for sample in sorted(interaction_src, key=lambda s: str(s.get("name", "")))
    ]
    interaction_sims = sorted(float(s.get("official_similarity", 0.0) or 0.0) for s in interaction_src)
    interaction_bottom_idx = max(0, int(math.floor(len(interaction_sims) * args.interaction_strict_bottom_quantile)) - 1)
    interaction_bottom_threshold = interaction_sims[interaction_bottom_idx] if interaction_sims else -1.0
    interaction_live_strict: List[Dict[str, Any]] = []
    for sample in interaction_live_extended:
        similarity = float(sample.get("official_similarity", 0.0) or 0.0)
        if similarity <= interaction_bottom_threshold:
            continue
        oracle = sample.get("oracle_user_replies", [])
        if not isinstance(oracle, list) or not oracle:
            continue
        has_must_interact_trigger = any(
            str(item.get("trigger_type") or "") in {"permission_query", "missing_slot_query"}
            for item in oracle
            if isinstance(item, dict)
        )
        if not has_must_interact_trigger:
            continue
        interaction_live_strict.append(sample)

    # Reuse persistent pairs.
    reuse_persistent = build_reuse_pairs(frozen, normalized_categories, args.max_pairs_per_reuse_group)

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
    dump_samples(outdir / "interaction_live.json", interaction_live_strict)
    dump_samples(outdir / "interaction_live_strict.json", interaction_live_strict)
    dump_samples(outdir / "interaction_live_extended.json", interaction_live_extended)
    dump_samples(outdir / "reuse_persistent.json", reuse_persistent)
    dump_samples(outdir / "noisy_stress.json", noisy_stress)

    print(f"input={in_path} total={len(frozen)}")
    print(f"main_clean={len(main_clean)}")
    print(f"skill_distractor={len(skill_distractor)}")
    print(f"interaction_live={len(interaction_live_strict)}")
    print(f"interaction_live_strict={len(interaction_live_strict)}")
    print(f"interaction_live_extended={len(interaction_live_extended)}")
    print(f"reuse_persistent={len(reuse_persistent)}")
    print(f"noisy_stress={len(noisy_stress)}")


if __name__ == "__main__":
    main()

