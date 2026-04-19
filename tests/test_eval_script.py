import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from toolclaw.benchmarks.baseline_runner import run_baseline
from toolclaw.interaction.repair_updater import InteractionRequest
from toolclaw.schemas.workflow import Workflow


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
    assert "reuse_mode" in rows[0]
    assert "reuse_tier" in rows[0]
    assert "reuse_source_family" in rows[0]
    assert "reuse_target_family" in rows[0]
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
    assert workflow.metadata["tool_execution_backend"] == "semantic_mock"


def test_build_workflow_from_task_planner_single_write_respects_target_path() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_single_write_target", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_planner_sensitive_003",
            "scenario": "single_tool",
            "query": "Save the release approval note with the compliant writer.",
            "target_path": "outputs/toolsandbox/reports/toolsandbox_planner_sensitive_003.txt",
            "tool_allow_list": ["ordering_write_tool", "write_tool"],
            "candidate_tools": [
                {"tool_id": "ordering_write_tool", "description": "Legacy ordering writer that should not be used."},
                {"tool_id": "write_tool", "description": "Compliant writer for release note output."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool", "single_user_turn"],
            },
        },
        mode="planner",
    )

    write_step = next(step for step in workflow.execution_plan if step.capability_id == "cap_write")
    assert write_step.inputs["target_path"] == "outputs/toolsandbox/reports/toolsandbox_planner_sensitive_003.txt"


def test_build_workflow_from_task_restores_toolsandbox_goal_from_messages() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_messages", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_message_001",
            "scenario": "multiple_user_turn",
            "query": "Send a message",
            "tool_allow_list": [
                "search_contacts",
                "send_message_with_phone_number",
                "set_cellular_service_status",
                "get_cellular_service_status",
            ],
            "candidate_tools": [
                "search_contacts",
                "send_message_with_phone_number",
                "set_cellular_service_status",
                "get_cellular_service_status",
            ],
            "messages": [
                {
                    "sender": "RoleType.SYSTEM",
                    "recipient": "RoleType.USER",
                    "content": 'USER_INSTRUCTION + "Send a message to Fredrik Thordendal saying: How\\\'s the new album coming along. You only know Fredrik Thordendal is in your contact. You don not have more information."',
                },
                {
                    "sender": "RoleType.USER",
                    "recipient": "RoleType.AGENT",
                    "content": "Send a message",
                },
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["state_dependency", "multiple_tool", "multiple_user_turn"],
            },
            "milestones": [
                "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SETTING, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'cellular': True}))])",
                "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SANDBOX, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'sender': RoleType.EXECUTION_ENVIRONMENT, 'recipient': RoleType.AGENT, 'tool_trace': json.dumps({'tool_name': 'search_contacts', 'arguments': {'name': 'Fredrik Thordendal'}}, ensure_ascii=False)}))], guardrail_database_exclusion_list=[DatabaseNamespace.SETTING])",
                "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.MESSAGING, snapshot_constraint=addition_similarity, target_dataframe=pl.DataFrame({'recipient_phone_number': '+12453344098', 'content': \"How's the new album coming along\"}), reference_milestone_node_index=0)], guardrail_database_exclusion_list=[DatabaseNamespace.SETTING])",
            ],
        },
        mode="planner",
    )

    assert workflow.task.user_goal != "Send a message"
    assert "Fredrik Thordendal" in workflow.task.user_goal
    assert "How's the new album coming along" in workflow.task.user_goal
    assert workflow.execution_plan[0].inputs["name"] == "Fredrik Thordendal"
    assert "query" not in workflow.execution_plan[0].inputs


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


def test_build_planning_request_preserves_toolsandbox_metadata() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_request", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata.update(
        {
            "benchmark": "toolsandbox",
            "messages": [{"sender": "system", "content": "full instruction"}],
            "tool_allow_list": ["search_contacts", "send_message_with_phone_number"],
            "backup_tool_map": {"send_message_with_phone_number": "backup_send_message_with_phone_number"},
            "milestones": ["retrieve contact", "send message"],
            "primary_failtax": "state",
            "failtaxes": ["state", "ordering"],
            "failure_step": "step_02",
            "expected_recovery_path": "patch_state_then_retry",
            "gold_tool": "send_message_with_phone_number",
            "state_slots": ["messages", "cellular_service_status"],
            "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
            "tool_execution_backend": "semantic_mock",
        }
    )

    request = module.build_planning_request(workflow, allow_reuse=False)

    assert request.hints.user_style["benchmark"] == "toolsandbox"
    assert request.hints.user_style["messages"] == [{"sender": "system", "content": "full instruction"}]
    assert request.hints.user_style["primary_failtax"] == "state"
    assert request.hints.user_style["dependency_edges"] == [{"source": "step_01", "target": "step_02", "type": "state"}]
    assert request.hints.user_style["backup_tool_map"] == {
        "send_message_with_phone_number": "backup_send_message_with_phone_number"
    }
    assert request.hints.user_style["tool_execution_backend"] == "semantic_mock"


def test_row_from_trace_reads_reuse_provenance_from_trace_metadata(tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_reuse_provenance", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "events": [],
                "metrics": {"success": True, "tool_calls": 1, "repair_actions": 0, "user_queries": 0, "total_steps": 2},
                "metadata": {
                    "task_annotations": {"primary_failtax": "selection"},
                    "reuse_provenance": {
                        "reuse_mode": "transfer_reuse",
                        "reuse_tier": "same_family_transfer_reuse",
                        "reuse_selected_asset_id": "ws_contact_001",
                        "reuse_source_task_id": "contact_edit__pair00__pass1",
                        "reuse_target_family": "contact_edit__pair01",
                        "reuse_source_family": "contact_edit__pair00",
                        "reuse_target_semantic_family": "contact_edit",
                        "reuse_source_semantic_family": "contact_edit",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    row = module.row_from_trace(
        task={
            "task_id": "contact_edit__pair01__pass2",
            "query": "Edit the contact",
            "metadata": {"reuse_family_id": "contact_edit__pair01"},
        },
        system="a4_reuse",
        scenario="canonicalization",
        trace_path=trace_path,
        reused_artifact=True,
    )

    assert row.reuse_mode == "transfer_reuse"
    assert row.reuse_tier == "same_family_transfer_reuse"
    assert row.reuse_selected_asset_id == "ws_contact_001"
    assert row.reuse_source_family == "contact_edit__pair00"
    assert row.reuse_target_family == "contact_edit__pair01"


def test_execute_system_planner_executor_skips_second_planner(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_execute", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    seed_workflow = Workflow.demo()
    seed_workflow.metadata["primary_failtax"] = "state"

    build_calls: list[str] = []
    executed: dict[str, object] = {}

    def fake_build_workflow_from_task(task, mode="demo"):
        build_calls.append(mode)
        return seed_workflow

    def fake_run_until_blocked(*, workflow, run_id, output_path, backup_tool_map):
        executed["workflow"] = workflow
        executed["run_id"] = run_id
        executed["output_path"] = output_path

    def fake_row_from_trace(*, task, system, scenario, trace_path, reused_artifact):
        return {"system": system, "scenario": scenario, "trace_path": str(trace_path)}

    def forbidden_plan(_request):
        raise AssertionError("execute_system should not invoke runtime.planner.plan for a2_planner")

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "row_from_trace", fake_row_from_trace)

    runtime = SimpleNamespace(
        planner=SimpleNamespace(plan=forbidden_plan),
        executor=SimpleNamespace(run_until_blocked=fake_run_until_blocked),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a2_planner"],
        task={"task_id": "toolsandbox_exec_001", "query": "Send a message"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=runtime,
    )

    assert build_calls == ["planner"]
    assert executed["workflow"] is seed_workflow
    assert row["system"] == "a2_planner"


def test_execute_system_baseline_uses_planner_workflow(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    build_calls: list[str] = []
    run_calls: dict[str, object] = {}

    def fake_build_workflow_from_task(task, mode="demo"):
        build_calls.append(mode)
        return workflow

    def fake_run_baseline(*, workflow, run_id, output_path):
        run_calls["workflow"] = workflow
        return SimpleNamespace(
            metrics=SimpleNamespace(
                success=True,
                tool_calls=1,
                repair_actions=0,
                total_steps=1,
                token_cost=0.0,
                latency_ms=0,
                clarification_precision=0.0,
                clarification_recall=0.0,
                unnecessary_question_rate=0.0,
                patch_success_rate=0.0,
                post_answer_retry_count=0,
                budget_violation=False,
                budget_violation_reason="",
                recovery_budget_used=0.0,
            )
        ), "success_criteria_satisfied"

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "run_baseline", fake_run_baseline)

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a0_baseline"],
        task={"task_id": "toolsandbox_baseline_001", "query": "Send a message"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=None,
    )

    assert build_calls == ["planner"]
    assert run_calls["workflow"] is workflow
    assert row.system == "a0_baseline"


def test_execute_system_recovery_executor_uses_seed_workflow(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_recovery", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    build_calls: list[str] = []
    executed: dict[str, object] = {}

    def fake_build_workflow_from_task(task, mode="demo"):
        build_calls.append(mode)
        return workflow

    def fake_run_until_blocked(*, workflow, run_id, output_path, backup_tool_map):
        executed["workflow"] = workflow

    def fake_row_from_trace(*, task, system, scenario, trace_path, reused_artifact):
        return {"system": system}

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "row_from_trace", fake_row_from_trace)

    runtime = SimpleNamespace(
        executor=SimpleNamespace(run_until_blocked=fake_run_until_blocked),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a1_recovery"],
        task={"task_id": "toolsandbox_recovery_001", "query": "Send a message"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=runtime,
    )

    assert build_calls == ["seed"]
    assert executed["workflow"] is workflow
    assert row["system"] == "a1_recovery"


def test_execute_system_rolls_back_transfer_reuse_to_a3_behavior(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_reuse_rollback", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    seed_workflow = Workflow.demo()
    seed_workflow.task.task_id = "toolsandbox_reuse_rollback_001"
    seed_workflow.task.user_goal = "retrieve and write report"

    def fake_build_workflow_from_task(task, mode="demo"):
        return seed_workflow

    def fake_row_from_trace(*, task, system, scenario, trace_path, reused_artifact):
        return {
            "system": system,
            "scenario": scenario,
            "reused_artifact": reused_artifact,
            "trace_path": str(trace_path),
        }

    call_log: list[dict[str, object]] = []

    class FakeShell:
        def run(self, *, request, run_id, output_path, backup_tool_map, use_reuse, compile_on_success):
            call_log.append(
                {
                    "use_reuse": use_reuse,
                    "compile_on_success": compile_on_success,
                    "allow_reuse": request.hints.allow_reuse,
                    "reusable_asset_ids": list(request.hints.reusable_asset_ids),
                }
            )
            trace_path = Path(output_path)
            if use_reuse:
                request.hints.reusable_asset_ids = ["asset_transfer_001"]
                trace_path.write_text(
                    json.dumps(
                        {
                            "events": [
                                {"event_type": "tool_call"},
                                {"event_type": "repair_triggered"},
                            ],
                            "metrics": {"repair_actions": 1, "success": False},
                        }
                    ),
                    encoding="utf-8",
                )
                workflow = Workflow.demo()
                workflow.metadata["reusable_context"] = {
                    "profile_loaded": True,
                    "reuse_mode": "transfer_reuse",
                    "resolved_asset_ids": ["asset_transfer_001"],
                    "selected_match": {"reuse_mode": "transfer_reuse"},
                }
                return SimpleNamespace(
                    run_id=run_id,
                    workflow=workflow,
                    success=False,
                    blocked=False,
                    pending_interaction=None,
                    final_state={},
                    trace_path=str(trace_path),
                    last_error_id=None,
                )
            trace_path.write_text(
                json.dumps(
                    {
                        "events": [{"event_type": "tool_call"}],
                        "metrics": {"repair_actions": 0, "success": True},
                    }
                ),
                encoding="utf-8",
            )
            workflow = Workflow.demo()
            workflow.metadata["reusable_context"] = {
                "profile_loaded": False,
                "reuse_mode": "none",
                "resolved_asset_ids": [],
            }
            return SimpleNamespace(
                run_id=run_id,
                workflow=workflow,
                success=True,
                blocked=False,
                pending_interaction=None,
                final_state={},
                trace_path=str(trace_path),
                last_error_id=None,
            )

    compile_calls: list[bool] = []

    runtime = SimpleNamespace(
        _compile_and_store_if_success=lambda outcome, enabled=True: compile_calls.append(bool(enabled and outcome.success)),
    )

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: FakeShell())
    monkeypatch.setattr(module, "row_from_trace", fake_row_from_trace)

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a4_reuse"],
        task={"task_id": "toolsandbox_reuse_rollback_001", "query": "retrieve and write report"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=runtime,
    )

    assert [entry["use_reuse"] for entry in call_log] == [True, False]
    assert all(entry["compile_on_success"] is False for entry in call_log)
    assert compile_calls == [True]
    assert row["reused_artifact"] is False
    trace_payload = json.loads(Path(row["trace_path"]).read_text(encoding="utf-8"))
    assert trace_payload["metadata"]["reuse_rollback"]["fallback_behavior"] == "a3_interaction"


def test_build_runtime_for_spec_detaches_executor_planner_for_non_replan_specs(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_runtime_specs", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    recovery_runtime = module.build_runtime_for_spec(spec=module.SYSTEM_SPECS["a1_recovery"])
    planner_runtime = module.build_runtime_for_spec(spec=module.SYSTEM_SPECS["a2_planner"])
    interaction_runtime = module.build_runtime_for_spec(spec=module.SYSTEM_SPECS["a3_interaction"])

    assert recovery_runtime.executor.planner is None
    assert planner_runtime.executor.planner is None
    assert interaction_runtime.executor.planner is not None


def test_run_baseline_preserves_toolsandbox_trace_metadata(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.workflow_id = "wf_toolsandbox_baseline_metadata_001"
    workflow.task.task_id = "toolsandbox_baseline_metadata_001"
    workflow.metadata.update(
        {
            "benchmark": "toolsandbox",
            "source": "toolsandbox.formal.json",
            "primary_failtax": "state",
            "failtaxes": ["state", "ordering"],
            "failure_step": "step_02",
            "expected_recovery_path": "patch_state_then_retry",
            "gold_tool": "write_tool",
            "state_slots": ["messages", "target_path"],
            "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
            "tool_execution_backend": "semantic_mock",
        }
    )

    trace, _ = run_baseline(
        workflow=workflow,
        run_id="run_toolsandbox_baseline_metadata_001",
        output_path=tmp_path / "baseline_trace.json",
    )

    assert trace.metadata.benchmark == "toolsandbox"
    assert trace.metadata.task_source == "toolsandbox.formal.json"
    assert trace.metadata.primary_failtax == "state"
    assert trace.metadata.failtaxes == ["state", "ordering"]
    assert trace.metadata.task_annotations["failure_step"] == "step_02"
    assert trace.metadata.task_annotations["expected_recovery_path"] == "patch_state_then_retry"
    assert trace.metadata.task_annotations["dependency_edges"] == [
        {"source": "step_01", "target": "step_02", "type": "state"}
    ]
    assert trace.metadata.task_annotations["chosen_tool"] == "write_tool"
    assert trace.metadata.budget_limits["max_tool_calls"] is None


def test_run_baseline_stops_on_approval_required_policy_gate(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.requires_user_approval = True

    trace, stop_reason = run_baseline(
        workflow=workflow,
        run_id="run_baseline_approval_001",
        output_path=tmp_path / "baseline_approval_trace.json",
    )

    assert trace.metrics.success is False
    assert stop_reason == "awaiting_user_interaction"


def test_run_eval_script_separates_recovery_only_and_planner_only_ablation(tmp_path: Path) -> None:
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
    assert toolclaw_rows[("task_binding_planner_001", "a2_planner")]["stop_reason"] == "repair_disabled"
    assert int(toolclaw_rows[("task_env_planner_001", "a2_planner")]["repair_actions"]) == 0


def test_build_shell_supports_configured_llm_backend_without_placeholder_error() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_llm", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    shell = module.build_shell(
        module.build_runtime(),
        {
            "interaction_backend": {
                "type": "llm",
                "provider_name": "scripted_llm",
                "payload": {"target_path": "outputs/reports/llm_reply.txt"},
            },
            "simulated_policy": {"approval_responses": {"int_001": True}},
        },
    )

    reply = shell.reply_provider.reply(
        InteractionRequest(
            interaction_id="int_001",
            question="Please provide the target path.",
            expected_answer_type="target_path_patch",
            metadata={"patch_targets": {"target_path": "step.inputs.target_path"}},
        )
    )

    assert reply.accepted is True
    assert reply.payload["target_path"] == "outputs/reports/llm_reply.txt"
    assert reply.metadata["provider"] == "scripted_llm"


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
    assert a4_pass2["reuse_mode"] == "exact_reuse"
    assert a4_pass2["reuse_tier"] == "exact_match_reuse"
    report = (outdir / "report.md").read_text(encoding="utf-8")
    assert "Verdict:" in report


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
    assert pass2["reused_artifact"] == "False"
    assert pass2["reuse_mode"] == "none"
    assert pass2["reuse_tier"] == "none"
    assert pass2["reuse_target_family"] == "reuse_transfer_001"


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
