import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_tau2_bench_script_generates_scoreboard(tmp_path: Path) -> None:
    source = tmp_path / "tau2.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau2_cli_001",
                    "scenario": "binding_failure",
                    "query": "retrieve and write report",
                    "candidate_tools": ["search_tool", "write_tool"],
                    "simulated_policy": {
                        "mode": "cooperative",
                        "missing_arg_values": {"target_path": "outputs/tau2/recovered.txt"},
                    },
                    "expected_user_turns": 1,
                    "expected_repairs": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "tau2_out"
    cmd = [
        sys.executable,
        "scripts/run_tau2_bench.py",
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
    assert scoreboard["benchmark"] == "tau2_bench"
    assert scoreboard["num_samples"] == 1
    assert set(scoreboard["systems"]) == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}
