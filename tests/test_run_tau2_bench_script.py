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


def test_run_tau2_bench_script_supports_failtax_slice_and_reuse_second_run(tmp_path: Path) -> None:
    source = tmp_path / "tau2_slice.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau2_state_cli_001",
                    "scenario": "state_failure",
                    "query": "retrieve and write report",
                    "primary_failtax": "state",
                    "failtaxes": ["state"],
                    "task_family": "t1_static_recovery",
                    "state_slots": ["retrieved_info"],
                    "gold_recovery_class": "patch_state_then_retry",
                    "budget_profile": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "constraints": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "state_failure_mode": "state_stale_slot",
                    "simulated_policy": {
                        "mode": "cooperative",
                        "missing_arg_values": {"retrieved_info": "refreshed summary"},
                    },
                    "expected_user_turns": 1,
                    "expected_repairs": 1,
                },
                {
                    "sample_id": "tau2_recovery_cli_001",
                    "scenario": "environment_failure",
                    "query": "retrieve and write report",
                    "primary_failtax": "recovery",
                    "failtaxes": ["recovery"],
                    "task_family": "t1_static_recovery",
                    "state_slots": ["target_path"],
                    "gold_recovery_class": "clarify_or_switch_then_retry",
                    "budget_profile": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "constraints": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "simulated_policy": {"mode": "cooperative"},
                    "expected_user_turns": 1,
                    "expected_repairs": 1,
                },
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "tau2_slice_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_tau2_bench.py",
            "--source",
            str(source),
            "--outdir",
            str(outdir),
            "--systems",
            "a3_interaction,a4_reuse",
            "--slice-by",
            "failtax",
            "--slice-values",
            "state",
            "--reuse-second-run",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    scoreboard = json.loads((outdir / "scoreboard.json").read_text(encoding="utf-8"))
    assert scoreboard["num_samples"] == 2
    run_task_ids = {entry["task_id"] for entry in scoreboard["runs"]}
    assert run_task_ids == {"tau2_state_cli_001__pass1", "tau2_state_cli_001__pass2"}
    manifest = json.loads((outdir / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["experiment_metadata"]["slice_by"] == "failtax"
    assert manifest["experiment_metadata"]["reuse_second_run"] is True


def test_run_tau2_bench_script_supports_budget_sweep(tmp_path: Path) -> None:
    source = tmp_path / "tau2_budget.json"
    source.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau2_budget_cli_001",
                    "scenario": "environment_failure",
                    "query": "retrieve and write report",
                    "primary_failtax": "recovery",
                    "failtaxes": ["recovery"],
                    "task_family": "t1_static_recovery",
                    "state_slots": ["target_path"],
                    "gold_recovery_class": "clarify_or_switch_then_retry",
                    "budget_profile": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "constraints": {"max_user_turns": 1, "max_repair_attempts": 1, "max_tool_calls": 3},
                    "simulated_policy": {"mode": "cooperative"},
                    "expected_user_turns": 1,
                    "expected_repairs": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "tau2_budget_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_tau2_bench.py",
            "--source",
            str(source),
            "--outdir",
            str(outdir),
            "--systems",
            "a3_interaction",
            "--budget-sweep",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert (outdir / "budget_sweep_summary.json").exists()
    assert (outdir / "budget_sweep_report.md").exists()
