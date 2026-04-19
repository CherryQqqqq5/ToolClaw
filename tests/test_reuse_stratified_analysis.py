import csv
import json
from pathlib import Path

from toolclaw.benchmarks.reuse_stratified_analysis import analyze_outdir


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_analyze_outdir_stratifies_exact_vs_transfer_and_recommends_narrow_framing(tmp_path: Path) -> None:
    rows = [
        {
            "run_index": "1",
            "task_id": "exact_task__pass2",
            "system": "a3_interaction",
            "success": "False",
            "tool_calls": "3",
            "repair_actions": "1",
            "user_turns": "1",
            "reused_artifact": "False",
            "reuse_tier": "none",
            "trace_path": "",
        },
        {
            "run_index": "1",
            "task_id": "exact_task__pass2",
            "system": "a4_reuse",
            "success": "True",
            "tool_calls": "2",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "True",
            "reuse_mode": "exact_reuse",
            "reuse_tier": "exact_match_reuse",
            "reuse_target_family": "contact_edit__pair00",
            "reuse_source_family": "contact_edit__pair00",
            "reuse_target_semantic_family": "contact_edit",
            "reuse_source_semantic_family": "contact_edit",
            "trace_path": "",
        },
        {
            "run_index": "1",
            "task_id": "same_family_task__pass2",
            "system": "a3_interaction",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "False",
            "reuse_tier": "none",
            "trace_path": "",
        },
        {
            "run_index": "1",
            "task_id": "same_family_task__pass2",
            "system": "a4_reuse",
            "success": "True",
            "tool_calls": "2",
            "repair_actions": "1",
            "user_turns": "1",
            "reused_artifact": "True",
            "reuse_mode": "transfer_reuse",
            "reuse_tier": "same_family_transfer_reuse",
            "reuse_target_family": "contact_edit__pair01",
            "reuse_source_family": "contact_edit__pair00",
            "reuse_target_semantic_family": "contact_edit",
            "reuse_source_semantic_family": "contact_edit",
            "trace_path": "",
        },
        {
            "run_index": "1",
            "task_id": "cross_family_task__pass2",
            "system": "a3_interaction",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "False",
            "reuse_tier": "none",
            "trace_path": "",
        },
        {
            "run_index": "1",
            "task_id": "cross_family_task__pass2",
            "system": "a4_reuse",
            "success": "False",
            "tool_calls": "2",
            "repair_actions": "1",
            "user_turns": "1",
            "reused_artifact": "True",
            "reuse_mode": "transfer_reuse",
            "reuse_tier": "cross_family_transfer_reuse",
            "reuse_target_family": "holiday_time__pair00",
            "reuse_source_family": "contact_edit__pair00",
            "reuse_target_semantic_family": "holiday_time",
            "reuse_source_semantic_family": "contact_edit",
            "trace_path": "",
        },
    ]
    _write_csv(tmp_path / "comparison.csv", rows)

    analysis = analyze_outdir(tmp_path)

    tiers = {entry["tier"]: entry for entry in analysis["tier_summary"]}
    assert tiers["exact_match_reuse"]["delta_success"] == 1.0
    assert tiers["same_family_transfer_reuse"]["delta_tool_calls"] == 1.0
    assert tiers["cross_family_transfer_reuse"]["delta_success"] == -1.0
    assert analysis["recommendation"]["headline"] == "exact-match benefit only"


def test_analyze_outdir_recovers_tier_from_trace_provenance_and_taskset(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "contact_edit__pair01__pass2",
            "reuse_family_id": "contact_edit__pair01",
        }
    ]
    taskset_path = tmp_path / "prepared.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")
    trace_path = tmp_path / "traces" / "a4.json"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "reuse_provenance": {
                        "reuse_mode": "transfer_reuse",
                        "reuse_source_family": "contact_edit__pair00",
                        "reuse_source_semantic_family": "contact_edit",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    rows = [
        {
            "task_id": "contact_edit__pair01__pass2",
            "system": "a3_interaction",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "False",
            "trace_path": "",
        },
        {
            "task_id": "contact_edit__pair01__pass2",
            "system": "a4_reuse",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "True",
            "trace_path": str(trace_path.relative_to(tmp_path)),
        },
    ]
    _write_csv(tmp_path / "comparison.csv", rows)

    analysis = analyze_outdir(tmp_path, taskset_path=taskset_path)

    tiers = {entry["tier"]: entry for entry in analysis["tier_summary"]}
    assert tiers["same_family_transfer_reuse"]["paired_cases"] == 1
