#!/usr/bin/env python3
"""Run fixed paper benchmark suites defined by the claim matrix."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
CLAIM_MATRIX_PATH = ROOT_DIR / "configs" / "paper_claim_matrix.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fixed paper benchmark suite")
    parser.add_argument("suite", help="Suite name defined in configs/paper_claim_matrix.yaml")
    parser.add_argument("--out-root", default="outputs/paper_suite", help="Root output directory")
    parser.add_argument("--source", default=None, help="Optional source override")
    parser.add_argument("--systems", default=None, help="Optional comma-separated system override")
    parser.add_argument("--mode", default=None, help="Optional mode override")
    parser.add_argument("--num-runs", type=int, default=None, help="Optional run-count override")
    parser.add_argument("--keep-normalized-taskset", action="store_true", help="Keep prepared tasksets when supported")
    parser.add_argument("--dry-run", action="store_true", help="Write placeholder manifests without executing runners")
    return parser.parse_args()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _suite_config(matrix: Dict[str, Any], suite: str) -> Dict[str, Any]:
    suites = matrix.get("suites", {})
    if suite not in suites:
        raise ValueError(f"Unknown paper suite: {suite}. Valid suites: {', '.join(sorted(suites))}")
    return dict(suites[suite])


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _bool_cli(value: bool) -> str:
    return "true" if value else "false"


def _resolve_source_path(raw_source: str) -> Path:
    path = Path(raw_source)
    return path if path.is_absolute() else (ROOT_DIR / path)


def _load_optional_json(path: Path | None) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _load_json(path)


def _run(command: List[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT_DIR,
        env={"PYTHONPATH": str(SRC_DIR), **dict(**__import__("os").environ)},
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _load_tau_audit(path_value: str | None) -> Dict[str, Any]:
    if not path_value:
        return {}
    path = ROOT_DIR / path_value
    if not path.exists():
        return {}
    return _load_json(path)


def _discover_source_manifest(source_path: Path) -> Path | None:
    manifest_path = (source_path / "manifest.json") if source_path.is_dir() else (source_path.parent / "manifest.json")
    return manifest_path if manifest_path.exists() else None


def _check_bfcl_formal_source_gate(suite_cfg: Dict[str, Any], args: argparse.Namespace) -> None:
    if not suite_cfg.get("requires_formal_source"):
        return
    source_path = _resolve_source_path(args.source or suite_cfg["default_source"])
    manifest_path = _discover_source_manifest(source_path)
    if manifest_path is None:
        raise SystemExit("BFCL formal suite requires a prepared-source manifest alongside the selected source.")

    source_manifest = _load_json(manifest_path)
    if str(source_manifest.get("source") or "").strip() == "repo_scaffold":
        raise SystemExit("BFCL formal suite cannot run from repo_scaffold data. Use a prepared formal source.")

    formal_lock_path = ROOT_DIR / str(suite_cfg.get("formal_lock") or "")
    if not formal_lock_path.exists():
        raise SystemExit("BFCL formal suite requires a tracked formal lock artifact.")
    formal_lock = _load_json(formal_lock_path)

    expected_manifest = str(formal_lock.get("prepared_manifest") or "").strip()
    actual_manifest = _display_path(manifest_path)
    if expected_manifest and actual_manifest != expected_manifest:
        raise SystemExit(
            f"BFCL formal suite source manifest mismatch: expected {expected_manifest}, got {actual_manifest}."
        )

    if formal_lock.get("counts") and source_manifest.get("counts") and formal_lock["counts"] != source_manifest["counts"]:
        raise SystemExit("BFCL formal suite counts do not match the tracked formal lock.")

    expected_wrapper = str(formal_lock.get("official_wrapper_path") or "").strip()
    actual_wrapper = str(source_manifest.get("official_evaluator_script") or "").strip()
    if expected_wrapper and actual_wrapper and expected_wrapper != actual_wrapper:
        raise SystemExit("BFCL formal suite official evaluator wrapper does not match the tracked formal lock.")


def _check_tau_promotion_gate(suite_cfg: Dict[str, Any]) -> None:
    if not suite_cfg.get("requires_audit_promotion"):
        return
    audit = _load_tau_audit(suite_cfg.get("audit_config"))
    if not bool(audit.get("promote_tau_bench", False)):
        raise SystemExit("tau-bench headline promotion is blocked by configs/tau_bench_semantic_audit.json")


def _command_for_suite(suite_cfg: Dict[str, Any], outdir: Path, args: argparse.Namespace) -> List[str]:
    runner = ROOT_DIR / suite_cfg["runner"]
    resolved_source = _resolve_source_path(args.source or suite_cfg["default_source"])
    command = [
        sys.executable,
        str(runner),
        "--source",
        str(resolved_source),
        "--outdir",
        str(outdir),
        "--mode",
        str(args.mode or suite_cfg["default_mode"]),
        "--systems",
        str(args.systems or suite_cfg["default_systems"]),
        "--num-runs",
        str(args.num_runs or suite_cfg["default_num_runs"]),
    ]
    if suite_cfg.get("slice_by"):
        command.extend(["--slice-by", str(suite_cfg["slice_by"])])
    if suite_cfg.get("slice_values"):
        command.extend(["--slice-values", str(suite_cfg["slice_values"])])
    if suite_cfg.get("reuse_second_run"):
        command.append("--reuse-second-run")
    if suite_cfg.get("track"):
        command.extend(["--track", str(suite_cfg["track"])])
    if "official_eval" in suite_cfg:
        command.extend(["--official-eval", _bool_cli(bool(suite_cfg["official_eval"]))])
    if "toolclaw_diagnostics" in suite_cfg:
        command.extend(["--toolclaw-diagnostics", _bool_cli(bool(suite_cfg["toolclaw_diagnostics"]))])
    if args.keep_normalized_taskset:
        command.append("--keep-normalized-taskset")
    return command


def _score_command(suite_cfg: Dict[str, Any], outdir: Path) -> List[str]:
    return [
        sys.executable,
        str(ROOT_DIR / suite_cfg["score_script"]),
        "--outdir",
        str(outdir),
        "--official-eval",
        _bool_cli(bool(suite_cfg.get("official_eval", False))),
        "--toolclaw-diagnostics",
        _bool_cli(bool(suite_cfg.get("toolclaw_diagnostics", False))),
    ]


def _post_analyze_reuse(outdir: Path) -> None:
    _run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "analyze_reuse_strata.py"),
            "--outdir",
            str(outdir),
            "--json-out",
            str(outdir / "reuse_strata_analysis.json"),
            "--md-out",
            str(outdir / "reuse_strata_analysis.md"),
        ]
    )
    _run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "analyze_reuse_headroom.py"),
            "--outdir",
            str(outdir),
            "--json-out",
            str(outdir / "reuse_headroom_analysis.json"),
            "--md-out",
            str(outdir / "reuse_headroom_analysis.md"),
        ]
    )


def _placeholder_csv(path: Path, suite: str, reason: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["suite", "status", "reason"])
        writer.writeheader()
        writer.writerow({"suite": suite, "status": "placeholder", "reason": reason})


def _ensure_standard_outputs(suite: str, outdir: Path) -> Dict[str, str]:
    raw_target = outdir / "comparison.raw.csv"
    scored_target = outdir / "comparison.scored.csv"
    if not raw_target.exists():
        if (outdir / "comparison.csv").exists():
            shutil.copy2(outdir / "comparison.csv", raw_target)
        else:
            _placeholder_csv(raw_target, suite, "raw comparison missing")
    if not scored_target.exists():
        if (outdir / "comparison.csv").exists():
            shutil.copy2(outdir / "comparison.csv", scored_target)
        else:
            _placeholder_csv(scored_target, suite, "scored comparison missing")
    return {
        "comparison_raw_path": _display_path(raw_target),
        "comparison_scored_path": _display_path(scored_target),
    }


def _materialize_claim_summary(
    *,
    outdir: Path,
    suite: str,
    status: str,
    suite_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    claim_summary_path = outdir / "claim_summary.json"
    if claim_summary_path.exists():
        payload = _load_json(claim_summary_path)
    else:
        payload = {}

    claims = payload.get("claims", [])
    if not isinstance(claims, list) or not claims:
        claims = [
            {
                "claim_id": claim_id,
                "paper_role": suite_cfg.get("paper_role"),
            }
            for claim_id in suite_cfg.get("claim_ids", [])
        ]

    payload["suite"] = suite
    payload["status"] = str(payload.get("status") or status)
    payload["claims"] = claims
    payload.setdefault("paper_role", suite_cfg.get("paper_role"))
    return payload


def _write_suite_manifest(
    *,
    outdir: Path,
    suite: str,
    suite_cfg: Dict[str, Any],
    runner_command: List[str],
    score_command: List[str] | None,
    claim_summary_path: Path,
    standardized_outputs: Dict[str, str],
    status: str,
) -> None:
    payload = {
        "suite": suite,
        "status": status,
        "paper_role": suite_cfg.get("paper_role"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": suite_cfg.get("runner"),
        "score_script": suite_cfg.get("score_script"),
        "runner_command": runner_command,
        "score_command": score_command,
        "claim_summary_path": _display_path(claim_summary_path),
        **standardized_outputs,
    }
    (outdir / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    matrix = _load_json(CLAIM_MATRIX_PATH)
    suite_cfg = _suite_config(matrix, args.suite)
    outdir = Path(args.out_root) / args.suite
    outdir.mkdir(parents=True, exist_ok=True)

    _check_tau_promotion_gate(suite_cfg)
    _check_bfcl_formal_source_gate(suite_cfg, args)

    runner_command = _command_for_suite(suite_cfg, outdir, args)
    score_command: List[str] | None = None
    status = "dry_run" if args.dry_run else str(suite_cfg.get("status", "implemented"))

    if not args.dry_run:
        _run(runner_command)
        if suite_cfg.get("score_script"):
            score_command = _score_command(suite_cfg, outdir)
            _run(score_command)
        if suite_cfg.get("post_analysis") == ["reuse_strata", "reuse_headroom"]:
            _post_analyze_reuse(outdir)
        status = "completed"

    standardized_outputs = _ensure_standard_outputs(args.suite, outdir)
    claim_summary = _materialize_claim_summary(
        outdir=outdir,
        suite=args.suite,
        status=status,
        suite_cfg=suite_cfg,
    )
    claim_summary_path = outdir / "claim_summary.json"
    claim_summary_path.write_text(json.dumps(claim_summary, indent=2), encoding="utf-8")
    _write_suite_manifest(
        outdir=outdir,
        suite=args.suite,
        suite_cfg=suite_cfg,
        runner_command=runner_command,
        score_command=score_command,
        claim_summary_path=claim_summary_path,
        standardized_outputs=standardized_outputs,
        status=status,
    )

    print(f"suite: {args.suite}")
    print(f"outdir: {outdir}")
    print(f"manifest: {outdir / 'manifest.json'}")
    print(f"claim_summary: {claim_summary_path}")


if __name__ == "__main__":
    main()
