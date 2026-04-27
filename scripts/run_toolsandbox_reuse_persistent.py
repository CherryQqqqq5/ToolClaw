#!/usr/bin/env python3
"""Run ToolSandbox persistent reuse as a two-stage paired benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


PASS2_ARMS = {
    "a3_interaction": {"system": "a3_interaction", "registry": None},
    "a4_reuse_cold": {"system": "a4_reuse", "registry": "cold"},
    "a4_reuse_warm": {"system": "a4_reuse", "registry": "warm"},
    "a4_reuse_sham": {"system": "a4_reuse", "registry": "sham"},
}


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True).strip()
    except Exception:
        return ""


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


SCORER_ONLY_TASK_KEYS = {
    "scorer_gold",
    "result_summary",
    "reference_result_summary",
    "official_milestone_mapping",
    "official_milestone_similarity",
    "official_similarity",
    "official_traceback",
    "official_exception_type",
}


def _false_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    return str(value).strip().lower() in {"0", "false", "no"}


def _initial_runtime_messages(messages: Any) -> List[Dict[str, Any]]:
    if not isinstance(messages, list):
        return []
    runtime_messages: List[Dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        sender = str(message.get("sender") or message.get("role") or "").lower()
        recipient = str(message.get("recipient") or "").lower()
        if sender == "system" or (sender == "user" and (not recipient or recipient == "agent")):
            runtime_messages.append(dict(message))
            if sender == "user":
                break
        elif runtime_messages:
            break
    return runtime_messages


def _sanitize_runtime_task(task: Dict[str, Any]) -> Dict[str, Any]:
    staged = deepcopy(task)
    metadata = dict(staged.get("metadata", {})) if isinstance(staged.get("metadata"), dict) else {}
    runtime_visibility = staged.get("runtime_visibility")
    if not isinstance(runtime_visibility, dict):
        runtime_visibility = metadata.get("runtime_visibility") if isinstance(metadata.get("runtime_visibility"), dict) else {}
    full_messages_hidden = _false_value(runtime_visibility.get("full_messages_runtime_visible"))
    milestones_hidden = _false_value(runtime_visibility.get("milestones_runtime_visible"))
    scorer_gold_hidden = _false_value(runtime_visibility.get("scorer_gold_runtime_visible"))
    if full_messages_hidden:
        runtime_messages = staged.get("runtime_messages")
        staged["messages"] = list(runtime_messages) if isinstance(runtime_messages, list) else _initial_runtime_messages(staged.get("messages"))
        metadata.pop("messages", None)
    if milestones_hidden:
        staged["milestones"] = []
        metadata.pop("milestones", None)
    if scorer_gold_hidden:
        for key in SCORER_ONLY_TASK_KEYS:
            staged.pop(key, None)
            metadata.pop(key, None)
    staged["metadata"] = metadata
    return staged


def _reuse_allowed_modes(reuse_scope: str) -> List[str]:
    scope = str(reuse_scope or "exact").strip().lower()
    if scope == "exact":
        return ["exact_reuse"]
    if scope == "transfer":
        return ["transfer_reuse"]
    return ["exact_reuse", "transfer_reuse"]


def _stage_task(
    task: Dict[str, Any],
    *,
    family_id: str,
    stage: str,
    pass_index: int,
    sham: bool = False,
    reuse_version: str = "toolsandbox_reuse_persistent_v1",
    reuse_scope: str = "exact",
    claim_scope: str = "exact_match_cost",
    signature_key: str = "",
) -> Dict[str, Any]:
    staged = _sanitize_runtime_task(task)
    metadata = dict(staged.get("metadata", {})) if isinstance(staged.get("metadata"), dict) else {}
    family = f"sham_unrelated::{family_id}" if sham else family_id
    task_id = f"{family_id}__{'sham_' if sham else ''}pass{pass_index}_{stage}"
    staged["task_id"] = task_id
    staged["name"] = task_id
    staged["reuse_family_id"] = family
    staged["reuse_pass_index"] = pass_index
    metadata.update(
        {
            "reuse_family_id": family,
            "reuse_pass_index": pass_index,
            "reuse_stage": stage,
            "reuse_scope": str(reuse_scope or "exact"),
            "reuse_claim_scope": str(claim_scope or "exact_match_cost"),
            "reuse_allowed_modes": _reuse_allowed_modes(str(reuse_scope or "exact")),
            "reuse_require_source_family_match": str(reuse_scope or "exact") == "exact",
            "reuse_signature_key": str(signature_key or ""),
            "reuse_persistent_v1": True,
            "reuse_persistent_version": reuse_version,
            "reuse_pass2_compile_allowed": False if pass_index == 2 else True,
            "original_reuse_family_id": family_id,
            "sham_registry_stage": sham,
            "reuse_runtime_verification_signal": True,
        }
    )
    staged["reuse_runtime_verification_signal"] = True
    staged["reuse_scope"] = str(reuse_scope or "exact")
    staged["reuse_claim_scope"] = str(claim_scope or "exact_match_cost")
    staged["reuse_allowed_modes"] = _reuse_allowed_modes(str(reuse_scope or "exact"))
    staged["reuse_require_source_family_match"] = str(reuse_scope or "exact") == "exact"
    staged["reuse_signature_key"] = str(signature_key or "")
    staged["metadata"] = metadata
    return staged


def _write_taskset(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _run_eval(taskset: Path, outdir: Path, *, system: str, registry_root: Path | None, quiet: bool) -> None:
    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "run_toolsandbox_bench.py"),
        "--source",
        str(taskset),
        "--outdir",
        str(outdir),
        "--systems",
        system,
        "--num-runs",
        "1",
        "--keep-normalized-taskset",
    ]
    if registry_root is not None:
        cmd.extend(["--asset-registry-root", str(registry_root)])
    completed = subprocess.run(cmd, cwd=ROOT_DIR, env={**os.environ, "PYTHONPATH": str(SRC_DIR)}, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _copy_trace(row: Dict[str, str], target_dir: Path, prefix: str) -> str:
    source = Path(row.get("trace_path", ""))
    if not source.exists():
        return row.get("trace_path", "")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{prefix}_{source.name}"
    shutil.copy2(source, target)
    return str(target)


def _merge_rows(outdir: Path, run_index: int, stage: str, arm: str, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    trace_dir = outdir / "traces"
    for row in rows:
        item = dict(row)
        item["run_index"] = str(run_index)
        item["stage"] = stage
        item["arm"] = arm
        item["system"] = arm
        item["trace_path"] = _copy_trace(item, trace_dir, f"run{run_index:02d}_{stage}_{arm}")
        merged.append(item)
    return merged


def _write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _registry_non_empty(path: Path) -> bool:
    if not path.exists():
        return False
    return any(item.is_file() and item.name != "index.json" for item in path.rglob("*"))


def _registry_for(base: Path, kind: str) -> Path:
    return base / kind


def _safe_name(value: str) -> str:
    safe = []
    for char in str(value):
        safe.append(char if char.isalnum() or char in {"_", "-", "."} else "_")
    return "".join(safe).strip("_") or "family"


def _semantic_family(family_id: str) -> str:
    text = str(family_id or "")
    if "__pair" in text:
        text = text.split("__pair", 1)[0]
    return text




def _row_value(row: Dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value not in (None, ""):
        return str(value)
    for task_key in ("pass1_compile", "pass2_eval"):
        task = row.get(task_key)
        if isinstance(task, dict):
            metadata = task.get("metadata")
            if isinstance(metadata, dict) and metadata.get(key) not in (None, ""):
                return str(metadata.get(key))
    return ""


def _unrelated_family(current: Dict[str, Any], families: List[Dict[str, Any]]) -> Dict[str, Any]:
    current_family = str(current["family_id"])
    current_semantic = _semantic_family(current_family)
    current_signature = str(current.get("signature_key") or "")
    current_failure = _row_value(current, "failure_context")
    current_capability = _row_value(current, "capability_skeleton")
    current_tool_signature = _row_value(current, "tool_signature")
    degraded_candidate: Dict[str, Any] | None = None

    for candidate in families:
        candidate_family = str(candidate["family_id"])
        candidate_signature = str(candidate.get("signature_key") or "")
        if candidate_family == current_family:
            continue
        if _semantic_family(candidate_family) == current_semantic:
            continue
        if candidate_signature == current_signature:
            continue
        if current_failure and _row_value(candidate, "failure_context") == current_failure:
            if degraded_candidate is None:
                degraded_candidate = candidate
            continue
        if current_capability and _row_value(candidate, "capability_skeleton") == current_capability:
            if degraded_candidate is None:
                degraded_candidate = candidate
            continue
        if current_tool_signature and _row_value(candidate, "tool_signature") == current_tool_signature:
            if degraded_candidate is None:
                degraded_candidate = candidate
            continue
        return candidate

    if degraded_candidate is not None:
        degraded_candidate["_sham_unrelated_selection_degraded"] = True
        return degraded_candidate

    for candidate in families:
        candidate_family = str(candidate["family_id"])
        candidate_signature = str(candidate.get("signature_key") or "")
        if (
            candidate_family != current_family
            and _semantic_family(candidate_family) != current_semantic
            and candidate_signature != current_signature
        ):
            return candidate
    for candidate in families:
        if str(candidate["family_id"]) != current_family:
            return candidate
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ToolSandbox persistent reuse benchmark")
    parser.add_argument("--source", required=True)
    parser.add_argument("--outdir", default="outputs/reuse_persistent_v1")
    parser.add_argument("--num-runs", type=int, default=1)
    parser.add_argument("--limit-families", type=int, default=0)
    parser.add_argument("--reuse-scope", choices=["exact", "transfer", "all"], default="exact")
    parser.add_argument("--mode", default="planner", help=argparse.SUPPRESS)
    parser.add_argument("--systems", default="a3_interaction,a4_reuse_cold,a4_reuse_warm,a4_reuse_sham", help=argparse.SUPPRESS)
    parser.add_argument("--quiet-progress", action="store_true")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    families = _read_jsonl(source)
    dataset_manifest = Path(str(source).replace(".jsonl", ".manifest.json"))
    source_manifest = json.loads(dataset_manifest.read_text(encoding="utf-8")) if dataset_manifest.exists() else {}
    reuse_version = str(source_manifest.get("version") or source_manifest.get("suite") or "toolsandbox_reuse_persistent_v1")
    if args.limit_families:
        families = families[: max(args.limit_families, 0)]
    if not families:
        raise SystemExit("no reuse families to run")

    staged_dir = outdir / "staged_tasksets"
    all_rows: List[Dict[str, str]] = []
    registry_preflight_passed = True
    degraded_sham_pairs: List[Dict[str, str]] = []

    for run_index in range(1, max(args.num_runs, 1) + 1):
        run_dir = outdir / "runs" / f"run_{run_index:02d}"
        registry_base = outdir / "asset_registries" / f"run_{run_index:02d}"
        for family_row in families:
            family_id = str(family_row["family_id"])
            sham_source = _unrelated_family(family_row, families)
            sham_family_id = str(sham_source["family_id"])
            if bool(sham_source.get("_sham_unrelated_selection_degraded")):
                degraded_sham_pairs.append(
                    {
                        "run_index": str(run_index),
                        "target_family_id": family_id,
                        "sham_family_id": sham_family_id,
                    }
                )
            claim_scope = str(family_row.get("claim_scope") or "exact_match_cost")
            signature_key = str(family_row.get("signature_key") or "")
            family_name = _safe_name(family_id)
            family_run_dir = run_dir / family_name
            warm_registry = _registry_for(registry_base / family_name, "warm")
            cold_registry = _registry_for(registry_base / family_name, "cold")
            sham_registry = _registry_for(registry_base / family_name, "sham")
            for path in (warm_registry, cold_registry, sham_registry):
                if path.exists():
                    shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)

            pass1_path = staged_dir / f"run_{run_index:02d}.{family_name}.pass1_compile.json"
            sham_path = staged_dir / f"run_{run_index:02d}.{family_name}.sham_compile.json"
            pass2_path = staged_dir / f"run_{run_index:02d}.{family_name}.pass2_eval.json"
            _write_taskset(
                pass1_path,
                [
                    _stage_task(
                        family_row["pass1_compile"],
                        family_id=family_id,
                        stage="compile",
                        pass_index=1,
                        reuse_version=reuse_version,
                        reuse_scope=str(args.reuse_scope),
                        claim_scope=claim_scope,
                        signature_key=signature_key,
                    )
                ],
            )
            _write_taskset(
                sham_path,
                [
                    _stage_task(
                        sham_source["pass1_compile"],
                        family_id=sham_family_id,
                        stage="compile",
                        pass_index=1,
                        sham=True,
                        reuse_version=reuse_version,
                        reuse_scope=str(args.reuse_scope),
                        claim_scope=str(sham_source.get("claim_scope") or "exact_match_cost"),
                        signature_key=str(sham_source.get("signature_key") or ""),
                    )
                ],
            )
            _write_taskset(
                pass2_path,
                [
                    _stage_task(
                        family_row["pass2_eval"],
                        family_id=family_id,
                        stage="eval",
                        pass_index=2,
                        reuse_version=reuse_version,
                        reuse_scope=str(args.reuse_scope),
                        claim_scope=claim_scope,
                        signature_key=signature_key,
                    )
                ],
            )

            _run_eval(pass1_path, family_run_dir / "pass1_compile_warm", system="a4_reuse", registry_root=warm_registry, quiet=args.quiet_progress)
            _run_eval(sham_path, family_run_dir / "pass1_compile_sham", system="a4_reuse", registry_root=sham_registry, quiet=args.quiet_progress)
            registry_preflight_passed = registry_preflight_passed and _registry_non_empty(warm_registry)

            all_rows.extend(_merge_rows(outdir, run_index, "pass1_compile", "a4_reuse_pass1_compile", _load_csv(family_run_dir / "pass1_compile_warm" / "comparison.scored.csv")))
            all_rows.extend(_merge_rows(outdir, run_index, "sham_compile", "a4_reuse_sham_compile", _load_csv(family_run_dir / "pass1_compile_sham" / "comparison.scored.csv")))

            for arm, cfg in PASS2_ARMS.items():
                registry = None
                if cfg["registry"] == "warm":
                    registry = warm_registry
                elif cfg["registry"] == "cold":
                    registry = cold_registry
                elif cfg["registry"] == "sham":
                    registry = sham_registry
                arm_outdir = family_run_dir / f"pass2_{arm}"
                _run_eval(pass2_path, arm_outdir, system=str(cfg["system"]), registry_root=registry, quiet=args.quiet_progress)
                all_rows.extend(_merge_rows(outdir, run_index, "pass2_eval", arm, _load_csv(arm_outdir / "comparison.scored.csv")))

    comparison_raw = outdir / "comparison.raw.csv"
    comparison_scored = outdir / "comparison.scored.csv"
    _write_csv(comparison_raw, all_rows)
    _write_csv(comparison_scored, all_rows)

    experiment_manifest = {
        "suite": reuse_version,
        "source": str(source),
        "source_manifest": str(dataset_manifest) if dataset_manifest.exists() else "",
        "git_commit": _git_commit(),
        "systems": list(PASS2_ARMS),
        "num_runs": max(args.num_runs, 1),
        "family_count": len(families),
        "reuse_scope": str(args.reuse_scope),
        "reuse_persistent_version": reuse_version,
        "statistical_claim_allowed": bool(source_manifest.get("statistical_claim_allowed", len(families) >= 20)),
        "registry_preflight_passed": bool(registry_preflight_passed),
        "sham_unrelated_selection_degraded": bool(degraded_sham_pairs),
        "sham_unrelated_selection_degraded_count": len(degraded_sham_pairs),
        "sham_unrelated_selection_degraded_pairs": degraded_sham_pairs,
        "comparison_raw": str(comparison_raw),
        "comparison_scored": str(comparison_scored),
    }
    (outdir / "experiment_manifest.json").write_text(json.dumps(experiment_manifest, indent=2), encoding="utf-8")

    score_cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "score_toolsandbox_reuse_persistent.py"),
        "--dataset",
        str(source),
        "--comparison",
        str(comparison_scored),
        "--outdir",
        str(outdir),
        "--reuse-scope",
        str(args.reuse_scope),
    ]
    completed = subprocess.run(score_cmd, cwd=ROOT_DIR, env={**os.environ, "PYTHONPATH": str(SRC_DIR)}, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    print(f"outputs written under: {outdir}")


if __name__ == "__main__":
    main()
