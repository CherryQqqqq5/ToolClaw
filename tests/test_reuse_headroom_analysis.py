import csv
import json
from pathlib import Path

from toolclaw.benchmarks.reuse_headroom_analysis import analyze_outdir


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_trace(path: Path, *, query_types: list[str], repair_types: list[str], reuse_application: str = "", continuation_hint_kinds: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    for repair_type in repair_types:
        events.append({"event_type": "repair_triggered", "output": {"repair_type": repair_type}})
    for question_type in query_types:
        events.append({"event_type": "user_query", "metadata": {"query_policy_decision": {"question_type": question_type}}})
    payload = {
        "metadata": {
            "reusable_context": {
                "reuse_application": reuse_application,
                "continuation_hints": [{"kind": kind} for kind in continuation_hint_kinds or []],
            }
        },
        "events": events,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_headroom_analysis_selects_only_exact_or_same_family_cases_with_cost_headroom(tmp_path: Path) -> None:
    taskset = [
        {"task_id": "approval_task__pass2", "reuse_family_id": "approval_task__pair00"},
        {"task_id": "cross_task__pass2", "reuse_family_id": "cross_task__pair00"},
    ]
    taskset_path = tmp_path / "prepared.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")
    a3_trace = tmp_path / "traces" / "a3.json"
    a4_trace = tmp_path / "traces" / "a4.json"
    _write_trace(a3_trace, query_types=["approval", "approval"], repair_types=["request_approval"])
    _write_trace(
        a4_trace,
        query_types=["approval_and_patch"],
        repair_types=["request_approval"],
        reuse_application="continuation_prior",
        continuation_hint_kinds=["approved_then_resume_same_step"],
    )
    rows = [
        {
            "task_id": "approval_task__pass2",
            "system": "a3_interaction",
            "success": "True",
            "tool_calls": "2",
            "repair_actions": "0",
            "user_turns": "2",
            "failure_type": "approval_required",
            "expected_recovery_path": "ask_approval_then_retry",
            "trace_path": str(a3_trace.relative_to(tmp_path)),
        },
        {
            "task_id": "approval_task__pass2",
            "system": "a4_reuse",
            "success": "True",
            "tool_calls": "2",
            "repair_actions": "0",
            "user_turns": "2",
            "reused_artifact": "True",
            "reuse_mode": "exact_reuse",
            "reuse_tier": "exact_match_reuse",
            "reuse_target_family": "approval_task__pair00",
            "reuse_source_family": "approval_task__pair00",
            "reuse_target_semantic_family": "approval_task",
            "reuse_source_semantic_family": "approval_task",
            "reuse_source_task_id": "approval_task__pass1",
            "failure_type": "approval_required",
            "expected_recovery_path": "ask_approval_then_retry",
            "trace_path": str(a4_trace.relative_to(tmp_path)),
        },
        {
            "task_id": "cross_task__pass2",
            "system": "a3_interaction",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "failure_type": "canonicalization",
            "expected_recovery_path": "rebind_or_switch_then_retry",
            "trace_path": "",
        },
        {
            "task_id": "cross_task__pass2",
            "system": "a4_reuse",
            "success": "True",
            "tool_calls": "1",
            "repair_actions": "0",
            "user_turns": "0",
            "reused_artifact": "True",
            "reuse_mode": "transfer_reuse",
            "reuse_tier": "cross_family_transfer_reuse",
            "reuse_target_family": "cross_task__pair00",
            "reuse_source_family": "other_task__pair00",
            "reuse_target_semantic_family": "cross_task",
            "reuse_source_semantic_family": "other_task",
            "failure_type": "canonicalization",
            "expected_recovery_path": "rebind_or_switch_then_retry",
            "trace_path": "",
        },
    ]
    _write_csv(tmp_path / "comparison.csv", rows)

    analysis = analyze_outdir(tmp_path, taskset_path=taskset_path)

    assert analysis["candidate_case_count"] == 1
    case = analysis["candidate_cases"][0]
    assert case["task_id"] == "approval_task__pass2"
    assert case["headroom_signals"] == ["interaction"]
    assert case["a4"]["query_types"] == ["approval_and_patch"]
    assert case["a4"]["reuse_application"] == "continuation_prior"
    assert case["a4"]["continuation_hint_kinds"] == ["approved_then_resume_same_step"]
    assert analysis["recommendation"]["headline"] == "reuse remains safe but not yet headroom-seeking"
