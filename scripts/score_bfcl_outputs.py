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
    else:
        claim_id = "bfcl_agentic_supporting"
        paper_safe = False
        headline_supported = False
        headline_blockers = ["agentic_ext_supporting_only"]
        interpretation = "BFCL agentic extension is supporting-only and must not be used as the planner/binder headline claim."
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
        "claims": [
            {
                "claim_id": claim_id,
                "paper_safe_for_claim": paper_safe,
                "headline_supported": headline_supported,
                "headline_blockers": headline_blockers,
                "metric_snapshot": official_metrics,
                "interpretation": interpretation,
            }
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

    (outdir / "official_scoreboard.json").write_text(json.dumps(official_scoreboard, indent=2), encoding="utf-8")
    (outdir / "toolclaw_diagnostics.json").write_text(json.dumps(toolclaw_diagnostics, indent=2), encoding="utf-8")
    (outdir / "claim_summary.json").write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")
    (outdir / "bfcl_failure_slice_summary.json").write_text(json.dumps(failure_slice_summary, indent=2), encoding="utf-8")
    _write_bfcl_failure_slice_markdown(failure_slice_summary, outdir / "bfcl_failure_slice_summary.md")

    manifest["comparison_scored_path"] = _display_path(comparison_scored_path)
    manifest["official_scoreboard_path"] = _display_path(outdir / "official_scoreboard.json")
    manifest["toolclaw_diagnostics_path"] = _display_path(outdir / "toolclaw_diagnostics.json")
    manifest["claim_summary_path"] = _display_path(outdir / "claim_summary.json")
    manifest["bfcl_failure_slice_summary_path"] = _display_path(outdir / "bfcl_failure_slice_summary.json")
    (outdir / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"official_scoreboard: {outdir / 'official_scoreboard.json'}")
    print(f"toolclaw_diagnostics: {outdir / 'toolclaw_diagnostics.json'}")
    print(f"claim_summary: {outdir / 'claim_summary.json'}")


if __name__ == "__main__":
    main()
