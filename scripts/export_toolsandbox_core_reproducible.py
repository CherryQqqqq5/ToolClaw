#!/usr/bin/env python3
"""Build and optionally run a ToolSandbox core reproducible export.

Default mode is a dry-run filter over the official scenario inventory. It does not
execute ToolSandbox and does not produce claim evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT_DIR / "data" / "toolsandbox_official_scenario_inventory.json"
DEFAULT_OFFICIAL_ROOT = ROOT_DIR / "data" / "external" / "ToolSandbox"
DEFAULT_OUT_PREFIX = ROOT_DIR / "data" / "toolsandbox.official_core_reproducible"
DEFAULT_OFFICIAL_OUTPUT_ROOT = ROOT_DIR / "outputs" / "toolsandbox_core_reproducible_official_runs"
EXCLUSION_REASON_PRIORITY = [
    "requires_external_api",
    "not_python_native",
    "missing_milestones",
    "missing_tool_allow_list",
    "official_scenario_unresolvable",
]


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _official_scenario_names(official_root: Path) -> set[str]:
    python_bin = official_root / ".venv" / "bin" / "python"
    if not python_bin.exists():
        return set()
    code = r'''
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.scenarios import named_scenarios
print("\n".join(sorted(named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT).keys())))
'''
    completed = subprocess.run(
        [str(python_bin), "-c", code],
        cwd=str(official_root),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def core_filter_rows(inventory: Mapping[str, Any], *, resolvable_names: set[str] | None = None, limit: int | None = None) -> Dict[str, Any]:
    rows = list(inventory.get("scenarios", []) or [])
    resolvable_names = resolvable_names or set()
    selected: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    primary_reason_counts: Counter[str] = Counter()
    for row in rows:
        scenario_name = str(row.get("scenario_name") or row.get("name") or "")
        reasons: List[str] = []
        if row.get("requires_external_api") is not False:
            reasons.append("requires_external_api")
        if str(row.get("external_dependency_status") or "") != "python_native":
            reasons.append("not_python_native")
        if not row.get("tool_allow_list"):
            reasons.append("missing_tool_allow_list")
        try:
            if int(row.get("milestone_count") or 0) <= 0:
                reasons.append("missing_milestones")
        except (TypeError, ValueError):
            reasons.append("missing_milestones")
        if resolvable_names and scenario_name not in resolvable_names:
            reasons.append("official_scenario_unresolvable")
        if reasons:
            reason_counts.update(reasons)
            primary_reason = next((reason for reason in EXCLUSION_REASON_PRIORITY if reason in reasons), "other")
            primary_reason_counts[primary_reason] += 1
            excluded.append({
                "scenario_name": scenario_name,
                "excluded_reasons": reasons,
                "requires_external_api": bool(row.get("requires_external_api")),
                "external_dependency_status": row.get("external_dependency_status"),
                "categories": row.get("categories", []),
                "tool_allow_list": row.get("tool_allow_list", []),
            })
        else:
            selected.append({
                "scenario_name": scenario_name,
                "categories": row.get("categories", []),
                "tool_allow_list": row.get("tool_allow_list", []),
                "tool_augmentation_list": row.get("tool_augmentation_list", []),
                "milestone_count": row.get("milestone_count"),
                "initial_user_query": row.get("initial_user_query", ""),
                "scenario_source_file": row.get("scenario_source_file", ""),
            })
    selected.sort(key=lambda row: row["scenario_name"])
    eligible_core_candidate_count = len(selected)
    if limit is not None:
        selected = selected[: max(0, limit)]
    selected_count_after_limit = len(selected)
    true_excluded_count = len(excluded)
    limit_truncated_candidate_count = max(0, eligible_core_candidate_count - selected_count_after_limit)
    category_counts = Counter(cat for row in selected for cat in row.get("categories", []))
    return {
        "filter_is_evidence": False,
        "filter_policy": "requires_external_api=false, external_dependency_status=python_native, tool_allow_list present, milestone_count>0, official scenario resolvable",
        "inventory_count": len(rows),
        "eligible_core_candidate_count": eligible_core_candidate_count,
        "core_candidate_count": eligible_core_candidate_count,
        "selected_count_after_limit": selected_count_after_limit,
        "true_excluded_count": true_excluded_count,
        "excluded_count": true_excluded_count,
        "limit": limit,
        "limit_applied": limit is not None,
        "limit_truncated_candidate_count": limit_truncated_candidate_count,
        "selected_scenarios": selected,
        "excluded_scenarios": excluded,
        "excluded_reason_counting": "multi_label_non_exclusive",
        "excluded_reason_counts": dict(sorted(reason_counts.items())),
        "primary_excluded_reason_counts": dict(sorted(primary_reason_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _latest_result_run_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates = [path.parent for path in root.rglob("result_summary.json")]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _run_official_scenarios(scenario_names: Sequence[str], *, output_root: Path, parallel: int, extra_args: Sequence[str]) -> Path:
    if not scenario_names:
        raise ValueError("no core scenarios selected for official run")
    output_root.mkdir(parents=True, exist_ok=True)
    before = _latest_result_run_dir(output_root)
    cmd = [
        str(ROOT_DIR / "scripts" / "run_toolsandbox_official.sh"),
        "--scenarios",
        *scenario_names,
        "--parallel",
        str(parallel),
        "--output_dir",
        str(output_root),
        *extra_args,
    ]
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    after = _latest_result_run_dir(output_root)
    if after is None or after == before:
        raise RuntimeError(f"official ToolSandbox run did not produce a new result_summary.json under {output_root}")
    return after


def _export_run_dir(run_dir: Path, out_path: Path, *, limit: int | None = None) -> List[Dict[str, Any]]:
    cmd = [
        "python3",
        str(ROOT_DIR / "scripts" / "prepare_toolsandbox_formal_dataset.py"),
        "--official-run-dir",
        str(run_dir),
        "--out",
        str(out_path),
    ]
    if limit is not None:
        cmd.extend(["--limit", str(limit)])
    subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
    payload = _read_json(out_path)
    if not isinstance(payload, list):
        raise ValueError(f"expected export JSON list: {out_path}")
    return payload


def _run_dir_ready(run_dir: Path | None) -> bool:
    return bool(run_dir and (run_dir / "result_summary.json").exists() and (run_dir / "trajectories").exists())


def artifact_paths(out_prefix: Path) -> Dict[str, Path]:
    base = str(out_prefix)
    return {
        "filter": Path(base + ".core_filter.json"),
        "export": Path(base + ".json"),
        "manifest": Path(base + ".manifest.json"),
    }


def build_manifest(
    *,
    filter_payload: Mapping[str, Any],
    export_rows: List[Dict[str, Any]],
    dry_run: bool,
    run_dir: Path | None,
    run_mode: str,
    out_prefix: Path,
) -> Dict[str, Any]:
    run_ready = _run_dir_ready(run_dir)
    export_complete = (not dry_run) and run_ready and bool(export_rows)
    limited_export = bool(filter_payload.get("limit_applied"))
    core_export_is_evidence = export_complete and not limited_export
    if dry_run:
        dataset_status = "dry_run_empty_export"
    elif not export_complete:
        dataset_status = "incomplete_core_export"
    elif limited_export:
        dataset_status = "executed_core_smoke_export"
    else:
        dataset_status = "executed_core_export"
    return {
        "version": "toolsandbox_official_core_reproducible",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toolclaw_commit": _git_commit(ROOT_DIR),
        "official_toolsandbox_commit": _git_commit(DEFAULT_OFFICIAL_ROOT),
        "dry_run": dry_run,
        "dataset_status": dataset_status,
        "requires_execute_before_benchmark": not core_export_is_evidence,
        "run_mode": run_mode,
        "run_dir": str(run_dir.resolve()) if run_dir else "",
        "result_summary_present": bool(run_dir and (run_dir / "result_summary.json").exists()),
        "trajectories_present": bool(run_dir and (run_dir / "trajectories").exists()),
        "core_filter_path": str(artifact_paths(out_prefix)["filter"]),
        "export_path": str(artifact_paths(out_prefix)["export"]),
        "manifest_path": str(artifact_paths(out_prefix)["manifest"]),
        "inventory_count": filter_payload.get("inventory_count", 0),
        "core_candidate_count": filter_payload.get("core_candidate_count", 0),
        "export_row_count": len(export_rows),
        "core_export_is_evidence": core_export_is_evidence,
        "full_trajectory_messages_runtime_visible": False,
        "runtime_visibility_policy": "runtime_messages_only; full official transcript is scorer/provenance-only",
        "claim_boundary": "dry-run and smoke exports are pipeline validation only; no headline or reuse claim is promoted by this artifact",
        "next_step": "use a confirmed core export to re-derive reuse v3 candidates; do not run reuse formal before pilot-confirming exact headroom families",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ToolSandbox core reproducible scenario filter and optional export")
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--official-root", default=str(DEFAULT_OFFICIAL_ROOT))
    parser.add_argument("--out-prefix", default=str(DEFAULT_OUT_PREFIX))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--run-dir", default="new", help="new, latest, or an existing run directory path")
    parser.add_argument("--official-output-root", default=str(DEFAULT_OFFICIAL_OUTPUT_ROOT))
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Filter and write non-evidence artifacts without running official ToolSandbox; this is the default")
    parser.add_argument("--execute", action="store_true", help="Actually run official ToolSandbox for selected core scenarios")
    parser.add_argument("official_args", nargs=argparse.REMAINDER, help="Extra args passed to official ToolSandbox after --")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dry_run and args.execute:
        raise ValueError("--dry-run and --execute are mutually exclusive")
    inventory = _read_json(Path(args.inventory))
    official_root = Path(args.official_root)
    out_prefix = Path(args.out_prefix)
    resolvable = _official_scenario_names(official_root)
    filter_payload = core_filter_rows(inventory, resolvable_names=resolvable, limit=args.limit)
    selected_names = [row["scenario_name"] for row in filter_payload["selected_scenarios"]]
    run_dir: Path | None = None
    dry_run = not args.execute and args.run_dir == "new"
    extra_args = list(args.official_args)
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    if args.execute:
        run_dir = _run_official_scenarios(selected_names, output_root=Path(args.official_output_root), parallel=args.parallel, extra_args=extra_args)
        dry_run = False
    elif args.run_dir == "latest":
        run_dir = _latest_result_run_dir(Path(args.official_output_root) if Path(args.official_output_root).exists() else ROOT_DIR / "data" / "external" / "ToolSandbox" / "data")
        dry_run = run_dir is None
    elif args.run_dir != "new":
        run_dir = Path(args.run_dir)
        dry_run = not _run_dir_ready(run_dir)
    export_rows: List[Dict[str, Any]] = []
    paths = artifact_paths(out_prefix)
    export_path = paths["export"]
    if not dry_run and _run_dir_ready(run_dir):
        export_rows = _export_run_dir(run_dir, export_path, limit=args.limit)
    else:
        _write_json(export_path, [])
    _write_json(paths["filter"], filter_payload)
    _write_json(paths["manifest"], build_manifest(filter_payload=filter_payload, export_rows=export_rows, dry_run=dry_run, run_dir=run_dir, run_mode=args.run_dir, out_prefix=out_prefix))
    print(f"wrote: {paths['filter']}")
    print(f"wrote: {export_path}")
    print(f"wrote: {paths['manifest']}")


if __name__ == "__main__":
    main()
