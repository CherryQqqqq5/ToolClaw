import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_toolsandbox_bench_script_generates_scoreboard_and_category_summary(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "toolsandbox_cli_001",
            "query": "retrieve and write report",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the data and save the report."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Write report"},
            ],
            "categories": ["State Dependency", "Multiple Tool Call"],
            "milestones": ["retrieve data", "write artifact"],
            "ideal_turn_count": 2,
            "ideal_tool_calls": 2,
        }
    ]
    source_path = tmp_path / "toolsandbox.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "toolsandbox_out"
    cmd = [
        sys.executable,
        "scripts/run_toolsandbox_bench.py",
        "--source",
        str(source_path),
        "--outdir",
        str(outdir),
        "--num-runs",
        "1",
    ]
    completed = subprocess.run(
        cmd,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    scoreboard_path = outdir / "scoreboard.json"
    per_system_path = outdir / "per_system_summary.json"
    per_category_md_path = outdir / "per_category_summary.md"
    normalized_path = outdir / "prepared" / "toolsandbox.normalized.json"

    assert scoreboard_path.exists()
    assert per_system_path.exists()
    assert per_category_md_path.exists()
    assert normalized_path.exists()

    scoreboard = json.loads(scoreboard_path.read_text(encoding="utf-8"))
    assert scoreboard["benchmark"] == "toolsandbox"
    assert scoreboard["num_samples"] == 1
    assert set(scoreboard["systems"]) == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}

    per_system = json.loads(per_system_path.read_text(encoding="utf-8"))
    assert "a0_baseline" in per_system
    assert "a4_reuse" in per_system
    assert "per_category" in per_system["a0_baseline"]
    assert "state_dependency" in per_system["a0_baseline"]["per_category"]

    per_category_md = per_category_md_path.read_text(encoding="utf-8")
    assert "ToolSandbox Category Summary" in per_category_md
    assert "state_dependency" in per_category_md
