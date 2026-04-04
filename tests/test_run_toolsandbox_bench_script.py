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
    per_category_json_path = outdir / "per_category_summary.json"
    normalized_path = outdir / "prepared" / "toolsandbox.normalized.json"
    report_path = outdir / "report.md"

    assert scoreboard_path.exists()
    assert per_system_path.exists()
    assert per_category_md_path.exists()
    assert per_category_json_path.exists()
    assert normalized_path.exists()
    assert report_path.exists()

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

    report = report_path.read_text(encoding="utf-8")
    assert "ToolSandbox Benchmark Report" in report
    assert "result_summary_coverage" in report
    assert "state_dependency_score" in report


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
