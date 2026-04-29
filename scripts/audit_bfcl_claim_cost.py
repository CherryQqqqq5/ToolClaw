#!/usr/bin/env python3
"""Audit BFCL claim consistency and interaction-cost proxy fields.

This script is intentionally post-hoc and audit-only. It reads scored BFCL
artifacts plus the paper claim matrix, then reports consistency gaps without
changing runtime, runner, planner, or scorer behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping


ROOT_DIR = Path(__file__).resolve().parents[1]

OFFICIAL_METRICS = [
    "official_bfcl_eval_success",
    "official_bfcl_eval_tool_selection_correctness",
    "official_bfcl_eval_argument_correctness",
    "official_bfcl_eval_structure_correctness",
]

COST_FIELDS = [
    "tool_calls",
    "user_turns",
    "repair_actions",
    "repair_extra_tool_calls",
    "repair_extra_user_turns",
    "token_cost",
    "wall_clock_ms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit BFCL claim consistency and cost proxy fields")
    parser.add_argument("--outdir", help="BFCL scored outdir containing comparison.scored.csv and score JSON files")
    parser.add_argument("--comparison", help="Path to comparison.scored.csv")
    parser.add_argument("--official-scoreboard", help="Path to official_scoreboard.json")
    parser.add_argument("--claim-summary", help="Path to claim_summary.json")
    parser.add_argument("--claim-matrix", default="configs/paper_claim_matrix.yaml", help="Path to paper claim matrix")
    parser.add_argument(
        "--selected-correct-summary",
        help="Optional path to bfcl_selected_correct_failure_summary.json for already-computed arg/shape buckets",
    )
    parser.add_argument("--output-json", help="Output JSON path")
    parser.add_argument("--output-md", help="Output Markdown path")
    return parser.parse_args()


def _path(raw: str | None, default: Path | None = None) -> Path:
    value = Path(raw) if raw else default
    if value is None:
        raise ValueError("missing required path")
    return value if value.is_absolute() else ROOT_DIR / value


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_claim_matrix(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Claim matrix must remain JSON-compatible for this audit-only script: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Claim matrix root must be an object: {path}")
    return payload


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _mean_float(rows: Iterable[Mapping[str, Any]], field: str) -> float:
    values = [_float(row.get(field)) for row in rows]
    return float(mean(values)) if values else 0.0


def _matrix_bfcl_suite(matrix: Mapping[str, Any]) -> Dict[str, Any]:
    for container_name in ("suites", "benchmark_suites"):
        suites = matrix.get(container_name)
        if isinstance(suites, Mapping) and isinstance(suites.get("bfcl_fc_core"), dict):
            return dict(suites["bfcl_fc_core"])
    # Some historical snapshots used a flatter layout.
    suite = matrix.get("bfcl_fc_core")
    return dict(suite) if isinstance(suite, Mapping) else {}


def _claim(matrix: Mapping[str, Any], claim_id: str) -> Dict[str, Any]:
    claims = matrix.get("claims")
    if isinstance(claims, Mapping) and isinstance(claims.get(claim_id), dict):
        return dict(claims[claim_id])
    return {}


def _claim_matrix_snapshot(matrix: Mapping[str, Any]) -> Dict[str, Any]:
    suite = _matrix_bfcl_suite(matrix)
    observed = suite.get("guarded_rerun_observed") if isinstance(suite.get("guarded_rerun_observed"), dict) else {}
    gates = suite.get("guarded_claim_gates") if isinstance(suite.get("guarded_claim_gates"), dict) else {}
    return {
        "planner_binding_headline_status": _claim(matrix, "planner_binding_headline").get("status"),
        "bfcl_exact_function_guard_status": _claim(matrix, "bfcl_exact_function_guard").get("status"),
        "bfcl_missing_required_guarded_reduction_status": _claim(
            matrix,
            "bfcl_missing_required_guarded_reduction",
        ).get("status"),
        "suite_status": suite.get("status"),
        "claim_strength": suite.get("claim_strength"),
        "paper_role": suite.get("paper_role"),
        "guard_policy_version": suite.get("guard_policy_version"),
        "latest_guarded_rerun_commit": suite.get("latest_guarded_rerun_commit"),
        "latest_guarded_rerun_outdir": suite.get("latest_guarded_rerun_outdir"),
        "reuse_claim_enabled_for_bfcl": suite.get("reuse_claim_enabled_for_bfcl"),
        "a4_interpreted_as_guarded_execution_variant_only": suite.get(
            "a4_interpreted_as_guarded_execution_variant_only"
        ),
        "guarded_claim_gates": gates,
        "guarded_rerun_observed": observed,
    }


def _gate_consistency(matrix_snapshot: Mapping[str, Any], claim_summary: Mapping[str, Any]) -> Dict[str, Any]:
    summary_gates = (
        claim_summary.get("bfcl_guard_claim_gates", {}).get("full_suite_gates", {})
        if isinstance(claim_summary.get("bfcl_guard_claim_gates"), Mapping)
        else {}
    )
    observed = matrix_snapshot.get("guarded_rerun_observed")
    observed = observed if isinstance(observed, Mapping) else {}
    keys = sorted(
        key
        for key in set(summary_gates).union(observed)
        if (key.startswith("a2_") and key.endswith(("_a0", "_a1")))
        or key in {"a2_tool_selection_ge_a0"}
    )
    rows: List[Dict[str, Any]] = []
    mismatch_count = 0
    for key in keys:
        matrix_value = _bool_or_none(observed.get(key))
        summary_value = _bool_or_none(summary_gates.get(key))
        if matrix_value is None and summary_value is None:
            continue
        consistent = matrix_value == summary_value
        if not consistent:
            mismatch_count += 1
        rows.append(
            {
                "gate": key,
                "matrix_guarded_rerun_observed": matrix_value,
                "claim_summary_full_suite_gate": summary_value,
                "consistent": consistent,
            }
        )

    extra_fields = []
    for key in ("reuse_claim_enabled_for_bfcl", "a4_interpreted_as_guarded_execution_variant_only"):
        matrix_value = _bool_or_none(matrix_snapshot.get(key))
        summary_value = _bool_or_none(claim_summary.get("bfcl_guard_claim_gates", {}).get(key))
        if matrix_value is None and summary_value is None:
            continue
        extra_fields.append(
            {
                "field": key,
                "matrix_value": matrix_value,
                "claim_summary_value": summary_value,
                "consistent": matrix_value == summary_value,
            }
        )
    return {
        "mismatch_count": mismatch_count,
        "all_consistent": mismatch_count == 0 and all(row["consistent"] for row in extra_fields),
        "full_suite_gate_rows": rows,
        "policy_field_rows": extra_fields,
    }


def _official_by_system(official_scoreboard: Mapping[str, Any]) -> Dict[str, Dict[str, float]]:
    per_system = official_scoreboard.get("per_system")
    if not isinstance(per_system, Mapping):
        return {}
    return {
        str(system): {metric: _float(values.get(metric)) for metric in OFFICIAL_METRICS}
        for system, values in per_system.items()
        if isinstance(values, Mapping)
    }


def _cost_by_system(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("system") or "")].append(row)
    result: Dict[str, Dict[str, float]] = {}
    for system, system_rows in sorted(grouped.items()):
        if not system:
            continue
        result[system] = {
            "num_rows": float(len(system_rows)),
            **{f"avg_{field}": _mean_float(system_rows, field) for field in COST_FIELDS},
        }
    return result


def _missing_required_by_system(claim_summary: Mapping[str, Any], official: Mapping[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    gates = claim_summary.get("bfcl_guard_claim_gates")
    buckets = gates.get("failure_bucket_counts_by_system") if isinstance(gates, Mapping) else {}
    if not isinstance(buckets, Mapping):
        return {}
    result: Dict[str, Dict[str, float]] = {}
    for system, counts in buckets.items():
        if not isinstance(counts, Mapping):
            continue
        missing = _float(counts.get("missing_required"))
        num_rows = _float(official.get(str(system), {}).get("num_rows") or counts.get("num_rows"))
        total = sum(_float(value) for value in counts.values())
        denominator = num_rows or total
        result[str(system)] = {
            "missing_required_count": missing,
            "missing_required_rate": missing / denominator if denominator else 0.0,
        }
    return result


def _failure_bucket_counts_by_system(claim_summary: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    gates = claim_summary.get("bfcl_guard_claim_gates")
    buckets = gates.get("failure_bucket_counts_by_system") if isinstance(gates, Mapping) else {}
    if not isinstance(buckets, Mapping):
        return {}
    result: Dict[str, Dict[str, int]] = {}
    for system, counts in buckets.items():
        if not isinstance(counts, Mapping):
            continue
        result[str(system)] = {str(bucket): int(_float(value)) for bucket, value in sorted(counts.items())}
    return result


def _selected_correct_failure_buckets(summary_payload: Mapping[str, Any] | None, source_path: Path | None) -> Dict[str, Any]:
    if not isinstance(summary_payload, Mapping):
        return {
            "available": False,
            "source_path": str(source_path) if source_path is not None else "",
            "note": "available buckets only; selected-correct arg/shape summary file not provided or not found",
        }
    summary = summary_payload.get("summary") if isinstance(summary_payload.get("summary"), Mapping) else {}
    by_system = summary_payload.get("by_system") if isinstance(summary_payload.get("by_system"), Mapping) else {}
    bucket_key = "selected_correct_failure_bucket_counts"
    return {
        "available": True,
        "source_path": str(source_path) if source_path is not None else "",
        "summary_bucket_counts": {
            str(bucket): int(_float(value))
            for bucket, value in sorted((summary.get(bucket_key) or {}).items())
        }
        if isinstance(summary.get(bucket_key), Mapping)
        else {},
        "by_system_bucket_counts": {
            str(system): {
                str(bucket): int(_float(value))
                for bucket, value in sorted((system_summary.get(bucket_key) or {}).items())
            }
            for system, system_summary in sorted(by_system.items())
            if isinstance(system_summary, Mapping) and isinstance(system_summary.get(bucket_key), Mapping)
        },
        "note": "available buckets only; values come from existing selected-correct failure summary artifact",
    }


def _per_system_summary(
    *,
    official_scoreboard: Mapping[str, Any],
    claim_summary: Mapping[str, Any],
    comparison_rows: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    official = _official_by_system(official_scoreboard)
    cost = _cost_by_system(comparison_rows)
    missing = _missing_required_by_system(claim_summary, official)
    systems = sorted(set(official).union(cost).union(missing))
    return {
        system: {
            **official.get(system, {}),
            **missing.get(system, {}),
            **cost.get(system, {}),
        }
        for system in systems
    }


def build_audit(
    *,
    comparison_rows: List[Dict[str, str]],
    official_scoreboard: Mapping[str, Any],
    claim_summary: Mapping[str, Any],
    claim_matrix: Mapping[str, Any],
    selected_correct_summary: Mapping[str, Any] | None = None,
    selected_correct_summary_path: Path | None = None,
) -> Dict[str, Any]:
    matrix_snapshot = _claim_matrix_snapshot(claim_matrix)
    failure_buckets = _failure_bucket_counts_by_system(claim_summary)
    return {
        "audit_schema_version": "bfcl_claim_cost_audit_v1",
        "audit_only": True,
        "token_cost_semantics": {
            "field": "token_cost",
            "is_proxy": True,
            "note": "token_cost is an aggregate cost proxy from existing traces/CSV, not raw LLM token count; this audit does not report LLM tokens.",
        },
        "claim_matrix_snapshot": matrix_snapshot,
        "failure_bucket_counts_by_system": failure_buckets,
        "selected_correct_failure_buckets": _selected_correct_failure_buckets(
            selected_correct_summary,
            selected_correct_summary_path,
        ),
        "claim_summary_status": {
            "suite": claim_summary.get("suite"),
            "status": claim_summary.get("status"),
            "paper_safe_for_claim": claim_summary.get("paper_safe_for_claim"),
            "headline_supported": claim_summary.get("headline_supported"),
            "headline_blockers": list(claim_summary.get("headline_blockers", []))
            if isinstance(claim_summary.get("headline_blockers"), list)
            else [],
        },
        "gate_consistency": _gate_consistency(matrix_snapshot, claim_summary),
        "per_system": _per_system_summary(
            official_scoreboard=official_scoreboard,
            claim_summary=claim_summary,
            comparison_rows=comparison_rows,
        ),
    }


def _write_markdown(audit: Mapping[str, Any], path: Path) -> None:
    status = audit.get("claim_summary_status", {}) if isinstance(audit.get("claim_summary_status"), Mapping) else {}
    consistency = audit.get("gate_consistency", {}) if isinstance(audit.get("gate_consistency"), Mapping) else {}
    lines = [
        "# BFCL Claim Consistency and Cost Audit",
        "",
        f"- audit_schema_version: `{audit.get('audit_schema_version')}`",
        f"- audit_only: `{audit.get('audit_only')}`",
        f"- headline_supported: `{status.get('headline_supported')}`",
        f"- headline_blockers: `{', '.join(status.get('headline_blockers') or []) or 'none'}`",
        f"- gate_mismatch_count: `{consistency.get('mismatch_count')}`",
        "",
        "Token cost note: `token_cost` is an aggregate proxy from existing traces/CSV, not raw LLM token count. This report does not call it LLM tokens.",
        "",
        "## Gate Consistency",
        "",
        "| gate | matrix guarded_rerun_observed | claim_summary full_suite_gates | consistent |",
        "|---|---:|---:|---|",
    ]
    for row in consistency.get("full_suite_gate_rows", []):
        lines.append(
            f"| {row.get('gate')} | {row.get('matrix_guarded_rerun_observed')} | {row.get('claim_summary_full_suite_gate')} | {row.get('consistent')} |"
        )
    if not consistency.get("full_suite_gate_rows"):
        lines.append("| none |  |  | True |")

    lines.extend(
        [
            "",
            "## Policy Fields",
            "",
            "| field | matrix | claim_summary | consistent |",
            "|---|---:|---:|---|",
        ]
    )
    for row in consistency.get("policy_field_rows", []):
        lines.append(
            f"| {row.get('field')} | {row.get('matrix_value')} | {row.get('claim_summary_value')} | {row.get('consistent')} |"
        )
    if not consistency.get("policy_field_rows"):
        lines.append("| none |  |  | True |")

    lines.extend(
        [
            "",
            "## Failure Buckets by System",
            "",
            "| system | bucket | count |",
            "|---|---|---:|",
        ]
    )
    failure_buckets = audit.get("failure_bucket_counts_by_system")
    if isinstance(failure_buckets, Mapping) and failure_buckets:
        for system, buckets in failure_buckets.items():
            if not isinstance(buckets, Mapping) or not buckets:
                lines.append(f"| {system} | none | 0 |")
                continue
            for bucket, count in buckets.items():
                lines.append(f"| {system} | {bucket} | {int(_float(count))} |")
    else:
        lines.append("| none | available buckets only | 0 |")

    selected_correct = audit.get("selected_correct_failure_buckets")
    selected_correct = selected_correct if isinstance(selected_correct, Mapping) else {}
    lines.extend(
        [
            "",
            "## Selected-Correct Arg/Shape Buckets",
            "",
            f"- available: `{selected_correct.get('available', False)}`",
            f"- note: `{selected_correct.get('note', 'available buckets only')}`",
            "",
            "| scope | bucket | count |",
            "|---|---|---:|",
        ]
    )
    summary_buckets = selected_correct.get("summary_bucket_counts")
    if isinstance(summary_buckets, Mapping) and summary_buckets:
        for bucket, count in summary_buckets.items():
            lines.append(f"| all | {bucket} | {int(_float(count))} |")
    else:
        lines.append("| all | available buckets only | 0 |")

    by_system_buckets = selected_correct.get("by_system_bucket_counts")
    if isinstance(by_system_buckets, Mapping):
        for system, buckets in by_system_buckets.items():
            if not isinstance(buckets, Mapping):
                continue
            for bucket, count in buckets.items():
                lines.append(f"| {system} | {bucket} | {int(_float(count))} |")

    lines.extend(
        [
            "",
            "## Per-System Metrics",
            "",
            "| system | success | tool_selection | argument | structure | missing_required_count | missing_required_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_token_cost_proxy |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    per_system = audit.get("per_system", {}) if isinstance(audit.get("per_system"), Mapping) else {}
    for system, row in per_system.items():
        lines.append(
            "| {system} | {success:.6f} | {tool:.6f} | {arg:.6f} | {structure:.6f} | {missing:.0f} | {missing_rate:.6f} | {tool_calls:.3f} | {user_turns:.3f} | {repairs:.3f} | {token:.6f} |".format(
                system=system,
                success=_float(row.get("official_bfcl_eval_success")),
                tool=_float(row.get("official_bfcl_eval_tool_selection_correctness")),
                arg=_float(row.get("official_bfcl_eval_argument_correctness")),
                structure=_float(row.get("official_bfcl_eval_structure_correctness")),
                missing=_float(row.get("missing_required_count")),
                missing_rate=_float(row.get("missing_required_rate")),
                tool_calls=_float(row.get("avg_tool_calls")),
                user_turns=_float(row.get("avg_user_turns")),
                repairs=_float(row.get("avg_repair_actions")),
                token=_float(row.get("avg_token_cost")),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    outdir = _path(args.outdir) if args.outdir else None
    comparison = _path(args.comparison, outdir / "comparison.scored.csv" if outdir else None)
    official_scoreboard = _path(args.official_scoreboard, outdir / "official_scoreboard.json" if outdir else None)
    claim_summary = _path(args.claim_summary, outdir / "claim_summary.json" if outdir else None)
    claim_matrix = _path(args.claim_matrix)
    selected_correct_summary = (
        _path(args.selected_correct_summary)
        if args.selected_correct_summary
        else (outdir / "bfcl_selected_correct_failure_summary.json" if outdir else None)
    )
    output_json = _path(args.output_json, outdir / "bfcl_claim_cost_audit.json" if outdir else None)
    output_md = _path(args.output_md, outdir / "bfcl_claim_cost_audit.md" if outdir else None)
    selected_correct_payload = None
    if selected_correct_summary is not None and selected_correct_summary.exists():
        selected_correct_payload = _load_json(selected_correct_summary)

    audit = build_audit(
        comparison_rows=_load_csv(comparison),
        official_scoreboard=_load_json(official_scoreboard),
        claim_summary=_load_json(claim_summary),
        claim_matrix=_load_claim_matrix(claim_matrix),
        selected_correct_summary=selected_correct_payload,
        selected_correct_summary_path=selected_correct_summary,
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    _write_markdown(audit, output_md)
    print(f"audit_json: {output_json}")
    print(f"audit_md: {output_md}")


if __name__ == "__main__":
    main()
