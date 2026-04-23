from __future__ import annotations

import csv
import importlib.util
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


def test_build_scored_row_includes_mean_user_queries() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_toolsandbox_bench.py"
    spec = importlib.util.spec_from_file_location("run_toolsandbox_bench_module_mean_user_queries", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    row = module._build_scored_row(
        run_index=1,
        raw_row={
            "task_id": "toolsandbox_query_metric_001",
            "system": "a3_full_interaction",
            "success": "True",
            "tool_calls": "1",
            "user_turns": "2",
            "trace_path": "trace.json",
        },
        score_payload={
            "success": True,
            "metrics": {
                "strict_scored_success": 1.0,
                "execution_verified_success": 1.0,
                "mean_user_queries": 2.0,
                "reply_usable_rate": 0.5,
                "target_aligned_patch_rate": 0.5,
                "effective_patch_rate": 0.25,
                "post_query_progress_rate": 0.75,
                "useful_interaction_round_rate": 0.25,
            },
            "diagnostics": {"user_queries": 2, "categories": ["multiple_user_turn"]},
        },
    )

    assert row["mean_user_queries"] == 2.0
    assert row["reply_usable_rate"] == 0.5
    assert row["target_aligned_patch_rate"] == 0.5
    assert row["effective_patch_rate"] == 0.25
    assert row["post_query_progress_rate"] == 0.75
    assert row["useful_interaction_round_rate"] == 0.25


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
    focused_slice_md_path = outdir / "focused_slice_summary.md"
    focused_slice_json_path = outdir / "focused_slice_summary.json"
    reuse_focused_md_path = outdir / "reuse_focused_summary.md"
    reuse_focused_json_path = outdir / "reuse_focused_summary.json"
    robustness_json_path = outdir / "statistical_robustness_summary.json"
    normalized_path = outdir / "prepared" / "toolsandbox.normalized.json"
    report_path = outdir / "report.md"
    manifest_path = outdir / "experiment_manifest.json"
    latest_raw_report_path = outdir / "latest_run_raw_report.md"

    assert scoreboard_path.exists()
    assert raw_comparison_path.exists()
    assert scored_comparison_path.exists()
    assert per_system_path.exists()
    assert per_category_md_path.exists()
    assert per_category_json_path.exists()
    assert focused_slice_md_path.exists()
    assert focused_slice_json_path.exists()
    assert reuse_focused_md_path.exists()
    assert reuse_focused_json_path.exists()
    assert robustness_json_path.exists()
    assert normalized_path.exists()
    assert report_path.exists()
    assert manifest_path.exists()
    assert latest_raw_report_path.exists()
    assert not (outdir / "comparison.csv").exists()
    assert not (outdir / "runs" / "run_01" / "report.md").exists()
    assert (outdir / "runs" / "run_01" / "raw_report.md").exists()

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
    assert "execution_verified_success" in per_system["a0_baseline"]
    assert "strict_scored_success" in per_system["a0_baseline"]
    assert "repair_scored_success" in per_system["a0_baseline"]
    assert "interaction_contract_satisfied" in per_system["a0_baseline"]
    assert "reply_usable_rate" in per_system["a0_baseline"]
    assert "target_aligned_patch_rate" in per_system["a0_baseline"]
    assert "effective_patch_rate" in per_system["a0_baseline"]
    assert "post_query_progress_rate" in per_system["a0_baseline"]
    assert "useful_interaction_round_rate" in per_system["a0_baseline"]
    assert "repair_interaction_satisfied" in per_system["a0_baseline"]
    assert "proxy_summary_success" in per_system["a0_baseline"]
    assert "raw_trace_success_rate" in per_system["a0_baseline"]
    assert "raw_execution_success_rate" in per_system["a0_baseline"]
    assert "milestone_signal_coverage" in per_system["a0_baseline"]
    assert "dominant_result_summary_source" in per_system["a0_baseline"]
    assert "benchmark_caution_flags" in scoreboard
    assert "single_validated_sample" in scoreboard["benchmark_caution_flags"]
    assert "no_reference_result_summaries" in scoreboard["benchmark_caution_flags"]
    assert "proxy_only_result_summaries" in scoreboard["benchmark_caution_flags"]
    experiment_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert experiment_manifest["comparison_path"].endswith("comparison.scored.csv")
    assert experiment_manifest["comparison_raw_path"].endswith("comparison.raw.csv")
    assert experiment_manifest["comparison_scored_path"].endswith("comparison.scored.csv")
    assert experiment_manifest["experiment_metadata"]["runner_script"].endswith("scripts/run_toolsandbox_bench.py")

    per_category_md = per_category_md_path.read_text(encoding="utf-8")
    assert "ToolSandbox Category Summary" in per_category_md
    assert "state_dependency" in per_category_md
    assert "result_summary_coverage" in per_category_md
    assert "strict_scored_success" in per_category_md
    assert "repair_scored_success" in per_category_md
    assert "interaction_contract_satisfied" in per_category_md
    assert "proxy_summary_success" in per_category_md
    assert "raw_trace_success_rate" in per_category_md
    assert "raw_execution_success_rate" in per_category_md
    assert "milestone_signal_coverage" in per_category_md
    assert "| a0_baseline | state_dependency | 1 | 1.000" in per_category_md
    per_category_json = json.loads(per_category_json_path.read_text(encoding="utf-8"))
    assert "a0_baseline" in per_category_json
    assert "per_category" not in per_category_json["a0_baseline"]
    assert "state_dependency" in per_category_json["a0_baseline"]
    assert float(per_category_json["a0_baseline"]["state_dependency"]["success_rate"]) == 1.0

    report = report_path.read_text(encoding="utf-8")
    assert "ToolSandbox Benchmark Report" in report
    assert "raw_execution_report" in report
    assert "strict_scored_success" in report
    assert "repair_scored_success" in report
    assert "interaction_contract_satisfied" in report
    assert "mean_user_queries" in report
    assert "reply_usable_rate" in report
    assert "target_aligned_patch_rate" in report
    assert "effective_patch_rate" in report
    assert "post_query_progress_rate" in report
    assert "useful_interaction_round_rate" in report
    assert "proxy_summary_success" in report
    assert "raw_trace_success_rate" in report
    assert "raw_execution_success_rate" in report
    assert "milestone_signal_coverage" in report
    assert "dominant_result_summary_source" in report
    assert "Result Summary Sources" in report
    assert "Readiness" in report
    assert "primary_result_ready:" in report
    assert "resolved_caution_flags" in report
    assert "unresolved_caution_flags" in report
    assert "single_validated_sample" in report
    assert "toolclaw_proxy" in report
    assert "result_summary_coverage" in report
    assert "reference_summary_coverage" in report
    assert "state_dependency_score" in report
    assert "focused_slice_summary.md" in report
    assert "reuse_focused_summary.md" in report
    assert "local_debug_only" in report
    assert "raw_vs_benchmark_gap_summary.md" in report
    assert "statistical_robustness_summary.json" in report
    assert "Reuse Focused" in report
    assert "Statistical Robustness" in report
    assert "bootstrap_95%_ci" in report
    assert "Focused Slice: approval" in report
    assert "reuse_scope: `within_invocation`" in report
    assert "asset_registry_root: `none`" in report
    assert "`repair_scored_success` is stricter" in report
    assert "avg_tool_calls" in report
    assert "reused_artifact_rate" in report
    assert "first_failure_recovered_rate" in report

    focused_slice_md = focused_slice_md_path.read_text(encoding="utf-8")
    assert "ToolSandbox Focused Slice Summary" in focused_slice_md
    focused_slice_json = json.loads(focused_slice_json_path.read_text(encoding="utf-8"))
    assert focused_slice_json["focus_categories"] == [
        "planner_sensitive",
        "insufficient_information",
        "multiple_user_turn",
        "single_tool",
    ]
    reuse_focused_md = reuse_focused_md_path.read_text(encoding="utf-8")
    assert "ToolSandbox Reuse Focused Summary" in reuse_focused_md
    assert "avg_repair_actions" in reuse_focused_md
    assert "mean_second_run_improvement" in reuse_focused_md
    reuse_focused_json = json.loads(reuse_focused_json_path.read_text(encoding="utf-8"))
    assert reuse_focused_json["reuse_scope"] == "within_invocation"
    assert reuse_focused_json["asset_registry_root"] is None
    assert "per_system" in reuse_focused_json
    assert "deltas" in reuse_focused_json
    robustness_json = json.loads(robustness_json_path.read_text(encoding="utf-8"))
    assert "paired_overall" in robustness_json
    assert "paired_focused_slices" in robustness_json

    trace_payload = json.loads(
        (outdir / "runs" / "run_01" / "traces" / "001_toolsandbox_cli_001_a0_baseline.json").read_text(encoding="utf-8")
    )
    assert trace_payload["metadata"]["toolsandbox_result"]["source"] == "toolclaw_proxy"
    assert trace_payload["metadata"]["toolsandbox_result_source"] == "toolclaw_proxy"


def test_toolsandbox_formal_dataset_includes_planner_sensitive_slices(tmp_path: Path) -> None:
    source_path = Path(__file__).resolve().parents[1] / "data" / "toolsandbox.formal.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    sample_ids = {
        str(item.get("name") or item.get("task_id") or item.get("id") or item.get("sample_id") or "")
        for item in payload
    }

    assert {
        "toolsandbox_planner_sensitive_001",
        "toolsandbox_planner_sensitive_002",
        "toolsandbox_planner_sensitive_003",
        "toolsandbox_planner_sensitive_004",
    }.issubset(sample_ids)

    outdir = tmp_path / "toolsandbox_formal_out"
    bench_completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(outdir),
            "--num-runs",
            "1",
            "--limit",
            "8",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert bench_completed.returncode == 0

    check_completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_benchmark_consistency.py",
            "--outdir",
            str(outdir),
            "--expected-systems",
            "a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
            "--expected-source",
            str(source_path),
            "--expected-config",
            "configs/benchmark_toolsandbox.yaml",
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


def test_run_toolsandbox_bench_default_source_prefers_multi_sample_formal_dataset() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_toolsandbox_bench.py"
    spec = importlib.util.spec_from_file_location("run_toolsandbox_bench_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.DEFAULT_SOURCE.name == "toolsandbox.formal.json"


def test_run_toolsandbox_bench_script_rejects_empty_shell_source(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "send_message_with_contact_content_cellular_off_multiple_user_turn",
            "query": "send_message_with_contact_content_cellular_off_multiple_user_turn",
            "messages": [],
            "tool_allow_list": [],
            "candidate_tools": [],
            "categories": ["State Dependency", "Multiple User Turn"],
            "milestones": [],
            "result_summary": {
                "traceback": "Traceback ... APIConnectionError ...",
            },
        }
    ]
    source_path = tmp_path / "toolsandbox_invalid.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(tmp_path / "toolsandbox_invalid_out"),
            "--smoke",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "No valid ToolSandbox samples remain after source validation" in completed.stderr


def test_run_toolsandbox_bench_script_rejects_smoke_profile_without_reuse_pair(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "smoke_recovery_001",
            "query": "Retrieve the billing summary and save the report with backup if needed.",
            "execution_scenario": "environment_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the billing summary and save the report with backup if needed."}],
            "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary writer"},
                {"tool_id": "backup_write_tool", "description": "Backup writer"},
            ],
            "backup_tool_map": {"write_tool": "backup_write_tool"},
            "categories": ["Insufficient Information", "Multiple User Turn", "Multiple Tool Call"],
            "milestones": ["retrieve", "switch tool", "write"],
        },
        {
            "name": "smoke_state_001",
            "query": "Retrieve the incident summary and recover missing state before writing.",
            "execution_scenario": "state_failure",
            "state_failure_mode": "resume_state_loss",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the incident summary and recover missing state before writing."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Write report"},
            ],
            "categories": ["State Dependency", "Multiple Tool Call"],
            "milestones": ["retrieve", "repair state", "write"],
        },
        {
            "name": "smoke_interaction_001",
            "query": "Retrieve the payout summary and ask for approval before writing.",
            "execution_scenario": "approval_required",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the payout summary and ask for approval before writing."}],
            "tool_allow_list": ["search_tool", "write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Standard writer"},
                {"tool_id": "ordering_write_tool", "description": "Legacy writer that violates dependency order"},
            ],
            "constraints": {"requires_user_approval": True, "risk_level": "high"},
            "categories": ["Multiple User Turn", "State Dependency"],
            "milestones": ["retrieve", "ask approval", "write"],
        },
        {
            "name": "toolsandbox_planner_sensitive_smoke_001",
            "query": "Retrieve the onboarding summary, then use the standard writer and never the legacy writer.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the onboarding summary, then use the standard writer and never the legacy writer."}],
            "tool_allow_list": ["search_tool", "write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Standard writer used after retrieval"},
                {"tool_id": "ordering_write_tool", "description": "Legacy writer that violates dependency order"},
            ],
            "categories": ["Multiple Tool Call", "State Dependency"],
            "milestones": ["retrieve", "choose writer", "write"],
        },
        {
            "name": "smoke_control_001",
            "query": "Retrieve the target document summary.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the target document summary."}],
            "tool_allow_list": ["search_tool"],
            "candidate_tools": [{"tool_id": "search_tool", "description": "Search information"}],
            "categories": ["Single Tool", "Single User Turn"],
            "milestones": ["retrieve"],
        },
        {
            "name": "smoke_binding_001",
            "query": "Retrieve the release summary and save the report even if one write argument is missing.",
            "execution_scenario": "binding_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the release summary and save the report even if one write argument is missing."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Write report"},
            ],
            "categories": ["Insufficient Information", "Single User Turn", "Multiple Tool Call"],
            "milestones": ["retrieve", "repair binding", "write"],
        },
        {
            "name": "toolsandbox_planner_sensitive_smoke_002",
            "query": "Find the audit summary, then write it with the primary writer and avoid both backup and legacy writers unless required.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Find the audit summary, then write it with the primary writer and avoid both backup and legacy writers unless required."}],
            "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary writer for normal operation"},
                {"tool_id": "backup_write_tool", "description": "Backup writer for outages only"},
                {"tool_id": "ordering_write_tool", "description": "Legacy writer that violates dependency order"},
            ],
            "categories": ["Multiple Tool Call", "State Dependency"],
            "milestones": ["retrieve", "choose writer", "write"],
        },
    ]
    source_path = tmp_path / "toolsandbox_smoke_invalid.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(tmp_path / "toolsandbox_smoke_invalid_out"),
            "--smoke",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "reuse-pair" in completed.stderr


def test_run_toolsandbox_bench_script_rejects_smoke_profile_without_transfer_reuse_pair(tmp_path: Path) -> None:
    taskset = [
        {
            "name": "smoke_recovery_001",
            "query": "Retrieve the billing summary and save the report with backup if needed.",
            "execution_scenario": "environment_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the billing summary and save the report with backup if needed."}],
            "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary standard writer"},
                {"tool_id": "backup_write_tool", "description": "Fallback backup writer reserved for outage recovery only"},
            ],
            "backup_tool_map": {"write_tool": "backup_write_tool"},
            "categories": ["Insufficient Information", "Multiple User Turn", "Multiple Tool Call"],
            "milestones": ["retrieve", "switch tool", "write"],
        },
        {
            "name": "smoke_state_001",
            "query": "Retrieve the incident summary and recover missing state before writing.",
            "execution_scenario": "state_failure",
            "state_failure_mode": "resume_state_loss",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the incident summary and recover missing state before writing."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Standard writer used after retrieval once the retrieved summary is available"},
            ],
            "categories": ["State Dependency", "Multiple Tool Call"],
            "milestones": ["retrieve", "repair state", "write"],
        },
        {
            "name": "smoke_interaction_001",
            "query": "Retrieve the payout summary and ask for approval before writing.",
            "execution_scenario": "approval_required",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the payout summary and ask for approval before writing."}],
            "tool_allow_list": ["search_tool", "write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary standard writer"},
                {"tool_id": "ordering_write_tool", "description": "Legacy ordering writer that violates dependency order and should never be selected"},
            ],
            "constraints": {"requires_user_approval": True, "risk_level": "high"},
            "categories": ["Multiple User Turn", "State Dependency"],
            "milestones": ["retrieve", "ask approval", "write"],
        },
        {
            "name": "smoke_binding_001",
            "query": "Retrieve the release summary and save the report even if one write argument is missing.",
            "execution_scenario": "binding_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the release summary and save the report even if one write argument is missing."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Standard writer used after retrieval to save the final report"},
            ],
            "categories": ["Insufficient Information", "Single User Turn", "Multiple Tool Call"],
            "milestones": ["retrieve", "repair binding", "write"],
        },
        {
            "name": "toolsandbox_planner_sensitive_smoke_001",
            "query": "Retrieve the onboarding summary, then use the standard writer and never the legacy writer.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the onboarding summary, then use the standard writer and never the legacy writer."}],
            "tool_allow_list": ["search_tool", "write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary standard writer used after retrieval"},
                {"tool_id": "ordering_write_tool", "description": "Legacy ordering writer that violates dependency order and should never be selected"},
            ],
            "categories": ["Multiple Tool Call", "State Dependency"],
            "milestones": ["retrieve", "choose writer", "write"],
        },
        {
            "name": "toolsandbox_planner_sensitive_smoke_002",
            "query": "Find the audit summary, then write it with the primary writer and avoid both backup and legacy writers unless required.",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Find the audit summary, then write it with the primary writer and avoid both backup and legacy writers unless required."}],
            "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool", "ordering_write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Search information"},
                {"tool_id": "write_tool", "description": "Primary standard writer for normal write operations after retrieval"},
                {"tool_id": "backup_write_tool", "description": "Fallback backup writer reserved for outage recovery only"},
                {"tool_id": "ordering_write_tool", "description": "Legacy ordering writer that violates dependency order and should never be selected"},
            ],
            "categories": ["Multiple Tool Call", "State Dependency"],
            "milestones": ["retrieve", "choose writer", "write"],
        },
        {
            "name": "smoke_reuse_exact_001__pass1",
            "query": "Retrieve the customer handoff summary and save the support handoff report.",
            "execution_scenario": "binding_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the customer handoff summary and save the support handoff report."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Retrieve handoff details"},
                {"tool_id": "write_tool", "description": "Primary standard writer"},
            ],
            "reuse_family_id": "smoke_reuse_exact_001",
            "reuse_pass_index": 1,
            "categories": ["Multiple Tool Call", "Insufficient Information"],
            "milestones": ["retrieve", "repair binding", "write"],
        },
        {
            "name": "smoke_reuse_exact_001__pass2",
            "query": "Retrieve the customer handoff summary and save the support handoff report.",
            "execution_scenario": "binding_failure",
            "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the customer handoff summary and save the support handoff report."}],
            "tool_allow_list": ["search_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "search_tool", "description": "Retrieve handoff details"},
                {"tool_id": "write_tool", "description": "Primary standard writer"},
            ],
            "reuse_family_id": "smoke_reuse_exact_001",
            "reuse_pass_index": 2,
            "categories": ["Multiple Tool Call", "Insufficient Information"],
            "milestones": ["retrieve", "repair binding", "write"],
        },
    ]
    source_path = tmp_path / "toolsandbox_smoke_missing_transfer.json"
    source_path.write_text(json.dumps(taskset), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_toolsandbox_bench.py",
            "--source",
            str(source_path),
            "--outdir",
            str(tmp_path / "toolsandbox_smoke_missing_transfer_out"),
            "--smoke",
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "transfer-style reuse" in completed.stderr


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
        for category, category_stats in system_stats.items():
            expected = float(category_stats["result_summary_coverage"])
            key = (system, category)
            assert report_category_rows[key] == expected
            assert category_md_rows[key] == expected


def test_build_scored_row_preserves_reuse_provenance() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_toolsandbox_bench.py"
    spec = importlib.util.spec_from_file_location("run_toolsandbox_bench_module_scored_row", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    scored = module._build_scored_row(
        run_index=3,
        raw_row={
            "task_id": "contact_edit__pair01__pass2",
            "system": "a4_reuse",
            "scenario": "canonicalization",
            "task_family": "t4_repeated_reusable",
            "failure_type": "canonicalization",
            "primary_failtax": "selection",
            "failtaxes": "[\"selection\"]",
            "failure_step": "step_02",
            "expected_recovery_path": "rebind_or_switch_then_retry",
            "gold_tool": "write_tool",
            "chosen_tool": "write_tool",
            "state_slots": "[\"query\"]",
            "dependency_edges": "[]",
            "success": "True",
            "stop_reason": "success_criteria_satisfied",
            "trace_path": "outputs/fake_trace.json",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "repair_triggered": "0",
            "total_steps": "1",
            "token_cost": "0.0",
            "wall_clock_ms": "0",
            "observed_error_type": "canonicalization",
            "first_failure_recovered": "False",
            "repair_extra_tool_calls": "0",
            "repair_extra_user_turns": "0",
            "repair_user_clarification": "False",
            "clarification_precision": "0.0",
            "clarification_recall": "0.0",
            "unnecessary_question_rate": "0.0",
            "patch_success_rate": "0.0",
            "post_answer_retry_count": "0",
            "reuse_pass_index": "2",
            "reused_artifact": "True",
            "reuse_mode": "transfer_reuse",
            "reuse_tier": "same_family_transfer_reuse",
            "reuse_selected_asset_id": "ws_contact_001",
            "reuse_selected_match_signature": "phase1::family=contact_edit",
            "reuse_source_task_id": "contact_edit__pair00__pass1",
            "reuse_target_family": "contact_edit__pair01",
            "reuse_source_family": "contact_edit__pair00",
            "reuse_target_semantic_family": "contact_edit",
            "reuse_source_semantic_family": "contact_edit",
            "second_run_improvement": "0.1",
            "budget_violation": "False",
            "budget_violation_reason": "",
            "recovery_budget_used": "0.0",
        },
        score_payload={
            "success": True,
            "metrics": {
                "execution_verified_success": 1.0,
                "strict_scored_success": 1.0,
                "repair_scored_success": 0.0,
                "proxy_summary_success": 0.0,
                "milestone_similarity": 1.0,
                "milestone_coverage": 1.0,
                "interaction_efficiency": 1.0,
                "tool_efficiency": 1.0,
                "turn_efficiency": 1.0,
                "hallucination_avoidance": 1.0,
                "state_dependency_score": 1.0,
                "write_target_verified": 1.0,
            },
            "diagnostics": {
                "categories": ["canonicalization"],
                "primary_category": "canonicalization",
                "raw_execution_success": True,
                "raw_trace_success": True,
                "tool_calls": 1,
                "user_queries": 0,
                "turn_count": 1,
                "expected_turn_count": 1,
                "expected_tool_calls": 1,
                "matched_milestones": 1,
                "total_milestones": 1,
                "used_result_summary": True,
                "reference_result_summary_available": True,
                "milestone_signal_available": True,
            },
        },
    )

    assert scored["reused_artifact"] is True
    assert scored["reuse_mode"] == "transfer_reuse"
    assert scored["reuse_tier"] == "same_family_transfer_reuse"
    assert scored["reuse_selected_asset_id"] == "ws_contact_001"
    assert scored["reuse_source_task_id"] == "contact_edit__pair00__pass1"
    assert scored["reuse_target_family"] == "contact_edit__pair01"
    assert scored["reuse_source_family"] == "contact_edit__pair00"
    assert scored["reuse_target_semantic_family"] == "contact_edit"
    assert scored["reuse_source_semantic_family"] == "contact_edit"


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
