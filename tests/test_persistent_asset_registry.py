import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))


def test_run_eval_can_persist_a4_reuse_assets_across_cli_invocations(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "persistent_reuse_001",
            "scenario": "success",
            "query": "retrieve and write report",
        }
    ]
    taskset_path = tmp_path / "taskset.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    registry_root = tmp_path / "asset_registry"
    first_outdir = tmp_path / "first_run"
    second_outdir = tmp_path / "second_run"
    base_cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--systems",
        "a4_reuse",
        "--asset-registry-root",
        str(registry_root),
    ]

    first = subprocess.run(
        [*base_cmd, "--outdir", str(first_outdir)],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [*base_cmd, "--outdir", str(second_outdir)],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0
    assert second.returncode == 0

    first_row = _load_rows(first_outdir / "comparison.csv")[0]
    second_row = _load_rows(second_outdir / "comparison.csv")[0]
    assert first_row["reused_artifact"] == "False"
    assert second_row["reused_artifact"] == "True"
