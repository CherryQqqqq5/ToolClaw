#!/usr/bin/env python3
"""Audit ToolSandbox interaction traces for attribution and provenance.

This read-only audit classifies interaction rounds so strict-ladder gains are
not conflated with semantic repair evidence. Singleton tool-choice/action-mask
completion is separated from typed state/binding repair and probe-only closure.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "1.0", "true", "yes"}


def _mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0


def _event_type(event: Dict[str, Any]) -> str:
    return str(event.get("event_type") or event.get("event") or "")


def _expected_answer_type(event: Dict[str, Any]) -> str:
    output = _as_dict(event.get("output"))
    metadata = _as_dict(event.get("metadata"))
    query_metadata = _as_dict(metadata.get("query_metadata"))
    query_policy = _as_dict(query_metadata.get("query_policy"))
    return str(
        output.get("expected_answer_type")
        or query_policy.get("question_type")
        or metadata.get("expected_answer_type")
        or ""
    )


def _tool_enum(schema: Dict[str, Any]) -> Optional[List[str]]:
    props = _as_dict(schema.get("properties"))
    tool_field = _as_dict(props.get("tool_id"))
    enum = tool_field.get("enum")
    if not isinstance(enum, list):
        return None
    return [str(item) for item in enum]


def _schema_keys(schema: Dict[str, Any]) -> List[str]:
    props = _as_dict(schema.get("properties"))
    return sorted(str(key) for key in props)


def _round_key(event: Dict[str, Any]) -> Tuple[str, str]:
    metadata = _as_dict(event.get("metadata"))
    return (str(metadata.get("interaction_id") or ""), str(event.get("step_id") or ""))


META_ANSWER_RE = re.compile(
    r"\b(please provide|please paste|was not provided|not provided|no .* provided|missing .* content|"
    r"cannot determine|can't determine|insufficient context|i don't know|not sure|unknown)\b",
    re.I,
)


def _reply_text(reply: Dict[str, Any]) -> str:
    output = _as_dict(reply.get("output"))
    for key in ("value", "raw_text", "text", "message"):
        if output.get(key) is not None:
            return str(output.get(key))
    return str(output) if output else ""


def _is_meta_answer(reply: Dict[str, Any]) -> bool:
    return bool(META_ANSWER_RE.search(_reply_text(reply)))


def _semantic_credit(round_class: str, flags: List[str], reply: Dict[str, Any], outcome: Dict[str, Any]) -> bool:
    if round_class in {"probe_contract_closure", "singleton_action_mask_completion"}:
        return False
    if _is_meta_answer(reply):
        return False
    outcome_output = _as_dict(outcome.get("output"))
    usable = bool(outcome_output.get("decoded_is_usable"))
    aligned = float(outcome_output.get("target_alignment", 0.0) or 0.0) >= 0.5
    effective = bool(outcome_output.get("effective_patch"))
    progress = bool(outcome_output.get("post_query_progress"))
    return usable and aligned and effective and progress


def _classify_round(query: Dict[str, Any], reply: Dict[str, Any], outcome: Dict[str, Any]) -> Tuple[str, List[str]]:
    query_metadata = _as_dict(_as_dict(query.get("metadata")).get("query_metadata"))
    patch_targets = _as_dict(_as_dict(query.get("metadata")).get("patch_targets")) or _as_dict(query_metadata.get("patch_targets"))
    context = _as_dict(_as_dict(query.get("metadata")).get("context_summary"))
    schema = _as_dict(_as_dict(query.get("metadata")).get("allowed_response_schema"))
    enum = _tool_enum(schema)
    expected = _expected_answer_type(query)
    reply_md = _as_dict(_as_dict(reply.get("metadata")).get("reply_metadata"))
    outcome_output = _as_dict(outcome.get("output"))
    outcome_md = _as_dict(outcome.get("metadata"))
    answer_patch = _as_dict(outcome_md.get("answer_patch"))

    decoded_slots = _as_dict(reply_md.get("decoded_slot_updates"))
    decoded_controls = _as_dict(reply_md.get("decoded_control_updates"))
    decoded_approvals = _as_dict(reply_md.get("decoded_approvals"))
    effect_scope = str(answer_patch.get("effect_scope") or "")
    step_id = str(query.get("step_id") or "")

    flags: List[str] = []
    if enum is not None:
        flags.append("tool_enum")
        flags.append("singleton_tool_enum" if len(enum) == 1 else "multi_tool_enum")
    if query_metadata.get("interaction_probe") or step_id == "interaction_probe":
        flags.append("interaction_probe")
    if _is_meta_answer(reply):
        flags.append("meta_answer")
    if decoded_slots:
        flags.append("decoded_slot_patch")
    if decoded_controls:
        flags.append("decoded_control_patch")
    if decoded_approvals:
        flags.append("decoded_approval_patch")
    if bool(outcome_output.get("effective_patch")):
        flags.append("effective_patch")
    if bool(outcome_output.get("post_query_progress")):
        flags.append("post_query_progress")
    if reply_md.get("provider") or reply_md.get("provider_mode"):
        flags.append("external_reply_provider")
    if str(reply_md.get("provider_mode") or "") == "openrouter":
        flags.append("llm_reply_provider")
    if not _as_list(context.get("missing_assets")) and not _as_list(query_metadata.get("missing_assets")):
        flags.append("no_explicit_missing_assets")
    if not _as_list(context.get("stale_assets")) and not _as_list(query_metadata.get("stale_assets")):
        flags.append("no_explicit_stale_assets")

    if enum is not None and len(enum) == 1 and expected in {"tool_switch", "tool_or_asset_hint", "environment_resolution"}:
        return "singleton_action_mask_completion", flags
    if expected in {"tool_switch", "tool_or_asset_hint", "environment_resolution"}:
        return "tool_switch_or_control_repair", flags
    if query_metadata.get("interaction_probe") or step_id == "interaction_probe":
        return "probe_contract_closure", flags
    if expected in {"missing_asset_patch", "missing_state_patch", "slot_fill"}:
        if decoded_slots or effect_scope in {"state", "asset", "slot"} or "value" in patch_targets:
            return "typed_missing_asset_or_state_patch", flags
        return "missing_asset_query_without_typed_effect", flags
    if decoded_approvals and (decoded_slots or decoded_controls):
        return "compound_approval_repair", flags
    if decoded_approvals:
        return "approval_only", flags
    if decoded_slots or decoded_controls:
        return "typed_workflow_repair", flags
    return "other_interaction", flags


def _iter_trace_paths(trace_dir: Path, system: str) -> Iterable[Path]:
    if trace_dir.is_file():
        yield trace_dir
        return
    pattern = f"*_{system}.json" if system else "*.json"
    yield from sorted(trace_dir.glob(pattern))


def audit(trace_dir: Path, system: str) -> Dict[str, Any]:
    class_counts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    enum_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    accepted_counts: Counter[str] = Counter()
    causality_counts: Counter[str] = Counter()
    gold_free_counts: Counter[str] = Counter()
    examples: Dict[str, Dict[str, Any]] = {}
    per_trace: List[Dict[str, Any]] = []
    trace_count = 0

    for path in _iter_trace_paths(trace_dir, system):
        payload = _load_json(path)
        events = [_as_dict(event) for event in _as_list(payload.get("events"))]
        queries: Dict[Tuple[str, str], Dict[str, Any]] = {}
        replies: Dict[Tuple[str, str], Dict[str, Any]] = {}
        outcomes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        trace_rounds: List[Dict[str, Any]] = []
        trace_count += 1

        for event in events:
            etype = _event_type(event)
            if etype == "user_query":
                queries[_round_key(event)] = event
            elif etype == "user_reply":
                replies[_round_key(event)] = event
            elif etype == "interaction_round_outcome":
                outcomes[_round_key(event)] = event

        for key, query in queries.items():
            reply = replies.get(key, {})
            outcome = outcomes.get(key, {})
            round_class, flags = _classify_round(query, reply, outcome)
            metadata = _as_dict(query.get("metadata"))
            schema = _as_dict(metadata.get("allowed_response_schema"))
            enum = _tool_enum(schema)
            expected = _expected_answer_type(query)
            reply_metadata = _as_dict(_as_dict(reply.get("metadata")).get("reply_metadata"))
            outcome_output = _as_dict(outcome.get("output"))
            outcome_metadata = _as_dict(outcome.get("metadata"))
            answer_patch = _as_dict(outcome_metadata.get("answer_patch"))
            provider = str(reply_metadata.get("provider") or reply_metadata.get("provider_mode") or "unknown")
            model = str(reply_metadata.get("model") or "unknown")
            accepted = str(_as_dict(reply.get("metadata")).get("accepted"))
            effective = bool(outcome_output.get("effective_patch"))
            progress = bool(outcome_output.get("post_query_progress"))
            usable = bool(outcome_output.get("decoded_is_usable", reply_metadata.get("decoded_is_usable", False)))
            target_aligned = float(outcome_output.get("target_alignment", reply_metadata.get("target_alignment", 0.0)) or 0.0)
            semantic_conflict = bool(outcome_output.get("semantic_conflict", reply_metadata.get("semantic_conflict", False)))
            query_metadata = _as_dict(metadata.get("query_metadata"))
            gold_free_key = "explicit_true" if query_metadata.get("gold_free") is True else "not_recorded"

            class_counts[round_class] += 1
            query_counts[expected or "unknown"] += 1
            enum_counts["none" if enum is None else str(len(enum))] += 1
            for flag in flags:
                flag_counts[flag] += 1
            provider_counts[provider] += 1
            model_counts[model] += 1
            accepted_counts[accepted] += 1
            gold_free_counts[gold_free_key] += 1
            causality_counts[f"usable={usable}"] += 1
            causality_counts[f"target_aligned={target_aligned >= 1.0}"] += 1
            causality_counts[f"effective_patch={effective}"] += 1
            causality_counts[f"post_query_progress={progress}"] += 1
            causality_counts[f"semantic_conflict={semantic_conflict}"] += 1
            semantic_credit = _semantic_credit(round_class, flags, reply, outcome)
            causality_counts[f"semantic_credit={semantic_credit}"] += 1

            record = {
                "trace": str(path),
                "task_id": str(payload.get("task_id") or path.stem),
                "step_id": str(query.get("step_id") or ""),
                "interaction_id": key[0],
                "round_class": round_class,
                "expected_answer_type": expected,
                "schema_keys": _schema_keys(schema),
                "tool_id_enum": enum,
                "singleton_tool_enum": bool(enum is not None and len(enum) == 1),
                "patch_targets": _as_dict(metadata.get("patch_targets")),
                "provider": provider,
                "model": model,
                "accepted": accepted,
                "decoded_is_usable": usable,
                "target_alignment": target_aligned,
                "semantic_conflict": semantic_conflict,
                "effective_patch": effective,
                "post_query_progress": progress,
                "semantic_credit": semantic_credit,
                "effect_scope": str(answer_patch.get("effect_scope") or ""),
                "actual_patch_targets": [str(item) for item in _as_list(answer_patch.get("actual_patch_targets"))],
                "flags": flags,
            }
            trace_rounds.append(record)
            examples.setdefault(round_class, record)

        if trace_rounds:
            per_trace.append({
                "trace": str(path),
                "task_id": str(payload.get("task_id") or path.stem),
                "rounds": trace_rounds,
            })

    return {
        "trace_dir": str(trace_dir),
        "system": system,
        "trace_count": trace_count,
        "interaction_round_count": sum(class_counts.values()),
        "round_class_counts": dict(sorted(class_counts.items())),
        "query_type_counts": dict(sorted(query_counts.items())),
        "tool_enum_size_counts": dict(sorted(enum_counts.items())),
        "flag_counts": dict(sorted(flag_counts.items())),
        "provider_counts": dict(sorted(provider_counts.items())),
        "model_counts": dict(sorted(model_counts.items())),
        "accepted_counts": dict(sorted(accepted_counts.items())),
        "causality_counts": dict(sorted(causality_counts.items())),
        "gold_free_counts": dict(sorted(gold_free_counts.items())),
        "examples": examples,
        "per_trace": per_trace,
        "claim_boundary": {
            "singleton_action_mask_completion": "Do not count as LLM tool-choice evidence; report as constrained control completion.",
            "probe_contract_closure": "Treat as strict interaction-contract closure unless accompanied by causal state/binding change.",
            "typed_missing_asset_or_state_patch": "Candidate mechanism evidence only with semantic_credit=true: decoded, target-aligned, effective, followed by progress, and not a meta-answer.",
            "semantic_credit": "Positive interaction mechanism credit requires usable/aligned/effective/progress and excludes probes, singleton action masks, and meta-answers.",
        },
    }


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _resolve_trace_path(raw_path: str, comparison_csv: Path) -> Optional[Path]:
    if not raw_path:
        return None
    path = Path(raw_path)
    candidates = [path] if path.is_absolute() else [Path.cwd() / path, comparison_csv.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def _trace_round_records(trace_path: Optional[Path], cache: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if trace_path is None:
        return []
    key = str(trace_path)
    if key not in cache:
        if not trace_path.exists():
            cache[key] = []
        else:
            summary = audit(trace_path, "")
            rounds: List[Dict[str, Any]] = []
            for item in _as_list(summary.get("per_trace")):
                rounds.extend(_as_list(_as_dict(item).get("rounds")))
            cache[key] = rounds
    return cache[key]


def _cost_proxy(row: Dict[str, str]) -> float:
    if row.get("raw_token_cost") not in (None, ""):
        return _float(row.get("raw_token_cost"))
    return _float(row.get("token_cost"))


def _row_repair_actions(row: Dict[str, str]) -> float:
    if row.get("raw_repair_actions") not in (None, ""):
        return _float(row.get("raw_repair_actions"))
    return _float(row.get("repair_actions"))


def _row_has_interaction_signal(row: Dict[str, str]) -> bool:
    keys = [
        "user_queries",
        "user_turns",
        "probe_user_queries",
        "repair_user_queries",
        "probe_user_replies",
        "repair_user_replies",
        "reply_usable_rate",
        "target_aligned_patch_rate",
        "effective_patch_rate",
        "post_query_progress_rate",
        "useful_interaction_round_rate",
    ]
    return any(_float(row.get(key)) > 0.0 for key in keys)


def _row_system_stats(rows: List[Dict[str, str]], round_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    round_classes = Counter(str(record.get("round_class") or "unknown") for record in round_records)
    semantic_credit_count = sum(1 for record in round_records if record.get("semantic_credit"))
    effective_round_count = sum(1 for record in round_records if record.get("effective_patch"))
    useful_round_count = sum(
        1
        for record in round_records
        if record.get("semantic_credit")
        or (record.get("effective_patch") and record.get("post_query_progress"))
    )
    strict_success_count = sum(1 for row in rows if _boolish(row.get("strict_scored_success")))
    tool_calls_sum = sum(_float(row.get("tool_calls")) for row in rows)
    user_queries_sum = sum(_float(row.get("user_queries", row.get("user_turns"))) for row in rows)
    probe_user_queries_sum = sum(_float(row.get("probe_user_queries")) for row in rows)
    return {
        "rows": len(rows),
        "strict_success_count": strict_success_count,
        "strict_success_rate": _mean(1.0 if _boolish(row.get("strict_scored_success")) else 0.0 for row in rows),
        "tool_calls_sum": tool_calls_sum,
        "tool_calls_mean": _mean(_float(row.get("tool_calls")) for row in rows),
        "tool_calls_per_strict_success": tool_calls_sum / strict_success_count if strict_success_count else 0.0,
        "user_queries_sum": user_queries_sum,
        "user_queries_mean": _mean(_float(row.get("user_queries", row.get("user_turns"))) for row in rows),
        "user_queries_per_strict_success": user_queries_sum / strict_success_count if strict_success_count else 0.0,
        "probe_user_queries_sum": probe_user_queries_sum,
        "probe_user_queries_mean": _mean(_float(row.get("probe_user_queries")) for row in rows),
        "probe_queries_per_strict_success": probe_user_queries_sum / strict_success_count if strict_success_count else 0.0,
        "repair_user_queries_sum": sum(_float(row.get("repair_user_queries")) for row in rows),
        "repair_user_queries_mean": _mean(_float(row.get("repair_user_queries")) for row in rows),
        "effective_patch_sum": sum(_float(row.get("effective_patch_rate")) for row in rows),
        "effective_patch_rate_mean": _mean(_float(row.get("effective_patch_rate")) for row in rows),
        "repair_actions_sum": sum(_row_repair_actions(row) for row in rows),
        "repair_actions_mean": _mean(_row_repair_actions(row) for row in rows),
        "cost_proxy_sum": sum(_cost_proxy(row) for row in rows),
        "cost_proxy_mean": _mean(_cost_proxy(row) for row in rows),
        "repair_user_replies_sum": sum(_float(row.get("repair_user_replies")) for row in rows),
        "probe_user_replies_sum": sum(_float(row.get("probe_user_replies")) for row in rows),
        "interaction_round_count": len(round_records),
        "probe_only_round_count": round_classes.get("probe_contract_closure", 0),
        "singleton_action_mask_round_count": round_classes.get("singleton_action_mask_completion", 0),
        "repair_or_control_round_count": len(round_records) - round_classes.get("probe_contract_closure", 0),
        "semantic_credit_round_count": semantic_credit_count,
        "effective_patch_round_count": effective_round_count,
        "useful_round_count": useful_round_count,
        "round_class_counts": dict(sorted(round_classes.items())),
    }


def _example_record(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "run_index": row.get("run_index"),
        "task_id": row.get("task_id"),
        "system": row.get("system"),
        "trace_path": row.get("trace_path"),
    }


def _paired_s3_vs_s2(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    s2_name = "s2_planner_overlay"
    s3_name = "s3_interaction_overlay"
    by_key: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = {}
    for row in rows:
        system = row.get("system")
        if system not in {s2_name, s3_name}:
            continue
        key = (str(row.get("run_index") or ""), str(row.get("task_id") or ""))
        by_key.setdefault(key, {})[system] = row

    examples: Dict[str, List[Dict[str, Any]]] = {"wins": [], "losses": [], "ties": []}
    counts = Counter()
    deltas = Counter()
    paired_count = 0
    for key, pair in sorted(by_key.items()):
        if s2_name not in pair or s3_name not in pair:
            continue
        paired_count += 1
        s2 = pair[s2_name]
        s3 = pair[s3_name]
        s2_success = _boolish(s2.get("strict_scored_success"))
        s3_success = _boolish(s3.get("strict_scored_success"))
        if s3_success and not s2_success:
            bucket = "wins"
        elif s2_success and not s3_success:
            bucket = "losses"
        else:
            bucket = "ties"
        counts[bucket] += 1
        if len(examples[bucket]) < 5:
            examples[bucket].append({
                "run_index": key[0],
                "task_id": key[1],
                "s2_trace_path": s2.get("trace_path"),
                "s3_trace_path": s3.get("trace_path"),
                "s2_strict": s2_success,
                "s3_strict": s3_success,
            })
        deltas["tool_calls_delta_sum"] += _float(s3.get("tool_calls")) - _float(s2.get("tool_calls"))
        deltas["user_queries_delta_sum"] += _float(s3.get("user_queries", s3.get("user_turns"))) - _float(s2.get("user_queries", s2.get("user_turns")))
        deltas["probe_user_queries_delta_sum"] += _float(s3.get("probe_user_queries")) - _float(s2.get("probe_user_queries"))
        deltas["repair_user_queries_delta_sum"] += _float(s3.get("repair_user_queries")) - _float(s2.get("repair_user_queries"))
        deltas["repair_actions_delta_sum"] += _row_repair_actions(s3) - _row_repair_actions(s2)
        deltas["cost_proxy_delta_sum"] += _cost_proxy(s3) - _cost_proxy(s2)

    additional_wins = counts.get("wins", 0)
    result: Dict[str, Any] = {
        "left_system": s2_name,
        "right_system": s3_name,
        "paired_rows": paired_count,
        "wins": counts.get("wins", 0),
        "additional_wins": additional_wins,
        "losses": counts.get("losses", 0),
        "ties": counts.get("ties", 0),
        "examples": examples,
    }
    for key, value in sorted(deltas.items()):
        result[key] = float(value)
        result[key.replace("_sum", "_mean")] = float(value / paired_count) if paired_count else 0.0
    result["user_queries_per_additional_win"] = float(deltas.get("user_queries_delta_sum", 0.0) / additional_wins) if additional_wins else 0.0
    result["probe_queries_per_additional_win"] = float(deltas.get("probe_user_queries_delta_sum", 0.0) / additional_wins) if additional_wins else 0.0
    result["repair_queries_per_additional_win"] = float(deltas.get("repair_user_queries_delta_sum", 0.0) / additional_wins) if additional_wins else 0.0
    result["tool_calls_per_additional_win"] = float(deltas.get("tool_calls_delta_sum", 0.0) / additional_wins) if additional_wins else 0.0
    return result


def audit_suite(comparison_csv: Path) -> Dict[str, Any]:
    rows = _read_csv_rows(comparison_csv)
    trace_cache: Dict[str, List[Dict[str, Any]]] = {}
    rows_by_system: Dict[str, List[Dict[str, str]]] = {}
    rounds_by_system: Dict[str, List[Dict[str, Any]]] = {}
    examples_by_system: Dict[str, List[Dict[str, Any]]] = {}
    warnings: List[Dict[str, Any]] = []

    for row in rows:
        system = str(row.get("system") or "unknown")
        rows_by_system.setdefault(system, []).append(row)
        rounds: List[Dict[str, Any]] = []
        if _row_has_interaction_signal(row):
            trace_path = _resolve_trace_path(str(row.get("trace_path") or ""), comparison_csv)
            rounds = _trace_round_records(trace_path, trace_cache)
        rounds_by_system.setdefault(system, []).extend(rounds)
        if rounds and len(examples_by_system.setdefault(system, [])) < 5:
            examples_by_system[system].append(_example_record(row))
        repair_replies = _float(row.get("repair_user_replies"))
        repair_queries = _float(row.get("repair_user_queries"))
        if repair_replies > repair_queries:
            warning = {
                "warning": "repair_user_replies_gt_repair_user_queries",
                "repair_user_replies": repair_replies,
                "repair_user_queries": repair_queries,
                **_example_record(row),
            }
            if len(warnings) < 25:
                warnings.append(warning)

    per_system = {
        system: _row_system_stats(system_rows, rounds_by_system.get(system, []))
        for system, system_rows in sorted(rows_by_system.items())
    }
    return {
        "audit_schema_version": "toolsandbox_interaction_cost_suite_v1",
        "comparison_csv": str(comparison_csv),
        "rows": len(rows),
        "systems": sorted(rows_by_system),
        "cost_proxy_note": "cost_proxy uses raw_token_cost/token_cost fields when present; it is not a measured LLM token count.",
        "semantic_credit_lower_bound_note": "semantic_credit_round_count is a lower bound: probe-only and singleton action-mask rounds are excluded even when effective_patch fields are true.",
        "per_system": per_system,
        "s3_vs_s2_paired": _paired_s3_vs_s2(rows),
        "warnings": {
            "repair_user_replies_gt_repair_user_queries_count": sum(
                1 for row in rows if _float(row.get("repair_user_replies")) > _float(row.get("repair_user_queries"))
            ),
            "repair_user_replies_gt_repair_user_queries_note": "Instrumentation/attribution limitation: scored CSV can record user replies as repair replies even when the corresponding query is classified as a probe.",
            "examples": warnings,
        },
        "examples": examples_by_system,
        "claim_boundary": {
            "probe_only": "Probe-only rounds are interaction-contract checks and should not be counted as repair mechanism evidence.",
            "repair_or_useful": "Useful repair evidence requires non-probe interaction with effective patch/progress or semantic_credit.",
            "semantic_credit_lower_bound": "semantic_credit_round_count is a lower bound because probe-only and singleton action-mask rounds are excluded.",
            "cost_proxy": "The cost field is a proxy from run traces, not an audited LLM token counter.",
        },
    }


def _write_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Interaction Attribution Audit",
        "",
        f"- Trace directory: `{summary['trace_dir']}`",
        f"- System: `{summary['system']}`",
        f"- Traces: `{summary['trace_count']}`",
        f"- Interaction rounds: `{summary['interaction_round_count']}`",
        "",
        "## Round Classes",
        "",
        "| class | count | boundary |",
        "|---|---:|---|",
    ]
    boundaries = summary.get("claim_boundary", {})
    for key, count in summary.get("round_class_counts", {}).items():
        lines.append(f"| `{key}` | {count} | {boundaries.get(key, '')} |")
    lines.extend(["", "## Query Types", "", "| query_type | count |", "|---|---:|"])
    for key, count in summary.get("query_type_counts", {}).items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Tool Enum Sizes", "", "| enum size | count |", "|---|---:|"])
    for key, count in summary.get("tool_enum_size_counts", {}).items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Causality Signals", "", "| signal | count |", "|---|---:|"])
    for key, count in summary.get("causality_counts", {}).items():
        lines.append(f"| `{key}` | {count} |")
    lines.extend(["", "## Claim Boundary", ""])
    lines.append("- Singleton tool enum/action-mask rounds must not be reported as open-ended LLM tool-choice evidence.")
    lines.append("- Probe-only contract closure should be separated from typed state or binding repair.")
    lines.append("- Mechanism evidence should rely on `semantic_credit=true`: decoded usable replies with target alignment, effective patch, post-query progress, and no probe/singleton/meta-answer shortcut.")
    lines.extend(["", "## Examples", ""])
    for key, record in summary.get("examples", {}).items():
        lines.append(f"- `{key}`: `{record.get('task_id')}` in `{Path(record.get('trace', '')).name}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_suite_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# ToolSandbox Interaction Cost Suite Audit",
        "",
        f"- Comparison CSV: `{summary['comparison_csv']}`",
        f"- Rows: `{summary['rows']}`",
        f"- Cost proxy note: {summary['cost_proxy_note']}",
        f"- Semantic credit lower bound: {summary['semantic_credit_lower_bound_note']}",
        "",
        "## Per System",
        "",
        "| system | rows | strict | strict_count | tool_calls | user_queries | probe_queries | repair_queries | effective_patch | repair_actions | cost_proxy | user_queries_per_strict | probe_queries_per_strict | tool_calls_per_strict | probe_only_rounds | repair_or_control_rounds | useful_rounds | semantic_credit_rounds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for system, stats in summary.get("per_system", {}).items():
        lines.append(
            "| {system} | {rows} | {strict:.3f} | {strict_count} | {tool:.3f} | {user:.3f} | {probe:.3f} | {repair:.3f} | {effective:.3f} | {actions:.3f} | {cost:.6f} | {user_per:.6f} | {probe_per:.6f} | {tool_per:.6f} | {probe_rounds} | {repair_rounds} | {useful} | {semantic} |".format(
                system=system,
                rows=int(stats.get("rows", 0)),
                strict=float(stats.get("strict_success_rate", 0.0)),
                strict_count=int(stats.get("strict_success_count", 0)),
                tool=float(stats.get("tool_calls_mean", 0.0)),
                user=float(stats.get("user_queries_mean", 0.0)),
                probe=float(stats.get("probe_user_queries_mean", 0.0)),
                repair=float(stats.get("repair_user_queries_mean", 0.0)),
                effective=float(stats.get("effective_patch_rate_mean", 0.0)),
                actions=float(stats.get("repair_actions_mean", 0.0)),
                cost=float(stats.get("cost_proxy_mean", 0.0)),
                user_per=float(stats.get("user_queries_per_strict_success", 0.0)),
                probe_per=float(stats.get("probe_queries_per_strict_success", 0.0)),
                tool_per=float(stats.get("tool_calls_per_strict_success", 0.0)),
                probe_rounds=int(stats.get("probe_only_round_count", 0)),
                repair_rounds=int(stats.get("repair_or_control_round_count", 0)),
                useful=int(stats.get("useful_round_count", 0)),
                semantic=int(stats.get("semantic_credit_round_count", 0)),
            )
        )

    paired = summary.get("s3_vs_s2_paired", {})
    lines.extend([
        "",
        "## s3 vs s2 Paired",
        "",
        f"- Paired rows: {int(paired.get('paired_rows', 0))}",
        f"- Wins/losses/ties: {int(paired.get('wins', 0))}/{int(paired.get('losses', 0))}/{int(paired.get('ties', 0))}",
        f"- Additional wins: {int(paired.get('additional_wins', 0))}",
        "",
        "| cost delta | sum | mean |",
        "|---|---:|---:|",
    ])
    for key in [
        "tool_calls_delta",
        "user_queries_delta",
        "probe_user_queries_delta",
        "repair_user_queries_delta",
        "repair_actions_delta",
        "cost_proxy_delta",
    ]:
        lines.append(
            f"| {key} | {float(paired.get(key + '_sum', 0.0)):.6f} | {float(paired.get(key + '_mean', 0.0)):.6f} |"
        )

    lines.extend([
        "",
        "## Cost Per Additional Win",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| user_queries_per_additional_win | {float(paired.get('user_queries_per_additional_win', 0.0)):.6f} |",
        f"| probe_queries_per_additional_win | {float(paired.get('probe_queries_per_additional_win', 0.0)):.6f} |",
        f"| repair_queries_per_additional_win | {float(paired.get('repair_queries_per_additional_win', 0.0)):.6f} |",
        f"| tool_calls_per_additional_win | {float(paired.get('tool_calls_per_additional_win', 0.0)):.6f} |",
    ])

    warnings = summary.get("warnings", {})
    lines.extend([
        "",
        "## Warnings",
        "",
        f"- `repair_user_replies_gt_repair_user_queries_count`: {int(warnings.get('repair_user_replies_gt_repair_user_queries_count', 0))}",
        f"- Note: {warnings.get('repair_user_replies_gt_repair_user_queries_note', '')}",
        "",
        "## Round Class Counts",
        "",
    ])
    for system, stats in summary.get("per_system", {}).items():
        lines.extend([f"### {system}", "", "| round_class | count |", "|---|---:|"])
        for key, count in stats.get("round_class_counts", {}).items():
            lines.append(f"| `{key}` | {int(count)} |")
        lines.append("")

    lines.extend(["## Examples", ""])
    for system, examples in summary.get("examples", {}).items():
        if not examples:
            continue
        lines.append(f"### {system}")
        for example in examples[:5]:
            lines.append(f"- `{example.get('task_id')}` run `{example.get('run_index')}`: `{Path(str(example.get('trace_path') or '')).name}`")
        lines.append("")
    lines.extend([
        "## Claim Boundary",
        "",
        "- Probe-only rounds are separated from repair/useful interaction evidence.",
        "- Singleton action-mask completions should not be counted as open-ended LLM tool-choice gains.",
        "- `semantic_credit_round_count` is a lower bound because those probe/singleton rounds are excluded.",
        "- `cost_proxy` is not a measured LLM token count.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-dir", type=Path, help="Trace directory or single trace JSON file")
    parser.add_argument("--comparison-csv", type=Path, help="Scored comparison CSV for suite-level cost audit")
    parser.add_argument("--system", default="s3_interaction_overlay", help="Trace filename system suffix to audit")
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args()

    if args.comparison_csv is not None:
        summary = audit_suite(args.comparison_csv)
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _write_suite_markdown(summary, args.out_md)
        print(json.dumps({
            "rows": summary["rows"],
            "systems": summary["systems"],
            "s3_vs_s2_paired": summary["s3_vs_s2_paired"],
            "warnings": summary["warnings"],
            "out_json": str(args.out_json),
            "out_md": str(args.out_md),
        }, indent=2, sort_keys=True))
        return

    if args.trace_dir is None:
        parser.error("--trace-dir is required unless --comparison-csv is provided")

    summary = audit(args.trace_dir, args.system)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(summary, args.out_md)
    print(json.dumps({
        "trace_count": summary["trace_count"],
        "interaction_round_count": summary["interaction_round_count"],
        "round_class_counts": summary["round_class_counts"],
        "out_json": str(args.out_json),
        "out_md": str(args.out_md),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
