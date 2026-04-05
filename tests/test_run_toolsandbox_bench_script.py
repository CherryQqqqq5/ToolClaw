import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def _markdown_table_rows(markdown: str, *, header_prefix: str) -> list[dict[str, str]]:
    lines = [line.rstrip() for line in markdown.splitlines()]
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|") or header_prefix not in stripped:
            continue
        if index + 1 >= len(lines):
            return []
        header = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for body_line in lines[index + 2 :]:
            body = body_line.strip()
            if not body.startswith("|"):
                break
            cells = [cell.strip() for cell in body.strip("|").split("|")]
            if len(cells) != len(header):
                continue
            rows.append(dict(zip(header, cells)))
        return rows
    return []


def _recompute_mean_success_rate(rows: list[dict[str, str]], system: str) -> float:
    per_task: dict[str, list[float]] = {}
    for row in rows:
        if row["system"] != system:
            continue
        per_task.setdefault(row["task_id"], []).append(1.0 if row["success"] == "True" else 0.0)
    assert per_task
    return sum(sum(values) / len(values) for values in per_task.values()) / len(per_task)


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
    raw_comparison_path = outdir / "comparison.raw.csv"
    scored_comparison_path = outdir / "comparison.scored.csv"
    per_system_path = outdir / "per_system_summary.json"
    per_category_md_path = outdir / "per_category_summary.md"
    per_category_json_path = outdir / "per_category_summary.json"
    normalized_path = outdir / "prepared" / "toolsandbox.normalized.json"
    report_path = outdir / "report.md"

    assert scoreboard_path.exists()
    assert raw_comparison_path.exists()
    assert scored_comparison_path.exists()
    assert per_system_path.exists()
    assert per_category_md_path.exists()
    assert per_category_json_path.exists()
    assert normalized_path.exists()
    assert report_path.exists()
    assert not (outdir / "comparison.csv").exists()

    scoreboard = json.loads(scoreboard_path.read_text(encoding="utf-8"))
    assert scoreboard["benchmark"] == "toolsandbox"
    assert scoreboard["num_samples"] == 1
    assert set(scoreboard["systems"]) == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}

    per_system = json.loads(per_system_path.read_text(encoding="utf-8"))
    assert "a0_baseline" in per_system
    assert "a4_reuse" in per_system
    assert "per_category" in per_system["a0_baseline"]
    assert "state_dependency" in per_system["a0_baseline"]["per_category"]
    assert "used_result_summary" in per_system["a0_baseline"]

    per_category_md = per_category_md_path.read_text(encoding="utf-8")
    assert "ToolSandbox Category Summary" in per_category_md
    assert "state_dependency" in per_category_md
    assert "result_summary_coverage" in per_category_md
    assert "| a0_baseline | state_dependency | 1 | 1.000" in per_category_md

    report = report_path.read_text(encoding="utf-8")
    assert "ToolSandbox Benchmark Report" in report
    assert "result_summary_coverage" in report
    assert "reference_summary_coverage" in report
    assert "state_dependency_score" in report

    trace_payload = json.loads(
        (outdir / "runs" / "run_01" / "traces" / "001_toolsandbox_cli_001_a0_baseline.json").read_text(encoding="utf-8")
    )
    assert trace_payload["metadata"]["toolsandbox_result"]["source"] == "toolclaw_proxy"
    assert trace_payload["metadata"]["toolsandbox_result_source"] == "toolclaw_proxy"


def test_run_toolsandbox_bench_script_writes_combined_comparison_across_runs(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "toolsandbox_cli_runs_001",
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
    source_path = tmp_path / "toolsandbox_runs.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "toolsandbox_runs_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(outdir),
            "--num-runs",
            "2",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    raw_rows = list(csv.DictReader((outdir / "comparison.raw.csv").read_text(encoding="utf-8").splitlines()))
    scored_rows = list(csv.DictReader((outdir / "comparison.scored.csv").read_text(encoding="utf-8").splitlines()))
    assert len(raw_rows) == 10
    assert len(scored_rows) == 10
    assert {row["run_index"] for row in raw_rows} == {"1", "2"}
    assert {row["run_index"] for row in scored_rows} == {"1", "2"}
    assert (outdir / "latest_run_comparison.raw.csv").exists()
    assert (outdir / "latest_run_comparison.scored.csv").exists()


def test_run_toolsandbox_bench_summary_recomputes_from_scored_rows(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "toolsandbox_success_001",
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
        },
        {
            "name": "toolsandbox_fail_001",
            "query": "retrieve and write report",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the data and save the report."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Write report"},
            ],
            "categories": ["Insufficient Information", "Single User Turn"],
            "milestones": ["retrieve data", "write artifact"],
            "ideal_turn_count": 1,
            "ideal_tool_calls": 2,
            "execution_scenario": "environment_failure",
        },
    ]
    source_path = tmp_path / "toolsandbox_regression.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "toolsandbox_regression_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(outdir),
            "--num-runs",
            "2",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    scored_rows = list(csv.DictReader((outdir / "comparison.scored.csv").read_text(encoding="utf-8").splitlines()))
    per_system = json.loads((outdir / "per_system_summary.json").read_text(encoding="utf-8"))
    for system, stats in per_system.items():
        recomputed = _recompute_mean_success_rate(scored_rows, system)
        assert recomputed == float(stats["mean_success_rate"])

    report_rows = _markdown_table_rows((outdir / "report.md").read_text(encoding="utf-8"), header_prefix="| system | category |")
    report_category_rows = {
        (row["system"], row["category"]): float(row["result_summary_coverage"])
        for row in report_rows
    }
    category_md_rows = {
        (row["system"], row["per_category"]): float(row["result_summary_coverage"])
        for row in _markdown_table_rows((outdir / "per_category_summary.md").read_text(encoding="utf-8"), header_prefix="| system | per_category |")
    }
    category_json = json.loads((outdir / "per_category_summary.json").read_text(encoding="utf-8"))
    for system, system_stats in category_json.items():
        for category, category_stats in system_stats["per_category"].items():
            expected = float(category_stats["result_summary_coverage"])
            key = (system, category)
            assert report_category_rows[key] == expected
            assert category_md_rows[key] == expected


def test_run_toolsandbox_bench_script_merges_external_result_summaries(tmp_path: Path) -> None:
    raw_source = tmp_path / "raw_toolsandbox.json"
    raw_source.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "name": "toolsandbox_cli_merged_001",
                        "dialogue": [{"role": "user", "text": "Find the details and write the report."}],
                        "allowed_tools": [{"name": "search_tool"}, {"name": "write_tool"}],
                        "tags": ["State Dependency", "Multiple Tool Call"],
                        "expected_milestones": ["find details", "write report"],
                        "expected_turn_count": 2,
                        "expected_tool_calls": 2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result_source = tmp_path / "results.jsonl"
    result_source.write_text(
        json.dumps(
            {
                "name": "toolsandbox_cli_merged_001",
                "result_summary": {"similarity": 0.91, "milestone_mapping": [0, 1]},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    outdir = tmp_path / "toolsandbox_out_merged"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox.py",
            "--source",
            str(raw_source),
            "--result-source",
            str(result_source),
            "--outdir",
            str(outdir),
            "--require-result-summary",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    prepared_aligned = outdir / "prepared" / "toolsandbox.aligned.jsonl"
    assert prepared_aligned.exists()
    rows = [json.loads(line) for line in prepared_aligned.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["result_summary"]["similarity"] == 0.91

    per_system = json.loads((outdir / "per_system_summary.json").read_text(encoding="utf-8"))
    assert float(per_system["a0_baseline"]["used_result_summary"]) >= 1.0
    assert float(per_system["a0_baseline"]["reference_result_summary_available"]) >= 1.0


def test_run_toolsandbox_bench_script_accepts_official_run_dir(tmp_path: Path) -> None:
    data_root = tmp_path / "official_data"
    run_dir = data_root / "agent_demo_user_demo_2026_04_04_00_00_00"
    scenario_dir = run_dir / "trajectories" / "wifi_off"
    scenario_dir.mkdir(parents=True)

    (run_dir / "result_summary.json").write_text(
        json.dumps(
            {
                "per_scenario_results": [
                    {
                        "name": "wifi_off",
                        "categories": ["state_dependency", "multiple_tool"],
                        "similarity": 0.95,
                        "turn_count": 2,
                        "milestone_mapping": {"0": [1, 1.0]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (scenario_dir / "conversation.json").write_text(
        json.dumps([{"sender": "USER", "recipient": "AGENT", "content": "Turn wifi off."}]),
        encoding="utf-8",
    )
    (scenario_dir / "scenario_export.json").write_text(
        json.dumps(
            {
                "tool_allow_list": ["set_wifi_status"],
                "candidate_tools": [{"tool_id": "set_wifi_status", "description": "Toggle WiFi"}],
                "ideal_tool_calls": 1,
                "milestones": ["disable wifi"],
            }
        ),
        encoding="utf-8",
    )

    outdir = tmp_path / "official_toolsandbox_out"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox.py",
            "--official-run-dir",
            "latest",
            "--official-data-root",
            str(data_root),
            "--outdir",
            str(outdir),
            "--require-result-summary",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    aligned_path = outdir / "prepared" / "toolsandbox.official.aligned.jsonl"
    assert aligned_path.exists()
    rows = [json.loads(line) for line in aligned_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["sample_id"] == "wifi_off"

    per_system = json.loads((outdir / "per_system_summary.json").read_text(encoding="utf-8"))
    assert float(per_system["a0_baseline"]["used_result_summary"]) >= 1.0
    assert float(per_system["a0_baseline"]["reference_result_summary_available"]) >= 1.0
