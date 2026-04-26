#!/usr/bin/env python3
"""Validate ToolSandbox core reproducible export freeze readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

REQUIRED_ROW_FIELDS = (
    "name",
    "query",
    "runtime_messages",
    "scorer_gold_messages",
    "runtime_visibility",
    "tool_allow_list",
    "candidate_tools",
    "milestones",
    "result_summary",
    "metadata",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _message_sender(message: Mapping[str, Any]) -> str:
    return str(message.get("sender") or message.get("role") or "").strip().lower()


def _runtime_messages_are_initial(messages: Sequence[Any]) -> bool:
    seen_user = False
    for item in messages:
        if not isinstance(item, dict):
            return False
        sender = _message_sender(item)
        if seen_user:
            return False
        if sender in {"assistant", "tool", "execution_environment", "environment"}:
            return False
        if sender == "user":
            seen_user = True
    return bool(messages)


def validate_core_export(export_rows: Any, manifest: Mapping[str, Any], *, allow_smoke: bool = False) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(export_rows, list):
        errors.append("export_must_be_json_list")
        export_rows = []
    dry_run = bool(manifest.get("dry_run"))
    dataset_status = str(manifest.get("dataset_status") or "")
    core_export_is_evidence = bool(manifest.get("core_export_is_evidence"))
    result_summary_present = bool(manifest.get("result_summary_present"))
    trajectories_present = bool(manifest.get("trajectories_present"))
    export_row_count = int(manifest.get("export_row_count") or 0)
    requires_execute = bool(manifest.get("requires_execute_before_benchmark"))
    runtime_visible = bool(manifest.get("full_trajectory_messages_runtime_visible"))

    if dry_run:
        errors.append("dry_run_export_not_freeze_ready")
    if runtime_visible:
        errors.append("full_trajectory_messages_marked_runtime_visible")
    if core_export_is_evidence:
        if dataset_status != "executed_core_export":
            errors.append("evidence_export_must_have_executed_core_export_status")
        if requires_execute:
            errors.append("evidence_export_must_not_require_execute_before_benchmark")
    else:
        warnings.append("core_export_is_not_evidence")
    if dataset_status == "executed_core_smoke_export":
        warnings.append("limited_smoke_export_not_claim_evidence")
        if not allow_smoke:
            errors.append("limited_smoke_export_not_freeze_ready")
    if not (result_summary_present and trajectories_present and export_row_count > 0 and len(export_rows) > 0):
        errors.append("missing_run_artifacts_or_empty_export")
    if export_row_count != len(export_rows):
        errors.append("manifest_export_row_count_mismatch")

    for index, row in enumerate(export_rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"row_{index}:not_object")
            continue
        row_id = str(row.get("name") or row.get("sample_id") or index)
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                errors.append(f"{row_id}:missing_{field}")
        if not (row.get("candidate_tools") or row.get("tool_allow_list")):
            errors.append(f"{row_id}:missing_candidate_tools_or_tool_allow_list")
        if not row.get("milestones"):
            errors.append(f"{row_id}:missing_milestones")
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        if not metadata.get("trajectory_dir"):
            errors.append(f"{row_id}:missing_trajectory_provenance")
        if not metadata.get("result_summary_path"):
            errors.append(f"{row_id}:missing_result_summary_provenance")
        runtime_visibility = row.get("runtime_visibility") if isinstance(row.get("runtime_visibility"), dict) else {}
        if runtime_visibility.get("full_messages_runtime_visible") is not False:
            errors.append(f"{row_id}:full_messages_runtime_visibility_not_false")
        if runtime_visibility.get("scorer_gold_runtime_visible") is not False:
            errors.append(f"{row_id}:scorer_gold_runtime_visibility_not_false")
        runtime_messages = row.get("runtime_messages")
        if not isinstance(runtime_messages, list) or not _runtime_messages_are_initial(runtime_messages):
            errors.append(f"{row_id}:runtime_messages_not_initial_user_prefix")
        messages = row.get("messages")
        if isinstance(messages, list) and isinstance(runtime_messages, list) and messages != runtime_messages:
            errors.append(f"{row_id}:legacy_messages_not_runtime_messages")
        scorer_gold_messages = row.get("scorer_gold_messages")
        if not isinstance(scorer_gold_messages, list) or not scorer_gold_messages:
            errors.append(f"{row_id}:missing_scorer_gold_messages")

    pipeline_valid = not errors
    freeze_ready = pipeline_valid and dataset_status == "executed_core_export" and core_export_is_evidence
    return {
        "pipeline_valid": pipeline_valid,
        "freeze_ready": freeze_ready,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "export_row_count": len(export_rows),
        "dataset_status": dataset_status,
        "core_export_is_evidence": core_export_is_evidence,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a ToolSandbox core reproducible export")
    parser.add_argument("--export", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--allow-smoke", action="store_true", help="Accept executed limited smoke exports as pipeline-valid but not freeze-ready")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate_core_export(_read_json(Path(args.export)), _read_json(Path(args.manifest)), allow_smoke=args.allow_smoke)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["pipeline_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
