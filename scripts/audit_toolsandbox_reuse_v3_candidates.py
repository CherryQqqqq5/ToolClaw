#!/usr/bin/env python3
"""Audit why ToolSandbox reuse persistent v3 candidates do not yet form evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT_DIR / "data" / "toolsandbox_official_scenario_inventory.json"
DEFAULT_LEDGER = ROOT_DIR / "data" / "toolsandbox_run_coverage_ledger.json"
DEFAULT_FROZEN = ROOT_DIR / "data" / "toolsandbox.formal.official.json"
DEFAULT_CANDIDATES = ROOT_DIR / "data" / "toolsandbox_reuse_persistent_v3_candidates.jsonl"
DEFAULT_CANDIDATES_MANIFEST = ROOT_DIR / "data" / "toolsandbox_reuse_persistent_v3_candidates.manifest.json"
DEFAULT_FINAL = ROOT_DIR / "data" / "toolsandbox_reuse_persistent_v3.jsonl"
DEFAULT_FINAL_MANIFEST = ROOT_DIR / "data" / "toolsandbox_reuse_persistent_v3.manifest.json"
DEFAULT_OUT = ROOT_DIR / "data" / "toolsandbox_reuse_persistent_v3_candidate_rejection_audit.json"
DEFAULT_MD = ROOT_DIR / "docs" / "toolsandbox_reuse_v3_candidate_audit_20260426.md"

PRIMARY_TARGETS = {
    "family_count": 20,
    "exact_claim_family_count": 12,
    "headroom_candidate_count": 10,
}


def _git_commit(path: Path = ROOT_DIR) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return ""


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "item"


def _norm_category(value: Any) -> str:
    return _slug(value).upper()


def _categories(row: Mapping[str, Any]) -> List[str]:
    raw = row.get("categories") or row.get("normalized_categories") or []
    values: List[str] = []
    for item in raw if isinstance(raw, list) else []:
        value = _norm_category(item)
        if value and value not in values:
            values.append(value)
    return values


def _tool_ids(row: Mapping[str, Any]) -> List[str]:
    raw = row.get("tool_allow_list") or row.get("candidate_tools") or []
    tools: List[str] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, str):
            tools.append(item)
        elif isinstance(item, dict):
            value = item.get("name") or item.get("id") or item.get("tool_id")
            if value:
                tools.append(str(value))
    return sorted(tool for tool in tools if tool)


def _signature(row: Mapping[str, Any]) -> str:
    categories = sorted(cat for cat in _categories(row) if cat not in {"NO_DISTRACTION_TOOLS"})
    tools = _tool_ids(row)
    if not tools:
        return ""
    return "tools=" + ",".join(tools) + "|categories=" + ",".join(categories)


def _scope_counts(candidates: Iterable[Mapping[str, Any]]) -> Counter:
    return Counter(str(row.get("claim_scope") or "missing") for row in candidates)


def _sample(rows: Iterable[Mapping[str, Any]], keys: List[str], limit: int = 8) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for row in rows:
        result.append({key: row.get(key) for key in keys if key in row})
        if len(result) >= limit:
            break
    return result


def _frozen_success_missing(row: Mapping[str, Any]) -> bool:
    result = row.get("result_summary") if isinstance(row.get("result_summary"), dict) else {}
    has_metric = any(key in result for key in ("success", "similarity", "milestone_similarity")) or any(
        key in row for key in ("official_similarity", "official_milestone_similarity")
    )
    return not has_metric


def build_audit(
    *,
    inventory: Mapping[str, Any],
    ledger: Mapping[str, Any],
    frozen_rows: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    final_rows: List[Dict[str, Any]],
    candidates_manifest: Mapping[str, Any] | None = None,
    final_manifest: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    ledger_scenarios = ledger.get("scenarios", []) if isinstance(ledger.get("scenarios"), list) else []
    frozen_by_signature: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    no_signature_rows: List[Dict[str, Any]] = []
    for row in frozen_rows:
        signature = _signature(row)
        if signature:
            frozen_by_signature[signature].append(row)
        else:
            no_signature_rows.append(row)

    singleton_signature_rows = [rows[0] for rows in frozen_by_signature.values() if len(rows) == 1]
    same_signature_pair_attempts = sum(len(rows) // 2 for rows in frozen_by_signature.values())
    unpaired_same_signature_rows = sum(len(rows) % 2 for rows in frozen_by_signature.values())
    candidate_scopes = _scope_counts(candidates)
    final_scopes = _scope_counts(final_rows)
    potential_exact = [row for row in candidates if row.get("claim_scope") == "exact_match_cost"]
    controls = [row for row in candidates if row.get("claim_scope") == "control_no_headroom"]
    transfers = [row for row in candidates if row.get("claim_scope") == "transfer_control"]
    included = [row for row in ledger_scenarios if row.get("included_in_frozen_export")]
    excluded = [row for row in ledger_scenarios if not row.get("included_in_frozen_export")]
    external_excluded = [row for row in excluded if row.get("requires_external_api")]
    missing_success = [row for row in frozen_rows if _frozen_success_missing(row)]
    final_included = [row for row in final_rows if row.get("claim_scope") == "exact_match_cost" and row.get("claim_inclusion")]
    awaiting_pilot = [
        row for row in candidates
        if row.get("claim_scope") == "exact_match_cost" and not row.get("claim_inclusion")
    ]

    rejection_bucket_counts = {
        "inventory_not_in_frozen_export": len(excluded),
        "external_api_only_no_trace": len(external_excluded),
        "insufficient_paired_frozen_evidence": len(singleton_signature_rows) + unpaired_same_signature_rows,
        "rejected_no_exact_signature": len(no_signature_rows),
        "rejected_toolset_mismatch": len(transfers),
        "rejected_no_headroom_static": len(controls),
        "transfer_only": len(transfers),
        "awaiting_pilot": len(awaiting_pilot),
        "missing_success_run_evidence": len(missing_success),
        "final_source_empty_pending_pilot": 1 if not final_rows else 0,
    }
    exact_gap = max(0, PRIMARY_TARGETS["exact_claim_family_count"] - len(final_included))
    potential_exact_gap = max(0, PRIMARY_TARGETS["exact_claim_family_count"] - len(potential_exact))
    headroom_gap = max(0, PRIMARY_TARGETS["headroom_candidate_count"] - sum(1 for row in final_included if row.get("pilot_headroom", {}).get("pilot_confirmed")))

    return {
        "audit_is_evidence": False,
        "audit_purpose": "pipeline diagnosis for ToolSandbox reuse persistent v3 candidate bottleneck",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toolclaw_commit": _git_commit(ROOT_DIR),
        "summary": {
            "inventory_count": int(inventory.get("scenario_count") or len(inventory.get("scenarios", []))),
            "frozen_export_count": len(frozen_rows),
            "matched_frozen_rows": len(included),
            "unmatched_frozen_export_rows": len(ledger.get("unmatched_frozen_export_rows", [])),
            "same_signature_pair_attempt_count": same_signature_pair_attempts,
            "candidate_pairs_attempted": len(candidates),
            "candidate_family_count": len(candidates),
            "selected_exact_candidates": len(potential_exact),
            "selected_no_headroom_controls": len(controls),
            "selected_transfer_controls": len(transfers),
            "final_formal_family_count": len(final_rows),
            "final_exact_claim_family_count": len(final_included),
            "formal_source_status": (final_manifest or {}).get("formal_source_status", "unknown"),
            "statistical_claim_allowed": bool((final_manifest or {}).get("statistical_claim_allowed", False)),
        },
        "candidate_manifest_summary": dict(candidates_manifest or {}),
        "final_manifest_summary": dict(final_manifest or {}),
        "frozen_signature_summary": {
            "signature_group_count": len(frozen_by_signature),
            "singleton_signature_group_count": sum(1 for rows in frozen_by_signature.values() if len(rows) == 1),
            "unpaired_same_signature_row_count": unpaired_same_signature_rows,
            "rows_without_signature_count": len(no_signature_rows),
        },
        "candidate_scope_counts": dict(candidate_scopes),
        "final_scope_counts": dict(final_scopes),
        "rejection_bucket_counts": rejection_bucket_counts,
        "gate_gaps": {
            "target_family_count": PRIMARY_TARGETS["family_count"],
            "target_exact_claim_family_count": PRIMARY_TARGETS["exact_claim_family_count"],
            "target_headroom_candidate_count": PRIMARY_TARGETS["headroom_candidate_count"],
            "final_exact_claim_family_gap": exact_gap,
            "potential_exact_candidate_gap_before_pilot": potential_exact_gap,
            "pilot_confirmed_headroom_gap": headroom_gap,
        },
        "samples": {
            "external_api_no_trace": _sample(external_excluded, ["scenario_name", "rapidapi_or_external_api_reason", "categories"], 10),
            "potential_exact_candidates": _sample(potential_exact, ["family_id", "claim_scope", "claim_exclusion_reason", "signature_key"], 10),
            "no_headroom_controls": _sample(controls, ["family_id", "claim_scope", "claim_exclusion_reason", "signature_key"], 10),
            "transfer_controls": _sample(transfers, ["family_id", "claim_scope", "pair_type", "signature_key"], 10),
            "singleton_signature_frozen_rows": _sample(singleton_signature_rows, ["name", "categories", "tool_allow_list"], 10),
        },
        "next_step_recommendation": "expand official-run evidence via core reproducible export, then re-derive candidates and run pilot; do not run formal while final source has zero pilot-confirmed families",
    }


def render_markdown(audit: Mapping[str, Any]) -> str:
    summary = audit.get("summary", {})
    buckets = audit.get("rejection_bucket_counts", {})
    gaps = audit.get("gate_gaps", {})
    lines = [
        "# ToolSandbox Reuse V3 Candidate Rejection Audit (2026-04-26)",
        "",
        "## Summary",
        "",
        "This audit diagnoses the reuse v3 evidence-generation funnel. It is not benchmark evidence and does not promote the reuse claim.",
        "",
        f"- inventory scenarios: `{summary.get('inventory_count', 0)}`",
        f"- frozen export rows: `{summary.get('frozen_export_count', 0)}`",
        f"- matched frozen rows: `{summary.get('matched_frozen_rows', 0)}`",
        f"- candidate families: `{summary.get('candidate_family_count', 0)}`",
        f"- potential exact candidates: `{summary.get('selected_exact_candidates', 0)}`",
        f"- no-headroom controls: `{summary.get('selected_no_headroom_controls', 0)}`",
        f"- transfer controls: `{summary.get('selected_transfer_controls', 0)}`",
        f"- final formal families: `{summary.get('final_formal_family_count', 0)}`",
        f"- formal source status: `{summary.get('formal_source_status', 'unknown')}`",
        "",
        "## Rejection Buckets",
        "",
        "| bucket | count |",
        "| --- | ---: |",
    ]
    for key, value in buckets.items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Gate Gaps",
        "",
        "| gate | value |",
        "| --- | ---: |",
    ])
    for key, value in gaps.items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The v3 runner/scorer pipeline is ready for separated exact/control evidence, but the current frozen export is too small to produce enough pilot-confirmed primary exact families. The immediate bottleneck is evidence source coverage and pilot confirmation, not reuse runtime behavior.",
        "",
        "Recommended next step: generate a core reproducible official-run export, re-derive v3 candidates, then run a one-run pilot before any formal reuse experiment.",
        "",
        "## Claim Boundary",
        "",
        "- Candidate inventory is not evidence.",
        "- Final v3 source remains pending while pilot-confirmed family count is zero.",
        "- No reuse claim should be marked supported from this audit.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ToolSandbox reuse persistent v3 candidate rejection funnel")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--frozen-export", default=str(DEFAULT_FROZEN))
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--candidates-manifest", default=str(DEFAULT_CANDIDATES_MANIFEST))
    parser.add_argument("--final", default=str(DEFAULT_FINAL))
    parser.add_argument("--final-manifest", default=str(DEFAULT_FINAL_MANIFEST))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(
        inventory=_read_json(Path(args.inventory), {}),
        ledger=_read_json(Path(args.ledger), {}),
        frozen_rows=_read_json(Path(args.frozen_export), []),
        candidates=_read_jsonl(Path(args.candidates)),
        final_rows=_read_jsonl(Path(args.final)),
        candidates_manifest=_read_json(Path(args.candidates_manifest), {}),
        final_manifest=_read_json(Path(args.final_manifest), {}),
    )
    _write_json(Path(args.out), audit)
    Path(args.md_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md_out).write_text(render_markdown(audit), encoding="utf-8")
    print(f"wrote: {args.out}")
    print(f"wrote: {args.md_out}")


if __name__ == "__main__":
    main()
