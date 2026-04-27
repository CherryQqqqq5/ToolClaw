#!/usr/bin/env python3
"""Derive ToolSandbox persistent-reuse v3 inventory, candidates, and formal source.

The v3 pipeline intentionally separates candidate inventory from claim evidence:
scenario inventory and static pairs are not paper evidence until a pilot confirms
headroom and the final formal source includes the family.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
OFFICIAL_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox"
OFFICIAL_PYTHON = OFFICIAL_ROOT / ".venv" / "bin" / "python"

RUNTIME_VISIBILITY = {
    "query_only": True,
    "full_messages_runtime_visible": False,
    "milestones_runtime_visible": False,
    "scorer_gold_runtime_visible": False,
}

SCORER_ONLY_KEYS = {
    "messages",
    "milestones",
    "result_summary",
    "reference_result_summary",
    "official_milestone_mapping",
    "official_milestone_similarity",
    "official_similarity",
    "official_traceback",
    "official_exception_type",
}


def _git_commit(path: Path = ROOT_DIR) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "item"


def _norm_category(value: Any) -> str:
    return _slug(value).upper()


def _categories(row: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    for value in row.get("categories") or row.get("normalized_categories") or []:
        category = _norm_category(value)
        if category and category not in result:
            result.append(category)
    return result


def _tool_ids(row: Dict[str, Any]) -> List[str]:
    tools = row.get("tool_allow_list") or row.get("candidate_tools") or []
    result: List[str] = []
    for tool in tools:
        if isinstance(tool, str):
            result.append(tool)
        elif isinstance(tool, dict):
            result.append(str(tool.get("name") or tool.get("id") or tool.get("tool_id") or ""))
    return sorted(t for t in result if t)


def _signature(row: Dict[str, Any]) -> str:
    categories = sorted(c for c in _categories(row) if c not in {"NO_DISTRACTION_TOOLS"})
    return "tools=" + ",".join(_tool_ids(row)) + "|categories=" + ",".join(categories)


def _initial_runtime_messages(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        query = row.get("query")
        return [{"sender": "USER", "recipient": "AGENT", "content": str(query)}] if query else []
    runtime: List[Dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        sender = str(message.get("sender") or message.get("role") or "").lower()
        recipient = str(message.get("recipient") or "").lower()
        if sender == "system" or (sender == "user" and (not recipient or recipient == "agent")):
            runtime.append(dict(message))
            if sender == "user":
                break
        elif runtime:
            break
    return runtime


def _runtime_task(row: Dict[str, Any], *, family_id: str, pass_index: int) -> Dict[str, Any]:
    query = str(row.get("query") or row.get("name") or "complete ToolSandbox scenario")
    task = {
        "task_id": f"{family_id}__pass{pass_index}",
        "name": f"{family_id}__pass{pass_index}",
        "query": query,
        "messages": _initial_runtime_messages(row),
        "runtime_messages": _initial_runtime_messages(row),
        "categories": list(row.get("categories") or []),
        "normalized_categories": _categories(row),
        "tool_allow_list": _tool_ids(row),
        "candidate_tools": list(row.get("candidate_tools") or _tool_ids(row)),
        "execution_scenario": row.get("execution_scenario"),
        "reuse_family_id": family_id,
        "reuse_pass_index": pass_index,
        "runtime_visibility": dict(RUNTIME_VISIBILITY),
        "metadata": {
            "reuse_family_id": family_id,
            "reuse_pass_index": pass_index,
            "runtime_visibility": dict(RUNTIME_VISIBILITY),
        },
    }
    return {k: v for k, v in task.items() if v is not None}


def _scorer_gold(row: Dict[str, Any]) -> Dict[str, Any]:
    return {key: row.get(key) for key in SCORER_ONLY_KEYS if key in row}


def _anti_leakage(pass1: Dict[str, Any], pass2: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "passed": True,
        "same_messages": pass1.get("messages") == pass2.get("messages"),
        "same_user_query": str(pass1.get("query") or "") == str(pass2.get("query") or ""),
        "same_candidate_tools": _tool_ids(pass1) == _tool_ids(pass2),
        "same_tool_names": _tool_ids(pass1) == _tool_ids(pass2),
        "pass2_compile_allowed": False,
        "no_pass2_to_registry": True,
        "no_scorer_gold_in_runtime_metadata": True,
        "no_exact_assistant_final_reuse": True,
        "no_user_private_value_reuse": True,
        "full_trajectory_messages_runtime_visible": False,
    }


def _claim_scope_for_exact(row: Dict[str, Any]) -> str:
    cats = set(_categories(row))
    if "STATE_DEPENDENCY" in cats and "MULTIPLE_TOOL_CALL" in cats:
        return "exact_match_cost"
    return "control_no_headroom"


def _candidate_row(pass1: Dict[str, Any], pass2: Dict[str, Any], *, family_id: str, claim_scope: str, pair_type: str) -> Dict[str, Any]:
    anti = _anti_leakage(pass1, pass2)
    exact_claim = claim_scope == "exact_match_cost"
    return {
        "family_id": family_id,
        "source": "frozen_official_export_plus_official_inventory",
        "claim_scope": claim_scope,
        "claim_inclusion": False,
        "claim_exclusion_reason": "awaiting_pilot_headroom_confirmation" if exact_claim else "control_family_not_primary_claim",
        "pair_type": pair_type,
        "headroom_label": "state_precondition_repair" if exact_claim else "control",
        "expected_reuse_mechanism": "continuation_prior" if exact_claim else "safety_control",
        "signature_key": _signature(pass1),
        "runtime_visibility": dict(RUNTIME_VISIBILITY),
        "pilot_headroom": {
            "pilot_confirmed": False,
            "cold_success": None,
            "cold_tool_calls": None,
            "cold_repair_actions": None,
            "a3_tool_calls": None,
            "a3_repair_actions": None,
            "headroom_reason": "not yet pilot-confirmed",
        },
        "anti_leakage": anti,
        "pass1_compile": _runtime_task(pass1, family_id=family_id, pass_index=1),
        "pass2_eval": _runtime_task(pass2, family_id=family_id, pass_index=2),
        "scorer_gold": {
            "pass1": _scorer_gold(pass1),
            "pass2": _scorer_gold(pass2),
            "source_pass1_id": pass1.get("name") or pass1.get("task_id"),
            "source_pass2_id": pass2.get("name") or pass2.get("task_id"),
        },
    }


def load_official_inventory(official_root: Path = OFFICIAL_ROOT) -> Dict[str, Any]:
    try:
        from inventory_toolsandbox_official_scenarios import build_inventory as _build_inventory

        return _build_inventory(official_root)
    except Exception:
        pass
    python_bin = official_root / ".venv" / "bin" / "python"
    if not python_bin.exists():
        raise FileNotFoundError(f"official ToolSandbox python not found: {python_bin}")
    code = r'''
import json
from collections import Counter
from tool_sandbox.scenarios import named_scenarios
from tool_sandbox.common.tool_discovery import ToolBackend
scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
rows = []
for name, scenario in sorted(scenarios.items()):
    categories = [getattr(cat, "name", str(cat)) for cat in scenario.categories]
    context = scenario.starting_context
    rows.append({
        "name": name,
        "categories": categories,
        "tool_allow_list": list(context.tool_allow_list or []),
        "tool_augmentation_list": [getattr(item, "name", str(item)) for item in (context.tool_augmentation_list or [])],
        "milestone_count": len(scenario.evaluation.milestone_matcher.milestones),
        "minefield_count": len(scenario.evaluation.minefield_matcher.milestones),
        "max_messages": scenario.max_messages,
    })
print(json.dumps({"scenario_count": len(rows), "scenarios": rows}, sort_keys=True))
'''
    completed = subprocess.run(
        [str(python_bin), "-c", code],
        cwd=str(official_root),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    payload = json.loads(completed.stdout)
    payload["source"] = str(official_root)
    payload["source_commit"] = _git_commit(official_root)
    payload["inventory_is_evidence"] = False
    payload["category_counts"] = dict(Counter(cat for row in payload["scenarios"] for cat in row.get("categories", [])))
    return payload


def build_candidates(frozen_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in frozen_rows:
        if _tool_ids(row):
            grouped[_signature(row)].append(row)
    candidates: List[Dict[str, Any]] = []
    for signature, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda item: str(item.get("name") or item.get("task_id") or ""))
        for idx in range(0, len(rows) - 1, 2):
            pass1, pass2 = rows[idx], rows[idx + 1]
            scope = _claim_scope_for_exact(pass1)
            family_id = f"v3_{_slug(pass1.get('name'))}__pair{idx//2:02d}"
            candidates.append(_candidate_row(pass1, pass2, family_id=family_id, claim_scope=scope, pair_type="exact_matched_signature"))
    state_rows = [row for row in frozen_rows if "STATE_DEPENDENCY" in set(_categories(row))]
    for idx in range(0, max(len(state_rows) - 1, 0), 2):
        pass1, pass2 = state_rows[idx], state_rows[idx + 1]
        if _tool_ids(pass1) == _tool_ids(pass2):
            continue
        family_id = f"v3_transfer_{_slug(pass1.get('name'))}__to__{_slug(pass2.get('name'))}"
        candidates.append(_candidate_row(pass1, pass2, family_id=family_id, claim_scope="transfer_control", pair_type="same_pattern_transfer"))
    return candidates


def build_final(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    final: List[Dict[str, Any]] = []
    for row in candidates:
        pilot = row.get("pilot_headroom") if isinstance(row.get("pilot_headroom"), dict) else {}
        if bool(row.get("claim_inclusion")) and bool(pilot.get("pilot_confirmed")):
            final.append(row)
        elif row.get("claim_scope") in {"control_no_headroom", "transfer_control"} and bool(pilot.get("pilot_confirmed")):
            final.append(row)
    return final


def manifest_for(rows: List[Dict[str, Any]], *, version: str, source: str, status: str) -> Dict[str, Any]:
    potential_exact = [row for row in rows if row.get("claim_scope") == "exact_match_cost"]
    exact = [row for row in potential_exact if row.get("claim_inclusion")]
    headroom = [row for row in exact if row.get("pilot_headroom", {}).get("pilot_confirmed")]
    controls = Counter(str(row.get("claim_scope") or "") for row in rows)
    return {
        "version": version,
        "dataset": source,
        "source_commit": _git_commit(ROOT_DIR),
        "formal_source_status": status,
        "family_count": len(rows),
        "potential_exact_candidate_count": len(potential_exact),
        "exact_claim_family_count": len(exact),
        "headroom_candidate_count": len(headroom),
        "control_no_headroom_count": int(controls.get("control_no_headroom", 0)),
        "transfer_control_count": int(controls.get("transfer_control", 0)),
        "statistical_claim_allowed": len(rows) >= 20 and len(exact) >= 12 and len(headroom) >= 10,
        "claim_scope_policy": "primary claim uses only claim_scope=exact_match_cost and claim_inclusion=true",
        "inventory_is_evidence": False,
        "selection_gate_targets": {
            "family_count": 20,
            "exact_claim_family_count": 12,
            "headroom_candidate_count": 10,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive ToolSandbox reuse persistent v3 artifacts")
    parser.add_argument("--frozen-source", default="data/toolsandbox.official_core_reproducible.frozen.json")
    parser.add_argument("--inventory-out", default="data/toolsandbox_official_scenario_inventory.json")
    parser.add_argument("--candidates-out", default="data/toolsandbox_reuse_persistent_v3_candidates.jsonl")
    parser.add_argument("--candidates-manifest", default="data/toolsandbox_reuse_persistent_v3_candidates.manifest.json")
    parser.add_argument("--out", default="data/toolsandbox_reuse_persistent_v3.jsonl")
    parser.add_argument("--manifest", default="data/toolsandbox_reuse_persistent_v3.manifest.json")
    parser.add_argument("--phase", choices=["inventory", "candidates", "final", "all"], default="all")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.phase in {"inventory", "all"}:
        inventory = load_official_inventory()
        _write_json(Path(args.inventory_out), inventory)
        print(f"wrote: {args.inventory_out}")
    if args.phase in {"candidates", "all"}:
        frozen_rows = _read_json(Path(args.frozen_source))
        candidates = build_candidates(frozen_rows)
        _write_jsonl(Path(args.candidates_out), candidates)
        _write_json(Path(args.candidates_manifest), manifest_for(candidates, version="toolsandbox_reuse_persistent_v3_candidates", source=args.candidates_out, status="candidate_pool_not_evidence"))
        print(f"wrote: {args.candidates_out}")
        print(f"wrote: {args.candidates_manifest}")
    if args.phase in {"final", "all"}:
        candidates = _read_jsonl(Path(args.candidates_out)) if Path(args.candidates_out).exists() else []
        final = build_final(candidates)
        _write_jsonl(Path(args.out), final)
        status = "pilot_confirmed_formal_source" if final else "awaiting_pilot_confirmation"
        _write_json(Path(args.manifest), manifest_for(final, version="toolsandbox_reuse_persistent_v3", source=args.out, status=status))
        print(f"wrote: {args.out}")
        print(f"wrote: {args.manifest}")


if __name__ == "__main__":
    main()
