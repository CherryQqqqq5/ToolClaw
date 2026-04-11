import json
import os
import subprocess
import sys
from pathlib import Path


def test_prepare_toolsandbox_formal_dataset_maps_official_run_to_formal_schema(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_a_dir = run_dir / "trajectories" / "wifi_off"
    scenario_b_dir = run_dir / "trajectories" / "find_contact_3_distraction_tools"
    scenario_a_dir.mkdir(parents=True)
    scenario_b_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": "find_contact_3_distraction_tools",
                        "categories": ["multiple_tool", "three_distraction_tools"],
                        "similarity": 0.84,
                        "turn_count": 4,
                        "milestone_mapping": {"0": [2, 1.0]},
                    },
                    {
                        "name": "wifi_off",
                        "categories": ["state_dependency", "single_tool"],
                        "similarity": 0.92,
                        "turn_count": 2,
                        "milestone_mapping": {"0": [1, 1.0], "1": [2, 1.0]},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (scenario_a_dir / "conversation.json").write_text(
        json.dumps([{"sender": "USER", "recipient": "AGENT", "content": "Turn wifi off and confirm it."}]),
        encoding="utf-8",
    )
    (scenario_a_dir / "scenario_export.json").write_text(
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
    (scenario_b_dir / "conversation.json").write_text(
        json.dumps([{"sender": "USER", "recipient": "AGENT", "content": "Find the contact and message them."}]),
        encoding="utf-8",
    )
    (scenario_b_dir / "scenario_export.json").write_text(
        json.dumps(
            {
                "tool_allow_list": ["search_contacts", "send_message"],
                "candidate_tools": [{"tool_id": "search_contacts", "description": "Find contacts"}],
                "ideal_tool_calls": 2,
            }
        ),
        encoding="utf-8",
    )

    out_path = tmp_path / "toolsandbox.formal.official.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_toolsandbox_formal_dataset.py",
            "--official-run-dir",
            "latest",
            "--official-data-root",
            str(data_root),
            "--exclude-augmented",
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

    rows = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "wifi_off"
    assert row["query"] == "Turn wifi off and confirm it."
    assert row["categories"] == ["State Dependency", "Single Tool"]
    assert row["tool_allow_list"] == ["set_wifi_status"]
    assert row["candidate_tools"][0]["tool_id"] == "set_wifi_status"
    assert row["milestones"] == ["disable wifi", "confirm wifi disabled"]
    assert row["ideal_turn_count"] == 2
    assert row["ideal_tool_calls"] == 1
    assert row["result_summary"]["similarity"] == 0.92
    assert row["has_ground_truth_messages"] is True
    assert row["has_ground_truth_milestones"] is True
    assert row["has_ground_truth_tools"] is True
    assert "warning: the prepared ToolSandbox formal dataset contains 1 or fewer validated samples" in completed.stderr


def test_prepare_toolsandbox_formal_dataset_skips_api_connection_shell_rows(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    valid_dir = run_dir / "trajectories" / "wifi_off"
    invalid_name = "api_connection_empty_shell_001"
    invalid_dir = run_dir / "trajectories" / invalid_name
    valid_dir.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": invalid_name,
                        "categories": ["state_dependency", "multiple_user_turn"],
                        "traceback": "Traceback ... APIConnectionError ...",
                    },
                    {
                        "name": "wifi_off",
                        "categories": ["state_dependency", "single_tool"],
                        "similarity": 0.92,
                        "turn_count": 2,
                        "milestone_mapping": {"0": [1, 1.0], "1": [2, 1.0]},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (valid_dir / "conversation.json").write_text(
        json.dumps([{"sender": "USER", "recipient": "AGENT", "content": "Turn wifi off and confirm it."}]),
        encoding="utf-8",
    )
    (valid_dir / "scenario_export.json").write_text(
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

    out_path = tmp_path / "toolsandbox.formal.official.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_toolsandbox_formal_dataset.py",
            "--official-run-dir",
            "latest",
            "--official-data-root",
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

    rows = json.loads(out_path.read_text(encoding="utf-8"))
    assert [row["name"] for row in rows] == ["wifi_off"]
    assert "skipping ToolSandbox sample without recoverable ground truth" in completed.stderr
