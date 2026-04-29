import csv
import importlib.util
import json
from pathlib import Path
from typing import Dict, List


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_toolsandbox_interaction_attribution.py"
SPEC = importlib.util.spec_from_file_location("audit_toolsandbox_interaction_attribution", MODULE_PATH)
audit_mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit_mod)


def _write_trace(path: Path, *, probe: bool = False, singleton: bool = False, useful: bool = False) -> None:
    expected = "tool_switch" if singleton else "missing_asset_patch"
    step_id = "interaction_probe" if probe else "step_01"
    schema = (
        {"type": "object", "properties": {"tool_id": {"type": "string", "enum": ["end_conversation"]}}}
        if singleton
        else {"type": "object", "properties": {"value": {"type": "string"}}}
    )
    payload = {
        "task_id": path.stem,
        "events": [
            {
                "event_type": "user_query",
                "step_id": step_id,
                "output": {"expected_answer_type": expected},
                "metadata": {
                    "interaction_id": "round_1",
                    "allowed_response_schema": schema,
                    "patch_targets": {"value": "state.slot"} if not singleton else {"tool_id": "binding.primary_tool"},
                    "query_metadata": {
                        "interaction_probe": probe,
                        "query_policy": {"question_type": expected},
                        "gold_free": True,
                    },
                },
            },
            {
                "event_type": "user_reply",
                "step_id": step_id,
                "output": {"value": "patched"},
                "metadata": {
                    "interaction_id": "round_1",
                    "accepted": True,
                    "reply_metadata": {
                        "decoded_slot_updates": {"value": "patched"} if useful else {},
                        "decoded_control_updates": {"tool_id": "end_conversation"} if singleton else {},
                        "decoded_is_usable": useful,
                        "target_alignment": 1.0 if useful else 0.0,
                    },
                },
            },
            {
                "event_type": "interaction_round_outcome",
                "step_id": step_id,
                "output": {
                    "decoded_is_usable": useful,
                    "target_alignment": 1.0 if useful else 0.0,
                    "effective_patch": useful,
                    "post_query_progress": useful,
                    "interaction_round_useful": useful,
                },
                "metadata": {
                    "interaction_id": "round_1",
                    "answer_patch": {
                        "effect_scope": "slot" if useful else "",
                        "actual_patch_targets": ["value"] if useful else [],
                    },
                },
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    fieldnames = [
        "run_index",
        "task_id",
        "system",
        "strict_scored_success",
        "tool_calls",
        "user_queries",
        "probe_user_queries",
        "repair_user_queries",
        "probe_user_replies",
        "repair_user_replies",
        "effective_patch_rate",
        "raw_repair_actions",
        "raw_token_cost",
        "trace_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_suite_mode_summarizes_cost_and_round_attribution(tmp_path: Path) -> None:
    s2_trace = tmp_path / "001_task_s2_planner_overlay.json"
    s3_trace = tmp_path / "001_task_s3_interaction_overlay.json"
    _write_trace(s2_trace, probe=False, singleton=True, useful=False)
    _write_trace(s3_trace, probe=False, singleton=False, useful=True)
    csv_path = tmp_path / "comparison.scored.csv"
    _write_csv(
        csv_path,
        [
            {
                "run_index": "1",
                "task_id": "task",
                "system": "s2_planner_overlay",
                "strict_scored_success": "False",
                "tool_calls": "1",
                "user_queries": "1",
                "probe_user_queries": "0",
                "repair_user_queries": "0",
                "probe_user_replies": "0",
                "repair_user_replies": "0",
                "effective_patch_rate": "0",
                "raw_repair_actions": "0",
                "raw_token_cost": "2",
                "trace_path": str(s2_trace),
            },
            {
                "run_index": "1",
                "task_id": "task",
                "system": "s3_interaction_overlay",
                "strict_scored_success": "True",
                "tool_calls": "2",
                "user_queries": "1",
                "probe_user_queries": "0",
                "repair_user_queries": "1",
                "probe_user_replies": "0",
                "repair_user_replies": "1",
                "effective_patch_rate": "1",
                "raw_repair_actions": "1",
                "raw_token_cost": "5",
                "trace_path": str(s3_trace),
            },
        ],
    )

    summary = audit_mod.audit_suite(csv_path)

    s3 = summary["per_system"]["s3_interaction_overlay"]
    assert s3["strict_success_count"] == 1
    assert s3["repair_user_queries_sum"] == 1
    assert s3["semantic_credit_round_count"] == 1
    assert s3["user_queries_per_strict_success"] == 1
    assert s3["probe_queries_per_strict_success"] == 0
    assert s3["tool_calls_per_strict_success"] == 2
    assert summary["per_system"]["s2_planner_overlay"]["singleton_action_mask_round_count"] == 1
    assert summary["s3_vs_s2_paired"]["wins"] == 1
    assert summary["s3_vs_s2_paired"]["additional_wins"] == 1
    assert summary["s3_vs_s2_paired"]["tool_calls_delta_sum"] == 1
    assert summary["s3_vs_s2_paired"]["cost_proxy_delta_sum"] == 3
    assert summary["s3_vs_s2_paired"]["user_queries_per_additional_win"] == 0
    assert summary["s3_vs_s2_paired"]["probe_queries_per_additional_win"] == 0
    assert summary["s3_vs_s2_paired"]["repair_queries_per_additional_win"] == 1
    assert summary["s3_vs_s2_paired"]["tool_calls_per_additional_win"] == 1
    assert "lower bound" in summary["semantic_credit_lower_bound_note"]


def test_suite_mode_flags_probe_only_and_reply_attribution_warning(tmp_path: Path) -> None:
    trace = tmp_path / "002_probe_s3_interaction_overlay.json"
    _write_trace(trace, probe=True, singleton=False, useful=False)
    csv_path = tmp_path / "comparison.scored.csv"
    _write_csv(
        csv_path,
        [
            {
                "run_index": "1",
                "task_id": "probe_task",
                "system": "s3_interaction_overlay",
                "strict_scored_success": "False",
                "tool_calls": "1",
                "user_queries": "1",
                "probe_user_queries": "1",
                "repair_user_queries": "0",
                "probe_user_replies": "0",
                "repair_user_replies": "1",
                "effective_patch_rate": "0",
                "raw_repair_actions": "0",
                "raw_token_cost": "0",
                "trace_path": str(trace),
            }
        ],
    )

    summary = audit_mod.audit_suite(csv_path)

    s3 = summary["per_system"]["s3_interaction_overlay"]
    assert s3["probe_only_round_count"] == 1
    assert s3["semantic_credit_round_count"] == 0
    assert summary["warnings"]["repair_user_replies_gt_repair_user_queries_count"] == 1
    assert "Instrumentation/attribution limitation" in summary["warnings"]["repair_user_replies_gt_repair_user_queries_note"]
    assert summary["warnings"]["examples"][0]["task_id"] == "probe_task"
