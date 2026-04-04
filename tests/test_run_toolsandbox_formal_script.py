import json
import os
import subprocess
from pathlib import Path


def test_run_toolsandbox_formal_script_builds_missing_dataset_then_runs(tmp_path: Path) -> None:
    data_root = tmp_path / "official_data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_dir = run_dir / "trajectories" / "wifi_off"
    scenario_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": "wifi_off",
                        "categories": ["state_dependency", "single_tool"],
                        "similarity": 0.95,
                        "turn_count": 2,
                        "milestone_mapping": {"0": [1, 1.0], "1": [2, 1.0]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "conversation.json").write_text(
        json.dumps([{"sender": "USER", "recipient": "AGENT", "content": "Turn wifi off and confirm it."}]),
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

    dataset_path = tmp_path / "toolsandbox.formal.official.json"
    outdir = tmp_path / "toolsandbox_bench_official_formal"
    completed = subprocess.run(
        [
            "bash",
            "scripts/run_toolsandbox_formal.sh",
            "--dataset",
            str(dataset_path),
            "--outdir",
            str(outdir),
            "--official-run-dir",
            "latest",
            "--official-data-root",
            str(data_root),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert dataset_path.exists()
    assert (outdir / "scoreboard.json").exists()
    assert (outdir / "report.md").exists()

    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert rows[0]["name"] == "wifi_off"
    scoreboard = json.loads((outdir / "scoreboard.json").read_text(encoding="utf-8"))
    assert scoreboard["benchmark"] == "toolsandbox"
