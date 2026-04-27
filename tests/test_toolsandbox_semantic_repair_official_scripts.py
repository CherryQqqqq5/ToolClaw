from __future__ import annotations

import csv
import json
import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_derive_toolsandbox_semantic_repair_official(tmp_path: Path) -> None:
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    trace = trace_dir / "turn_on_wifi_low_battery_mode_a3_full_interaction.json"
    trace.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_type": "user_query",
                        "metadata": {
                            "query_metadata": {
                                "question_type": "missing_slot_query",
                                "patch_targets": {"retrieved_info": "state.retrieved_info"},
                            }
                        },
                    },
                    {
                        "event_type": "interaction_round_outcome",
                        "metadata": {
                            "answer_patch": {
                                "effect_scope": "slot",
                                "effective_patch": True,
                                "expected_patch_targets": ["retrieved_info"],
                            },
                            "reply_metadata": {
                                "decoded_intent_type": "slot_fill",
                                "decoded_slot_updates": {"retrieved_info": "wifi_enabled"},
                                "expected_targets": ["retrieved_info"],
                            },
                        },
                        "output": {
                            "target_alignment": 1.0,
                            "effective_patch": True,
                            "post_query_progress": True,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            [
                {"name": "turn_on_wifi_low_battery_mode", "categories": ["state_dependency"]},
                {"name": "turn_on_wifi_low_battery_mode_implicit", "categories": ["state_dependency"]},
                {"name": "turn_on_location_low_battery_mode", "categories": ["state_dependency"]},
                {"name": "turn_on_location_low_battery_mode_implicit", "categories": ["state_dependency"]},
                {"name": "turn_on_cellular_low_battery_mode", "categories": ["state_dependency"]},
                {"name": "turn_on_cellular_low_battery_mode_implicit", "categories": ["state_dependency"]},
                {"name": "add_reminder_content_and_date_and_time_multiple_user_turn", "categories": ["multiple_user_turn"]},
                {"name": "add_reminder_content_and_week_delta_and_time_multiple_user_turn", "categories": ["multiple_user_turn"]},
                {"name": "find_days_till_holiday_multiple_user_turn", "categories": ["multiple_user_turn"]},
                {"name": "search_message_with_recency_latest_multiple_user_turn", "categories": ["multiple_user_turn"]},
                {"name": "remove_contact_by_phone_no_remove_contact_insufficient_information", "categories": ["insufficient_information"]},
                {"name": "remove_contact_by_phone_no_remove_contact_insufficient_information_alt", "categories": ["insufficient_information"]},
            ]
        ),
        encoding="utf-8",
    )
    comparison = tmp_path / "comparison.scored.csv"
    rows = []
    systems = ["a3_full_interaction", "a3_no_query", "a3_noisy_user"]
    for task_id in [
        "turn_on_wifi_low_battery_mode",
        "turn_on_wifi_low_battery_mode_implicit",
        "turn_on_location_low_battery_mode",
        "turn_on_location_low_battery_mode_implicit",
        "turn_on_cellular_low_battery_mode",
        "turn_on_cellular_low_battery_mode_implicit",
        "add_reminder_content_and_date_and_time_multiple_user_turn",
        "add_reminder_content_and_week_delta_and_time_multiple_user_turn",
        "find_days_till_holiday_multiple_user_turn",
        "search_message_with_recency_latest_multiple_user_turn",
        "remove_contact_by_phone_no_remove_contact_insufficient_information",
        "remove_contact_by_phone_no_remove_contact_insufficient_information_alt",
    ]:
        for system in systems:
            rows.append(
                {
                    "task_id": task_id,
                    "system": system,
                    "strict_scored_success_rate": "1.0" if system == "a3_full_interaction" else "0.0",
                    "reply_usable_rate": "1.0" if system == "a3_full_interaction" and "turn_on_" in task_id else "0.0",
                    "effective_patch_rate": "1.0" if system == "a3_full_interaction" and "turn_on_" in task_id else "0.0",
                    "useful_interaction_round_rate": "1.0" if system == "a3_full_interaction" and "turn_on_" in task_id else "0.0",
                    "trace_path": str(trace),
                }
            )
    _write_csv(comparison, rows)
    out = tmp_path / "dataset.jsonl"
    manifest = tmp_path / "dataset.manifest.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "derive_toolsandbox_semantic_repair_official.py"),
            "--source",
            str(source),
            "--comparison",
            str(comparison),
            "--out",
            str(out),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 12
    primary = [row for row in rows if row["slice_type"] == "repair_semantic_positive"]
    assert len(primary) == 6
    assert all(row["manual_label_status"].startswith("human_verified") for row in primary)


def test_score_toolsandbox_semantic_repair_official(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps({"task_id": "repair_1", "slice_type": "repair_semantic_positive"}),
                json.dumps({"task_id": "probe_1", "slice_type": "probe_only_control"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir()
    useful_trace = trace_dir / "repair_a3_full_interaction.json"
    useful_trace.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_type": "interaction_round_outcome",
                        "metadata": {"decoded_is_usable": True},
                        "output": {
                            "decoded_is_usable": True,
                            "target_alignment": 1.0,
                            "effective_patch": True,
                            "post_query_progress": True,
                            "interaction_round_useful": True,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    inert_trace = trace_dir / "probe_a3_noisy_user.json"
    inert_trace.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_type": "interaction_round_outcome",
                        "metadata": {"decoded_is_usable": False},
                        "output": {
                            "decoded_is_usable": False,
                            "target_alignment": 0.0,
                            "effective_patch": False,
                            "post_query_progress": False,
                            "interaction_round_useful": False,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    comparison = tmp_path / "comparison.scored.csv"
    rows = [
        {
            "task_id": "repair_1",
            "system": "a2_planner",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "0.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "repair_1",
            "system": "a3_full_interaction",
            "strict_scored_success_rate": "1.0",
            "execution_verified_success_rate": "1.0",
            "reply_usable_rate": "1.0",
            "target_aligned_patch_rate": "1.0",
            "effective_patch_rate": "1.0",
            "post_query_progress_rate": "1.0",
            "useful_interaction_round_rate": "1.0",
            "mean_user_queries": "1.0",
            "tool_calls": "1",
            "trace_path": str(useful_trace),
        },
        {
            "task_id": "repair_1",
            "system": "a3_no_query",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "0.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "repair_1",
            "system": "a3_noisy_user",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "1.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "probe_1",
            "system": "a2_planner",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "0.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "probe_1",
            "system": "a3_full_interaction",
            "strict_scored_success_rate": "1.0",
            "execution_verified_success_rate": "1.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "1.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "probe_1",
            "system": "a3_no_query",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "0.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
        {
            "task_id": "probe_1",
            "system": "a3_noisy_user",
            "strict_scored_success_rate": "1.0",
            "execution_verified_success_rate": "1.0",
            "reply_usable_rate": "0.0",
            "target_aligned_patch_rate": "0.0",
            "effective_patch_rate": "0.0",
            "post_query_progress_rate": "0.0",
            "useful_interaction_round_rate": "0.0",
            "mean_user_queries": "1.0",
            "tool_calls": "1",
            "trace_path": str(inert_trace),
        },
    ]
    _write_csv(comparison, rows)
    outdir = tmp_path / "out"
    outdir.mkdir()
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "scripts" / "score_toolsandbox_semantic_repair_official.py"),
            "--dataset",
            str(dataset),
            "--comparison",
            str(comparison),
            "--outdir",
            str(outdir),
        ],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    claim = json.loads((outdir / "claim_summary.json").read_text(encoding="utf-8"))
    assert claim["semantic_repair_mechanism_supported"] is True
    assert claim["probe_only_success_caveat_present"] is True
    paired = json.loads((outdir / "paired_delta_summary.json").read_text(encoding="utf-8"))
    repair_stats = paired["comparisons"]["a3_full_interaction_vs_a2_planner"]["by_slice"]["repair_semantic_positive"]
    assert repair_stats["wins"] == 1
    assert repair_stats["losses"] == 0
    assert repair_stats["ties"] == 0
    assert repair_stats["mean_delta"] == 1.0
    probe_stats = paired["comparisons"]["a3_full_interaction_vs_a3_noisy_user"]["by_slice"]["probe_only_control"]
    assert probe_stats["wins"] == 0
    assert probe_stats["ties"] == 1
    assert (outdir / "paired_delta_summary.md").exists()


def test_derive_toolsandbox_semantic_repair_official_v2_manifest(tmp_path: Path) -> None:
    module_path = ROOT_DIR / "scripts" / "derive_toolsandbox_semantic_repair_official.py"
    spec = importlib.util.spec_from_file_location("derive_toolsandbox_semantic_repair_official", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = tmp_path / "source.json"
    task_ids = list(module.PRIMARY_TASK_IDS) + list(module.PROBE_CONTROL_TASK_IDS)
    source.write_text(json.dumps([{"name": task_id, "categories": ["state_dependency"]} for task_id in task_ids]), encoding="utf-8")
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"events": [{"event_type": "interaction_round_outcome", "metadata": {"answer_patch": {"effective_patch": True}}, "output": {"target_alignment": 1.0, "effective_patch": True, "post_query_progress": True}}]}), encoding="utf-8")
    comparison = tmp_path / "comparison.csv"
    rows = []
    for task_id in task_ids:
        for system in ["a3_full_interaction", "a3_no_query", "a3_noisy_user"]:
            rows.append({"task_id": task_id, "system": system, "trace_path": str(trace), "strict_scored_success_rate": "1.0" if system == "a3_full_interaction" else "0.0"})
    _write_csv(comparison, rows)

    dataset, manifest = module.derive(
        source,
        comparison,
        dataset_name="toolsandbox_semantic_repair_official_v2",
        slice_policy_version="toolsandbox_semantic_repair_official_v2",
        metadata_key="semantic_repair_official_v2",
        manual_label_suffix="20260427",
    )

    assert manifest["dataset"] == "toolsandbox_semantic_repair_official_v2"
    assert manifest["source"].endswith("source.json")
    assert manifest["row_count"] == 12
    assert dataset[0]["manual_label_status"].endswith("20260427")
    assert "semantic_repair_official_v2" in dataset[0]["metadata"]
