#!/usr/bin/env python3
"""Aggregate BFCL official evaluation and ToolClaw diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.adapters import BFCLAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score BFCL benchmark outputs")
    parser.add_argument("--outdir", required=True, help="BFCL benchmark outdir from run_bfcl_bench.py")
    parser.add_argument("--official-eval", choices=["true", "false"], default="true", help="Whether to run the official BFCL evaluator")
    parser.add_argument("--toolclaw-diagnostics", choices=["true", "false"], default="true", help="Whether to compute ToolClaw diagnostics")
    parser.add_argument("--official-evaluator-script", default=None, help="Optional override for the official evaluator wrapper script")
    return parser.parse_args()


def _bool_from_flag(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _key(row: Dict[str, Any]) -> Tuple[int, str, str]:
    return (int(row.get("run_index", 0) or 0), str(row.get("task_id") or ""), str(row.get("system") or ""))


def _suite_name_for_track(track: str) -> str:
    if track == "fc_core":
        return "bfcl_fc_core"
    if track == "agentic_ext":
        return "bfcl_agentic_ext"
    if track == "full_v4":
        return "bfcl_full_v4"
    return "bfcl"


def _load_task_lookup(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return {}
    return {str(task.get("task_id") or ""): task for task in payload if isinstance(task, dict)}


def _discover_official_evaluator(
    manifest: Dict[str, Any],
    override: str | None,
    *,
    normalized_taskset: Path | None = None,
) -> Path | None:
    if override:
        path = Path(override)
        return path if path.exists() else None
    source_manifest = manifest.get("source_manifest")
    if source_manifest:
        path = ROOT_DIR / source_manifest
        if path.exists():
            payload = _load_json(path)
            script = str(payload.get("official_evaluator_script") or "").strip()
            if script:
                candidate = (ROOT_DIR / script) if not Path(script).is_absolute() else Path(script)
                if candidate.exists():
                    return candidate
    if normalized_taskset and normalized_taskset.exists():
        try:
            payload = json.loads(normalized_taskset.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = []
        if isinstance(payload, list):
            for task in payload:
                if not isinstance(task, dict):
                    continue
                metadata = task.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                script = str(metadata.get("official_evaluator_script") or "").strip()
                if not script:
                    continue
                candidate = (ROOT_DIR / script) if not Path(script).is_absolute() else Path(script)
                if candidate.exists():
                    return candidate
    return None



def _parse_python_version(stdout: str) -> Tuple[int, int, int] | None:
    raw = str(stdout or "").strip()
    parts = raw.split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return (major, minor, patch)


def _python_version(executable: str) -> Tuple[int, int, int] | None:
    try:
        completed = subprocess.run(
            [executable, "-c", "import sys; print(\".\".join(str(part) for part in sys.version_info[:3]))"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return _parse_python_version(completed.stdout)


def _discover_official_python() -> Tuple[str, Tuple[int, int, int] | None]:
    candidates: List[str] = []
    override = os.environ.get("BFCL_OFFICIAL_PYTHON", "").strip()
    if override:
        candidates.append(override)
    candidates.append(sys.executable)
    for binary in ("python3.13", "python3.12", "python3.11", "python3.10", "python3.9"):
        resolved = shutil.which(binary)
        if resolved:
            candidates.append(resolved)
    for candidate in ("/cephfs/qiuyn/miniconda3/bin/python3.13", "/cephfs/qiuyn/miniconda3/bin/python3"):
        if Path(candidate).exists():
            candidates.append(candidate)

    seen = set()
    for candidate in candidates:
        normalized = str(Path(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        version = _python_version(normalized)
        if version is not None and version >= (3, 9, 0):
            return normalized, version

    fallback = str(Path(sys.executable))
    return fallback, _python_version(fallback)


def _bfcl_requires_multi_turn_dependency(normalized_taskset: Path) -> bool:
    try:
        payload = json.loads(normalized_taskset.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(payload, list):
        return True
    for task in payload:
        if not isinstance(task, dict):
            continue
        metadata = task.get("metadata", {})
        if isinstance(metadata, dict) and str(metadata.get("bfcl_group") or "") == "multi_turn":
            return True
    return False


def _check_official_python_dependencies(executable: str, required_modules: List[str]) -> List[str]:
    if not required_modules:
        return []
    code = (
        "import importlib.util, json; "
        f"mods={required_modules!r}; "
        "print(json.dumps([m for m in mods if importlib.util.find_spec(m) is None]))"
    )
    completed = subprocess.run(
        [executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return list(required_modules)
    try:
        payload = json.loads(completed.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return list(required_modules)
    return [str(item) for item in payload if str(item)]

def _run_official_evaluator(
    *,
    evaluator_script: Path | None,
    normalized_taskset: Path,
    comparison_raw: Path,
    outdir: Path,
    official_requested: bool,
) -> Tuple[Dict[Tuple[int, str, str], Dict[str, Any]], List[Dict[str, Any]]]:
    if not official_requested:
        return {}, [{"stratum": "all", "reason": "official_eval_disabled", "paper_safe": False}]
    if evaluator_script is None:
        return {}, [{"stratum": "all", "reason": "official_evaluator_unavailable", "paper_safe": False}]

    evaluator_python, evaluator_version = _discover_official_python()
    required_modules = ["mpmath"] if _bfcl_requires_multi_turn_dependency(normalized_taskset) else []
    missing_modules = _check_official_python_dependencies(evaluator_python, required_modules)
    if missing_modules:
        reason = "missing_official_eval_dependency:" + ",".join(sorted(missing_modules))
        error_row: Dict[str, Any] = {
            "stratum": "all",
            "reason": reason,
            "paper_safe": False,
            "python_executable": evaluator_python,
        }
        if evaluator_version is not None:
            error_row["python_version"] = ".".join(str(part) for part in evaluator_version)
        raise SystemExit(
            "BFCL official evaluator dependency preflight failed: "
            f"{reason}. Install the missing module(s) in {evaluator_python} before scoring."
        )
    with tempfile.TemporaryDirectory(prefix="toolclaw_bfcl_eval_") as tmp:
        output_path = Path(tmp) / "official_eval.json"
        completed = subprocess.run(
            [
                evaluator_python,
                str(evaluator_script),
                "--prepared-taskset",
                str(normalized_taskset),
                "--comparison",
                str(comparison_raw),
                "--out",
                str(output_path),
            ],
            cwd=ROOT_DIR,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not output_path.exists():
            error_row: Dict[str, Any] = {"stratum": "all", "reason": "official_evaluator_failed", "paper_safe": False, "stderr": completed.stderr.strip(), "python_executable": evaluator_python}
            if evaluator_version is not None:
                error_row["python_version"] = ".".join(str(part) for part in evaluator_version)
            return {}, [error_row]
        payload = _load_json(output_path)

    results: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    for row in payload.get("results", []):
        if not isinstance(row, dict):
            continue
        results[_key(row)] = {
            "success": float(row.get("success", 0.0)),
            "tool_selection_correctness": float(row.get("tool_selection_correctness", 0.0)),
            "argument_correctness": float(row.get("argument_correctness", 0.0)),
            "structure_correctness": float(row.get("structure_correctness", 0.0)),
            "paper_safe": bool(row.get("paper_safe", False)),
            "unsupported_reasons": list(row.get("unsupported_reasons", [])) if isinstance(row.get("unsupported_reasons"), list) else [],
        }
    unsupported = list(payload.get("unsupported_strata", [])) if isinstance(payload.get("unsupported_strata"), list) else []
    return results, unsupported


def _toolclaw_row_scores(
    *,
    adapter: BFCLAdapter,
    row: Dict[str, str],
    task_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    task = task_lookup[row["task_id"]]
    sample = adapter.load_samples_from_tasks([task])[0]
    trace_path = Path(row["trace_path"])
    if not trace_path.is_absolute():
        trace_path = ROOT_DIR / row["trace_path"]
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    score = adapter.score_trace(sample, trace_payload)
    return {
        "binder_selection_match": float(score.metrics.get("binder_selection_match", 0.0)),
        "tool_sequence_match": float(score.metrics.get("tool_sequence_match", 0.0)),
        "parameter_fill_ratio": float(score.metrics.get("parameter_fill_ratio", 0.0)),
        "policy_format_compliance": float(score.metrics.get("policy_format_compliance", 0.0)),
        "repair_overhead": float(score.metrics.get("repair_overhead", 0.0)),
        "missing_required_arg_rate": float(score.metrics.get("missing_required_arg_rate", 0.0)),
        "preflight_interception_rate": float(score.metrics.get("preflight_interception_rate", 0.0)),
        "repair_success_rate": float(score.metrics.get("repair_success_rate", 0.0)),
        "repair_applied_count": float(score.metrics.get("repair_applied_count", 0.0)),
        "repair_success_count": float(score.metrics.get("repair_success_count", 0.0)),
        "exec_verified": float(score.metrics.get("exec_verified", 0.0)),
        "avg_tool_calls": float(score.metrics.get("avg_tool_calls", 0.0)),
        "avg_user_queries": float(score.metrics.get("avg_user_queries", 0.0)),
    }


def _mean(items: Iterable[float]) -> float:
    values = list(items)
    if not values:
        return 0.0
    return float(mean(values))


def _aggregate(rows: List[Dict[str, Any]], metric_keys: List[str]) -> Dict[str, Dict[str, float]]:
    per_system: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        per_system.setdefault(str(row["system"]), []).append(row)
    summary: Dict[str, Dict[str, float]] = {}
    for system, system_rows in per_system.items():
        summary[system] = {
            "num_rows": float(len(system_rows)),
            **{key: _mean(float(row.get(key, 0.0)) for row in system_rows) for key in metric_keys},
        }
    return summary


def _decode_reasons(raw_value: Any) -> List[str]:
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if str(item)]
    text = str(raw_value or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(payload, list):
        return [str(item) for item in payload if str(item)]
    return [str(payload)] if str(payload) else []


def _reason_bucket(reasons: List[str]) -> str:
    if not reasons:
        return "official_success_or_safe_failure"
    joined = " ".join(reasons)
    if "wrong_func_name" in joined:
        return "wrong_func_name"
    if "missing_required" in joined:
        return "missing_required"
    if "wrong_count" in joined:
        return "wrong_count"
    if "value_error" in joined:
        return "value_error"
    if "missing_multi_turn_dependency" in joined or "missing_official_eval_dependency" in joined:
        return "missing_multi_turn_dependency"
    if "multi_turn" in joined and "mismatch" in joined:
        return "multi_turn_mismatch"
    if "multi_turn" in joined:
        return "multi_turn_other"
    return "other_official_failure"


_RUNTIME_GOLD_FIELD_NAMES = {
    "expected_function",
    "expected_tool",
    "expected_call_count",
    "expected_call_order",
    "gold_tool",
    "gold_call_count",
    "gold_order",
    "official_failure_bucket",
}


def _trace_task_annotations(row: Dict[str, Any]) -> Dict[str, Any]:
    trace_path_value = str(row.get("trace_path") or "").strip()
    if not trace_path_value:
        return {}
    trace_path = Path(trace_path_value)
    if not trace_path.is_absolute():
        trace_path = ROOT_DIR / trace_path_value
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    annotations = metadata.get("task_annotations", {}) if isinstance(metadata, dict) else {}
    return annotations if isinstance(annotations, dict) else {}


def _first_bfcl_selection_diagnostic(row: Dict[str, Any]) -> Dict[str, Any]:
    annotations = _trace_task_annotations(row)
    diagnostics = annotations.get("bfcl_rerank_diagnostics")
    if isinstance(diagnostics, list) and diagnostics:
        first = diagnostics[0]
        return first if isinstance(first, dict) else {}
    if isinstance(diagnostics, dict):
        return diagnostics
    return {}


def _diagnostic_contains_gold_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) in _RUNTIME_GOLD_FIELD_NAMES:
                return True
            if _diagnostic_contains_gold_fields(nested):
                return True
    elif isinstance(value, list):
        return any(_diagnostic_contains_gold_fields(item) for item in value)
    return False


def _top_ids(diagnostic: Dict[str, Any]) -> List[str]:
    top = diagnostic.get("schema_top_5", [])
    if not isinstance(top, list):
        return []
    return [str(item.get("tool_id") or "") for item in top if isinstance(item, dict) and str(item.get("tool_id") or "")]


def _guardability_flags(*, expected: str, planner: str, selected_reason: str, top_ids: List[str]) -> Dict[str, bool]:
    planner_wrong = bool(expected) and bool(planner) and planner != expected
    planner_correct = bool(expected) and bool(planner) and planner == expected
    schema_top1 = top_ids[0] if top_ids else ""
    flags = {
        "schema_top1_expected": bool(expected) and bool(schema_top1) and schema_top1 == expected,
        "schema_top1_wrong_expected_in_top5": bool(expected) and bool(schema_top1) and schema_top1 != expected and expected in top_ids[:5],
        "expected_absent_from_schema_top5": bool(expected) and expected not in top_ids[:5],
        "planner_wrong_schema_top1_expected": planner_wrong and schema_top1 == expected,
        "planner_wrong_schema_top2_expected": planner_wrong and expected in top_ids[:2],
        "planner_wrong_schema_top5_expected": planner_wrong and expected in top_ids[:5],
        "planner_wrong_schema_also_wrong": planner_wrong and schema_top1 != expected,
        "planner_correct_schema_wrong": planner_correct and bool(schema_top1) and schema_top1 != expected,
        "planner_tie_dropped_correct": selected_reason == "planner_tie_dropped" and bool(expected) and schema_top1 == expected,
        "planner_tie_dropped_incorrect": selected_reason == "planner_tie_dropped" and bool(expected) and schema_top1 != expected,
    }
    return flags


def _bfcl_function_selection_audit(scored_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows_out: List[Dict[str, Any]] = []
    bucket_counts: Dict[str, Counter] = defaultdict(Counter)
    runtime_gold_leak_count = 0
    for row in scored_rows:
        reasons = _decode_reasons(row.get("official_bfcl_eval_unsupported_reasons"))
        failure_bucket = _reason_bucket(reasons)
        diagnostic = _first_bfcl_selection_diagnostic(row)
        if _diagnostic_contains_gold_fields(diagnostic):
            runtime_gold_leak_count += 1
        expected = str(row.get("gold_tool") or "").strip()
        planner = str(diagnostic.get("planner_tool_id") or row.get("chosen_tool") or "").strip()
        selected = str(diagnostic.get("selected_tool_id") or row.get("chosen_tool") or "").strip()
        top_ids = _top_ids(diagnostic)
        selected_reason = str(diagnostic.get("selected_reason") or "")
        flags = _guardability_flags(
            expected=expected,
            planner=planner,
            selected_reason=selected_reason,
            top_ids=top_ids,
        )
        system = str(row.get("system") or "")
        for key, enabled in flags.items():
            if enabled:
                bucket_counts[system][key] += 1
        rows_out.append(
            {
                "run_index": int(row.get("run_index", 0) or 0),
                "task_id": str(row.get("task_id") or ""),
                "system": system,
                "expected_function": expected,
                "planner_function": planner,
                "selected_function": selected,
                "schema_top_5": diagnostic.get("schema_top_5", []),
                "schema_top_tool_id": str(diagnostic.get("schema_top_tool_id") or (top_ids[0] if top_ids else "")),
                "schema_top_score": diagnostic.get("schema_top_score"),
                "planner_score": diagnostic.get("planner_score"),
                "score_margin": diagnostic.get("score_margin"),
                "selected_reason": selected_reason,
                "planner_required_argument_coverage": diagnostic.get("planner_required_argument_coverage"),
                "selected_required_argument_coverage": diagnostic.get("selected_required_argument_coverage"),
                "planner_required_args_present": diagnostic.get("planner_required_args_present", []),
                "selected_required_args_present": diagnostic.get("selected_required_args_present", []),
                "planner_missing_required_args": diagnostic.get("planner_missing_required_args", []),
                "selected_missing_required_args": diagnostic.get("selected_missing_required_args", []),
                "official_failure_bucket": failure_bucket,
                "guardability_flags": flags,
                "runtime_diagnostic_gold_free": not _diagnostic_contains_gold_fields(diagnostic),
            }
        )
    return {
        "audit_schema_version": "bfcl_function_selection_audit_v1",
        "guard_policy_version": "strict_schema_top1_tie_drop_v1",
        "gold_fields_added_after_execution": True,
        "runtime_diagnostics_gold_free": runtime_gold_leak_count == 0,
        "runtime_gold_field_leak_count": runtime_gold_leak_count,
        "guardability_bucket_counts": {system: dict(counts) for system, counts in sorted(bucket_counts.items())},
        "rows": rows_out,
    }


def _write_bfcl_function_selection_audit_markdown(audit: Dict[str, Any], path: Path) -> None:
    lines = [
        "# BFCL Function Selection Audit",
        "",
        "This report is gold-enriched after execution. Runtime diagnostics remain gold-free.",
        "",
        f"- audit_schema_version: `{audit.get('audit_schema_version')}`",
        f"- guard_policy_version: `{audit.get('guard_policy_version')}`",
        f"- runtime_diagnostics_gold_free: `{audit.get('runtime_diagnostics_gold_free')}`",
        "",
        "## Guardability Buckets",
        "",
        "| system | bucket | count |",
        "|---|---|---:|",
    ]
    for system, counts in audit.get("guardability_bucket_counts", {}).items():
        if not counts:
            lines.append(f"| {system} | none | 0 |")
            continue
        for bucket, count in sorted(counts.items()):
            lines.append(f"| {system} | {bucket} | {int(count)} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _bucket_counts_by_system(scored_rows: List[Dict[str, Any]]) -> Dict[str, Counter]:
    counts: Dict[str, Counter] = defaultdict(Counter)
    for row in scored_rows:
        system = str(row.get("system") or "")
        counts[system][_reason_bucket(_decode_reasons(row.get("official_bfcl_eval_unsupported_reasons")))] += 1
    return counts


def _baseline_missing_required_slice(scored_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_key = {_key(row): row for row in scored_rows}
    baseline_keys = {
        (int(row.get("run_index", 0) or 0), str(row.get("task_id") or ""))
        for row in scored_rows
        if str(row.get("system") or "") == "a0_baseline"
        and _reason_bucket(_decode_reasons(row.get("official_bfcl_eval_unsupported_reasons"))) == "missing_required"
    }
    per_system: Dict[str, Dict[str, float]] = {}
    systems = sorted({str(row.get("system") or "") for row in scored_rows})
    for system in systems:
        rows = [
            by_key.get((run_index, task_id, system))
            for run_index, task_id in baseline_keys
            if by_key.get((run_index, task_id, system)) is not None
        ]
        total = float(len(rows))
        if not rows:
            per_system[system] = {
                "num_rows": 0.0,
                "missing_required_rate": 0.0,
                "wrong_func_name_rate": 0.0,
                "success_rate": 0.0,
            }
            continue
        buckets = [_reason_bucket(_decode_reasons(row.get("official_bfcl_eval_unsupported_reasons"))) for row in rows]
        per_system[system] = {
            "num_rows": total,
            "missing_required_rate": buckets.count("missing_required") / total,
            "wrong_func_name_rate": buckets.count("wrong_func_name") / total,
            "success_rate": _mean(float(row.get("official_bfcl_eval_success", 0.0)) for row in rows),
        }
    return {
        "slice_id": "baseline_missing_required_slice",
        "definition": "rows where a0_baseline official failure bucket == missing_required",
        "num_task_run_pairs": float(len(baseline_keys)),
        "per_system": per_system,
    }


def _bfcl_guard_claim_gates(scored_rows: List[Dict[str, Any]], official_scoreboard: Dict[str, Any]) -> Dict[str, Any]:
    bucket_counts = _bucket_counts_by_system(scored_rows)
    official = official_scoreboard.get("per_system", {})
    a0 = official.get("a0_baseline", {}) if isinstance(official, dict) else {}
    a2 = official.get("a2_planner", {}) if isinstance(official, dict) else {}
    a0_buckets = bucket_counts.get("a0_baseline", Counter())
    a2_buckets = bucket_counts.get("a2_planner", Counter())
    full_suite_gates = {
        "a2_wrong_func_name_le_a0": int(a2_buckets.get("wrong_func_name", 0)) <= int(a0_buckets.get("wrong_func_name", 0)),
        "a2_missing_required_lt_a0": int(a2_buckets.get("missing_required", 0)) < int(a0_buckets.get("missing_required", 0)),
        "a2_tool_selection_ge_a0": float(a2.get("official_bfcl_eval_tool_selection_correctness", 0.0) or 0.0) >= float(a0.get("official_bfcl_eval_tool_selection_correctness", 0.0) or 0.0),
        "a2_success_ge_a0": float(a2.get("official_bfcl_eval_success", 0.0) or 0.0) >= float(a0.get("official_bfcl_eval_success", 0.0) or 0.0),
    }
    baseline_slice = _baseline_missing_required_slice(scored_rows)
    a0_slice = baseline_slice.get("per_system", {}).get("a0_baseline", {})
    a2_slice = baseline_slice.get("per_system", {}).get("a2_planner", {})
    baseline_slice_gates = {
        "a2_guarded_missing_required_rate_lt_a0": float(a2_slice.get("missing_required_rate", 0.0)) < float(a0_slice.get("missing_required_rate", 0.0)),
        "a2_guarded_wrong_func_name_rate_le_a0": float(a2_slice.get("wrong_func_name_rate", 0.0)) <= float(a0_slice.get("wrong_func_name_rate", 0.0)),
        "a2_guarded_success_rate_ge_a0": float(a2_slice.get("success_rate", 0.0)) >= float(a0_slice.get("success_rate", 0.0)),
    }
    wrong_function_non_regression_ready = (
        bool(full_suite_gates.get("a2_wrong_func_name_le_a0", False))
        and bool(full_suite_gates.get("a2_tool_selection_ge_a0", False))
        and bool(full_suite_gates.get("a2_success_ge_a0", False))
    )
    missing_required_reduction_ready = bool(full_suite_gates.get("a2_missing_required_lt_a0", False))
    full_suite_supporting_ready = wrong_function_non_regression_ready and missing_required_reduction_ready
    baseline_missing_required_slice_ready = all(baseline_slice_gates.values())
    return {
        "guard_policy_version": "strict_schema_top1_tie_drop_v1",
        "reuse_claim_enabled_for_bfcl": False,
        "a4_interpreted_as_guarded_execution_variant_only": True,
        "failure_bucket_counts_by_system": {system: dict(counts) for system, counts in sorted(bucket_counts.items())},
        "full_suite_gates": full_suite_gates,
        "wrong_function_non_regression_ready": wrong_function_non_regression_ready,
        "missing_required_reduction_ready": missing_required_reduction_ready,
        "full_suite_supporting_ready": full_suite_supporting_ready,
        "baseline_missing_required_slice": baseline_slice,
        "baseline_missing_required_slice_gates": baseline_slice_gates,
        "baseline_missing_required_slice_ready": baseline_missing_required_slice_ready,
        "missing_required_guarded_reduction_ready": full_suite_supporting_ready and baseline_missing_required_slice_ready,
    }


def _bfcl_failure_slice_summary(scored_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    group_fields = [
        ("system",),
        ("system", "bfcl_group"),
        ("system", "bfcl_call_pattern"),
        ("system", "bfcl_group", "bfcl_call_pattern"),
        ("system", "official_failure_bucket"),
    ]
    enriched: List[Dict[str, Any]] = []
    for row in scored_rows:
        reasons = _decode_reasons(row.get("official_bfcl_eval_unsupported_reasons"))
        enriched.append(
            {
                **row,
                "official_failure_bucket": _reason_bucket(reasons),
                "official_failure_reasons": reasons,
            }
        )

    summaries: Dict[str, List[Dict[str, Any]]] = {}
    for fields in group_fields:
        grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
        for row in enriched:
            grouped[tuple(str(row.get(field) or "") for field in fields)].append(row)
        rows_out: List[Dict[str, Any]] = []
        for key, rows in sorted(grouped.items()):
            bucket_counts = Counter(str(row.get("official_failure_bucket") or "") for row in rows)
            rows_out.append(
                {
                    **{field: value for field, value in zip(fields, key)},
                    "num_rows": float(len(rows)),
                    "official_bfcl_eval_success": _mean(float(row.get("official_bfcl_eval_success", 0.0)) for row in rows),
                    "official_bfcl_eval_tool_selection_correctness": _mean(float(row.get("official_bfcl_eval_tool_selection_correctness", 0.0)) for row in rows),
                    "official_bfcl_eval_argument_correctness": _mean(float(row.get("official_bfcl_eval_argument_correctness", 0.0)) for row in rows),
                    "official_bfcl_eval_structure_correctness": _mean(float(row.get("official_bfcl_eval_structure_correctness", 0.0)) for row in rows),
                    "toolclaw_diagnostics_binder_selection_match": _mean(float(row.get("toolclaw_diagnostics_binder_selection_match", 0.0)) for row in rows),
                    "toolclaw_diagnostics_parameter_fill_ratio": _mean(float(row.get("toolclaw_diagnostics_parameter_fill_ratio", 0.0)) for row in rows),
                    "failure_bucket_counts": dict(bucket_counts),
                }
            )
        summaries["__".join(fields)] = rows_out
    return {
        "benchmark": "bfcl",
        "diagnostic": "failure_slice_summary",
        "reason_buckets": [
            "wrong_func_name",
            "missing_required",
            "wrong_count",
            "value_error",
            "multi_turn_mismatch",
            "missing_multi_turn_dependency",
            "other_official_failure",
        ],
        "summaries": summaries,
    }


def _write_bfcl_failure_slice_markdown(summary: Dict[str, Any], path: Path) -> None:
    lines = [
        "# BFCL Failure Slice Diagnostic",
        "",
        "This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.",
        "",
    ]
    for section, rows in summary.get("summaries", {}).items():
        lines.extend([f"## {section}", ""])
        lines.append("| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")
        for row in rows:
            labels = [
                f"{key}={value}"
                for key, value in row.items()
                if key
                in {
                    "system",
                    "bfcl_group",
                    "bfcl_call_pattern",
                    "official_failure_bucket",
                }
            ]
            lines.append(
                "| "
                + " / ".join(labels)
                + f" | {int(float(row.get('num_rows', 0.0)))}"
                + f" | {float(row.get('official_bfcl_eval_success', 0.0)):.4f}"
                + f" | {float(row.get('official_bfcl_eval_tool_selection_correctness', 0.0)):.4f}"
                + f" | {float(row.get('official_bfcl_eval_argument_correctness', 0.0)):.4f}"
                + f" | {float(row.get('official_bfcl_eval_structure_correctness', 0.0)):.4f}"
                + f" | {float(row.get('toolclaw_diagnostics_binder_selection_match', 0.0)):.4f}"
                + f" | {float(row.get('toolclaw_diagnostics_parameter_fill_ratio', 0.0)):.4f}"
                + f" | `{json.dumps(row.get('failure_bucket_counts', {}), sort_keys=True)}` |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _paper_safe_for_fc_core(rows: List[Dict[str, Any]], unsupported: List[Dict[str, Any]]) -> bool:
    if unsupported:
        return False
    if not rows:
        return False
    return all(bool(row.get("official_bfcl_eval_paper_safe")) for row in rows)


def _claim_summary(
    *,
    suite: str,
    track: str,
    official_scoreboard: Dict[str, Any],
    toolclaw_diagnostics: Dict[str, Any],
    scored_rows: List[Dict[str, Any]],
    unsupported: List[Dict[str, Any]],
) -> Dict[str, Any]:
    official_metrics = official_scoreboard.get("per_system", {})
    a0 = official_metrics.get("a0_baseline", {}) if isinstance(official_metrics, dict) else {}
    a1 = official_metrics.get("a1_recovery", {}) if isinstance(official_metrics, dict) else {}
    a2 = official_metrics.get("a2_planner", {}) if isinstance(official_metrics, dict) else {}
    a2_success = float(a2.get("official_bfcl_eval_success", 0.0) or 0.0)
    a0_success = float(a0.get("official_bfcl_eval_success", 0.0) or 0.0)
    a1_success = float(a1.get("official_bfcl_eval_success", 0.0) or 0.0)
    headline_metric_keys = [
        "official_bfcl_eval_tool_selection_correctness",
        "official_bfcl_eval_argument_correctness",
        "official_bfcl_eval_structure_correctness",
    ]
    headline_metric_improvements = [
        key
        for key in headline_metric_keys
        if float(a2.get(key, 0.0) or 0.0) > max(float(a0.get(key, 0.0) or 0.0), float(a1.get(key, 0.0) or 0.0))
    ]
    if track == "fc_core":
        claim_id = "planner_binding_headline"
        paper_safe = _paper_safe_for_fc_core(scored_rows, unsupported)
        headline_supported = (
            paper_safe
            and a2_success > a0_success
            and a2_success > a1_success
            and len(headline_metric_improvements) >= 2
        )
        headline_blockers: List[str] = []
        if not paper_safe:
            headline_blockers.append("official_evaluator_not_paper_safe")
        if a2_success <= a0_success:
            headline_blockers.append("a2_success_not_above_a0")
        if a2_success <= a1_success:
            headline_blockers.append("a2_success_not_above_a1")
        if len(headline_metric_improvements) < 2:
            headline_blockers.append("a2_not_better_on_two_headline_submetrics")
        interpretation = (
            "BFCL fc_core is paper-safe after official evaluator dependency preflight, "
            "but planner/binder headline support additionally requires a2_planner to beat a0/a1 on success "
            "and improve at least two headline submetrics."
        )
        guard_claim_gates = _bfcl_guard_claim_gates(scored_rows, official_scoreboard)
    else:
        claim_id = "bfcl_agentic_supporting"
        paper_safe = False
        headline_supported = False
        headline_blockers = ["agentic_ext_supporting_only"]
        interpretation = "BFCL agentic extension is supporting-only and must not be used as the planner/binder headline claim."
        guard_claim_gates = {
            "reuse_claim_enabled_for_bfcl": False,
            "a4_interpreted_as_guarded_execution_variant_only": True,
            "full_suite_gates": {},
            "full_suite_supporting_ready": False,
            "baseline_missing_required_slice": {},
            "baseline_missing_required_slice_gates": {},
            "missing_required_guarded_reduction_ready": False,
        }
    exact_guard_ready = bool(paper_safe and guard_claim_gates.get("full_suite_supporting_ready"))
    exact_guard_diagnostic_ready = bool(
        paper_safe
        and not exact_guard_ready
        and guard_claim_gates.get("wrong_function_non_regression_ready")
    )
    missing_required_ready = bool(paper_safe and guard_claim_gates.get("missing_required_guarded_reduction_ready"))
    return {
        "suite": suite,
        "status": "completed",
        "track": track,
        "paper_safe_for_claim": paper_safe,
        "headline_supported": headline_supported,
        "headline_blockers": headline_blockers,
        "headline_metric_improvements": headline_metric_improvements,
        "official_bfcl_eval": official_metrics,
        "toolclaw_diagnostics": toolclaw_diagnostics.get("per_system", {}),
        "unsupported_strata": unsupported,
        "bfcl_guard_claim_gates": guard_claim_gates,
        "reuse_claim_enabled_for_bfcl": False,
        "a4_interpreted_as_guarded_execution_variant_only": True,
        "claims": [
            {
                "claim_id": claim_id,
                "paper_safe_for_claim": paper_safe,
                "headline_supported": headline_supported,
                "headline_blockers": headline_blockers,
                "metric_snapshot": official_metrics,
                "interpretation": interpretation,
            },
            {
                "claim_id": "bfcl_exact_function_guard",
                "claim_strength": "supporting" if exact_guard_ready else ("diagnostic_supporting" if exact_guard_diagnostic_ready else "unsupported"),
                "paper_safe_for_claim": exact_guard_ready,
                "supporting_ready": exact_guard_ready,
                "diagnostic_supporting_ready": exact_guard_diagnostic_ready,
                "gates": guard_claim_gates.get("full_suite_gates", {}),
                "interpretation": "Guarded BFCL adapter evidence is supporting only if wrong-function, missing-required, tool-selection, and success non-regression gates all pass.",
            },
            {
                "claim_id": "bfcl_missing_required_guarded_reduction",
                "claim_strength": "supporting" if missing_required_ready else "unsupported",
                "paper_safe_for_claim": missing_required_ready,
                "supporting_ready": missing_required_ready,
                "gates": guard_claim_gates.get("baseline_missing_required_slice_gates", {}),
                "slice": guard_claim_gates.get("baseline_missing_required_slice", {}),
                "interpretation": "This claim is supporting only if full-suite gates and the pre-registered baseline-missing-required slice gates both pass.",
            },
        ],
    }


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    manifest_path = outdir / "experiment_manifest.json"
    comparison_raw_path = outdir / "comparison.raw.csv"
    if not manifest_path.exists() or not comparison_raw_path.exists():
        raise FileNotFoundError("Expected BFCL raw outputs are missing")

    manifest = _load_json(manifest_path)
    normalized_taskset = ROOT_DIR / manifest["normalized_taskset"] if not Path(manifest["normalized_taskset"]).is_absolute() else Path(manifest["normalized_taskset"])
    rows = _load_csv(comparison_raw_path)
    task_lookup = _load_task_lookup(normalized_taskset)
    adapter = BFCLAdapter()

    evaluator_script = _discover_official_evaluator(
        manifest,
        args.official_evaluator_script,
        normalized_taskset=normalized_taskset,
    )
    official_results, unsupported = _run_official_evaluator(
        evaluator_script=evaluator_script,
        normalized_taskset=normalized_taskset,
        comparison_raw=comparison_raw_path,
        outdir=outdir,
        official_requested=_bool_from_flag(args.official_eval),
    )

    scored_rows: List[Dict[str, Any]] = []
    for row in rows:
        official = official_results.get(
            (int(row.get("run_index", "0") or 0), row["task_id"], row["system"]),
            {
                "success": 0.0,
                "tool_selection_correctness": 0.0,
                "argument_correctness": 0.0,
                "structure_correctness": 0.0,
                "paper_safe": False,
                "unsupported_reasons": ["official_evaluator_unavailable"],
            },
        )
        diagnostics = (
            _toolclaw_row_scores(adapter=adapter, row=row, task_lookup=task_lookup)
            if _bool_from_flag(args.toolclaw_diagnostics)
            else {
                "binder_selection_match": 0.0,
                "tool_sequence_match": 0.0,
                "parameter_fill_ratio": 0.0,
                "policy_format_compliance": 0.0,
                "repair_overhead": 0.0,
                "missing_required_arg_rate": 0.0,
                "preflight_interception_rate": 0.0,
                "repair_success_rate": 0.0,
                "repair_applied_count": 0.0,
                "repair_success_count": 0.0,
                "exec_verified": 0.0,
                "avg_tool_calls": 0.0,
                "avg_user_queries": 0.0,
            }
        )
        scored_rows.append(
            {
                **row,
                "official_bfcl_eval_success": float(official["success"]),
                "official_bfcl_eval_tool_selection_correctness": float(official["tool_selection_correctness"]),
                "official_bfcl_eval_argument_correctness": float(official["argument_correctness"]),
                "official_bfcl_eval_structure_correctness": float(official["structure_correctness"]),
                "official_bfcl_eval_paper_safe": bool(official["paper_safe"]),
                "official_bfcl_eval_unsupported_reasons": json.dumps(official.get("unsupported_reasons", [])),
                "toolclaw_diagnostics_binder_selection_match": diagnostics["binder_selection_match"],
                "toolclaw_diagnostics_tool_sequence_match": diagnostics["tool_sequence_match"],
                "toolclaw_diagnostics_parameter_fill_ratio": diagnostics["parameter_fill_ratio"],
                "toolclaw_diagnostics_policy_format_compliance": diagnostics["policy_format_compliance"],
                "toolclaw_diagnostics_repair_overhead": diagnostics["repair_overhead"],
                "toolclaw_diagnostics_missing_required_arg_rate": diagnostics["missing_required_arg_rate"],
                "toolclaw_diagnostics_preflight_interception_rate": diagnostics["preflight_interception_rate"],
                "toolclaw_diagnostics_repair_success_rate": diagnostics["repair_success_rate"],
                "toolclaw_diagnostics_repair_applied_count": diagnostics["repair_applied_count"],
                "toolclaw_diagnostics_repair_success_count": diagnostics["repair_success_count"],
                "toolclaw_diagnostics_exec_verified": diagnostics["exec_verified"],
                "toolclaw_diagnostics_avg_tool_calls": diagnostics["avg_tool_calls"],
                "toolclaw_diagnostics_avg_user_queries": diagnostics["avg_user_queries"],
            }
        )

    comparison_scored_path = outdir / "comparison.scored.csv"
    _write_csv(scored_rows, comparison_scored_path)

    official_scoreboard = {
        "benchmark": "bfcl",
        "track": manifest.get("track"),
        "namespace": "official_bfcl_eval",
        "per_system": _aggregate(
            scored_rows,
            [
                "official_bfcl_eval_success",
                "official_bfcl_eval_tool_selection_correctness",
                "official_bfcl_eval_argument_correctness",
                "official_bfcl_eval_structure_correctness",
            ],
        ),
        "unsupported_strata": unsupported,
    }
    toolclaw_diagnostics = {
        "benchmark": "bfcl",
        "track": manifest.get("track"),
        "namespace": "toolclaw_diagnostics",
        "per_system": _aggregate(
            scored_rows,
            [
                "toolclaw_diagnostics_binder_selection_match",
                "toolclaw_diagnostics_tool_sequence_match",
                "toolclaw_diagnostics_parameter_fill_ratio",
                "toolclaw_diagnostics_policy_format_compliance",
                "toolclaw_diagnostics_repair_overhead",
                "toolclaw_diagnostics_missing_required_arg_rate",
                "toolclaw_diagnostics_preflight_interception_rate",
                "toolclaw_diagnostics_repair_success_rate",
                "toolclaw_diagnostics_repair_applied_count",
                "toolclaw_diagnostics_repair_success_count",
                "toolclaw_diagnostics_exec_verified",
                "toolclaw_diagnostics_avg_tool_calls",
                "toolclaw_diagnostics_avg_user_queries",
            ],
        ),
    }
    claim_summary = _claim_summary(
        suite=_suite_name_for_track(str(manifest.get("track") or "")),
        track=str(manifest.get("track") or ""),
        official_scoreboard=official_scoreboard,
        toolclaw_diagnostics=toolclaw_diagnostics,
        scored_rows=scored_rows,
        unsupported=unsupported,
    )
    failure_slice_summary = _bfcl_failure_slice_summary(scored_rows)
    function_selection_audit = _bfcl_function_selection_audit(scored_rows)

    (outdir / "official_scoreboard.json").write_text(json.dumps(official_scoreboard, indent=2), encoding="utf-8")
    (outdir / "toolclaw_diagnostics.json").write_text(json.dumps(toolclaw_diagnostics, indent=2), encoding="utf-8")
    (outdir / "claim_summary.json").write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")
    (outdir / "bfcl_failure_slice_summary.json").write_text(json.dumps(failure_slice_summary, indent=2), encoding="utf-8")
    _write_bfcl_failure_slice_markdown(failure_slice_summary, outdir / "bfcl_failure_slice_summary.md")
    (outdir / "bfcl_function_selection_audit.json").write_text(json.dumps(function_selection_audit, indent=2), encoding="utf-8")
    _write_bfcl_function_selection_audit_markdown(function_selection_audit, outdir / "bfcl_function_selection_audit.md")

    manifest["comparison_scored_path"] = _display_path(comparison_scored_path)
    manifest["official_scoreboard_path"] = _display_path(outdir / "official_scoreboard.json")
    manifest["toolclaw_diagnostics_path"] = _display_path(outdir / "toolclaw_diagnostics.json")
    manifest["claim_summary_path"] = _display_path(outdir / "claim_summary.json")
    manifest["bfcl_failure_slice_summary_path"] = _display_path(outdir / "bfcl_failure_slice_summary.json")
    manifest["bfcl_function_selection_audit_path"] = _display_path(outdir / "bfcl_function_selection_audit.json")
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"official_scoreboard: {outdir / 'official_scoreboard.json'}")
    print(f"toolclaw_diagnostics: {outdir / 'toolclaw_diagnostics.json'}")
    print(f"claim_summary: {outdir / 'claim_summary.json'}")
    print(f"bfcl_function_selection_audit: {outdir / 'bfcl_function_selection_audit.json'}")


if __name__ == "__main__":
    main()
