import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_tau_bench_script_generates_scoreboard(tmp_path: Path) -> None:
    source = tmp_path / "tau.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau_cli_001",
                    "query": "retrieve and write report",
                    "scenario": "success",
                    "candidate_tools": ["search_tool", "write_tool"],
                }
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "tau_out"
    cmd = [
        sys.executable,
        "scripts/run_tau_bench.py",
        "--source",
        str(source),
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
    assert (outdir / "scoreboard.json").exists()
    assert (outdir / "per_system_summary.json").exists()

    scoreboard = json.loads((outdir / "scoreboard.json").read_text(encoding="utf-8"))
    assert scoreboard["benchmark"] == "tau_bench"
    assert scoreboard["num_samples"] == 1
    assert set(scoreboard["systems"]) == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}
