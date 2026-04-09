import os
import subprocess
from pathlib import Path


def test_run_tau_bench_remote_script_reports_missing_source_with_hint() -> None:
    completed = subprocess.run(
        [
            "bash",
            "scripts/run_tau_bench_remote.sh",
            "data/does_not_exist.json",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "tau-bench source not found: data/does_not_exist.json" in completed.stderr
    assert "hint: try source path data/tau_bench/tau_bench.aligned.jsonl" in completed.stderr
