from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def test_command_for_suite_includes_runner_flags(tmp_path: Path) -> None:
    module_path = Path("scripts/run_paper_bench_suite.py")
    spec = importlib.util.spec_from_file_location("run_paper_bench_suite", module_path)
    assert spec is not None and spec.loader is not None
    suite_runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite_runner)

    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    suite_cfg = {
        "runner": "scripts/run_toolsandbox_bench.py",
        "default_source": str(source),
        "default_mode": "planner",
        "default_systems": "a1_recovery,a2_planner",
        "default_num_runs": 1,
        "runner_flags": ["--planner-sensitive-protocol"],
    }
    args = argparse.Namespace(
        source=None,
        mode=None,
        systems=None,
        num_runs=None,
        keep_normalized_taskset=False,
    )
    command = suite_runner._command_for_suite(suite_cfg, tmp_path / "out", args)
    assert "--planner-sensitive-protocol" in command



def test_planner_sensitive_score_command_includes_source_and_comparison(tmp_path: Path) -> None:
    module_path = Path("scripts/run_paper_bench_suite.py")
    spec = importlib.util.spec_from_file_location("run_paper_bench_suite", module_path)
    assert spec is not None and spec.loader is not None
    suite_runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite_runner)

    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    outdir = tmp_path / "out"
    outdir.mkdir()
    comparison = outdir / "comparison.scored.csv"
    comparison.write_text("task_id,system\n", encoding="utf-8")
    suite_cfg = {
        "score_script": "scripts/score_toolsandbox_planner_sensitive.py",
        "default_source": str(source),
    }
    args = argparse.Namespace(source=None)
    command = suite_runner._score_command(suite_cfg, outdir, args)
    assert "--source" in command
    assert str(source) in command
    assert "--comparison" in command
    assert str(comparison) in command
    assert "--outdir" in command
