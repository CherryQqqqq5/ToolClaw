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


def _json_list_field(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _candidate_tool_records(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for idx, raw_tool in enumerate(_json_list_field(row.get("candidate_tools")), start=1):
        if isinstance(raw_tool, str):
            records.append(
                {
                    "tool_id": raw_tool,
                    "bfcl_original_function_name": raw_tool,
                    "bfcl_original_index": idx,
                }
            )
            continue
        if not isinstance(raw_tool, dict):
            continue
        metadata = raw_tool.get("metadata", {}) if isinstance(raw_tool.get("metadata"), dict) else {}
        tool_id = str(raw_tool.get("tool_id") or raw_tool.get("name") or "").strip()
        original_name = str(metadata.get("bfcl_original_function_name") or raw_tool.get("name") or tool_id).strip()
        records.append(
            {
                "tool_id": tool_id,
                "bfcl_original_function_name": original_name,
                "bfcl_original_index": metadata.get("bfcl_original_index", idx),
                "canonical_name": str(metadata.get("canonical_name") or tool_id),
                "normalization_trace": list(metadata.get("normalization_trace", [])) if isinstance(metadata.get("normalization_trace"), list) else [],
            }
        )
    return records


def _name_variants(record: Dict[str, Any]) -> List[str]:
    values = [
        record.get("tool_id"),
        record.get("bfcl_original_function_name"),
        record.get("canonical_name"),
    ]
    return [str(value).strip() for value in values if str(value or "").strip()]


def _contains_name(records: List[Dict[str, Any]], expected: str) -> bool:
    if not expected:
        return False
    return any(expected in _name_variants(record) for record in records)


def _match_name(records: List[Dict[str, Any]], expected: str, key: str) -> str | None:
    if not expected:
        return None
    for record in records:
        if expected in _name_variants(record):
            value = str(record.get(key) or "").strip()
            return value or None
    return None


def _diagnostic_tool_records(diagnostic: Dict[str, Any], *, id_key: str, original_key: str) -> List[Dict[str, Any]]:
    ids = diagnostic.get(id_key, [])
    originals = diagnostic.get(original_key, [])
    if not isinstance(ids, list):
        ids = []
    if not isinstance(originals, list):
        originals = []
    records: List[Dict[str, Any]] = []
    for idx, tool_id in enumerate(ids):
        original = originals[idx] if idx < len(originals) else tool_id
        records.append(
            {
                "tool_id": str(tool_id or ""),
                "bfcl_original_function_name": str(original or tool_id or ""),
            }
        )
    return records


def _schema_top_records(diagnostic: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    top = diagnostic.get("schema_top_5", [])
    if not isinstance(top, list):
        return records
    for item in top:
        if not isinstance(item, dict):
            continue
        tool_id = str(item.get("tool_id") or "").strip()
        records.append(
            {
                "tool_id": tool_id,
                "bfcl_original_function_name": str(item.get("bfcl_original_function_name") or tool_id),
                "score": item.get("score"),
                "required_argument_coverage": item.get("required_argument_coverage"),
                "exact_match": item.get("exact_match"),
            }
        )
    return records


def _selected_matches_expected(diagnostic: Dict[str, Any], expected: str) -> bool:
    selected = str(diagnostic.get("selected_tool_id") or "").strip()
    if not expected or not selected:
        return False
    if selected == expected:
        return True
    runtime_records = _diagnostic_tool_records(
        diagnostic,
        id_key="runtime_candidate_tool_ids",
        original_key="runtime_candidate_original_function_names",
    )
    return any(record.get("tool_id") == selected and expected in _name_variants(record) for record in runtime_records)


def _bfcl_coverage_drop_stage(
    *,
    expected: str,
    expected_in_raw: bool,
    expected_in_prepared: bool,
    expected_in_runtime: bool,
    expected_in_ranker: bool,
    expected_in_top5: bool,
    expected_is_top1: bool,
    selected_is_expected: bool,
    success: bool,
    candidate_pool_exception: str = "",
) -> Tuple[str, str]:
    if not expected:
        return "no_expected_function", "row has no expected function"
    if not expected_in_raw:
        return "raw_absent", "expected function is absent from candidate/raw function docs"
    if not expected_in_prepared:
        return "raw_to_prepared_drop", "expected function is absent after preparation/schema normalization"
    if not expected_in_runtime and candidate_pool_exception == "bfcl_abstain":
        return "bfcl_abstain_candidate_elision", "BFCL abstain intentionally elides runtime candidate pool"
    if not expected_in_runtime:
        return "prepared_to_runtime_drop", "expected function is absent from runtime candidate pool"
    if not expected_in_ranker or not expected_in_top5:
        return "runtime_to_top5_rank_drop", "expected function is available at runtime but absent from schema top-5"
    if not expected_is_top1:
        return "top5_to_top1_rank_error", "expected function is in schema top-5 but not schema top-1"
    if not selected_is_expected:
        return "top1_to_selected_guard_error", "schema top-1 is expected but final selected function differs"
    if not success:
        return "selected_correct_arg_or_shape_error", "selected function is expected but official scorer still fails"
    return "selected_correct_success", "selected function is expected and official scorer succeeds"


def _bfcl_candidate_coverage_row(row: Dict[str, Any]) -> Dict[str, Any]:
    diagnostic = _first_bfcl_selection_diagnostic(row)
    expected = str(row.get("gold_tool") or "").strip()
    failure_bucket = _reason_bucket(_decode_reasons(row.get("official_bfcl_eval_unsupported_reasons")))
    prepared_records = _candidate_tool_records(row)
    # In aligned BFCL sources, raw function docs and prepared schema are represented
    # by the candidate tool list plus provenance metadata. The two stages are kept
    # separate in the audit so future raw-source manifests can populate raw-only loss.
    raw_records = list(prepared_records)
    runtime_records = _diagnostic_tool_records(
        diagnostic,
        id_key="runtime_candidate_tool_ids",
        original_key="runtime_candidate_original_function_names",
    )
    ranker_records = _diagnostic_tool_records(
        diagnostic,
        id_key="ranker_candidate_tool_ids",
        original_key="ranker_candidate_original_function_names",
    )
    top5_records = _schema_top_records(diagnostic)
    expected_in_raw = _contains_name(raw_records, expected)
    expected_in_prepared = _contains_name(prepared_records, expected)
    expected_in_runtime = _contains_name(runtime_records, expected)
    expected_in_ranker = _contains_name(ranker_records, expected)
    expected_in_top5 = _contains_name(top5_records, expected)
    expected_is_top1 = _contains_name(top5_records[:1], expected)
    selected_is_expected = _selected_matches_expected(diagnostic, expected)
    success = float(row.get("official_bfcl_eval_success", 0.0) or 0.0) >= 1.0
    candidate_pool_exception = str(diagnostic.get("candidate_pool_exception") or "")
    drop_stage, drop_reason = _bfcl_coverage_drop_stage(
        expected=expected,
        expected_in_raw=expected_in_raw,
        expected_in_prepared=expected_in_prepared,
        expected_in_runtime=expected_in_runtime,
        expected_in_ranker=expected_in_ranker,
        expected_in_top5=expected_in_top5,
        expected_is_top1=expected_is_top1,
        selected_is_expected=selected_is_expected,
        success=success,
        candidate_pool_exception=candidate_pool_exception,
    )
    case_type = ":".join(
        item
        for item in [str(row.get("bfcl_group") or "unknown"), str(row.get("bfcl_call_pattern") or "unknown")]
        if item
    )
    return {
        "row_id": f"{row.get('run_index')}::{row.get('task_id')}::{row.get('system')}",
        "run_index": int(row.get("run_index", 0) or 0),
        "task_id": str(row.get("task_id") or ""),
        "system": str(row.get("system") or ""),
        "case_type": case_type,
        "expected_function": expected,
        "raw_function_count": len(raw_records),
        "prepared_function_count": len(prepared_records),
        "runtime_candidate_count": int(diagnostic.get("runtime_candidate_count", len(runtime_records)) or 0),
        "ranker_candidate_count": int(diagnostic.get("ranker_candidate_count", len(ranker_records)) or 0),
        "candidate_pool_preserved": bool(diagnostic.get("candidate_pool_preserved", False)),
        "candidate_pool_source": str(diagnostic.get("candidate_pool_source") or ""),
        "candidate_pool_exception": candidate_pool_exception,
        "planner_narrowing_applied": bool(diagnostic.get("planner_narrowing_applied", False)),
        "abstain_reason": str(diagnostic.get("abstain_reason") or ""),
        "abstain_policy_version": str(diagnostic.get("abstain_policy_version") or ""),
        "abstain_due_to_irrelevance_classifier": bool(diagnostic.get("abstain_due_to_irrelevance_classifier", False)),
        "abstain_due_to_no_viable_schema_top1": bool(diagnostic.get("abstain_due_to_no_viable_schema_top1", False)),
        "abstain_due_to_no_groundable_required_args": bool(diagnostic.get("abstain_due_to_no_groundable_required_args", False)),
        "abstain_due_to_planner_noop": bool(diagnostic.get("abstain_due_to_planner_noop", False)),
        "abstain_due_to_parallel_shape_guard": bool(diagnostic.get("abstain_due_to_parallel_shape_guard", False)),
        "abstain_with_schema_top1_available": bool(diagnostic.get("abstain_with_schema_top1_available", False)),
        "abstain_with_operation_cues_present": bool(diagnostic.get("abstain_with_operation_cues_present", False)),
        "abstain_blocked_by_serial_schema_top1": bool(diagnostic.get("abstain_blocked_by_serial_schema_top1", False)),
        "serial_positive_call_forced": bool(diagnostic.get("serial_positive_call_forced", False)),
        "irrelevance_abstain_allowed": bool(diagnostic.get("irrelevance_abstain_allowed", False)),
        "explicit_no_call_signal": bool(diagnostic.get("explicit_no_call_signal", False)),
        "operation_cues_present": bool(diagnostic.get("operation_cues_present", False)),
        "expected_in_raw_function_docs": expected_in_raw,
        "expected_in_prepared_schema": expected_in_prepared,
        "expected_in_runtime_candidates": expected_in_runtime,
        "expected_in_ranker_candidates": expected_in_ranker,
        "expected_in_schema_top5": expected_in_top5,
        "expected_is_schema_top1": expected_is_top1,
        "selected_is_expected": selected_is_expected,
        "selected_correct_but_args_wrong": selected_is_expected and failure_bucket in {"missing_required", "value_error", "other_official_failure"},
        "selected_correct_but_call_shape_wrong": selected_is_expected and failure_bucket in {"wrong_count", "multi_turn_mismatch", "multi_turn_other"},
        "raw_match_name": _match_name(raw_records, expected, "bfcl_original_function_name"),
        "prepared_match_tool_id": _match_name(prepared_records, expected, "tool_id"),
        "runtime_match_tool_id": _match_name(runtime_records, expected, "tool_id"),
        "drop_stage": drop_stage,
        "drop_reason": drop_reason,
        "schema_top5": top5_records,
        "selected_tool_id": str(diagnostic.get("selected_tool_id") or row.get("chosen_tool") or ""),
        "selected_reason": str(diagnostic.get("selected_reason") or ""),
        "official_failure_bucket": failure_bucket,
        "official_success": success,
    }


def _ratio(count: int, denominator: int) -> float:
    return float(count) / float(denominator) if denominator else 0.0


def _coverage_summary_for_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    selected_expected = [row for row in rows if row.get("selected_is_expected")]
    runtime_expected = [row for row in rows if row.get("expected_in_runtime_candidates")]
    abstain_rows = [row for row in rows if row.get("candidate_pool_exception") == "bfcl_abstain"]
    return {
        "total_rows": total,
        "expected_in_raw_function_docs": sum(1 for row in rows if row.get("expected_in_raw_function_docs")),
        "expected_in_prepared_schema": sum(1 for row in rows if row.get("expected_in_prepared_schema")),
        "expected_in_runtime_candidates": sum(1 for row in rows if row.get("expected_in_runtime_candidates")),
        "expected_in_schema_top5": sum(1 for row in rows if row.get("expected_in_schema_top5")),
        "expected_is_schema_top1": sum(1 for row in rows if row.get("expected_is_schema_top1")),
        "selected_is_expected": len(selected_expected),
        "selected_expected_success": sum(1 for row in selected_expected if row.get("official_success")),
        "coverage_raw": _ratio(sum(1 for row in rows if row.get("expected_in_raw_function_docs")), total),
        "coverage_prepared": _ratio(sum(1 for row in rows if row.get("expected_in_prepared_schema")), total),
        "coverage_runtime": _ratio(sum(1 for row in rows if row.get("expected_in_runtime_candidates")), total),
        "coverage_top5": _ratio(sum(1 for row in rows if row.get("expected_in_schema_top5")), total),
        "ranker_top1": _ratio(sum(1 for row in rows if row.get("expected_is_schema_top1")), len(runtime_expected)),
        "selection_accuracy": _ratio(len(selected_expected), len(runtime_expected)),
        "arg_success_given_correct_tool": _ratio(sum(1 for row in selected_expected if row.get("official_success")), len(selected_expected)),
        "drop_stage_counts": dict(Counter(str(row.get("drop_stage") or "unknown") for row in rows)),
        "abstain_substage_counts": {
            "bfcl_abstain_total": len(abstain_rows),
            "abstain_due_to_irrelevance_classifier": sum(1 for row in abstain_rows if row.get("abstain_due_to_irrelevance_classifier")),
            "abstain_due_to_no_viable_schema_top1": sum(1 for row in abstain_rows if row.get("abstain_due_to_no_viable_schema_top1")),
            "abstain_due_to_no_groundable_required_args": sum(1 for row in abstain_rows if row.get("abstain_due_to_no_groundable_required_args")),
            "abstain_due_to_planner_noop": sum(1 for row in abstain_rows if row.get("abstain_due_to_planner_noop")),
            "abstain_due_to_parallel_shape_guard": sum(1 for row in abstain_rows if row.get("abstain_due_to_parallel_shape_guard")),
            "abstain_with_schema_top1_available": sum(1 for row in abstain_rows if row.get("abstain_with_schema_top1_available")),
            "abstain_with_operation_cues_present": sum(1 for row in abstain_rows if row.get("abstain_with_operation_cues_present")),
            "abstain_blocked_by_serial_schema_top1": sum(1 for row in rows if row.get("abstain_blocked_by_serial_schema_top1")),
            "serial_positive_call_forced": sum(1 for row in rows if row.get("serial_positive_call_forced")),
            "irrelevance_abstain_allowed": sum(1 for row in rows if row.get("irrelevance_abstain_allowed")),
        },
        "abstain_reason_counts": dict(Counter(str(row.get("abstain_reason") or "unknown") for row in abstain_rows)),
    }


def _bfcl_candidate_coverage_audit(scored_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [_bfcl_candidate_coverage_row(row) for row in scored_rows]
    runtime_gold_leak_count = sum(
        1
        for row in scored_rows
        if _diagnostic_contains_gold_fields(_first_bfcl_selection_diagnostic(row))
    )
    by_case: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_system: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_system_case: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        case_type = str(row.get("case_type") or "unknown")
        system = str(row.get("system") or "unknown")
        by_case[case_type].append(row)
        by_system[system].append(row)
        by_system_case[f"{system}::{case_type}"].append(row)
    return {
        "audit_schema_version": "bfcl_candidate_coverage_audit_v1",
        "gold_fields_added_after_execution": True,
        "runtime_diagnostics_gold_free": runtime_gold_leak_count == 0,
        "runtime_gold_field_leak_count": runtime_gold_leak_count,
        "summary": _coverage_summary_for_rows(rows),
        "by_case_type": {key: _coverage_summary_for_rows(value) for key, value in sorted(by_case.items())},
        "by_system": {key: _coverage_summary_for_rows(value) for key, value in sorted(by_system.items())},
        "by_system_case_type": {key: _coverage_summary_for_rows(value) for key, value in sorted(by_system_case.items())},
        "rows": rows,
    }


def _write_bfcl_candidate_coverage_markdown(audit: Dict[str, Any], path: Path) -> None:
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    lines = [
        "# BFCL Candidate Coverage Audit",
        "",
        "This report is gold-enriched after execution. Runtime diagnostics remain gold-free.",
        "",
        f"- audit_schema_version: `{audit.get('audit_schema_version')}`",
        f"- runtime_diagnostics_gold_free: `{audit.get('runtime_diagnostics_gold_free')}`",
        "",
        "## Funnel Summary",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in [
        "total_rows",
        "expected_in_raw_function_docs",
        "expected_in_prepared_schema",
        "expected_in_runtime_candidates",
        "expected_in_schema_top5",
        "expected_is_schema_top1",
        "selected_is_expected",
        "selected_expected_success",
        "coverage_raw",
        "coverage_prepared",
        "coverage_runtime",
        "coverage_top5",
        "ranker_top1",
        "selection_accuracy",
        "arg_success_given_correct_tool",
    ]:
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.extend(["", "## Drop Stages", "", "| drop_stage | count |", "|---|---:|"])
    for stage, count in sorted((summary.get("drop_stage_counts") or {}).items()):
        lines.append(f"| {stage} | {count} |")
    lines.extend(["", "## By Case Type", "", "| case_type | total | runtime coverage | top5 coverage | selected expected | top drop stage |", "|---|---:|---:|---:|---:|---|"])
    for case_type, case_summary in audit.get("by_case_type", {}).items():
        drops = case_summary.get("drop_stage_counts") or {}
        top_drop = max(drops.items(), key=lambda item: item[1])[0] if drops else "none"
        lines.append(
            f"| {case_type} | {case_summary.get('total_rows', 0)} | {case_summary.get('coverage_runtime', 0)} | {case_summary.get('coverage_top5', 0)} | {case_summary.get('selected_is_expected', 0)} | {top_drop} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _json_dict_field(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _expected_calls_from_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    structure = _json_dict_field(row.get("expected_call_structure"))
    raw_calls = structure.get("calls", [])
    if not isinstance(raw_calls, list):
        raw_calls = []
    calls: List[Dict[str, Any]] = []
    for raw_call in raw_calls:
        if not isinstance(raw_call, dict):
            continue
        tool_name = str(
            raw_call.get("tool_name")
            or raw_call.get("name")
            or raw_call.get("function")
            or raw_call.get("tool_id")
            or ""
        ).strip()
        arguments = raw_call.get("arguments", raw_call.get("args", {}))
        calls.append(
            {
                "tool_name": tool_name,
                "arguments": arguments if isinstance(arguments, dict) else {},
            }
        )
    return calls


def _trace_payload(row: Dict[str, Any]) -> Dict[str, Any] | None:
    trace_path_value = str(row.get("trace_path") or "").strip()
    if not trace_path_value:
        return None
    trace_path = Path(trace_path_value)
    if not trace_path.is_absolute():
        trace_path = ROOT_DIR / trace_path_value
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _emitted_calls_from_trace(row: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    payload = _trace_payload(row)
    if payload is None:
        return [], "trace_missing_or_unparseable"
    events = payload.get("events", [])
    if not isinstance(events, list):
        return [], "trace_missing_or_unparseable"
    calls: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict) or str(event.get("event_type") or "") != "tool_call":
            continue
        args = event.get("tool_args", {})
        calls.append(
            {
                "tool_name": str(event.get("tool_id") or "").strip(),
                "arguments": args if isinstance(args, dict) else {},
            }
        )
    return calls, "ok"


def _parameter_schema_by_name(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    schemas: Dict[str, Dict[str, Any]] = {}
    for raw_tool in _json_list_field(row.get("candidate_tools")):
        if isinstance(raw_tool, str):
            schemas[raw_tool] = {}
            continue
        if not isinstance(raw_tool, dict):
            continue
        metadata = raw_tool.get("metadata", {}) if isinstance(raw_tool.get("metadata"), dict) else {}
        parameters = raw_tool.get("parameters") or metadata.get("parameters") or {}
        if not isinstance(parameters, dict):
            parameters = {}
        names = {
            str(raw_tool.get("tool_id") or "").strip(),
            str(raw_tool.get("name") or "").strip(),
            str(metadata.get("bfcl_original_function_name") or "").strip(),
            str(metadata.get("canonical_name") or "").strip(),
        }
        for name in names:
            if name:
                schemas[name] = parameters
    return schemas


def _schema_type_matches(value: Any, schema: Dict[str, Any]) -> bool:
    expected_type = str(schema.get("type") or "").lower()
    if not expected_type:
        return True
    if expected_type in {"string", "str"}:
        return isinstance(value, str)
    if expected_type in {"integer", "int"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type in {"number", "float"}:
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected_type in {"boolean", "bool"}:
        return isinstance(value, bool)
    if expected_type in {"array", "list"}:
        return isinstance(value, list)
    if expected_type in {"object", "dict"}:
        return isinstance(value, dict)
    return True


def _normalize_bfcl_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return lowered
    if isinstance(value, list):
        return [_normalize_bfcl_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_bfcl_value(nested) for key, nested in sorted(value.items())}
    return value


def _nested_structure_mismatches(expected: Any, emitted: Any, prefix: str) -> List[str]:
    mismatches: List[str] = []
    if isinstance(expected, dict):
        if not isinstance(emitted, dict):
            return [prefix]
        for key, expected_value in expected.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in emitted:
                mismatches.append(child_prefix)
                continue
            mismatches.extend(_nested_structure_mismatches(expected_value, emitted.get(key), child_prefix))
        return mismatches
    if isinstance(expected, list):
        if not isinstance(emitted, list):
            return [prefix]
        if expected and emitted:
            mismatches.extend(_nested_structure_mismatches(expected[0], emitted[0], f"{prefix}[0]"))
        return mismatches
    return mismatches


def _argument_mismatches(
    expected_calls: List[Dict[str, Any]],
    emitted_calls: List[Dict[str, Any]],
    row: Dict[str, Any],
) -> Dict[str, List[str]]:
    schema_by_name = _parameter_schema_by_name(row)
    missing_required: List[str] = []
    wrong_type: List[str] = []
    wrong_value: List[str] = []
    wrong_structure: List[str] = []
    for index, expected_call in enumerate(expected_calls[: len(emitted_calls)]):
        emitted_call = emitted_calls[index]
        tool_name = str(expected_call.get("tool_name") or emitted_call.get("tool_name") or "")
        expected_args = expected_call.get("arguments", {})
        emitted_args = emitted_call.get("arguments", {})
        if not isinstance(expected_args, dict):
            expected_args = {}
        if not isinstance(emitted_args, dict):
            emitted_args = {}
        schema = schema_by_name.get(tool_name, {})
        required = schema.get("required", []) if isinstance(schema, dict) else []
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if not isinstance(required, list):
            required = []
        if not isinstance(properties, dict):
            properties = {}
        required_keys = {str(key) for key in required}
        required_keys.update(str(key) for key in expected_args.keys())
        for arg_name in sorted(required_keys):
            label = f"call_{index + 1}.{arg_name}"
            emitted_value = emitted_args.get(arg_name)
            expected_value = expected_args.get(arg_name)
            if arg_name not in emitted_args or emitted_value in (None, ""):
                if expected_value not in (None, ""):
                    missing_required.append(label)
                continue
            arg_schema = properties.get(arg_name, {}) if isinstance(properties.get(arg_name, {}), dict) else {}
            structure_mismatches = _nested_structure_mismatches(expected_value, emitted_value, label)
            if structure_mismatches:
                wrong_structure.extend(structure_mismatches)
                continue
            if not _schema_type_matches(emitted_value, arg_schema):
                wrong_type.append(label)
                continue
            if _normalize_bfcl_value(expected_value) != _normalize_bfcl_value(emitted_value):
                wrong_value.append(label)
    return {
        "missing_required_args": missing_required,
        "wrong_type_args": wrong_type,
        "wrong_value_args": wrong_value,
        "nested_structure_mismatches": wrong_structure,
    }


def _bfcl_arg_name_from_label(label: str) -> str:
    raw = str(label or "")
    if "." in raw:
        raw = raw.split(".", 1)[1]
    return raw.split(".", 1)[0].split("[", 1)[0]


def _missing_required_subcauses(
    *,
    missing_required_args: List[str],
    diagnostic: Dict[str, Any],
    emitted_calls: List[Dict[str, Any]],
    trace_metric_tool_calls: int,
) -> Dict[str, Any]:
    if not missing_required_args:
        return {
            "missing_required_due_to_no_query_cue": False,
            "missing_required_due_to_schema_alias_mismatch": False,
            "missing_required_due_to_grounder_not_attempted": False,
            "missing_required_due_to_value_filtered": False,
            "missing_required_due_to_final_answer_serializer_drop": False,
            "missing_required_no_query_cue_args": [],
            "missing_required_schema_alias_mismatch_args": [],
            "missing_required_value_filtered_args": [],
            "missing_required_serializer_drop_args": [],
        }
    required_args = {str(item) for item in diagnostic.get("required_args", []) if str(item)}
    grounded_args = {str(item) for item in diagnostic.get("grounded_required_args", []) if str(item)}
    ungrounded_args = {str(item) for item in diagnostic.get("ungrounded_required_args", []) if str(item)}
    source_by_arg = diagnostic.get("grounding_source_by_arg", {}) if isinstance(diagnostic.get("grounding_source_by_arg"), dict) else {}
    attempted = bool(diagnostic.get("serial_required_grounding_attempted"))
    if not attempted:
        return {
            "missing_required_due_to_no_query_cue": False,
            "missing_required_due_to_schema_alias_mismatch": False,
            "missing_required_due_to_grounder_not_attempted": True,
            "missing_required_due_to_value_filtered": False,
            "missing_required_due_to_final_answer_serializer_drop": False,
            "missing_required_no_query_cue_args": [],
            "missing_required_schema_alias_mismatch_args": [],
            "missing_required_value_filtered_args": [],
            "missing_required_serializer_drop_args": [],
        }
    emitted_arg_keys = set()
    for call in emitted_calls:
        args = call.get("arguments", {}) if isinstance(call, dict) else {}
        if isinstance(args, dict):
            emitted_arg_keys.update(str(key) for key in args.keys())

    no_query_cue: List[str] = []
    schema_alias_mismatch: List[str] = []
    value_filtered: List[str] = []
    serializer_drop: List[str] = []
    for label in missing_required_args:
        arg = _bfcl_arg_name_from_label(label)
        source = str(source_by_arg.get(arg) or "")
        if required_args and arg not in required_args:
            schema_alias_mismatch.append(label)
        elif arg in grounded_args and arg not in emitted_arg_keys:
            serializer_drop.append(label)
        elif arg in ungrounded_args or source == "unresolved":
            no_query_cue.append(label)
        elif trace_metric_tool_calls > 0 and not emitted_calls:
            serializer_drop.append(label)
        else:
            value_filtered.append(label)
    return {
        "missing_required_due_to_no_query_cue": bool(no_query_cue),
        "missing_required_due_to_schema_alias_mismatch": bool(schema_alias_mismatch),
        "missing_required_due_to_grounder_not_attempted": bool(missing_required_args and not attempted),
        "missing_required_due_to_value_filtered": bool(value_filtered),
        "missing_required_due_to_final_answer_serializer_drop": bool(serializer_drop),
        "missing_required_no_query_cue_args": no_query_cue,
        "missing_required_schema_alias_mismatch_args": schema_alias_mismatch,
        "missing_required_value_filtered_args": value_filtered,
        "missing_required_serializer_drop_args": serializer_drop,
    }


def _call_order_mismatch(expected_calls: List[Dict[str, Any]], emitted_calls: List[Dict[str, Any]]) -> bool:
    if len(expected_calls) != len(emitted_calls):
        return False
    expected_order = [str(call.get("tool_name") or "") for call in expected_calls]
    emitted_order = [str(call.get("tool_name") or "") for call in emitted_calls]
    return expected_order != emitted_order and sorted(expected_order) == sorted(emitted_order)


def _call_shape_breakdown(
    *,
    selected_is_expected: bool,
    expected_calls: List[Dict[str, Any]],
    emitted_calls: List[Dict[str, Any]],
    call_pattern: str,
    case_type: str,
    failure_bucket: str,
) -> Dict[str, Any]:
    expected_call_count = len(expected_calls)
    emitted_call_count = len(emitted_calls)
    call_count_delta = emitted_call_count - expected_call_count
    is_parallel = call_pattern == "parallel" or "parallel" in case_type
    wrong_call_count = selected_is_expected and expected_call_count != emitted_call_count
    wrong_call_order = selected_is_expected and _call_order_mismatch(expected_calls, emitted_calls)
    expected_tools = [str(call.get("tool_name") or "") for call in expected_calls]
    emitted_tools = [str(call.get("tool_name") or "") for call in emitted_calls]
    same_tool_multiset = Counter(expected_tools) == Counter(emitted_tools)
    parallel_shape_error = bool(selected_is_expected and is_parallel and (wrong_call_count or failure_bucket == "wrong_count"))
    return {
        "call_count_delta": call_count_delta,
        "wrong_call_count": wrong_call_count,
        "wrong_call_order": wrong_call_order,
        "wrong_call_count_missing_calls": bool(selected_is_expected and expected_call_count > emitted_call_count),
        "wrong_call_count_extra_calls": bool(selected_is_expected and emitted_call_count > expected_call_count),
        "wrong_call_count_zero_emitted": bool(selected_is_expected and expected_call_count > 0 and emitted_call_count == 0),
        "wrong_call_count_single_for_multiple": bool(selected_is_expected and expected_call_count > 1 and emitted_call_count == 1),
        "wrong_call_count_multiple_for_single": bool(selected_is_expected and expected_call_count == 1 and emitted_call_count > 1),
        "parallel_expected_but_serial_emitted": bool(selected_is_expected and is_parallel and expected_call_count > 1 and emitted_call_count == 1),
        "serial_expected_but_parallel_emitted": bool(selected_is_expected and not is_parallel and expected_call_count == 1 and emitted_call_count > 1),
        "parallel_grouping_mismatch": bool(selected_is_expected and is_parallel and failure_bucket == "wrong_count" and expected_call_count == emitted_call_count and not same_tool_multiset),
        "parallel_call_count_correct_but_grouping_wrong": bool(selected_is_expected and is_parallel and expected_call_count == emitted_call_count and failure_bucket == "wrong_count"),
        "parallel_order_only_mismatch": bool(selected_is_expected and is_parallel and wrong_call_order),
        "parallel_or_multiple_shape_mismatch": parallel_shape_error,
    }


def _trace_parallel_bridge_features(trace_payload: Dict[str, Any] | None) -> Dict[str, Any]:
    events = trace_payload.get("events", []) if isinstance(trace_payload, dict) else []
    if not isinstance(events, list):
        events = []
    workflow_step_count = 0
    trace_tool_call_event_count = 0
    preflight_blocked_steps: set[str] = set()
    preflight_missing_required_inputs: set[str] = set()
    stop_reason = ""
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        if event_type == "tool_call":
            trace_tool_call_event_count += 1
        if event_type == "plan_generated":
            output = event.get("output", {}) if isinstance(event.get("output"), dict) else {}
            try:
                workflow_step_count = max(workflow_step_count, int(output.get("steps", 0) or 0))
            except (TypeError, ValueError):
                pass
        if event_type == "preflight_check":
            output = event.get("output", {}) if isinstance(event.get("output"), dict) else {}
            missing = output.get("missing_required_inputs", [])
            if isinstance(missing, list):
                preflight_missing_required_inputs.update(str(item) for item in missing if str(item))
            status = str(output.get("status") or "").lower()
            reason = str(output.get("reason") or "").lower()
            ok_value = output.get("ok")
            blocked = bool(
                missing
                or status == "failed"
                or reason == "missing_required_input"
                or ok_value is False
            )
            if blocked:
                step_id = str(event.get("step_id") or "").strip()
                if step_id:
                    preflight_blocked_steps.add(step_id)
        if event_type == "stop":
            output = event.get("output", {}) if isinstance(event.get("output"), dict) else {}
            stop_reason = str(output.get("reason") or output.get("status") or stop_reason or "")
    metrics = trace_payload.get("metrics", {}) if isinstance(trace_payload, dict) else {}
    if isinstance(metrics, dict):
        try:
            workflow_step_count = max(workflow_step_count, int(metrics.get("total_steps", 0) or 0))
        except (TypeError, ValueError):
            pass
    return {
        "parallel_workflow_step_count": workflow_step_count,
        "parallel_trace_tool_call_event_count": trace_tool_call_event_count,
        "parallel_preflight_blocked_step_count": len(preflight_blocked_steps),
        "parallel_preflight_missing_required_inputs": sorted(preflight_missing_required_inputs),
        "parallel_stop_reason": stop_reason,
    }


def _parallel_count_alignment_breakdown(
    *,
    selected_is_expected: bool,
    is_parallel_case: bool,
    expected_call_count: int,
    emitted_call_count: int,
    trace_metric_tool_calls: int,
    parallel_argument_set_count: int,
    parallel_clause_materialized_count: int,
) -> Dict[str, Any]:
    argument_set_count_delta = parallel_argument_set_count - expected_call_count
    materialized_count_delta = parallel_clause_materialized_count - expected_call_count
    emitted_vs_materialized_delta = emitted_call_count - parallel_clause_materialized_count
    trace_vs_materialized_delta = trace_metric_tool_calls - parallel_clause_materialized_count
    bucket = ""
    if selected_is_expected and is_parallel_case:
        if expected_call_count > 1 and parallel_argument_set_count == 1:
            bucket = "single_extracted_for_multi_expected"
        elif expected_call_count == 1 and parallel_argument_set_count > 1:
            bucket = "multi_extracted_for_single_expected"
        elif parallel_argument_set_count < expected_call_count:
            bucket = "extracted_too_few_argument_sets"
        elif parallel_argument_set_count > expected_call_count:
            bucket = "extracted_too_many_argument_sets"
        elif parallel_clause_materialized_count == emitted_call_count and emitted_call_count != expected_call_count:
            bucket = "materialized_count_matches_emitted_but_not_expected"
        elif parallel_clause_materialized_count < parallel_argument_set_count:
            bucket = "materialized_less_than_extracted"
        elif emitted_call_count < parallel_clause_materialized_count:
            bucket = "emitted_less_than_materialized"
        elif emitted_call_count > expected_call_count:
            bucket = "emitted_more_than_expected"
        elif expected_call_count == parallel_clause_materialized_count == emitted_call_count:
            bucket = "count_aligned"
        else:
            bucket = "parallel_count_alignment_unclassified"
    return {
        "argument_set_count_delta": argument_set_count_delta,
        "materialized_count_delta": materialized_count_delta,
        "emitted_vs_materialized_delta": emitted_vs_materialized_delta,
        "trace_vs_materialized_delta": trace_vs_materialized_delta,
        "parallel_count_alignment_bucket": bucket,
    }


def _parallel_bridge_breakdown(
    *,
    selected_is_expected: bool,
    is_parallel_case: bool,
    official_success: bool,
    failure_bucket: str,
    expected_call_count: int,
    emitted_call_count: int,
    trace_metric_tool_calls: int,
    shape: Dict[str, Any],
    mismatches: Dict[str, List[str]],
    parallel_argument_set_count: int,
    parallel_clause_materialized_count: int,
    trace_features: Dict[str, Any],
) -> Dict[str, Any]:
    workflow_step_count = int(trace_features.get("parallel_workflow_step_count") or 0)
    trace_tool_call_event_count = int(trace_features.get("parallel_trace_tool_call_event_count") or 0)
    preflight_blocked_count = int(trace_features.get("parallel_preflight_blocked_step_count") or 0)
    trace_call_count = max(trace_metric_tool_calls, trace_tool_call_event_count)
    trace_matches_emitted = trace_call_count == emitted_call_count
    emitted_matches_expected = emitted_call_count == expected_call_count
    stage = ""
    reason = ""
    if selected_is_expected and is_parallel_case:
        if parallel_argument_set_count > 0 and workflow_step_count == 0:
            stage = "parallel_sets_extracted_but_no_workflow_steps"
            reason = "argument_sets_extracted_without_plan_steps"
        elif parallel_clause_materialized_count > 0 and trace_call_count == 0 and preflight_blocked_count > 0:
            stage = "parallel_workflow_steps_built_but_preflight_blocked"
            reason = "preflight_missing_required_inputs"
        elif parallel_clause_materialized_count > 0 and trace_call_count == 0:
            stage = "parallel_workflow_steps_built_but_not_executed"
            reason = "no_tool_call_events_after_materialized_steps"
        elif trace_call_count > 0 and emitted_call_count == 0:
            stage = "parallel_tool_calls_in_trace_but_not_in_emitted_answer"
            reason = "trace_to_bfcl_answer_extraction_drop"
        elif emitted_call_count > 0 and emitted_call_count != expected_call_count:
            stage = "parallel_emitted_calls_wrong_count"
            reason = "emitted_call_count_differs_from_expected"
        elif emitted_matches_expected and official_success:
            stage = "parallel_emitted_calls_success"
            reason = "official_success"
        elif emitted_matches_expected and str(failure_bucket) == "wrong_count":
            stage = "parallel_emitted_calls_but_wrong_official_grouping"
            reason = "official_wrong_count_with_matching_call_count"
        elif emitted_matches_expected and (
            mismatches.get("missing_required_args")
            or mismatches.get("wrong_type_args")
            or mismatches.get("wrong_value_args")
            or mismatches.get("nested_structure_mismatches")
            or str(failure_bucket) in {"missing_required", "value_error", "other_official_failure"}
        ):
            stage = "parallel_emitted_calls_wrong_args"
            reason = "argument_mismatch_after_parallel_emission"
        elif bool(shape.get("parallel_or_multiple_shape_mismatch")):
            stage = "parallel_emitted_calls_wrong_count"
            reason = "parallel_shape_mismatch"
        else:
            stage = "parallel_bridge_not_applicable"
            reason = "no_parallel_bridge_drop_detected"
    return {
        **trace_features,
        "parallel_bridge_drop_stage": stage,
        "parallel_bridge_drop_reason": reason,
        "parallel_trace_calls_match_emitted_calls": trace_matches_emitted,
        "parallel_emitted_calls_match_expected_count": emitted_matches_expected,
    }


def _bfcl_selected_correct_failure_row(row: Dict[str, Any]) -> Dict[str, Any]:
    coverage = _bfcl_candidate_coverage_row(row)
    expected_calls = _expected_calls_from_row(row)
    emitted_calls, trace_status = _emitted_calls_from_trace(row)
    selected_is_expected = bool(coverage.get("selected_is_expected"))
    official_success = float(row.get("official_bfcl_eval_success", 0.0) or 0.0) >= 1.0
    failure_bucket = str(coverage.get("official_failure_bucket") or "")
    expected_call_count = len(expected_calls)
    emitted_call_count = len(emitted_calls)
    call_pattern = str(row.get("bfcl_call_pattern") or "")
    case_type = str(coverage.get("case_type") or "")
    shape = _call_shape_breakdown(
        selected_is_expected=selected_is_expected,
        expected_calls=expected_calls,
        emitted_calls=emitted_calls,
        call_pattern=call_pattern,
        case_type=case_type,
        failure_bucket=failure_bucket,
    )
    diagnostic = _first_bfcl_selection_diagnostic(row)
    trace_payload = _trace_payload(row)
    trace_metric_tool_calls = 0
    if isinstance(trace_payload, dict):
        metrics = trace_payload.get("metrics", {})
        if isinstance(metrics, dict):
            try:
                trace_metric_tool_calls = int(metrics.get("tool_calls", 0) or 0)
            except (TypeError, ValueError):
                trace_metric_tool_calls = 0
    trace_features = _trace_parallel_bridge_features(trace_payload)
    zero_emitted = bool(expected_call_count > 0 and emitted_call_count == 0)
    candidate_pool_exception = str(coverage.get("candidate_pool_exception") or "")
    selected_required_coverage = diagnostic.get("selected_required_argument_coverage") if isinstance(diagnostic, dict) else None
    try:
        selected_required_coverage_value = float(selected_required_coverage or 0.0)
    except (TypeError, ValueError):
        selected_required_coverage_value = 0.0
    is_parallel_case = call_pattern == "parallel" or "parallel" in case_type
    parallel_argument_set_count = int(diagnostic.get("parallel_argument_set_count") or 0)
    parallel_clause_materialized_count = int(diagnostic.get("parallel_clause_materialized_count") or 0)
    is_serial_case = call_pattern == "serial" and "multi_turn" not in case_type
    trace_tool_call_expected_by_bfcl_serial = bool(diagnostic.get("trace_tool_call_expected_by_bfcl_serial"))
    serial_selected_top1_materialization_blocked = bool(
        diagnostic.get("serial_selected_top1_materialization_blocked")
    )
    selected_top1_but_no_emitted_call = bool(
        zero_emitted
        and selected_is_expected
        and is_serial_case
        and trace_tool_call_expected_by_bfcl_serial
        and candidate_pool_exception != "bfcl_abstain"
    )
    selected_top1_but_final_answer_parser_drops_call = bool(
        selected_is_expected and emitted_call_count == 0 and trace_metric_tool_calls > 0
    )
    wrong_call_count = bool(shape["wrong_call_count"])
    wrong_call_order = bool(shape["wrong_call_order"])
    parallel_shape_error = bool(shape["parallel_or_multiple_shape_mismatch"])
    multi_turn_state_mismatch = bool(selected_is_expected and failure_bucket in {"multi_turn_mismatch", "multi_turn_other"})
    mismatches = _argument_mismatches(expected_calls, emitted_calls, row) if selected_is_expected and not wrong_call_count else {
        "missing_required_args": [],
        "wrong_type_args": [],
        "wrong_value_args": [],
        "nested_structure_mismatches": [],
    }

    if not selected_is_expected:
        selected_correct_failure_bucket = "not_selected_expected"
    elif trace_status != "ok":
        selected_correct_failure_bucket = "trace_missing_or_unparseable"
    elif official_success:
        selected_correct_failure_bucket = "selected_correct_success"
    elif multi_turn_state_mismatch:
        selected_correct_failure_bucket = "multi_turn_state_error"
    elif parallel_shape_error:
        selected_correct_failure_bucket = "parallel_shape_error"
    elif wrong_call_count:
        selected_correct_failure_bucket = "wrong_call_count"
    elif wrong_call_order:
        selected_correct_failure_bucket = "wrong_call_order"
    elif mismatches["missing_required_args"] or failure_bucket == "missing_required":
        selected_correct_failure_bucket = "missing_required"
    elif mismatches["nested_structure_mismatches"]:
        selected_correct_failure_bucket = "wrong_arg_structure"
    elif mismatches["wrong_type_args"]:
        selected_correct_failure_bucket = "wrong_arg_type"
    elif mismatches["wrong_value_args"] or failure_bucket in {"value_error", "other_official_failure"}:
        selected_correct_failure_bucket = "wrong_arg_value"
    else:
        selected_correct_failure_bucket = "other_selected_correct_failure"

    missing_required_subcauses = _missing_required_subcauses(
        missing_required_args=mismatches["missing_required_args"],
        diagnostic=diagnostic if isinstance(diagnostic, dict) else {},
        emitted_calls=emitted_calls,
        trace_metric_tool_calls=trace_metric_tool_calls,
    )
    parallel_bridge = _parallel_bridge_breakdown(
        selected_is_expected=selected_is_expected,
        is_parallel_case=is_parallel_case,
        official_success=official_success,
        failure_bucket=failure_bucket,
        expected_call_count=expected_call_count,
        emitted_call_count=emitted_call_count,
        trace_metric_tool_calls=trace_metric_tool_calls,
        shape=shape,
        mismatches=mismatches,
        parallel_argument_set_count=parallel_argument_set_count,
        parallel_clause_materialized_count=parallel_clause_materialized_count,
        trace_features=trace_features,
    )
    parallel_count_alignment = _parallel_count_alignment_breakdown(
        selected_is_expected=selected_is_expected,
        is_parallel_case=is_parallel_case,
        expected_call_count=expected_call_count,
        emitted_call_count=emitted_call_count,
        trace_metric_tool_calls=trace_metric_tool_calls,
        parallel_argument_set_count=parallel_argument_set_count,
        parallel_clause_materialized_count=parallel_clause_materialized_count,
    )

    return {
        "row_id": str(coverage.get("row_id") or ""),
        "run_index": int(row.get("run_index", 0) or 0),
        "task_id": str(row.get("task_id") or ""),
        "system": str(row.get("system") or ""),
        "case_type": case_type,
        "official_dataset_category": str(row.get("official_dataset_category") or ""),
        "selected_is_expected": selected_is_expected,
        "official_success": official_success,
        "official_failure_bucket": failure_bucket,
        "expected_call_count": expected_call_count,
        "emitted_call_count": emitted_call_count,
        "call_count_delta": shape["call_count_delta"],
        "missing_required_args": mismatches["missing_required_args"],
        "wrong_type_args": mismatches["wrong_type_args"],
        "wrong_value_args": mismatches["wrong_value_args"],
        "nested_structure_mismatches": mismatches["nested_structure_mismatches"],
        **missing_required_subcauses,
        "wrong_call_count": wrong_call_count,
        "wrong_call_order": wrong_call_order,
        "wrong_call_count_missing_calls": shape["wrong_call_count_missing_calls"],
        "wrong_call_count_extra_calls": shape["wrong_call_count_extra_calls"],
        "wrong_call_count_zero_emitted": shape["wrong_call_count_zero_emitted"],
        "wrong_call_count_single_for_multiple": shape["wrong_call_count_single_for_multiple"],
        "wrong_call_count_multiple_for_single": shape["wrong_call_count_multiple_for_single"],
        "parallel_expected_but_serial_emitted": shape["parallel_expected_but_serial_emitted"],
        "serial_expected_but_parallel_emitted": shape["serial_expected_but_parallel_emitted"],
        "parallel_grouping_mismatch": shape["parallel_grouping_mismatch"],
        "parallel_call_count_correct_but_grouping_wrong": shape["parallel_call_count_correct_but_grouping_wrong"],
        "parallel_order_only_mismatch": shape["parallel_order_only_mismatch"],
        "parallel_or_multiple_shape_mismatch": parallel_shape_error,
        "multi_turn_state_mismatch": multi_turn_state_mismatch,
        "zero_emitted_due_to_abstain_classifier": bool(zero_emitted and candidate_pool_exception == "bfcl_abstain"),
        "zero_emitted_after_schema_selection": bool(zero_emitted and selected_is_expected and candidate_pool_exception != "bfcl_abstain"),
        "zero_emitted_due_to_call_shape_canonicalizer": bool(zero_emitted and selected_is_expected and not is_parallel_case),
        "zero_emitted_due_to_parallel_clause_drop": bool(zero_emitted and selected_is_expected and is_parallel_case),
        "zero_emitted_due_to_no_grounded_args": bool(zero_emitted and selected_is_expected and selected_required_coverage_value == 0.0),
        "selected_top1_but_no_emitted_call": selected_top1_but_no_emitted_call,
        "selected_top1_but_trace_has_call_not_in_final_answer": selected_top1_but_final_answer_parser_drops_call,
        "selected_top1_but_final_answer_parser_drops_call": selected_top1_but_final_answer_parser_drops_call,
        "selected_top1_but_serial_call_missing_args_and_suppressed": bool(
            selected_top1_but_no_emitted_call and selected_required_coverage_value == 0.0
        ),
        "parallel_materialization_policy_version": str(diagnostic.get("parallel_materialization_policy_version") or ""),
        "parallel_argument_sets_extracted": bool(diagnostic.get("parallel_argument_sets_extracted")),
        "parallel_argument_set_count": parallel_argument_set_count,
        "parallel_clause_materialized_count": parallel_clause_materialized_count,
        "parallel_clause_drop_count": int(diagnostic.get("parallel_clause_drop_count") or 0),
        "parallel_collapsed_to_serial": bool(diagnostic.get("parallel_collapsed_to_serial")),
        "parallel_clause_drop_reasons": list(diagnostic.get("parallel_clause_drop_reasons") or []) if isinstance(diagnostic.get("parallel_clause_drop_reasons"), list) else [],
        **parallel_bridge,
        **parallel_count_alignment,
        "trace_tool_call_expected_by_bfcl_serial": trace_tool_call_expected_by_bfcl_serial,
        "serial_selected_top1_materialization_blocked": serial_selected_top1_materialization_blocked,
        "serial_materialization_block_reason": str(diagnostic.get("serial_materialization_block_reason") or ""),
        "trace_metric_tool_calls": trace_metric_tool_calls,
        "trace_status": trace_status,
        "selected_correct_failure_bucket": selected_correct_failure_bucket,
    }


def _selected_correct_summary_for_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    selected_rows = [row for row in rows if row.get("selected_is_expected")]
    selected_count = len(selected_rows)
    bucket_counts = Counter(str(row.get("selected_correct_failure_bucket") or "unknown") for row in selected_rows)
    success_count = int(bucket_counts.get("selected_correct_success", 0))
    call_count_deltas = Counter(str(int(row.get("call_count_delta", 0) or 0)) for row in selected_rows)
    parallel_bridge_rows = [row for row in selected_rows if row.get("parallel_bridge_drop_stage")]
    parallel_count_alignment_rows = [row for row in selected_rows if row.get("parallel_count_alignment_bucket")]
    return {
        "total_rows": len(rows),
        "selected_is_expected_count": selected_count,
        "success_given_selected_is_expected": success_count,
        "success_rate_given_selected_is_expected": _ratio(success_count, selected_count),
        "missing_required_given_selected_is_expected": int(bucket_counts.get("missing_required", 0)),
        "wrong_arg_value_given_selected_is_expected": int(bucket_counts.get("wrong_arg_value", 0)),
        "wrong_arg_type_given_selected_is_expected": int(bucket_counts.get("wrong_arg_type", 0)),
        "wrong_arg_structure_given_selected_is_expected": int(bucket_counts.get("wrong_arg_structure", 0)),
        "wrong_call_count_given_selected_is_expected": int(bucket_counts.get("wrong_call_count", 0)),
        "wrong_call_order_given_selected_is_expected": int(bucket_counts.get("wrong_call_order", 0)),
        "parallel_shape_error_given_selected_is_expected": int(bucket_counts.get("parallel_shape_error", 0)),
        "multi_turn_state_error_given_selected_is_expected": int(bucket_counts.get("multi_turn_state_error", 0)),
        "trace_missing_or_unparseable_given_selected_is_expected": int(bucket_counts.get("trace_missing_or_unparseable", 0)),
        "other_selected_correct_failure_given_selected_is_expected": int(bucket_counts.get("other_selected_correct_failure", 0)),
        "wrong_call_count_missing_calls": sum(1 for row in selected_rows if row.get("wrong_call_count_missing_calls")),
        "wrong_call_count_extra_calls": sum(1 for row in selected_rows if row.get("wrong_call_count_extra_calls")),
        "wrong_call_count_zero_emitted": sum(1 for row in selected_rows if row.get("wrong_call_count_zero_emitted")),
        "wrong_call_count_single_for_multiple": sum(1 for row in selected_rows if row.get("wrong_call_count_single_for_multiple")),
        "wrong_call_count_multiple_for_single": sum(1 for row in selected_rows if row.get("wrong_call_count_multiple_for_single")),
        "parallel_expected_but_serial_emitted": sum(1 for row in selected_rows if row.get("parallel_expected_but_serial_emitted")),
        "serial_expected_but_parallel_emitted": sum(1 for row in selected_rows if row.get("serial_expected_but_parallel_emitted")),
        "parallel_grouping_mismatch": sum(1 for row in selected_rows if row.get("parallel_grouping_mismatch")),
        "parallel_call_count_correct_but_grouping_wrong": sum(1 for row in selected_rows if row.get("parallel_call_count_correct_but_grouping_wrong")),
        "parallel_order_only_mismatch": sum(1 for row in selected_rows if row.get("parallel_order_only_mismatch")),
        "zero_emitted_due_to_abstain_classifier": sum(1 for row in rows if row.get("zero_emitted_due_to_abstain_classifier")),
        "zero_emitted_after_schema_selection": sum(1 for row in selected_rows if row.get("zero_emitted_after_schema_selection")),
        "zero_emitted_due_to_call_shape_canonicalizer": sum(1 for row in selected_rows if row.get("zero_emitted_due_to_call_shape_canonicalizer")),
        "zero_emitted_due_to_parallel_clause_drop": sum(1 for row in selected_rows if row.get("zero_emitted_due_to_parallel_clause_drop")),
        "zero_emitted_due_to_no_grounded_args": sum(1 for row in selected_rows if row.get("zero_emitted_due_to_no_grounded_args")),
        "selected_top1_but_no_emitted_call": sum(1 for row in selected_rows if row.get("selected_top1_but_no_emitted_call")),
        "selected_top1_but_trace_has_call_not_in_final_answer": sum(1 for row in selected_rows if row.get("selected_top1_but_trace_has_call_not_in_final_answer")),
        "selected_top1_but_final_answer_parser_drops_call": sum(1 for row in selected_rows if row.get("selected_top1_but_final_answer_parser_drops_call")),
        "selected_top1_but_serial_call_missing_args_and_suppressed": sum(1 for row in selected_rows if row.get("selected_top1_but_serial_call_missing_args_and_suppressed")),
        "parallel_argument_sets_extracted": sum(1 for row in selected_rows if row.get("parallel_argument_sets_extracted")),
        "parallel_argument_set_count": sum(int(row.get("parallel_argument_set_count") or 0) for row in selected_rows),
        "parallel_clause_materialized_count": sum(int(row.get("parallel_clause_materialized_count") or 0) for row in selected_rows),
        "parallel_clause_drop_count": sum(int(row.get("parallel_clause_drop_count") or 0) for row in selected_rows),
        "parallel_collapsed_to_serial": sum(1 for row in selected_rows if row.get("parallel_collapsed_to_serial")),
        "parallel_bridge_drop_stage_counts": dict(Counter(str(row.get("parallel_bridge_drop_stage") or "") for row in parallel_bridge_rows)),
        "parallel_count_alignment_bucket_counts": dict(Counter(str(row.get("parallel_count_alignment_bucket") or "") for row in parallel_count_alignment_rows)),
        "extracted_too_few_argument_sets": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "extracted_too_few_argument_sets"),
        "extracted_too_many_argument_sets": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "extracted_too_many_argument_sets"),
        "materialized_less_than_extracted": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "materialized_less_than_extracted"),
        "emitted_less_than_materialized": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "emitted_less_than_materialized"),
        "emitted_more_than_expected": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "emitted_more_than_expected"),
        "materialized_count_matches_emitted_but_not_expected": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "materialized_count_matches_emitted_but_not_expected"),
        "single_extracted_for_multi_expected": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "single_extracted_for_multi_expected"),
        "multi_extracted_for_single_expected": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "multi_extracted_for_single_expected"),
        "count_aligned": sum(1 for row in parallel_count_alignment_rows if row.get("parallel_count_alignment_bucket") == "count_aligned"),
        "materialized_gt0_trace0": sum(1 for row in selected_rows if int(row.get("parallel_clause_materialized_count") or 0) > 0 and int(row.get("trace_metric_tool_calls") or 0) == 0),
        "trace_gt0_emitted0": sum(1 for row in parallel_bridge_rows if int(row.get("trace_metric_tool_calls") or 0) > 0 and int(row.get("emitted_call_count") or 0) == 0),
        "emitted_gt0_wrong_count": sum(1 for row in parallel_bridge_rows if int(row.get("emitted_call_count") or 0) > 0 and row.get("wrong_call_count")),
        "emitted_count_correct_wrong_grouping": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_emitted_calls_but_wrong_official_grouping"),
        "parallel_sets_extracted_but_no_workflow_steps": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_sets_extracted_but_no_workflow_steps"),
        "parallel_workflow_steps_built_but_preflight_blocked": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_workflow_steps_built_but_preflight_blocked"),
        "parallel_workflow_steps_built_but_not_executed": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_workflow_steps_built_but_not_executed"),
        "parallel_tool_calls_in_trace_but_not_in_emitted_answer": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_tool_calls_in_trace_but_not_in_emitted_answer"),
        "parallel_emitted_calls_but_wrong_official_grouping": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_emitted_calls_but_wrong_official_grouping"),
        "parallel_emitted_calls_wrong_count": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_emitted_calls_wrong_count"),
        "parallel_emitted_calls_wrong_args": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_emitted_calls_wrong_args"),
        "parallel_emitted_calls_success": sum(1 for row in selected_rows if row.get("parallel_bridge_drop_stage") == "parallel_emitted_calls_success"),
        "missing_required_due_to_no_query_cue": sum(1 for row in selected_rows if row.get("missing_required_due_to_no_query_cue")),
        "missing_required_due_to_schema_alias_mismatch": sum(1 for row in selected_rows if row.get("missing_required_due_to_schema_alias_mismatch")),
        "missing_required_due_to_grounder_not_attempted": sum(1 for row in selected_rows if row.get("missing_required_due_to_grounder_not_attempted")),
        "missing_required_due_to_value_filtered": sum(1 for row in selected_rows if row.get("missing_required_due_to_value_filtered")),
        "missing_required_due_to_final_answer_serializer_drop": sum(1 for row in selected_rows if row.get("missing_required_due_to_final_answer_serializer_drop")),
        "call_count_delta_counts": dict(call_count_deltas),
        "selected_correct_failure_bucket_counts": dict(bucket_counts),
    }


def _bfcl_selected_correct_failure_audit(scored_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [_bfcl_selected_correct_failure_row(row) for row in scored_rows]
    runtime_gold_leak_count = sum(
        1
        for row in scored_rows
        if _diagnostic_contains_gold_fields(_first_bfcl_selection_diagnostic(row))
    )
    by_case: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_system: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_dataset_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_system_case: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        case_type = str(row.get("case_type") or "unknown")
        system = str(row.get("system") or "unknown")
        category = str(row.get("official_dataset_category") or "unknown")
        by_case[case_type].append(row)
        by_system[system].append(row)
        by_dataset_category[category].append(row)
        by_system_case[f"{system}::{case_type}"].append(row)
    return {
        "audit_schema_version": "bfcl_selected_correct_failure_audit_v1",
        "gold_fields_added_after_execution": True,
        "runtime_diagnostics_gold_free": runtime_gold_leak_count == 0,
        "runtime_gold_field_leak_count": runtime_gold_leak_count,
        "summary": _selected_correct_summary_for_rows(rows),
        "by_case_type": {key: _selected_correct_summary_for_rows(value) for key, value in sorted(by_case.items())},
        "by_system": {key: _selected_correct_summary_for_rows(value) for key, value in sorted(by_system.items())},
        "by_official_dataset_category": {key: _selected_correct_summary_for_rows(value) for key, value in sorted(by_dataset_category.items())},
        "by_system_case_type": {key: _selected_correct_summary_for_rows(value) for key, value in sorted(by_system_case.items())},
        "rows": rows,
    }


def _write_bfcl_selected_correct_failure_markdown(audit: Dict[str, Any], path: Path) -> None:
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    lines = [
        "# BFCL Selected-Correct Failure Audit",
        "",
        "This report is gold-enriched after execution. Runtime diagnostics remain gold-free.",
        "",
        f"- audit_schema_version: `{audit.get('audit_schema_version')}`",
        f"- runtime_diagnostics_gold_free: `{audit.get('runtime_diagnostics_gold_free')}`",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key in [
        "selected_is_expected_count",
        "success_given_selected_is_expected",
        "success_rate_given_selected_is_expected",
        "missing_required_given_selected_is_expected",
        "wrong_arg_value_given_selected_is_expected",
        "wrong_arg_type_given_selected_is_expected",
        "wrong_arg_structure_given_selected_is_expected",
        "wrong_call_count_given_selected_is_expected",
        "wrong_call_order_given_selected_is_expected",
        "parallel_shape_error_given_selected_is_expected",
        "multi_turn_state_error_given_selected_is_expected",
        "wrong_call_count_missing_calls",
        "wrong_call_count_extra_calls",
        "wrong_call_count_zero_emitted",
        "wrong_call_count_single_for_multiple",
        "wrong_call_count_multiple_for_single",
        "parallel_expected_but_serial_emitted",
        "serial_expected_but_parallel_emitted",
        "parallel_grouping_mismatch",
        "parallel_call_count_correct_but_grouping_wrong",
        "parallel_order_only_mismatch",
        "trace_missing_or_unparseable_given_selected_is_expected",
        "other_selected_correct_failure_given_selected_is_expected",
        "missing_required_due_to_no_query_cue",
        "missing_required_due_to_schema_alias_mismatch",
        "missing_required_due_to_grounder_not_attempted",
        "missing_required_due_to_value_filtered",
        "missing_required_due_to_final_answer_serializer_drop",
    ]:
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.extend(["", "## Failure Buckets", "", "| bucket | count |", "|---|---:|"])
    for bucket, count in sorted((summary.get("selected_correct_failure_bucket_counts") or {}).items()):
        lines.append(f"| {bucket} | {count} |")
    lines.extend(["", "## By Case Type", "", "| case_type | selected expected | success | top bucket |", "|---|---:|---:|---|"])
    for case_type, case_summary in audit.get("by_case_type", {}).items():
        buckets = case_summary.get("selected_correct_failure_bucket_counts") or {}
        top_bucket = max(buckets.items(), key=lambda item: item[1])[0] if buckets else "none"
        lines.append(
            f"| {case_type} | {case_summary.get('selected_is_expected_count', 0)} | {case_summary.get('success_given_selected_is_expected', 0)} | {top_bucket} |"
        )
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
    wrong_function_bucket_non_regression = bool(full_suite_gates.get("a2_wrong_func_name_le_a0", False))
    exact_function_guard_claim_ready = (
        wrong_function_bucket_non_regression
        and bool(full_suite_gates.get("a2_tool_selection_ge_a0", False))
        and bool(full_suite_gates.get("a2_success_ge_a0", False))
    )
    wrong_function_non_regression_ready = exact_function_guard_claim_ready
    missing_required_reduction_ready = bool(full_suite_gates.get("a2_missing_required_lt_a0", False))
    full_suite_supporting_ready = exact_function_guard_claim_ready and missing_required_reduction_ready
    baseline_missing_required_slice_ready = all(baseline_slice_gates.values())
    return {
        "guard_policy_version": "strict_schema_top1_tie_drop_v1",
        "reuse_claim_enabled_for_bfcl": False,
        "a4_interpreted_as_guarded_execution_variant_only": True,
        "failure_bucket_counts_by_system": {system: dict(counts) for system, counts in sorted(bucket_counts.items())},
        "full_suite_gates": full_suite_gates,
        "wrong_function_bucket_non_regression": wrong_function_bucket_non_regression,
        "exact_function_guard_claim_ready": exact_function_guard_claim_ready,
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
        and guard_claim_gates.get("exact_function_guard_claim_ready")
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
    candidate_coverage_audit = _bfcl_candidate_coverage_audit(scored_rows)
    selected_correct_failure_audit = _bfcl_selected_correct_failure_audit(scored_rows)
    candidate_coverage_summary = {
        "audit_schema_version": "bfcl_candidate_coverage_summary_v1",
        "summary": candidate_coverage_audit.get("summary", {}),
        "by_case_type": candidate_coverage_audit.get("by_case_type", {}),
        "by_system": candidate_coverage_audit.get("by_system", {}),
    }
    selected_correct_failure_summary = {
        "audit_schema_version": "bfcl_selected_correct_failure_summary_v1",
        "summary": selected_correct_failure_audit.get("summary", {}),
        "by_case_type": selected_correct_failure_audit.get("by_case_type", {}),
        "by_system": selected_correct_failure_audit.get("by_system", {}),
        "by_official_dataset_category": selected_correct_failure_audit.get("by_official_dataset_category", {}),
    }

    (outdir / "official_scoreboard.json").write_text(json.dumps(official_scoreboard, indent=2), encoding="utf-8")
    (outdir / "toolclaw_diagnostics.json").write_text(json.dumps(toolclaw_diagnostics, indent=2), encoding="utf-8")
    (outdir / "claim_summary.json").write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")
    (outdir / "bfcl_failure_slice_summary.json").write_text(json.dumps(failure_slice_summary, indent=2), encoding="utf-8")
    _write_bfcl_failure_slice_markdown(failure_slice_summary, outdir / "bfcl_failure_slice_summary.md")
    (outdir / "bfcl_function_selection_audit.json").write_text(json.dumps(function_selection_audit, indent=2), encoding="utf-8")
    _write_bfcl_function_selection_audit_markdown(function_selection_audit, outdir / "bfcl_function_selection_audit.md")
    (outdir / "bfcl_candidate_coverage_audit.json").write_text(json.dumps(candidate_coverage_audit, indent=2), encoding="utf-8")
    _write_bfcl_candidate_coverage_markdown(candidate_coverage_audit, outdir / "bfcl_candidate_coverage_audit.md")
    (outdir / "bfcl_candidate_coverage_summary.json").write_text(json.dumps(candidate_coverage_summary, indent=2), encoding="utf-8")
    _write_bfcl_candidate_coverage_markdown(candidate_coverage_audit, outdir / "bfcl_candidate_coverage_summary.md")
    (outdir / "bfcl_selected_correct_failure_audit.json").write_text(json.dumps(selected_correct_failure_audit, indent=2), encoding="utf-8")
    _write_bfcl_selected_correct_failure_markdown(selected_correct_failure_audit, outdir / "bfcl_selected_correct_failure_audit.md")
    (outdir / "bfcl_selected_correct_failure_summary.json").write_text(json.dumps(selected_correct_failure_summary, indent=2), encoding="utf-8")
    _write_bfcl_selected_correct_failure_markdown(selected_correct_failure_audit, outdir / "bfcl_selected_correct_failure_summary.md")

    manifest["comparison_scored_path"] = _display_path(comparison_scored_path)
    manifest["official_scoreboard_path"] = _display_path(outdir / "official_scoreboard.json")
    manifest["toolclaw_diagnostics_path"] = _display_path(outdir / "toolclaw_diagnostics.json")
    manifest["claim_summary_path"] = _display_path(outdir / "claim_summary.json")
    manifest["bfcl_failure_slice_summary_path"] = _display_path(outdir / "bfcl_failure_slice_summary.json")
    manifest["bfcl_function_selection_audit_path"] = _display_path(outdir / "bfcl_function_selection_audit.json")
    manifest["bfcl_candidate_coverage_audit_path"] = _display_path(outdir / "bfcl_candidate_coverage_audit.json")
    manifest["bfcl_candidate_coverage_summary_path"] = _display_path(outdir / "bfcl_candidate_coverage_summary.json")
    manifest["bfcl_selected_correct_failure_audit_path"] = _display_path(outdir / "bfcl_selected_correct_failure_audit.json")
    manifest["bfcl_selected_correct_failure_summary_path"] = _display_path(outdir / "bfcl_selected_correct_failure_summary.json")
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"official_scoreboard: {outdir / 'official_scoreboard.json'}")
    print(f"toolclaw_diagnostics: {outdir / 'toolclaw_diagnostics.json'}")
    print(f"claim_summary: {outdir / 'claim_summary.json'}")
    print(f"bfcl_function_selection_audit: {outdir / 'bfcl_function_selection_audit.json'}")
    print(f"bfcl_candidate_coverage_audit: {outdir / 'bfcl_candidate_coverage_audit.json'}")
    print(f"bfcl_selected_correct_failure_audit: {outdir / 'bfcl_selected_correct_failure_audit.json'}")


if __name__ == "__main__":
    main()
