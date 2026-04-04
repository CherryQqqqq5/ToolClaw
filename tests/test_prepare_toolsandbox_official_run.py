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
