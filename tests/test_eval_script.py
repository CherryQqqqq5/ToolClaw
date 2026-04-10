import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_eval_script_generates_csv_and_report(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_success_001",
            "scenario": "success",
            "query": "target document summary",
            "target_path": "outputs/reports/task_success_001.txt",
        },
        {
            "task_id": "task_env_001",
            "scenario": "environment_failure",
            "query": "target document summary",
            "target_path": "outputs/reports/task_env_001.txt",
            "backup_tool_map": {"write_tool": "backup_write_tool"},
        },
    ]
    taskset_path = tmp_path / "taskset.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
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

    csv_path = outdir / "comparison.csv"
    report_path = outdir / "report.md"
    assert csv_path.exists()
    assert report_path.exists()

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 10
    systems = {row["system"] for row in rows}
    assert systems == {"a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse"}
    assert "task_family" in rows[0]
    assert "failure_type" in rows[0]
    assert "reused_artifact" in rows[0]
    assert "second_run_improvement" in rows[0]
    assert "token_cost" in rows[0]
    assert "wall_clock_ms" in rows[0]
    assert "observed_error_type" in rows[0]
    assert "repair_extra_tool_calls" in rows[0]
    assert "repair_extra_user_turns" in rows[0]
    assert "repair_user_clarification" in rows[0]

    report = report_path.read_text(encoding="utf-8")
    assert "ToolClaw Evaluation Report" in report
    assert "Delta (A4 Reuse vs A0 Baseline)" in report
    assert "Per-Task Results" in report
    assert "Scenario Breakdown" in report
    assert "Failure-Type Breakdown" in report
    assert "Task-Family Breakdown" in report
    assert "repair_success_rate" in report
    assert "avg_user_turns" in report
    assert "fail_stop_rate" in report
    assert "Observed Error-Type Breakdown" in report
    assert "Recovery And Cost" in report
    assert "avg_token_cost" in report
    assert "safe_abort_rate" in report
    assert "policy_compliance_success_rate" in report


def test_run_eval_script_with_planner_mode(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_success_planner_001",
            "scenario": "success",
            "query": "retrieve and write report",
        }
    ]
    taskset_path = tmp_path / "taskset_planner.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_planner"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--mode",
        "planner",
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
    assert (outdir / "comparison.csv").exists()


def test_build_workflow_from_task_plans_with_toolsandbox_candidate_tools() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_single_tool_001",
            "scenario": "single_tool",
            "query": "Turn wifi off and confirm it.",
            "tool_allow_list": ["set_wifi_status"],
            "candidate_tools": [{"tool_id": "set_wifi_status", "description": "Toggle WiFi"}],
            "messages": [{"sender": "user", "recipient": "agent", "content": "Turn wifi off and confirm it."}],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool", "state_dependency"],
            },
        },
        mode="planner",
    )

    assert [tool.tool_id for tool in workflow.context.candidate_tools] == ["set_wifi_status"]
    assert workflow.execution_plan[0].tool_id == "set_wifi_status"


def test_build_workflow_from_task_rejects_empty_toolsandbox_tool_space() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_empty", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    try:
        module.build_workflow_from_task(
            {
                "task_id": "toolsandbox_empty_001",
                "scenario": "multiple_user_turn",
                "query": "send_message_with_contact_content_cellular_off_multiple_user_turn",
                "tool_allow_list": [],
                "candidate_tools": [],
                "messages": [],
                "metadata": {
                    "benchmark": "toolsandbox",
                    "toolsandbox_categories": ["state_dependency", "multiple_user_turn"],
                },
            },
            mode="planner",
        )
    except ValueError as exc:
        assert "empty candidate_tools/tool_allow_list" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty ToolSandbox tool space")


def test_run_eval_script_preserves_failure_injection_for_toolclaw_lite(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_binding_planner_001",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
        },
        {
            "task_id": "task_env_planner_001",
            "scenario": "environment_failure",
            "query": "retrieve and write report",
            "backup_tool_map": {"write_tool": "backup_write_tool"},
        },
    ]
    taskset_path = tmp_path / "taskset_failures.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_failures"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--mode",
        "planner",
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

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    toolclaw_rows = {(row["task_id"], row["system"]): row for row in rows}
    assert int(toolclaw_rows[("task_binding_planner_001", "a1_recovery")]["repair_actions"]) >= 1
    assert int(toolclaw_rows[("task_env_planner_001", "a2_planner")]["repair_actions"]) >= 1


def test_run_eval_script_supports_legacy_aliases(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_alias_001",
            "scenario": "success",
            "query": "retrieve and write report",
        }
    ]
    taskset_path = tmp_path / "taskset_alias.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_alias"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(taskset_path),
        "--outdir",
        str(outdir),
        "--systems",
        "baseline,planning,interactive",
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

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    systems = {row["system"] for row in rows}
    assert systems == {"a0_baseline", "a2_planner", "a3_interaction"}


def test_run_eval_script_reports_repeated_family_contrast(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "reuse_case_001__pass1",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
            "metadata": {"reuse_family_id": "reuse_case_001", "reuse_pass_index": 1},
        },
        {
            "task_id": "reuse_case_001__pass2",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
            "metadata": {"reuse_family_id": "reuse_case_001", "reuse_pass_index": 2},
        },
    ]
    taskset_path = tmp_path / "taskset_reuse.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_reuse"
    completed = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a3_interaction,a4_reuse"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    a4_pass2 = next(row for row in rows if row["system"] == "a4_reuse" and row["task_id"].endswith("__pass2"))
    assert a4_pass2["reused_artifact"] == "True"
    assert float(a4_pass2["second_run_improvement"]) != 0.0
    report = (outdir / "report.md").read_text(encoding="utf-8")
    assert "Verdict: **reuse_efficiency_gain**." in report


def test_run_eval_script_supports_state_failure_slice(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "state_slice_001",
            "scenario": "state_failure",
            "query": "retrieve and write report",
            "state_failure_mode": "state_slot_mismatch",
            "simulated_policy": {
                "mode": "cooperative",
                "missing_arg_values": {"retrieved_summary": "summary for: retrieve and write report"},
            },
        }
    ]
    taskset_path = tmp_path / "taskset_state.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_state"
    completed = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a3_interaction"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    assert rows[0]["primary_failtax"] == "state"
    assert rows[0]["failure_type"] == "state_failure"


def test_run_eval_script_reuses_artifact_for_structurally_similar_query_variant(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "reuse_transfer_001__pass1",
            "scenario": "binding_failure",
            "query": "Retrieve the customer handoff summary and save the support report.",
            "metadata": {"reuse_family_id": "reuse_transfer_001", "reuse_pass_index": 1},
        },
        {
            "task_id": "reuse_transfer_001__pass2",
            "scenario": "binding_failure",
            "query": "Fetch the customer transition notes and write the support brief.",
            "metadata": {"reuse_family_id": "reuse_transfer_001", "reuse_pass_index": 2},
        },
    ]
    taskset_path = tmp_path / "taskset_reuse_transfer.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_reuse_transfer"
    completed = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a4_reuse"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    pass2 = next(row for row in rows if row["task_id"].endswith("__pass2"))
    assert pass2["reused_artifact"] == "True"


def test_run_eval_script_recovers_stale_state_without_budget_double_count(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "state_stale_001",
            "scenario": "state_failure",
            "query": "retrieve and write report",
            "state_failure_mode": "state_stale_slot",
            "constraints": {
                "max_tool_calls": 3,
                "max_user_turns": 1,
                "max_repair_attempts": 1,
                "max_recovery_budget": 1.0,
            },
            "simulated_policy": {
                "mode": "cooperative",
                "missing_arg_values": {"retrieved_info": "refreshed summary for: retrieve and write report"},
            },
        }
    ]
    taskset_path = tmp_path / "taskset_state_stale.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_state_stale"
    completed = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a3_interaction"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    row = rows[0]
    assert row["success"] == "True"
    assert row["observed_error_type"] == "state_failure"
    assert row["stop_reason"] != "max_recovery_budget_exceeded"


def test_run_eval_script_wrong_write_target_fails_baseline(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "state_wrong_target_001",
            "scenario": "state_failure",
            "query": "retrieve and write report",
            "target_path": "outputs/reports/state_wrong_target_001.txt",
            "wrong_target_path": "outputs/reports/state_wrong_target_001.shadow.txt",
            "state_failure_mode": "wrong_write_target",
            "reuse_override_inputs": {"cap_write": ["target_path"]},
            "simulated_policy": {
                "mode": "cooperative",
                "missing_arg_values": {"target_path": "outputs/reports/state_wrong_target_001.txt"},
            },
        }
    ]
    taskset_path = tmp_path / "taskset_wrong_target.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_wrong_target"
    completed = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--taskset", str(taskset_path), "--outdir", str(outdir), "--systems", "a0_baseline"],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    row = rows[0]
    assert row["success"] == "False"
    assert row["observed_error_type"] == "state_failure"


def test_run_eval_script_supports_matched_ablation_systems_and_disable_repair(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "task_binding_001",
            "scenario": "binding_failure",
            "query": "retrieve and write report",
        }
    ]
    taskset_path = tmp_path / "taskset_matched.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_matched"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_eval.py",
            "--taskset",
            str(taskset_path),
            "--outdir",
            str(outdir),
            "--systems",
            "tc_no_repair,tc_no_reuse,tc_planner_only",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    rows = list(csv.DictReader((outdir / "comparison.csv").read_text(encoding="utf-8").splitlines()))
    systems = {row["system"] for row in rows}
    assert systems == {"tc_no_repair", "tc_no_reuse", "tc_planner_only"}
    no_repair = next(row for row in rows if row["system"] == "tc_no_repair")
    assert no_repair["stop_reason"] == "repair_disabled"
    assert no_repair["success"] == "False"

    report = (outdir / "report.md").read_text(encoding="utf-8")
    assert "Recovery And Cost" in report
    assert "Observed Error-Type Breakdown" in report


def test_run_eval_script_missing_taskset_shows_clear_error(tmp_path: Path) -> None:
    outdir = tmp_path / "eval_out_missing"
    missing_path = tmp_path / "does_not_exist.json"
    cmd = [
        sys.executable,
        "scripts/run_eval.py",
        "--taskset",
        str(missing_path),
        "--outdir",
        str(outdir),
    ]
    completed = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "taskset file not found" in completed.stderr
    assert "data/eval_tasks.sample.json" in completed.stderr


def test_shell_wrappers_parse_as_bash() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for script_name in ("scripts/run_eval.sh", "scripts/run_ablation.sh"):
        completed = subprocess.run(
            ["bash", "-n", script_name],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
