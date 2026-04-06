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
    assert (outdir / "experiment_manifest.json").exists()

    scoreboard = json.loads((outdir / "scoreboard.json").read_text(encoding="utf-8"))
    assert scoreboard["benchmark"] == "tau_bench"
    assert scoreboard["num_samples"] == 1
    assert set(scoreboard["systems"]) == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}
    experiment_manifest = json.loads((outdir / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert experiment_manifest["experiment_metadata"]["runner_script"].endswith("scripts/run_tau_bench.py")
    assert experiment_manifest["comparison_path"].endswith("comparison.csv")
    assert len(experiment_manifest["archived_files"]) >= 1

    check_completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_benchmark_consistency.py",
            "--outdir",
            str(outdir),
            "--expected-systems",
            "a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
            "--expected-source",
            str(source),
            "--expected-config",
            "configs/benchmark_tau.yaml",
            "--expected-model-version",
            "phase1_executor",
            "--expected-num-runs",
            "1",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert check_completed.returncode == 0
    assert "CONSISTENCY CHECK: PASSED" in check_completed.stdout
