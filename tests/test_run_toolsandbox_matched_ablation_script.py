import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_toolsandbox_matched_ablation_script_generates_outputs(tmp_path: Path) -> None:
    source = tmp_path / "toolsandbox.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "toolsandbox_cli_001",
                    "query": "retrieve and write report",
                    "scenario": "binding_failure",
                    "candidate_tools": ["search_tool", "write_tool"],
                    "tool_allow_list": ["search_tool", "write_tool"],
                    "milestones": ["retrieve data", "write report"],
                    "ideal_tool_calls": 2,
                }
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "matched_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_matched_ablation.py",
            "--source",
            str(source),
            "--outdir",
            str(outdir),
            "--num-runs",
            "1",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert (outdir / "scoreboard.json").exists()
    assert (outdir / "per_system_summary.json").exists()
    scoreboard = json.loads((outdir / "scoreboard.json").read_text(encoding="utf-8"))
    assert set(scoreboard["systems"]) == {
        "tc_full",
        "tc_no_repair",
        "tc_no_fallback",
        "tc_no_reuse",
        "tc_planner_only",
    }
