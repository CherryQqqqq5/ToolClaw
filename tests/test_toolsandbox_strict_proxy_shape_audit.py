from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


def _load_script():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "audit_toolsandbox_strict_proxy_shape.py"
    spec = importlib.util.spec_from_file_location("audit_toolsandbox_strict_proxy_shape", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_trace(path: Path, *, payload, state_patch=True, proxy=None):
    output = {"status": "success", "payload": payload}
    if state_patch:
        output["state_patch"] = {"last_reminder": payload, "reminders": [payload]}
    path.write_text(
        json.dumps(
            {
                "metadata": {"toolsandbox_result": proxy or {"similarity": 0.5, "matched_milestones": 1, "milestone_mapping": [0, None], "value_level_answer_verified": False}},
                "events": [
                    {"event_type": "tool_call", "tool_id": "add_reminder", "tool_args": {"query": "Remind me"}},
                    {"event_type": "tool_result", "tool_id": "add_reminder", "output": output},
                    {"event_type": "completion_verification", "output": {"completion_verified": True, "recommended_action": "finalize"}},
                    {"event_type": "final_response_synthesized", "output": {"content": "Done"}},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_shape_audit_counts_slot_complete_proxy_gap(tmp_path: Path) -> None:
    module = _load_script()
    trace = tmp_path / "trace.json"
    _write_trace(trace, payload={"content": "buy milk", "reminder_timestamp": 1777280400.0})
    rows = [
        {
            "task_id": "task",
            "system": "s4_reuse_overlay",
            "strict_scored_success": "False",
            "trace_path": str(trace),
        }
    ]

    summary = module.build_audit(rows, repo_root=tmp_path, target_system="s4_reuse_overlay")

    assert summary["strict_1_of_2_failure_count"] == 1
    assert summary["slot_complete_state_diff_strict_failure_count"] == 1
    assert summary["shape_gap_counts"] == {"proxy_milestone_cardinality_or_wrapper_gap": 1}
    record = summary["records"][0]
    assert record["action_executed"] is True
    assert record["all_required_slots_bound"] is True
    assert record["all_action_state_diff_exists"] is True


def test_shape_audit_distinguishes_missing_slot_and_state_diff(tmp_path: Path) -> None:
    module = _load_script()
    missing_slot_trace = tmp_path / "missing_slot.json"
    missing_state_trace = tmp_path / "missing_state.json"
    _write_trace(missing_slot_trace, payload={"content": "buy milk", "reminder_timestamp": None})
    _write_trace(missing_state_trace, payload={"content": "buy milk", "reminder_timestamp": 1777280400.0}, state_patch=False)
    rows = [
        {"task_id": "missing_slot", "system": "s4_reuse_overlay", "strict_scored_success": "False", "trace_path": str(missing_slot_trace)},
        {"task_id": "missing_state", "system": "s4_reuse_overlay", "strict_scored_success": "False", "trace_path": str(missing_state_trace)},
    ]

    summary = module.build_audit(rows, repo_root=tmp_path, target_system="s4_reuse_overlay")

    assert summary["shape_gap_counts"] == {"missing_required_slot": 1, "missing_state_diff": 1}
