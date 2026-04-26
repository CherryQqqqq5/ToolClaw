import json
import os
import subprocess
import sys
from pathlib import Path


def test_prepare_toolsandbox_official_run_extracts_latest_run(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_dir = run_dir / "trajectories" / "wifi_off"
    scenario_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": "wifi_off",
                        "categories": ["state_dependency", "multiple_tool"],
                        "similarity": 0.92,
                        "turn_count": 3,
                        "milestone_mapping": {"0": [1, 1.0], "1": [2, 1.0]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "conversation.json").write_text(
        json.dumps(
            [
                {"sender": "USER", "recipient": "AGENT", "content": "Turn wifi off and confirm it."},
                {"sender": "AGENT", "recipient": "USER", "content": "I will do that."},
            ]
        ),
        encoding="utf-8",
    )
    (scenario_dir / "scenario_export.json").write_text(
        json.dumps(
            {
                "tool_allow_list": ["set_wifi_status"],
                "candidate_tools": [{"tool_id": "set_wifi_status", "description": "Toggle WiFi"}],
                "ideal_tool_calls": 1,
                "milestones": ["disable wifi", "confirm wifi disabled"],
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "official.aligned.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_toolsandbox_official_run.py",
            "--run-dir",
            "latest",
            "--data-root",
            str(data_root),
            "--out",
            str(out_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert out_path.exists()

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "wifi_off"
    assert row["query"] == "Turn wifi off and confirm it."
    assert row["tool_allow_list"] == ["set_wifi_status"]
    assert row["candidate_tools"][0]["tool_id"] == "set_wifi_status"
    assert row["milestones"] == ["disable wifi", "confirm wifi disabled"]
    assert row["result_summary"]["similarity"] == 0.92
    assert row["metadata"]["scenario_export_present"] is True
    assert row["has_ground_truth_messages"] is True
    assert row["has_ground_truth_milestones"] is True
    assert row["has_ground_truth_tools"] is True


def test_prepare_toolsandbox_official_run_backfills_ground_truth_when_export_is_missing(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_name = "send_message_with_contact_content_cellular_off_multiple_user_turn"
    (run_dir / "trajectories" / scenario_name).mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": scenario_name,
                        "categories": ["state_dependency", "multiple_user_turn"],
                        "similarity": 0.0,
                        "turn_count": 4,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "official.aligned.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_toolsandbox_official_run.py",
            "--run-dir",
            "latest",
            "--data-root",
            str(data_root),
            "--out",
            str(out_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["query"] == "Send a message"
    assert row["tool_allow_list"] == [
        "search_contacts",
        "send_message_with_phone_number",
        "set_cellular_service_status",
        "get_cellular_service_status",
    ]
    assert row["candidate_tools"] == row["tool_allow_list"]
    assert len(row["milestones"]) == 4
    assert row["has_ground_truth_messages"] is True
    assert row["has_ground_truth_milestones"] is True
    assert row["has_ground_truth_tools"] is True
    assert row["metadata"]["scenario_export_present"] is False
    assert row["metadata"]["ground_truth_backfill_source"] == "vendored_scenario_source"


def test_prepare_toolsandbox_official_run_uses_execution_context_tool_allow_list(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_name = "custom_execution_context_only"
    scenario_dir = run_dir / "trajectories" / scenario_name
    scenario_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": scenario_name,
                        "categories": ["SINGLE_TOOL_CALL", "SINGLE_USER_TURN"],
                        "similarity": 0.75,
                        "turn_count": 3,
                        "milestone_mapping": {"0": [1, 1.0]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "conversation.json").write_text(
        json.dumps(
            [
                {"role": "system", "content": "Use tools carefully."},
                {"role": "user", "content": "Add Ada Lovelace to my contacts."},
                {"role": "assistant", "content": "Done."},
            ]
        ),
        encoding="utf-8",
    )
    (scenario_dir / "execution_context.json").write_text(
        json.dumps(
            {
                "tool_allow_list": ["add_contact", "end_conversation"],
                "tool_augmentation_list": ["THREE_DISTRACTION_TOOLS"],
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "official.aligned.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_toolsandbox_official_run.py",
            "--run-dir",
            "latest",
            "--data-root",
            str(data_root),
            "--out",
            str(out_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["query"] == "Add Ada Lovelace to my contacts."
    assert row["tool_allow_list"] == ["add_contact", "end_conversation"]
    assert row["candidate_tools"] == ["add_contact", "end_conversation"]
    assert row["milestones"] == ["milestone_0"]
    assert row["has_ground_truth_tools"] is True
    assert row["metadata"]["scenario_export_present"] is True
