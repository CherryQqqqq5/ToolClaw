import json
import os
import subprocess
from pathlib import Path


def test_run_ablation_script_runs_toolsandbox_formal_slice(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_success_001",
            "scenario": "success",
            "query": "target document summary",
            "target_path": "outputs/reports/task_success_001.txt",
        }
    ]
    taskset_path = tmp_path / "taskset.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    fallback_dataset = tmp_path / "toolsandbox.formal.json"
    fallback_dataset.write_text(
        json.dumps(
            [
                {
                    "name": "toolsandbox_ablation_001",
                    "query": "Turn wifi off and confirm it.",
                    "messages": [
                        {"sender": "user", "recipient": "agent", "content": "Turn wifi off and confirm it."}
                    ],
                    "tool_allow_list": ["set_wifi_status"],
                    "candidate_tools": [{"tool_id": "set_wifi_status", "description": "Toggle WiFi"}],
                    "categories": ["State Dependency", "Single Tool"],
                    "milestones": ["disable wifi", "confirm wifi disabled"],
                    "ideal_turn_count": 2,
                    "ideal_tool_calls": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "ablation_out"
    completed = subprocess.run(
        ["bash", "scripts/run_ablation.sh", str(taskset_path), str(outdir)],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "PYTHONPATH": "src",
            "TOOLSANDBOX_FORMAL_DATASET": str(tmp_path / "toolsandbox.formal.official.json"),
            "TOOLSANDBOX_FALLBACK_DATASET": str(fallback_dataset),
            "TOOLSANDBOX_OFFICIAL_DATA_ROOT": str(tmp_path / "missing_official_data"),
        },
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert (outdir / "matrix" / "comparison.csv").exists()
    assert (outdir / "reuse" / "reuse_summary.json").exists()
    assert (outdir / "toolsandbox_formal" / "scoreboard.json").exists()
    assert "toolsandbox_formal:" in completed.stdout
