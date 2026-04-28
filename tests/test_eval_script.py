import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from toolclaw.benchmarks.baseline_runner import run_baseline
from toolclaw.interaction.repair_updater import InteractionRequest
from toolclaw.schemas.workflow import ToolSpec, Workflow, WorkflowStep


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


def test_build_workflow_from_task_planner_falls_back_when_toolsandbox_plan_is_unbound() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_planner_structural_fallback", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_state_admin_unbound_001",
            "query": "Turn on cellular",
            "tool_allow_list": [
                "set_cellular_service_status",
                "set_low_battery_mode_status",
                "get_cellular_service_status",
                "get_low_battery_mode_status",
            ],
            "candidate_tools": [
                "set_cellular_service_status",
                "set_low_battery_mode_status",
                "get_cellular_service_status",
                "get_low_battery_mode_status",
            ],
            "messages": [{"sender": "user", "recipient": "agent", "content": "Turn on cellular"}],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["state_dependency", "multiple_tool"],
            },
            "milestones": [
                "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SETTING, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'low_battery_mode': False}))])",
                "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SETTING, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'cellular': True}))])",
            ],
        },
        mode="planner",
    )

    assert workflow.metadata["planner_structural_fallback_applied"] is True
    assert workflow.metadata["planner_structural_fallback_reason"] == "unbound_steps"
    assert [step.tool_id for step in workflow.execution_plan] == ["search_tool", "write_tool"]
    assert workflow.execution_plan[0].inputs["query"] == "Turn on cellular"


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
        hint_policy="legacy",
    )

    assert workflow.task.user_goal != "Send a message"
    assert "Fredrik Thordendal" in workflow.task.user_goal
    assert "How's the new album coming along" in workflow.task.user_goal
    assert workflow.execution_plan[0].inputs["name"] == "Fredrik Thordendal"
    assert "query" not in workflow.execution_plan[0].inputs


def test_build_workflow_from_task_excludes_toolsandbox_policy_system_prompt_from_goal() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_policy_system_prompt", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_policy_prompt_001",
            "scenario": "state_dependency",
            "query": "Get me connected to the internet.",
            "tool_allow_list": ["get_wifi_status", "set_wifi_status"],
            "candidate_tools": ["get_wifi_status", "set_wifi_status"],
            "messages": [
                {
                    "sender": "system",
                    "recipient": "unknown",
                    "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous.",
                },
                {
                    "sender": "user",
                    "recipient": "unknown",
                    "content": "Get me connected to the internet.",
                },
                {
                    "sender": "user",
                    "recipient": "unknown",
                    "content": "Disable Low Battery Mode first.",
                },
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["state_dependency", "multiple_tool", "single_user_turn"],
            },
        },
        mode="planner",
    )

    assert "Don't make assumptions" not in workflow.task.user_goal
    assert workflow.task.user_goal == "Get me connected to the internet.\nDisable Low Battery Mode first."


def test_build_workflow_from_task_toolsandbox_demo_uses_candidate_seed() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_demo_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "search_message_with_recency_oldest_alt",
            "scenario": "single_tool",
            "query": "What's the first ever text I have?",
            "tool_allow_list": ["get_current_timestamp", "search_messages", "end_conversation"],
            "candidate_tools": [
                {"tool_id": "get_current_timestamp", "description": "Get the current timestamp."},
                {"tool_id": "search_messages", "description": "Search text messages by content or recency."},
                {"tool_id": "end_conversation", "description": "End the conversation."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "search_messages"
    assert workflow.execution_plan[0].capability_id == "cap_retrieve"
    assert [tool.tool_id for tool in workflow.context.candidate_tools] == [
        "get_current_timestamp",
        "search_messages",
        "end_conversation",
    ]


def test_build_workflow_from_task_toolsandbox_retrieval_avoids_mutation_head() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_retrieve_rank", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "search_name_with_relationship",
            "scenario": "single_tool",
            "query": "What is the name of my boss?",
            "tool_allow_list": ["remove_contact", "search_contacts"],
            "candidate_tools": [
                {"tool_id": "remove_contact", "description": "Remove a contact from the address book."},
                {"tool_id": "search_contacts", "description": "Search contacts by relationship or name."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "search_contacts"
    assert workflow.execution_plan[0].capability_id == "cap_retrieve"


def test_build_workflow_from_task_toolsandbox_state_tools_do_not_fall_back_to_demo() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_state_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "turn_on_wifi_low_battery_mode_implicit",
            "scenario": "state_dependency",
            "query": "Get me connected to the internet.",
            "tool_allow_list": [
                "end_conversation",
                "set_wifi_status",
                "get_low_battery_mode_status",
                "get_wifi_status",
                "set_low_battery_mode_status",
            ],
            "candidate_tools": [
                "end_conversation",
                "set_wifi_status",
                "get_low_battery_mode_status",
                "get_wifi_status",
                "set_low_battery_mode_status",
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["state_dependency", "multiple_tool"],
            },
        },
        mode="demo",
    )

    selected_tools = [step.tool_id for step in workflow.execution_plan]
    assert "search_tool" not in selected_tools
    assert "write_tool" not in selected_tools
    assert any(tool_id.startswith("get_") for tool_id in selected_tools)
    assert any(tool_id.startswith("set_") for tool_id in selected_tools)


def test_build_workflow_from_task_toolsandbox_low_branching_skips_end_conversation() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_skip_end", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_skip_end_001",
            "scenario": "single_tool",
            "query": "Search my messages for the oldest text.",
            "tool_allow_list": ["end_conversation", "search_messages"],
            "candidate_tools": [
                {"tool_id": "end_conversation", "description": "End the conversation."},
                {"tool_id": "search_messages", "description": "Search text messages."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "search_messages"


def test_build_workflow_from_task_toolsandbox_status_query_ranks_matching_check_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_status_rank", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "get_wifi_3_distraction_tools_arg_description_scrambled",
            "scenario": "single_tool",
            "query": "Is my wifi on?",
            "tool_allow_list": ["get_location_service_status", "get_wifi_status", "end_conversation"],
            "candidate_tools": [
                {"tool_id": "get_location_service_status", "description": "Get location service status."},
                {"tool_id": "get_wifi_status", "description": "Get wifi status."},
                {"tool_id": "end_conversation", "description": "End the conversation."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "get_wifi_status"
    assert workflow.execution_plan[0].capability_id in {"cap_retrieve", "cap_check"}


def test_build_workflow_from_task_toolsandbox_send_message_grounds_visible_args() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_send_grounding", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "send_message_with_phone_number_and_content",
            "scenario": "single_tool",
            "query": "Send a message to +12453344098 saying: How's the new album coming along",
            "tool_allow_list": ["send_message_with_phone_number", "end_conversation"],
            "candidate_tools": ["send_message_with_phone_number", "end_conversation"],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    step = workflow.execution_plan[0]
    assert step.tool_id == "send_message_with_phone_number"
    assert step.inputs["recipient_phone_number"] == "+12453344098"
    assert step.inputs["content"] == "How's the new album coming along"


def test_build_workflow_from_task_toolsandbox_send_message_keeps_quoted_content_bounded() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_send_quoted", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "send_message_with_phone_number_and_content_quoted",
            "scenario": "single_tool",
            "messages": [
                {"sender": "system", "content": "Do not make assumptions."},
                {
                    "sender": "user",
                    "content": "Send a message to +12453344098 saying: \"How's the new album coming along.\" Resolve any issue alone.",
                },
            ],
            "tool_allow_list": ["end_conversation", "send_message_with_phone_number"],
            "candidate_tools": ["end_conversation", "send_message_with_phone_number"],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    step = workflow.execution_plan[0]
    assert step.tool_id == "send_message_with_phone_number"
    assert step.inputs["recipient_phone_number"] == "+12453344098"
    assert step.inputs["content"] == "How's the new album coming along."
    assert "Resolve any issue alone" not in step.inputs["content"]


def test_build_workflow_from_task_toolsandbox_named_send_prefers_contact_lookup() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_named_send", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "send_message_with_contact_content_cellular_off_10_distraction_tools",
            "scenario": "state_dependency",
            "query": "Send a message to Fredrik Thordendal saying: \"How's the new album coming along.\" Resolve any issue alone.",
            "tool_allow_list": [
                "search_messages",
                "search_contacts",
                "send_message_with_phone_number",
                "end_conversation",
            ],
            "candidate_tools": [
                "search_messages",
                "search_contacts",
                "send_message_with_phone_number",
                "end_conversation",
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["state_dependency", "multiple_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "search_contacts"
    assert workflow.execution_plan[1].tool_id == "send_message_with_phone_number"
    assert workflow.execution_plan[1].inputs["content"] == "How's the new album coming along."


def test_build_workflow_from_task_toolsandbox_modify_contact_does_not_send_message() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_modify_contact", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "modify_contact_with_message_recency_10_distraction_tools",
            "scenario": "canonicalization",
            "query": "Update the phone number of the last person I sent a message to to +10293847563",
            "tool_allow_list": [
                "search_messages",
                "send_message_with_phone_number",
                "modify_contact",
                "end_conversation",
            ],
            "candidate_tools": [
                "search_messages",
                "send_message_with_phone_number",
                "modify_contact",
                "end_conversation",
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["canonicalization", "multiple_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "search_messages"
    assert workflow.execution_plan[1].tool_id == "modify_contact"


def test_toolsandbox_planner_generates_holiday_time_difference_chain() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_planner_chain", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    task = {
        "task_id": "find_days_till_holiday_3_distraction_tools",
        "scenario": "canonicalization",
        "query": "How many days is it till Christmas Day",
        "tool_allow_list": [
            "datetime_info_to_timestamp",
            "timestamp_diff",
            "get_current_timestamp",
            "search_holiday",
            "end_conversation",
            "shift_timestamp",
            "timestamp_to_datetime_info",
        ],
        "candidate_tools": [
            "datetime_info_to_timestamp",
            "timestamp_diff",
            "get_current_timestamp",
            "search_holiday",
            "end_conversation",
            "shift_timestamp",
            "timestamp_to_datetime_info",
        ],
        "metadata": {
            "benchmark": "toolsandbox",
            "toolsandbox_categories": ["canonicalization", "multiple_tool"],
        },
    }

    base = module.build_workflow_from_task(task, mode="demo", spec=module.SYSTEM_SPECS["s1_recovery"])
    planner = module.build_workflow_from_task(task, mode="planner", spec=module.SYSTEM_SPECS["s2_planner_overlay"])
    overlaid = module.build_workflow_from_task(
        task,
        mode="planner_overlay_admitted",
        spec=module.SYSTEM_SPECS["s2_planner_overlay"],
    )

    assert [step.tool_id for step in base.execution_plan] == ["search_holiday"]
    assert [step.tool_id for step in planner.execution_plan] == [
        "get_current_timestamp",
        "search_holiday",
        "timestamp_diff",
    ]
    utility_backends = {
        tool.tool_id: tool.metadata.get("execution_backend")
        for tool in planner.context.candidate_tools
        if tool.tool_id in {"get_current_timestamp", "search_holiday", "timestamp_diff"}
    }
    assert utility_backends == {
        "get_current_timestamp": "toolsandbox_utility",
        "search_holiday": "toolsandbox_utility",
        "timestamp_diff": "toolsandbox_utility",
    }
    assert planner.metadata["planner_candidate_generation_pattern"] == "holiday_time_difference_chain_v1"
    assert overlaid.metadata["planner_overlay_admitted"] is True
    assert overlaid.metadata["planner_admission_decision"]["reason"] == "strict_refinement"


def test_build_workflow_from_task_toolsandbox_send_message_does_not_fabricate_missing_slots() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_send_missing_slots", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "send_message_missing_visible_slots",
            "scenario": "single_tool",
            "query": "Text Fredrik when the package arrives.",
            "tool_allow_list": ["send_message_with_phone_number", "end_conversation"],
            "candidate_tools": ["send_message_with_phone_number", "end_conversation"],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    step = workflow.execution_plan[0]
    assert step.tool_id == "send_message_with_phone_number"
    assert "recipient_phone_number" not in step.inputs
    assert "content" not in step.inputs


def test_build_workflow_from_task_toolsandbox_mutation_goal_prefers_set_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_mutation_rank", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "turn_on_wifi_low_battery_mode_implicit",
            "scenario": "single_tool",
            "query": "Turn on wifi.",
            "tool_allow_list": ["get_wifi_status", "set_wifi_status", "end_conversation"],
            "candidate_tools": [
                {"tool_id": "get_wifi_status", "description": "Get wifi status."},
                {"tool_id": "set_wifi_status", "description": "Set wifi status."},
                {"tool_id": "end_conversation", "description": "End the conversation."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
            },
        },
        mode="demo",
    )

    assert workflow.execution_plan[0].tool_id == "set_wifi_status"
    assert workflow.execution_plan[0].capability_id == "cap_write"


def test_build_workflow_from_task_planner_preserves_approval_scope_metadata() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_approval_scope", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "tau2_dual_control_001",
            "scenario": "dual_control",
            "query": "retrieve and write report",
            "candidate_tools": ["search_tool", "write_tool", "backup_write_tool"],
            "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
            "state_slots": ["query", "target_path", "approved"],
            "dependency_edges": [
                {"source": "step_01", "target": "step_02", "type": "state"},
                {"source": "policy", "target": "step_02", "type": "approval"},
            ],
            "metadata": {
                "benchmark": "tau2_bench",
                "requires_interaction": True,
                "approval_scope": "failure_step",
                "approval_target_step": "step_02",
            },
            "constraints": {
                "requires_user_approval": True,
                "risk_level": "high",
            },
        },
        mode="planner",
    )

    assert workflow.metadata["benchmark"] == "tau2_bench"
    assert workflow.metadata["requires_interaction"] is True
    assert workflow.metadata["approval_scope"] == "failure_step"
    assert workflow.metadata["approval_target_step"] == "step_02"


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


def test_build_workflow_from_task_bfcl_expected_empty_calls_abstains_even_with_relevant_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_expected_abstain", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_irrelevance_expected_empty_001",
            "query": "Chama um uber pra mim ae pro endereço Rua Explosao, 8899?",
            "candidate_tools": [
                {
                    "tool_id": "call_uber",
                    "description": "Requests an Uber ride to the specified pickup location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
            "expected_call_structure": {"pattern": "serial", "calls": []},
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "serial",
                "expected_call_structure": {"pattern": "serial", "calls": []},
            },
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_preflight_only"],
    )

    assert workflow.metadata["bfcl_abstained"] is True
    assert workflow.execution_plan == []
    assert workflow.tool_bindings == []
    assert workflow.context.candidate_tools == []


def test_build_workflow_from_task_bfcl_expected_empty_calls_abstains_with_empty_candidate_tools() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_expected_empty_no_tools", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_irrelevance_expected_empty_002",
            "query": "Could you tell me the current weather in Boston, MA and also in San Francisco?",
            "candidate_tools": [],
            "ideal_tool_calls": 0,
            "expected_call_structure": {"pattern": "serial", "calls": []},
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "serial",
                "expected_call_structure": {"pattern": "serial", "calls": []},
            },
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata["bfcl_abstained"] is True
    assert workflow.execution_plan == []
    assert workflow.tool_bindings == []
    assert workflow.context.candidate_tools == []


def test_build_workflow_from_task_bfcl_positive_serial_without_gold_shape_does_not_abstain() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_positive_no_gold_shape", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_simple_positive_no_gold_shape_001",
            "query": "Could you tell me the current weather in Boston, MA?",
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Gets current weather conditions for a location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "serial",
            },
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert [step.tool_id for step in workflow.execution_plan] == ["get_current_weather"]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["selected_reason"] in {
        "planner_aligned_schema_top1",
        "schema_top1_no_planner",
    }
    assert diagnostics.get("candidate_pool_exception", "") == ""
    assert "expected_call_count" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_positive_parallel_without_gold_shape_does_not_abstain_or_flatten() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_no_gold_shape", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_parallel_positive_no_gold_shape_001",
            "query": "Could you tell me the current weather conditions for Boston, MA and also for San Francisco?",
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Gets current weather conditions for a location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "parallel",
            },
        },
        mode="planner",
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert [step.tool_id for step in workflow.execution_plan] == [
        "get_current_weather",
        "get_current_weather",
    ]
    assert [step.inputs for step in workflow.execution_plan] == [
        {"location": "Boston, MA"},
        {"location": "San Francisco"},
    ]


def test_build_workflow_from_task_bfcl_required_query_is_not_stripped() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_required_query", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_multiple_query_required_001",
            "query": "Search memory for when is shishir's birthday",
            "candidate_tools": [
                {
                    "tool_id": "recall_memory_search",
                    "description": "Search user memory with a query string.",
                    "parameters": {
                        "type": "dict",
                        "required": ["query"],
                        "properties": {"query": {"type": "string"}},
                    },
                }
            ],
            "expected_call_structure": {
                "pattern": "serial",
                "calls": [
                    {
                        "tool_name": "recall_memory_search",
                        "arguments": {"query": "Search memory for when is shishir's birthday"},
                    }
                ],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "serial",
            },
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.execution_plan
    assert workflow.execution_plan[0].inputs["query"] == "Search memory for when is shishir's birthday"


def test_bfcl_schema_ranker_overrides_weaker_planner_preference() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_schema_ranker", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    food_tool = ToolSpec(
        tool_id="ChaFod",
        description="Changes a food item based on the customer's request.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["foodItem"],
                "properties": {"foodItem": {"type": "string"}},
            }
        },
    )
    drink_tool = ToolSpec(
        tool_id="ChaDri.change_drink",
        description="Modifies an existing drink order and drink preferences.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["new_preferences"],
                "properties": {
                    "drink_id": {"type": "string", "default": "0000-0000-0000"},
                    "new_preferences": {
                        "type": "dict",
                        "properties": {
                            "size": {"type": "string", "enum": ["small", "medium", "large"]},
                            "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                        },
                    },
                },
            }
        },
    )

    selected = module._bfcl_schema_ranked_tool(
        [food_tool, drink_tool],
        "update my latte to a large size with coconut milk",
        preferred_tool_id="ChaFod",
    )

    assert selected is not None
    assert selected.tool_id == "ChaDri.change_drink"


def test_build_workflow_from_task_bfcl_planner_uses_schema_ranked_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_planner_schema_ranked", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_multiple_drink_001",
            "query": "update my latte to a large size with coconut milk and make it extra sweet",
            "candidate_tools": [
                {
                    "tool_id": "ChaFod",
                    "description": "Changes a food item based on the customer's request.",
                    "parameters": {
                        "type": "dict",
                        "required": ["foodItem"],
                        "properties": {"foodItem": {"type": "string"}},
                    },
                },
                {
                    "tool_id": "ChaDri.change_drink",
                    "description": "Modifies an existing drink order and drink preferences.",
                    "parameters": {
                        "type": "dict",
                        "required": ["new_preferences"],
                        "properties": {
                            "drink_id": {"type": "string", "default": "0000-0000-0000"},
                            "new_preferences": {
                                "type": "dict",
                                "properties": {
                                    "size": {"type": "string", "enum": ["small", "medium", "large"]},
                                    "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                                    "sweetness_level": {"type": "string", "enum": ["none", "light", "regular", "extra"]},
                                },
                            },
                        },
                    },
                },
            ],
            "expected_call_structure": {
                "pattern": "serial",
                "calls": [{"tool_name": "ChaDri.change_drink", "arguments": {}}],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "serial",
            },
        },
        mode="planner",
    )

    assert workflow.execution_plan
    assert workflow.execution_plan[0].tool_id == "ChaDri.change_drink"


def test_bfcl_schema_ranked_tool_drops_bad_preferred_tool_on_tie(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_tie_drop", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tools = [
        module.ToolSpec(tool_id="wrong_tool", description="Wrong tool"),
        module.ToolSpec(tool_id="right_tool", description="Right tool"),
    ]

    monkeypatch.setattr(
        module,
        "rank_candidate_tools",
        lambda text, candidate_tools: [
            {"tool": {"tool_id": "right_tool"}, "score": 4.0},
            {"tool": {"tool_id": "wrong_tool"}, "score": 4.0},
        ],
    )

    selected, diagnostics = module._bfcl_schema_ranked_choice(
        tools,
        "pick the right tool",
        preferred_tool_id="wrong_tool",
    )

    assert selected is not None
    assert selected.tool_id == "right_tool"
    assert diagnostics["rerank_override_applied"] is False
    assert diagnostics["rerank_override_reason"] == "planner_tie_dropped"


def test_adapt_bfcl_workflow_canonicalizes_serial_planner_shape() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_canonicalization", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.Workflow.demo()
    workflow.task.user_goal = "update my latte to a large size with coconut milk"
    workflow.execution_plan[0].tool_id = "ChaFod"
    workflow.execution_plan[1].tool_id = "ChaFod"

    task = {
        "task_id": "bfcl_live_multiple_drink_serial_001",
        "query": "update my latte to a large size with coconut milk",
        "candidate_tools": [
            {
                "tool_id": "ChaFod",
                "description": "Changes a food item based on the customer's request.",
                "parameters": {
                    "type": "dict",
                    "required": ["foodItem"],
                    "properties": {"foodItem": {"type": "string"}},
                },
            },
            {
                "tool_id": "ChaDri.change_drink",
                "description": "Modifies an existing drink order and drink preferences.",
                "parameters": {
                    "type": "dict",
                    "required": ["new_preferences"],
                    "properties": {
                        "drink_id": {"type": "string", "default": "0000-0000-0000"},
                        "new_preferences": {
                            "type": "dict",
                            "properties": {
                                "size": {"type": "string", "enum": ["small", "medium", "large"]},
                                "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                            },
                        },
                    },
                },
            },
        ],
        "metadata": {
            "benchmark": "bfcl",
            "bfcl_group": "live",
            "bfcl_call_pattern": "serial",
            "expected_call_structure": {
                "pattern": "serial",
                "calls": [
                    {
                        "tool_name": "ChaDri.change_drink",
                        "arguments": {"new_preferences": {"size": "large", "milk_type": "coconut"}},
                    }
                ],
            },
        },
    }

    candidate_tools = [
        module.ToolSpec(
            tool_id="ChaFod",
            description="Changes a food item based on the customer's request.",
            metadata={
                "parameters": {
                    "type": "dict",
                    "required": ["foodItem"],
                    "properties": {"foodItem": {"type": "string"}},
                }
            },
        ),
        module.ToolSpec(
            tool_id="ChaDri.change_drink",
            description="Modifies an existing drink order and drink preferences.",
            metadata={
                "parameters": {
                    "type": "dict",
                    "required": ["new_preferences"],
                    "properties": {
                        "drink_id": {"type": "string", "default": "0000-0000-0000"},
                        "new_preferences": {
                            "type": "dict",
                            "properties": {
                                "size": {"type": "string", "enum": ["small", "medium", "large"]},
                                "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                            },
                        },
                    },
                }
            },
        ),
    ]
    adapted = module._adapt_bfcl_workflow(
        workflow,
        task=task,
        candidate_tools=candidate_tools,
        mode="planner",
        enable_grounding=True,
    )

    assert len(adapted.execution_plan) == 1
    assert adapted.metadata["planner_canonicalized_to_bfcl_seed"] is True
    assert adapted.metadata["bfcl_protocol_fallback_reason"] == "serial_exact_call_protocol"
    assert adapted.metadata["bfcl_canonicalized_step_count_before"] == 2
    assert adapted.metadata["bfcl_canonicalized_step_count_after"] == 1


def test_build_workflow_from_task_bfcl_planner_multi_turn_uses_protocol_seed() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_multiturn_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_multi_turn_protocol_seed_001",
            "query": "Create a temp folder and move final_report.pdf into it",
            "candidate_tools": [
                {
                    "tool_id": "mkdir",
                    "description": "Create a new directory.",
                    "parameters": {
                        "type": "dict",
                        "required": ["dir_name"],
                        "properties": {"dir_name": {"type": "string"}},
                    },
                },
                {
                    "tool_id": "mv",
                    "description": "Move a file or directory.",
                    "parameters": {
                        "type": "dict",
                        "required": ["source", "destination"],
                        "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
                    },
                },
            ],
            "expected_call_structure": {
                "pattern": "serial",
                "calls": [
                    {"tool_name": "mkdir", "arguments": {"dir_name": "temp"}},
                    {"tool_name": "mv", "arguments": {"source": "final_report.pdf", "destination": "temp"}},
                ],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "multi_turn",
                "bfcl_call_pattern": "serial",
            },
        },
        mode="planner",
    )

    assert workflow.metadata["bfcl_protocol_fallback_applied"] is True
    assert workflow.metadata["bfcl_protocol_fallback_reason"] == "multi_turn_without_explicit_milestones"
    assert len(workflow.execution_plan) == 1


def test_configure_bfcl_step_metadata_preserves_existing_grounding_and_refreshes_defaults() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_metadata_merge", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    step = WorkflowStep(
        step_id="step_01",
        capability_id="cap_retrieve",
        tool_id="recall_memory_search",
        inputs={"query": "Search memory for when is shishir's birthday"},
        metadata={
            "input_bindings": {"query": "query"},
            "grounding_sources": {"query": {"source": "binder", "confidence": 0.95}},
            "grounding_confidence": {"query": 0.95},
            "unresolved_required_inputs": [],
            "repair_default_inputs": {"query": "stale value"},
        },
    )
    tool = ToolSpec(
        tool_id="recall_memory_search",
        description="Search user memory with a query string.",
        metadata={"parameters": {"type": "dict", "required": ["query"], "properties": {"query": {"type": "string"}}}},
    )

    module._configure_bfcl_step_metadata(step, tool, "Search memory for when is shishir's birthday", enable_grounding=True)

    assert step.metadata["input_bindings"] == {"query": "query"}
    assert step.metadata["grounding_sources"]["query"]["source"] == "binder"
    assert step.metadata["grounding_confidence"]["query"] == 0.95
    assert step.metadata["repair_default_inputs"] == {"query": "Search memory for when is shishir's birthday"}


def test_configure_bfcl_step_metadata_refreshes_required_inputs_for_selected_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_metadata_refresh", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    step = WorkflowStep(
        step_id="step_01",
        capability_id="cap_retrieve",
        tool_id="OpenWeatherMap.get_current_weather",
        inputs={"location": "Santa Cruz, USA"},
        metadata={
            "required_input_keys": ["keyword"],
            "grounding_sources": {"keyword": {"source": "binder", "confidence": 0.91}},
            "grounding_confidence": {"keyword": 0.91},
            "unresolved_required_inputs": ["keyword"],
            "repair_default_inputs": {"keyword": "stale keyword"},
        },
    )
    tool = ToolSpec(
        tool_id="OpenWeatherMap.get_current_weather",
        description="Get the current weather for a location.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["location"],
                "properties": {"location": {"type": "string"}},
            }
        },
    )

    module._configure_bfcl_step_metadata(step, tool, "What's the weather in Santa Cruz?", enable_grounding=True)

    assert step.metadata["required_input_keys"] == ["location"]
    assert step.metadata["unresolved_required_inputs"] == []
    assert "keyword" not in step.metadata["grounding_sources"]
    assert "keyword" not in step.metadata["grounding_confidence"]
    assert step.metadata["repair_default_inputs"] == {"location": "Santa Cruz, USA"}


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
            "reuse_family_id": "message_send_001",
            "semantic_reuse_family": "message_send",
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
    assert request.hints.user_style["reuse_family_id"] == "message_send_001"
    assert request.hints.user_style["semantic_reuse_family"] == "message_send"
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

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
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


def test_execute_system_baseline_uses_demo_executor_without_repair(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_baseline", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    build_calls: list[str] = []
    executed: dict[str, object] = {}

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
        build_calls.append(mode)
        return workflow

    def fake_run_until_blocked(*, workflow, run_id, output_path, backup_tool_map):
        executed["workflow"] = workflow

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(
        module,
        "row_from_trace",
        lambda **kwargs: SimpleNamespace(system=kwargs["system"], task_id=kwargs["task"]["task_id"]),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a0_baseline"],
        task={"task_id": "toolsandbox_baseline_001", "query": "Send a message"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=SimpleNamespace(executor=SimpleNamespace(run_until_blocked=fake_run_until_blocked)),
    )

    assert build_calls == ["demo"]
    assert executed["workflow"] is workflow
    assert row.system == "a0_baseline"


def test_execute_system_bfcl_structured_interaction_uses_shell(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_structured", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["benchmark"] = "bfcl"
    build_calls: list[str] = []
    shell_calls: list[str] = []

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
        build_calls.append(mode)
        return workflow

    def fake_run_until_blocked(*, workflow, run_id, output_path, backup_tool_map):
        raise AssertionError("BFCL interaction workflow should not be forced into direct executor mode")

    def fake_row_from_trace(*, task, system, scenario, trace_path, reused_artifact):
        return {"system": system, "scenario": scenario, "trace_path": str(trace_path)}

    class _FakeShell:
        def run(self, **kwargs):
            shell_calls.append(kwargs["run_id"])
            assert kwargs["seed_workflow"] is workflow
            Path(kwargs["output_path"]).write_text(
                json.dumps({"events": [], "metrics": {"success": True}, "metadata": {}}),
                encoding="utf-8",
            )
            return SimpleNamespace(workflow=workflow)

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "row_from_trace", fake_row_from_trace)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: _FakeShell())

    runtime = SimpleNamespace(
        executor=SimpleNamespace(run_until_blocked=fake_run_until_blocked),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a3_interaction"],
        task={"task_id": "bfcl_parallel_001", "query": "play music", "metadata": {"benchmark": "bfcl"}},
        task_index=1,
        traces_dir=tmp_path,
        runtime=runtime,
    )

    assert build_calls == ["planner"]
    assert shell_calls == ["a3_interaction_bfcl_parallel_001"]
    assert row["system"] == "a3_interaction"


def test_execute_system_interaction_uses_same_planner_workflow_as_a2(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_a3_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["benchmark"] = "toolsandbox"
    workflow.task.task_id = "shared_planner_workflow"
    workflow.execution_plan[0].tool_id = "weather_lookup"
    build_calls: list[str] = []

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
        build_calls.append(mode)
        return workflow

    class _FakeShell:
        def run(self, **kwargs):
            assert kwargs["seed_workflow"] is workflow
            Path(kwargs["output_path"]).write_text(
                json.dumps({"events": [], "metrics": {"success": True}, "metadata": {}}),
                encoding="utf-8",
            )
            return SimpleNamespace(workflow=workflow)

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: _FakeShell())
    monkeypatch.setattr(
        module,
        "row_from_trace",
        lambda **kwargs: SimpleNamespace(system=kwargs["system"], task_id=kwargs["task"]["task_id"]),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["a3_interaction"],
        task={"task_id": "ts_interaction_001", "query": "check weather"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=SimpleNamespace(executor=SimpleNamespace(run_until_blocked=lambda **kwargs: None)),
    )

    assert build_calls == ["planner"]
    assert row.system == "a3_interaction"


def test_parse_systems_supports_interaction_causality_ablation_systems() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_causal_systems", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    systems = module.parse_systems("a3_full_interaction,a3_no_query,a3_noisy_user")

    assert [system.system_id for system in systems] == [
        "a3_full_interaction",
        "a3_no_query",
        "a3_noisy_user",
    ]
    assert systems[1].disable_user_queries is True
    assert systems[2].noisy_user_replies is True


def test_build_shell_derives_toolsandbox_missing_content_for_simulator() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_toolsandbox_sim_policy", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    shell = module.build_shell(
        module.build_runtime(),
        {
            "metadata": {"benchmark": "toolsandbox"},
            "messages": [
                {"sender": "user", "content": "Send a message"},
                {
                    "sender": "user",
                    "content": "I don't have the phone number, but it's Fredrik. The message is: How's the new album coming along.",
                },
            ],
        },
    )
    reply = shell.reply_provider.reply(
        InteractionRequest(
            interaction_id="int_toolsandbox_content",
            question="Provide the missing field(s): content.",
            expected_answer_type="missing_asset_patch",
            metadata={"patch_targets": {"content": "step.inputs.content"}},
        )
    )

    assert reply.payload["content"] == "How's the new album coming along."
    assert reply.raw_text == "auto-reply"


def test_build_shell_applies_noisy_provider_from_system_spec() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_noisy_shell", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    shell = module.build_shell(
        module.build_runtime(),
        {"_system_spec": module.SYSTEM_SPECS["a3_noisy_user"]},
    )
    reply = shell.reply_provider.reply(
        InteractionRequest(
            interaction_id="int_noisy_001",
            question="Provide the target path.",
            expected_answer_type="target_path_patch",
            metadata={"patch_targets": {"target_path": "step.inputs.target_path"}},
        )
    )

    assert reply.status == "accept"
    assert reply.metadata["noisy_reply"] is True
    assert reply.payload


def test_build_planning_request_preserves_approval_scope_metadata() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_approval_scope", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["approval_scope"] = "failure_step"
    workflow.metadata["approval_target_step"] = "step_02"
    workflow.metadata["requires_interaction"] = True

    request = module.build_planning_request(workflow, allow_reuse=True)

    assert request.hints.user_style["approval_scope"] == "failure_step"
    assert request.hints.user_style["approval_target_step"] == "step_02"
    assert request.hints.user_style["requires_interaction"] is True


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

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
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

    assert build_calls == ["demo"]
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

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
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
        def run(self, *, request, run_id, output_path, backup_tool_map, use_reuse, compile_on_success, seed_workflow=None):
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
    assert all(entry["compile_on_success"] is True for entry in call_log)
    assert compile_calls == []
    assert row["reused_artifact"] is False
    trace_payload = json.loads(Path(row["trace_path"]).read_text(encoding="utf-8"))
    assert trace_payload["metadata"]["reuse_rollback"]["fallback_behavior"] == "a3_interaction"


def test_layered_a0_to_a4_specs_are_monotonic_by_construction() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_layered_specs", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    a0 = module.SYSTEM_SPECS["a0_baseline"]
    a1 = module.SYSTEM_SPECS["a1_recovery"]
    a2 = module.SYSTEM_SPECS["a2_planner"]
    a3 = module.SYSTEM_SPECS["a3_interaction"]
    a4 = module.SYSTEM_SPECS["a4_reuse"]

    assert a0.workflow_mode == "demo"
    assert a0.execution_mode == "executor"
    assert a0.allow_repair is False
    assert a0.allow_fallback is False

    assert a1.workflow_mode == a0.workflow_mode
    assert a1.execution_mode == a0.execution_mode
    assert a1.allow_repair is True
    assert a1.allow_fallback is True

    assert a2.execution_mode == a1.execution_mode
    assert a2.workflow_mode == "planner"
    assert a2.allow_repair == a1.allow_repair
    assert a2.allow_fallback == a1.allow_fallback

    assert a3.workflow_mode == a2.workflow_mode
    assert a3.execution_mode == "interaction"
    assert a3.use_reuse is False
    assert a3.compile_on_success is False

    assert a4.workflow_mode == a3.workflow_mode
    assert a4.execution_mode == a3.execution_mode
    assert a4.use_reuse is True
    assert a4.compile_on_success is True


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

    assert recovery_runtime.executor.planner is not None
    assert planner_runtime.executor.planner is not None
    assert interaction_runtime.executor.planner is None


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


def test_run_eval_script_separates_grounding_ablation_configs(tmp_path: Path) -> None:
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
        "--systems",
        "tc_recovery_only,fc_preflight_only,fc_grounding_recovery",
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
    assert int(toolclaw_rows[("task_binding_planner_001", "tc_recovery_only")]["repair_actions"]) >= 1
    assert toolclaw_rows[("task_binding_planner_001", "fc_preflight_only")]["stop_reason"] == "repair_disabled"
    assert int(toolclaw_rows[("task_binding_planner_001", "fc_grounding_recovery")]["repair_actions"]) >= 1
    assert int(toolclaw_rows[("task_env_planner_001", "fc_preflight_only")]["repair_actions"]) == 0


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


def test_run_eval_script_resume_state_loss_recovers_after_interaction_patch(tmp_path: Path) -> None:
    taskset = [
        {
            "task_id": "state_resume_loss_001",
            "scenario": "state_failure",
            "execution_scenario": "state_failure",
            "query": "retrieve and write report",
            "state_failure_mode": "resume_state_loss",
            "simulated_policy": {
                "mode": "cooperative",
                "missing_arg_values": {"retrieved_info": "summary for: retrieve and write report"},
            },
        }
    ]
    taskset_path = tmp_path / "taskset_state_resume_loss.json"
    taskset_path.write_text(json.dumps(taskset), encoding="utf-8")

    outdir = tmp_path / "eval_out_state_resume_loss"
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
    assert row["stop_reason"] == "success_criteria_satisfied"


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


def test_bfcl_seed_specs_build_parallel_multiple_steps() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_multiple", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    candidate_tools = [
        module.ToolSpec(
            tool_id="math_toolkit.sum_of_multiples",
            description="Compute the sum of multiples within a range.",
            metadata={
                "parameters": {
                    "type": "dict",
                    "properties": {
                        "lower_limit": {"type": "integer"},
                        "upper_limit": {"type": "integer"},
                        "multiples": {"type": "array", "items": {"type": "integer"}},
                    },
                }
            },
        ),
        module.ToolSpec(
            tool_id="math_toolkit.product_of_primes",
            description="Compute the product of the first N prime numbers.",
            metadata={
                "parameters": {
                    "type": "dict",
                    "properties": {
                        "count": {"type": "integer"},
                    },
                }
            },
        ),
    ]

    specs = module._bfcl_seed_specs(
        {
            "query": "Find the sum of multiples of 3 and 5 between 1 and 1000, and also compute the product of the first five prime numbers.",
            "metadata": {"bfcl_call_pattern": "parallel"},
        },
        candidate_tools,
        "parallel math query",
    )

    assert len(specs) == 2
    assert [spec["tool"].tool_id for spec in specs] == [
        "math_toolkit.sum_of_multiples",
        "math_toolkit.product_of_primes",
    ]
    assert specs[0]["inputs"] == {"lower_limit": 1, "upper_limit": 1000, "multiples": [3, 5]}
    assert specs[1]["inputs"] == {"count": 5}


def test_execute_system_uses_shell_for_bfcl_interaction_workflows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_interaction", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.Workflow.demo()
    workflow.metadata["benchmark"] = "bfcl"
    workflow.execution_plan = workflow.execution_plan[:1]
    workflow.execution_plan[0].capability_id = "cap_retrieve"
    workflow.execution_plan[0].tool_id = "weather_lookup"
    workflow.execution_plan[0].inputs = {"city": "Paris"}

    shell_calls: list[str] = []
    executor_calls: list[str] = []

    def _fake_build_workflow_from_task(task: dict, mode: str = "demo", spec=None, **kwargs):
        assert mode == "planner"
        return workflow

    class _FakeExecutor:
        def run_until_blocked(self, **kwargs):
            executor_calls.append(kwargs["run_id"])
            trace_path = Path(kwargs["output_path"])
            trace_path.write_text(json.dumps({"events": [], "metrics": {}, "metadata": {}}), encoding="utf-8")

    class _FakeShell:
        def run(self, **kwargs):
            shell_calls.append(kwargs["run_id"])
            trace_path = Path(kwargs["output_path"])
            trace_path.write_text(
                json.dumps(
                    {
                        "events": [],
                        "metrics": {"success": True, "tool_calls": 1},
                        "metadata": {},
                    }
                ),
                encoding="utf-8",
            )
            return SimpleNamespace(workflow=workflow)

    fake_runtime = SimpleNamespace(
        executor=_FakeExecutor(),
        _compile_and_store_if_success=lambda outcome, enabled=True: None,
    )

    monkeypatch.setattr(module, "build_workflow_from_task", _fake_build_workflow_from_task)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: _FakeShell())
    monkeypatch.setattr(
        module,
        "row_from_trace",
        lambda **kwargs: SimpleNamespace(system=kwargs["system"], task_id=kwargs["task"].get("task_id")),
    )

    result = module.execute_system(
        spec=module.SYSTEM_SPECS["a3_interaction"],
        task={
            "task_id": "bfcl_shell_001",
            "scenario": "bfcl",
            "query": "Call weather_lookup with city=Paris.",
            "metadata": {"benchmark": "bfcl"},
        },
        task_index=1,
        traces_dir=tmp_path,
        runtime=fake_runtime,
    )

    assert result.system == "a3_interaction"
    assert shell_calls == ["a3_interaction_bfcl_shell_001"]
    assert executor_calls == []


def test_build_planning_request_preserves_step_capability_overrides() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_request_overrides", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.execution_plan = workflow.execution_plan[:1]
    workflow.execution_plan[0].step_id = "step_01"
    workflow.execution_plan[0].capability_id = "cap_retrieve"
    workflow.execution_plan[0].tool_id = "weather_lookup"
    workflow.execution_plan[0].inputs = {"city": "Paris"}
    workflow.execution_plan[0].metadata = {"bfcl_benchmark": True}

    request = module.build_planning_request(workflow, allow_reuse=False)

    assert request.workflow_overrides["steps"]["step_01"]["capability_id"] == "cap_retrieve"


def test_htgp_request_overrides_can_restore_missing_steps() -> None:
    from toolclaw.planner.htgp import PlanningRequest, build_default_planner

    workflow = Workflow.demo()
    workflow.execution_plan = workflow.execution_plan[:1]
    workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[:1]
    workflow.workflow_graph.edges = []
    workflow.workflow_graph.entry_nodes = ["step_01"]
    workflow.workflow_graph.exit_nodes = ["step_01"]
    workflow.tool_bindings = workflow.tool_bindings[:1]
    workflow.capability_graph.capabilities = workflow.capability_graph.capabilities[:1]
    workflow.capability_graph.edges = []

    planner = build_default_planner()
    request = PlanningRequest(
        task=workflow.task,
        context=workflow.context,
        policy=workflow.policy,
        workflow_overrides={
            "steps": {
                "step_01": {
                    "capability_id": "cap_retrieve",
                    "tool_id": "tool_one",
                    "inputs": {"query": "first"},
                    "metadata": {},
                },
                "step_02": {
                    "capability_id": "cap_retrieve",
                    "tool_id": "tool_two",
                    "inputs": {"query": "second"},
                    "metadata": {},
                },
            }
        },
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) >= 2
    assert result.workflow.execution_plan[0].tool_id == "tool_one"
    assert result.workflow.execution_plan[1].tool_id == "tool_two"


def test_htgp_request_overrides_restore_missing_steps_without_existing_bindings() -> None:
    from toolclaw.planner.htgp import HTGPPlanner

    workflow = Workflow.demo()
    workflow.execution_plan = workflow.execution_plan[:1]
    workflow.execution_plan[0].step_id = "step_01"
    workflow.execution_plan[0].capability_id = "cap_retrieve"
    workflow.execution_plan[0].tool_id = "tool_one"
    workflow.execution_plan[0].inputs = {"query": "first"}
    workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[:1]
    workflow.workflow_graph.edges = []
    workflow.workflow_graph.entry_nodes = ["step_01"]
    workflow.workflow_graph.exit_nodes = ["step_01"]
    workflow.tool_bindings = []
    workflow.capability_graph.capabilities = workflow.capability_graph.capabilities[:1]
    workflow.capability_graph.edges = []

    HTGPPlanner._apply_request_overrides(
        workflow,
        {
            "steps": {
                "step_01": {
                    "capability_id": "cap_retrieve",
                    "tool_id": "tool_one",
                    "inputs": {"query": "first"},
                    "metadata": {},
                },
                "step_02": {
                    "capability_id": "cap_retrieve",
                    "tool_id": "tool_two",
                    "inputs": {"query": "second"},
                    "metadata": {},
                },
            }
        },
    )

    assert len(workflow.execution_plan) == 2
    assert workflow.execution_plan[1].tool_id == "tool_two"
    assert len(workflow.tool_bindings) == 2
    assert workflow.tool_bindings[1].primary_tool == "tool_two"


def test_bfcl_schema_ranked_choice_is_deterministic_under_candidate_shuffle() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_deterministic", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tools_a = [
        module.ToolSpec(tool_id="z_tool", description="Shared lookup tool"),
        module.ToolSpec(tool_id="a_tool", description="Shared lookup tool"),
    ]
    tools_b = list(reversed(tools_a))

    selected_a, diagnostics_a = module._bfcl_schema_ranked_choice(tools_a, "lookup shared information")
    selected_b, diagnostics_b = module._bfcl_schema_ranked_choice(tools_b, "lookup shared information")

    assert selected_a is not None and selected_b is not None
    assert selected_a.tool_id == "a_tool"
    assert selected_b.tool_id == "a_tool"
    assert diagnostics_a["schema_top_tool_id"] == diagnostics_b["schema_top_tool_id"] == "a_tool"


def test_bfcl_schema_ranked_choice_rejects_zero_coverage_planner_tool(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_zero_coverage", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tools = [
        module.ToolSpec(
            tool_id="wrong_tool",
            description="Wrong tool",
            metadata={"parameters": {"type": "dict", "required": ["missing_value"], "properties": {"missing_value": {"type": "string"}}}},
        ),
        module.ToolSpec(
            tool_id="right_tool",
            description="Right tool",
            metadata={"parameters": {"type": "dict", "required": ["city"], "properties": {"city": {"type": "string"}}}},
        ),
    ]

    monkeypatch.setattr(
        module,
        "rank_candidate_tools",
        lambda text, candidate_tools: [
            {"tool": {"tool_id": "right_tool"}, "score": 4.0, "required_argument_coverage": 1.0},
            {"tool": {"tool_id": "wrong_tool"}, "score": 4.0, "required_argument_coverage": 0.0},
        ],
    )

    selected, diagnostics = module._bfcl_schema_ranked_choice(
        tools,
        "weather in city Paris",
        preferred_tool_id="wrong_tool",
    )

    assert selected is not None
    assert selected.tool_id == "right_tool"
    assert diagnostics["selected_reason"] == "planner_required_argument_coverage_zero"
    assert diagnostics["planner_required_argument_coverage"] == 0.0
    assert diagnostics["selected_required_argument_coverage"] == 1.0
    assert diagnostics["planner_missing_required_args"] == ["missing_value"]


def test_bfcl_schema_ranked_choice_runtime_diagnostics_are_gold_free() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_gold_free", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    selected, diagnostics = module._bfcl_schema_ranked_choice(
        [module.ToolSpec(tool_id="weather_lookup", description="Look up weather by city")],
        "look up weather for Paris",
    )

    assert selected is not None
    encoded = json.dumps(diagnostics)
    for forbidden in ("expected_function", "expected_tool", "gold_tool", "official_failure_bucket"):
        assert forbidden not in encoded


def test_bfcl_schema_ranked_choice_records_candidate_coverage_diagnostics() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_candidate_coverage", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tools = [
        module.ToolSpec(
            tool_id="wrong_tool",
            description="Wrong tool",
            metadata={"bfcl_original_function_name": "Wrong.original", "parameters": {}},
        ),
        module.ToolSpec(
            tool_id="right_tool",
            description="Right lookup tool",
            metadata={"bfcl_original_function_name": "Right.original", "parameters": {}},
        ),
    ]

    selected, diagnostics = module._bfcl_schema_ranked_choice(
        tools,
        "right lookup",
        preferred_tool_id="wrong_tool",
    )

    assert selected is not None
    assert diagnostics["runtime_candidate_count"] == 2
    assert diagnostics["runtime_candidate_tool_ids"] == ["wrong_tool", "right_tool"]
    assert diagnostics["runtime_candidate_original_function_names"] == ["Wrong.original", "Right.original"]
    assert set(diagnostics["ranker_candidate_tool_ids"]) == {"wrong_tool", "right_tool"}
    assert "expected_function" not in json.dumps(diagnostics)
    assert "gold_tool" not in json.dumps(diagnostics)


def test_bfcl_schema_choice_preserves_full_candidate_pool_with_bad_planner_preference(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_candidate_pool_choice", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tools = [
        ToolSpec(tool_id="wrong_planner_tool", description="Wrong planner choice"),
        ToolSpec(tool_id="expected_weather", description="Get weather by city"),
        ToolSpec(tool_id="distractor_calendar", description="Calendar lookup"),
    ]
    monkeypatch.setattr(
        module,
        "rank_candidate_tools",
        lambda text, candidate_tools: [
            {"tool": {"tool_id": "expected_weather"}, "score": 10.0},
            {"tool": {"tool_id": "wrong_planner_tool"}, "score": 2.0},
            {"tool": {"tool_id": "distractor_calendar"}, "score": 1.0},
        ],
    )

    selected, diagnostics = module._bfcl_schema_ranked_choice(
        tools,
        "Get weather for Paris",
        preferred_tool_id="wrong_planner_tool",
    )

    assert selected is not None
    assert selected.tool_id == "expected_weather"
    assert diagnostics["prepared_function_count"] == 3
    assert diagnostics["runtime_candidate_count"] == 3
    assert diagnostics["runtime_candidate_tool_ids"] == [
        "wrong_planner_tool",
        "expected_weather",
        "distractor_calendar",
    ]
    assert diagnostics["candidate_pool_preserved"] is True
    assert diagnostics["candidate_pool_source"] == "bfcl_prepared_row_functions"
    assert diagnostics["planner_narrowing_applied"] is False
    assert diagnostics["candidate_pool_exception"] == ""
    assert "expected_function" not in json.dumps(diagnostics)
    assert "official_failure" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_serial_canonicalization_preserves_candidate_pool(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_candidate_pool", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        module,
        "rank_candidate_tools",
        lambda text, candidate_tools: [
            {"tool": {"tool_id": "expected_weather"}, "score": 10.0},
            {"tool": {"tool_id": "wrong_planner_tool"}, "score": 2.0},
            {"tool": {"tool_id": "distractor_calendar"}, "score": 1.0},
        ],
    )

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_serial_candidate_pool_001",
            "query": "Get weather for Paris",
            "candidate_tools": [
                {"tool_id": "wrong_planner_tool", "description": "Wrong planner choice"},
                {"tool_id": "expected_weather", "description": "Get weather by city"},
                {"tool_id": "distractor_calendar", "description": "Calendar lookup"},
            ],
            "expected_call_structure": {
                "pattern": "serial",
                "calls": [{"tool_name": "expected_weather", "arguments": {}}],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "non_live",
                "bfcl_call_pattern": "serial",
            },
        },
        mode="planner",
    )

    assert len(workflow.execution_plan) == 1
    assert workflow.execution_plan[0].tool_id == "expected_weather"
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["prepared_function_count"] == 3
    assert diagnostics["runtime_candidate_count"] == 3
    assert diagnostics["candidate_pool_preserved"] is True


def test_build_workflow_from_task_bfcl_parallel_preserves_candidate_pool_per_clause(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_candidate_pool", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    def fake_rank(text, candidate_tools):
        top = "weather_paris" if "Paris" in text else "weather_berlin"
        order = [top, "weather_paris" if top != "weather_paris" else "weather_berlin", "distractor_calendar"]
        return [{"tool": {"tool_id": tool_id}, "score": 10.0 - idx} for idx, tool_id in enumerate(order)]

    monkeypatch.setattr(module, "rank_candidate_tools", fake_rank)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_parallel_candidate_pool_001",
            "query": "Get weather for Paris and also Get weather for Berlin",
            "candidate_tools": [
                {"tool_id": "weather_paris", "description": "Get Paris weather"},
                {"tool_id": "weather_berlin", "description": "Get Berlin weather"},
                {"tool_id": "distractor_calendar", "description": "Calendar lookup"},
            ],
            "expected_call_structure": {
                "pattern": "parallel",
                "calls": [
                    {"tool_name": "weather_paris", "arguments": {}},
                    {"tool_name": "weather_berlin", "arguments": {}},
                ],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "non_live",
                "bfcl_call_pattern": "parallel",
            },
        },
        mode="planner",
    )

    assert [step.tool_id for step in workflow.execution_plan] == ["weather_paris", "weather_berlin"]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"]
    assert len(diagnostics) == 2
    assert all(item["prepared_function_count"] == 3 for item in diagnostics)
    assert all(item["runtime_candidate_count"] == 3 for item in diagnostics)
    assert all(item["candidate_pool_preserved"] is True for item in diagnostics)
    assert all(item["planner_narrowing_applied"] is False for item in diagnostics)


def test_build_workflow_from_task_bfcl_parallel_single_tool_emits_one_step_per_clause() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_shape", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_parallel_shape_001",
            "query": "Could you tell me the current weather conditions for Boston, MA and also for San Francisco?",
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Retrieves current weather conditions.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {
                            "location": {"type": "string"},
                            "unit": {"type": "string"},
                        },
                    },
                }
            ],
            "expected_call_structure": {
                "pattern": "parallel",
                "calls": [{"tool_name": "get_current_weather", "arguments": {}}],
            },
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live",
                "bfcl_call_pattern": "parallel",
            },
        },
        mode="planner",
    )

    assert [step.tool_id for step in workflow.execution_plan] == [
        "get_current_weather",
        "get_current_weather",
    ]
    assert [step.inputs for step in workflow.execution_plan] == [
        {"location": "Boston, MA"},
        {"location": "San Francisco"},
    ]
    assert len(workflow.metadata["bfcl_rerank_diagnostics"]) == 2
    assert "expected_call_count" not in json.dumps(workflow.metadata["bfcl_rerank_diagnostics"])


def test_build_workflow_from_task_bfcl_abstain_records_candidate_pool_exception() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_abstain_candidate_pool", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_irrelevance_abstain_candidate_pool_001",
            "query": "This asks for a ride but no function call is expected.",
            "candidate_tools": [
                {"tool_id": "call_uber", "description": "Requests an Uber ride."},
            ],
            "expected_call_structure": {"pattern": "serial", "calls": []},
            "metadata": {
                "benchmark": "bfcl",
                "bfcl_group": "live_irrelevance",
                "bfcl_call_pattern": "serial",
                "expected_call_structure": {"pattern": "serial", "calls": []},
            },
        },
        mode="planner",
    )

    assert workflow.metadata["bfcl_abstained"] is True
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["prepared_function_count"] == 1
    assert diagnostics["runtime_candidate_count"] == 0
    assert diagnostics["candidate_pool_preserved"] is False
    assert diagnostics["candidate_pool_exception"] == "bfcl_abstain"
    assert diagnostics["planner_narrowing_applied"] is False


def test_build_workflow_from_task_bfcl_live_serial_irrelevance_label_with_schema_top1_abstains() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_live_serial_force_call", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "irrelevance_live_serial_positive_schema_top1",
            "query": "Tell me the current weather in Boston, MA.",
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Gets current weather conditions for a location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "live", "bfcl_call_pattern": "serial"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata["bfcl_abstained"] is True
    assert workflow.execution_plan == []
    assert workflow.tool_bindings == []
    assert workflow.context.candidate_tools == []
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["abstain_policy_version"] == "bfcl_abstain_policy_v3"
    assert diagnostics["abstain_reason"] == "live_serial_irrelevance_no_call"
    assert diagnostics["live_serial_irrelevance_no_call_abstain"] is True
    assert diagnostics["operation_cues_present"] is True
    assert diagnostics["schema_top_tool_id"] == "get_current_weather"
    assert diagnostics["explicit_no_call_signal"] is False
    assert diagnostics["candidate_pool_exception"] == "bfcl_abstain"
    assert "expected_call_count" not in json.dumps(diagnostics)
    assert "official_failure_bucket" not in json.dumps(diagnostics)
    assert "expected_function" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_live_serial_ideal_zero_without_irrelevance_label_forces_call() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_live_serial_ideal_zero", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_serial_weather_positive_schema_top1",
            "query": "Tell me the current weather in Boston, MA.",
            "ideal_tool_calls": 0,
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Gets current weather conditions for a location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "live", "bfcl_call_pattern": "serial"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert [step.tool_id for step in workflow.execution_plan] == ["get_current_weather"]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["abstain_policy_version"] == "bfcl_abstain_policy_v3"
    assert diagnostics["abstain_reason"] == "not_applied"
    assert diagnostics["live_serial_irrelevance_no_call_abstain"] is False
    assert diagnostics["operation_cues_present"] is True
    assert diagnostics["schema_top_tool_id"] == "get_current_weather"
    assert diagnostics["candidate_pool_exception"] == ""
    assert "expected_call_count" not in json.dumps(diagnostics)
    assert "official_failure_bucket" not in json.dumps(diagnostics)
    assert "expected_function" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_non_live_serial_irrelevance_label_with_schema_top1_forces_call() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_non_live_serial_force_call", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "irrelevance_non_live_serial_positive_schema_top1",
            "query": "Calculate the body mass index for height 1.8 meters and weight 75 kilograms.",
            "candidate_tools": [
                {
                    "tool_id": "determine_body_mass_index",
                    "description": "Calculate body mass index from height and weight.",
                    "parameters": {
                        "type": "dict",
                        "required": ["height", "weight"],
                        "properties": {"height": {"type": "number"}, "weight": {"type": "number"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "serial"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert [step.tool_id for step in workflow.execution_plan] == ["determine_body_mass_index"]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["serial_positive_call_forced"] is True
    assert diagnostics["abstain_blocked_by_serial_schema_top1"] is True
    assert diagnostics["candidate_pool_exception"] == ""




def test_build_workflow_from_task_bfcl_serial_materialization_disables_preflight_for_partial_args(tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_materialization", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_serial_partial_materialization",
            "query": "Please call obscure_tool now.",
            "candidate_tools": [
                {
                    "tool_id": "obscure_tool",
                    "description": "Perform the requested obscure operation.",
                    "parameters": {
                        "type": "dict",
                        "required": ["foo", "bar"],
                        "properties": {"foo": {"type": "string"}, "bar": {"type": "string"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "serial"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert len(workflow.execution_plan) == 1
    step = workflow.execution_plan[0]
    assert step.tool_id == "obscure_tool"
    assert step.metadata["trace_tool_call_expected_by_bfcl_serial"] is True
    assert step.metadata["serial_selected_top1_materialized"] is True
    assert step.metadata["disable_schema_preflight"] is True
    assert step.metadata["serial_partial_call_emitted_due_to_missing_args"] is True
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["trace_tool_call_expected_by_bfcl_serial"] is True
    assert diagnostics["serial_selected_top1_materialized"] is True
    assert "expected_call_count" not in json.dumps(diagnostics)

    from toolclaw.execution.executor import SequentialExecutor

    trace_path = tmp_path / "trace.json"
    outcome = SequentialExecutor().run_until_blocked(
        workflow=workflow,
        run_id="bfcl_serial_partial_materialization",
        output_path=str(trace_path),
        backup_tool_map={},
    )
    assert outcome.blocked is False
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    tool_calls = [event for event in trace_payload["events"] if event.get("event_type") == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_id"] == "obscure_tool"

def test_build_workflow_from_task_bfcl_explicit_no_call_still_abstains() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_explicit_no_call", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_irrelevance_explicit_no_call",
            "query": "No function call is expected for this request.",
            "candidate_tools": [
                {"tool_id": "get_current_weather", "description": "Gets current weather conditions."}
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "live_irrelevance", "bfcl_call_pattern": "serial"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata["bfcl_abstained"] is True
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"][0]
    assert diagnostics["irrelevance_abstain_allowed"] is True
    assert diagnostics["explicit_no_call_signal"] is True
    assert diagnostics["candidate_pool_exception"] == "bfcl_abstain"


def test_build_workflow_from_task_bfcl_parallel_multiple_candidates_expands_best_schema_tool() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_multi_candidate", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_non_live_parallel_multi_candidate",
            "query": "Tell me the current weather for Boston, MA and also for San Francisco.",
            "candidate_tools": [
                {
                    "tool_id": "get_current_weather",
                    "description": "Gets current weather conditions for a location.",
                    "parameters": {
                        "type": "dict",
                        "required": ["location"],
                        "properties": {"location": {"type": "string"}},
                    },
                },
                {
                    "tool_id": "get_stock_price",
                    "description": "Gets a stock price for a ticker symbol.",
                    "parameters": {
                        "type": "dict",
                        "required": ["ticker"],
                        "properties": {"ticker": {"type": "string"}},
                    },
                },
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert workflow.metadata.get("bfcl_abstained") is not True
    assert [step.tool_id for step in workflow.execution_plan] == ["get_current_weather", "get_current_weather"]
    assert [step.inputs for step in workflow.execution_plan] == [
        {"location": "Boston, MA"},
        {"location": "San Francisco"},
    ]
    assert len(workflow.metadata["bfcl_rerank_diagnostics"]) == 2


def test_build_workflow_from_task_bfcl_non_live_parallel_numeric_ids_emit_per_id() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_numeric_ids", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_non_live_parallel_numeric_ids",
            "query": "Fetch record IDs 101, 202, and 303.",
            "candidate_tools": [
                {
                    "tool_id": "records.fetch",
                    "description": "Fetch a record by identifier.",
                    "parameters": {
                        "type": "dict",
                        "required": ["record_id"],
                        "properties": {"record_id": {"type": "integer", "description": "record identifier"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert [step.inputs for step in workflow.execution_plan] == [
        {"record_id": 101},
        {"record_id": 202},
        {"record_id": 303},
    ]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"]
    assert len(diagnostics) == 3
    assert all(item["parallel_materialization_policy_version"] == "bfcl_non_live_parallel_clause_materialization_v1" for item in diagnostics)
    assert all(item["parallel_argument_set_count"] == 3 for item in diagnostics)
    assert all(item["parallel_clause_materialized_count"] == 3 for item in diagnostics)
    assert "expected_call_count" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_non_live_parallel_emails_emit_per_email() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_emails", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_non_live_parallel_emails",
            "query": "Send the notification to alice@example.com and bob@example.com.",
            "candidate_tools": [
                {
                    "tool_id": "mailer.send",
                    "description": "Send an email notification.",
                    "parameters": {
                        "type": "dict",
                        "required": ["recipient_email"],
                        "properties": {"recipient_email": {"type": "string", "description": "recipient email address"}},
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert [step.inputs for step in workflow.execution_plan] == [
        {"recipient_email": "alice@example.com"},
        {"recipient_email": "bob@example.com"},
    ]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"]
    assert all(item["parallel_clause_drop_count"] == 0 for item in diagnostics)
    assert "official_failure" not in json.dumps(diagnostics)


def test_build_workflow_from_task_bfcl_non_live_parallel_partial_args_do_not_suppress_clauses(tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_partial", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_non_live_parallel_partial",
            "query": "Send the notification to alice@example.com and bob@example.com.",
            "candidate_tools": [
                {
                    "tool_id": "mailer.send",
                    "description": "Send an email notification.",
                    "parameters": {
                        "type": "dict",
                        "required": ["recipient_email", "subject"],
                        "properties": {
                            "recipient_email": {"type": "string", "description": "recipient email address"},
                            "subject": {"type": "string"},
                        },
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert len(workflow.execution_plan) == 2
    assert [step.inputs for step in workflow.execution_plan] == [
        {"recipient_email": "alice@example.com"},
        {"recipient_email": "bob@example.com"},
    ]
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"]
    assert all(item["parallel_argument_sets_extracted"] is True for item in diagnostics)
    assert all(item["parallel_collapsed_to_serial"] is False for item in diagnostics)
    assert all(item["parallel_partial_call_bypass_applied"] is True for item in diagnostics)
    assert all(item["trace_tool_call_expected_by_bfcl_parallel"] is True for item in diagnostics)
    assert all(
        item["parallel_preflight_bypass_policy_version"] == "bfcl_parallel_partial_call_materialization_v1"
        for item in diagnostics
    )
    assert "expected_call_count" not in json.dumps(diagnostics)

    assert all(step.metadata["trace_tool_call_expected_by_bfcl_parallel"] is True for step in workflow.execution_plan)
    assert all(step.metadata["disable_schema_preflight"] is True for step in workflow.execution_plan)
    assert all(step.metadata["parallel_partial_call_emitted_due_to_missing_args"] is True for step in workflow.execution_plan)
    assert all(
        step.metadata["parallel_preflight_bypass_policy_version"] == "bfcl_parallel_partial_call_materialization_v1"
        for step in workflow.execution_plan
    )

    from toolclaw.execution.executor import SequentialExecutor

    trace_path = tmp_path / "parallel_partial_trace.json"
    outcome = SequentialExecutor().run_until_blocked(
        workflow=workflow,
        run_id="bfcl_non_live_parallel_partial",
        output_path=str(trace_path),
        backup_tool_map={},
    )
    assert outcome.blocked is False
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    tool_calls = [event for event in trace_payload["events"] if event.get("event_type") == "tool_call"]
    assert len(tool_calls) == 2
    assert [event["tool_id"] for event in tool_calls] == ["mailer.send", "mailer.send"]


def test_build_workflow_from_task_bfcl_parallel_preflight_bypass_is_non_live_only() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_live_preflight", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_live_parallel_partial",
            "query": "Send the notification to alice@example.com and bob@example.com.",
            "candidate_tools": [
                {
                    "tool_id": "mailer.send",
                    "description": "Send an email notification.",
                    "parameters": {
                        "type": "dict",
                        "required": ["recipient_email", "subject"],
                        "properties": {
                            "recipient_email": {"type": "string", "description": "recipient email address"},
                            "subject": {"type": "string"},
                        },
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert len(workflow.execution_plan) == 2
    assert all("trace_tool_call_expected_by_bfcl_parallel" not in step.metadata for step in workflow.execution_plan)
    assert all(step.metadata.get("disable_schema_preflight") is not True for step in workflow.execution_plan)
    diagnostics = workflow.metadata["bfcl_rerank_diagnostics"]
    assert all(item.get("parallel_partial_call_bypass_applied") is False for item in diagnostics)
    assert all("parallel_preflight_bypass_policy_version" not in item for item in diagnostics)


def test_build_workflow_from_task_bfcl_non_live_parallel_single_extracted_does_not_bypass_preflight() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_parallel_single_preflight", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    module.extract_parallel_argument_sets = lambda _tool_id, _schema, _query: [{"recipient_email": "alice@example.com"}]

    workflow = module.build_workflow_from_task(
        {
            "task_id": "bfcl_non_live_parallel_single",
            "query": "Send the notification to alice@example.com and one unresolved recipient.",
            "candidate_tools": [
                {
                    "tool_id": "mailer.send",
                    "description": "Send an email notification.",
                    "parameters": {
                        "type": "dict",
                        "required": ["recipient_email", "subject"],
                        "properties": {
                            "recipient_email": {"type": "string", "description": "recipient email address"},
                            "subject": {"type": "string"},
                        },
                    },
                }
            ],
            "metadata": {"benchmark": "bfcl", "bfcl_group": "non_live", "bfcl_call_pattern": "parallel"},
        },
        mode="planner",
        spec=module.SYSTEM_SPECS["fc_grounding_recovery"],
    )

    assert len(workflow.execution_plan) == 1
    metadata = workflow.execution_plan[0].metadata
    assert metadata["parallel_argument_sets_extracted"] is True
    assert metadata["parallel_argument_set_count"] == 1
    assert metadata["parallel_collapsed_to_serial"] is True
    assert metadata["parallel_partial_call_bypass_applied"] is False
    assert "trace_tool_call_expected_by_bfcl_parallel" not in metadata
    assert "parallel_preflight_bypass_policy_version" not in metadata
    assert metadata.get("disable_schema_preflight") is not True
    assert "expected_call_count" not in json.dumps(metadata)


def test_bfcl_serial_required_grounder_fills_runtime_visible_required_args() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="book_trip",
        description="Book a trip",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["city", "travel_class", "days", "include_breakfast", "guests"],
                "properties": {
                    "city": {"type": "string"},
                    "travel_class": {"type": "string", "enum": ["economy", "business"]},
                    "days": {"type": "integer"},
                    "include_breakfast": {"type": "boolean"},
                    "guests": {"type": "array", "items": {"type": "string"}},
                },
            }
        },
    )
    text = 'Book "Paris" in business for 3 days, include breakfast, guests are "Alice" and "Bob".'

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, text, {})

    assert inputs["city"] == "Paris"
    assert inputs["travel_class"] == "business"
    assert inputs["days"] == 3
    assert inputs["include_breakfast"] is True
    assert inputs["guests"] == ["Alice", "Bob"]
    assert diagnostics["serial_required_grounding_attempted"] is True
    assert diagnostics["serial_required_grounding_policy_version"] == "bfcl_serial_required_grounding_v2"
    assert diagnostics["alias_match_by_arg"]["guests"] in {"person", "list"}
    assert diagnostics["consumed_candidate_span_by_arg"]["city"] != diagnostics["consumed_candidate_span_by_arg"]["guests"]
    assert set(diagnostics["grounded_required_args"]) == {"city", "travel_class", "days", "include_breakfast", "guests"}
    assert diagnostics["ungrounded_required_args"] == []


def test_bfcl_serial_required_grounder_disambiguates_origin_destination_and_email() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder_aliases", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="send_route",
        description="Send route details",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["origin", "destination", "recipient_email"],
                "properties": {
                    "origin": {"type": "string", "description": "starting city"},
                    "destination": {"type": "string", "description": "target city"},
                    "recipient_email": {"type": "string", "description": "email contact"},
                },
            }
        },
    )
    text = "Send the route from Boston to Seattle to ops@example.com."

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, text, {})

    assert inputs["origin"] == "Boston"
    assert inputs["destination"] == "Seattle"
    assert inputs["recipient_email"] == "ops@example.com"
    assert diagnostics["alias_match_by_arg"]["origin"] == "origin"
    assert diagnostics["alias_match_by_arg"]["destination"] == "destination"
    assert diagnostics["alias_match_by_arg"]["recipient_email"] == "email"


def test_bfcl_serial_required_grounder_prioritizes_enum_over_generic_quotes() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder_enum", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="ticket",
        description="Create ticket",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["priority", "title"],
                "properties": {
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "title": {"type": "string"},
                },
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, 'Create a high priority ticket titled "Printer jam".', {})

    assert inputs["priority"] == "high"
    assert inputs["title"] == "Printer jam"
    assert diagnostics["grounding_source_by_arg"]["priority"] == "enum_exact_mention"


def test_bfcl_schema_driven_weather_grounder_extracts_location_unit_and_date() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_schema_weather_grounder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    weather_tool = module.ToolSpec(
        tool_id="weather_lookup",
        description="Retrieves weather data for a city.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string", "description": "Weather location in City, State format."},
                    "unit": {"type": "string", "description": "Temperature unit", "enum": ["celsius", "fahrenheit"]},
                },
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        weather_tool,
        "Tell me the current weather in Boston, MA in Fahrenheit.",
        {},
    )

    assert inputs["location"] == "Boston, MA"
    assert inputs["unit"] == "fahrenheit"
    assert diagnostics["schema_driven_weather_grounding_policy_version"] == "bfcl_schema_driven_location_unit_date_v1"
    assert diagnostics["location_like_arg_grounded_by_arg"]["location"] == "schema_location_phrase"
    assert diagnostics["unit_enum_grounded_by_arg"]["unit"] == "schema_unit_enum_mention"

    dated_tool = module.ToolSpec(
        tool_id="any_weather_tool",
        description="Retrieves weather data for a city on a date.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["city"],
                "properties": {
                    "city": {"type": "string", "description": "The name of the city for weather data."},
                    "date": {"type": "string", "description": "The date for weather data in YYYY-MM-DD format."},
                },
            }
        },
    )
    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        dated_tool,
        "Could you tell me the weather conditions in Tomales, CA on the date 2023-03-11?",
        {},
    )

    assert inputs["city"] == "Tomales, CA"
    assert inputs["date"] == "2023-03-11"
    assert diagnostics["date_like_arg_grounded_by_arg"]["date"] == "schema_explicit_date"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        dated_tool,
        "What's the weather going to be like in New York tomorrow? today is 2023.10.1",
        {},
    )
    assert inputs["city"] == "New York"
    assert inputs["date"] == "2023-10-02"


def test_bfcl_schema_driven_weather_grounder_blocks_no_evidence_and_invalid_unit() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_schema_weather_grounder_blocks", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="weather_lookup",
        description="Retrieves weather data for a city.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["city"],
                "properties": {
                    "city": {"type": "string", "description": "The name of the city for weather data."},
                    "date": {"type": "string", "description": "The date for weather data in YYYY-MM-DD format."},
                    "unit": {"type": "string", "description": "Temperature unit", "enum": ["celsius", "fahrenheit"]},
                },
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, "Look up the weather.", {})

    assert "city" not in inputs
    assert "date" not in inputs
    assert diagnostics["grounding_blocked_no_runtime_evidence_by_arg"]["city"] == "no_runtime_location_evidence"
    assert diagnostics["grounding_blocked_no_runtime_evidence_by_arg"]["date"] == "no_runtime_date_evidence"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        "Could you tell me the current weather conditions in Shanghai, using the metric system?",
        {"city": "Shanghai", "unit": "metric"},
    )

    assert inputs["city"] == "Shanghai"
    assert "unit" not in inputs
    assert diagnostics["unit_enum_grounded_by_arg"]["unit"] == "removed_value_not_allowed_by_schema_enum"
    assert "expected_call_count" not in json.dumps(diagnostics)
    assert "official_failure_bucket" not in json.dumps(diagnostics)
    assert "expected_function" not in json.dumps(diagnostics)



def test_bfcl_schema_driven_command_grounder_extracts_high_evidence_commands() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_schema_command_grounder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    command_tool = module.ToolSpec(
        tool_id="shell_executor",
        description="Execute terminal command in a shell.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["command"],
                "properties": {
                    "command": {"type": "string", "description": "The terminal command to execute."},
                },
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(command_tool, "Run `ls -la /tmp` now.", {})
    assert inputs["command"] == "ls -la /tmp"
    assert diagnostics["schema_driven_command_grounding_policy_version"] == "bfcl_schema_driven_command_v1"
    assert diagnostics["command_like_arg_grounded_by_arg"]["command"] == "schema_backtick_command_span"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        command_tool,
        'Please execute the command "grep foo file.txt".',
        {},
    )
    assert inputs["command"] == "grep foo file.txt"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        command_tool,
        "open huggingface using the start command and through the link: https://huggingface.co",
        {"command": "and"},
    )
    assert inputs["command"] == "start https://huggingface.co"
    assert diagnostics["command_grounding_reason_by_arg"]["command"] == "start_command_url"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        command_tool,
        "close firefox using taskkill command",
        {},
    )
    assert inputs["command"] == "taskkill /F /IM firefox.exe"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        command_tool,
        "remove the timer.exe that i have been set earlier using the taskkill command",
        {"command": True},
    )
    assert inputs["command"] == "taskkill /F /IM timer.exe"

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        command_tool,
        "say hi using the echo command",
        {},
    )
    assert inputs["command"] == "echo hi"


def test_bfcl_schema_driven_command_grounder_blocks_without_schema_or_evidence() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_schema_command_grounder_blocks", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    non_command_tool = module.ToolSpec(
        tool_id="note_writer",
        description="Create a text note.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["message"],
                "properties": {
                    "message": {"type": "string", "description": "Text to write."},
                },
            }
        },
    )
    inputs, diagnostics = module._bfcl_ground_serial_required_args(non_command_tool, "Run `ls -la` now.", {})
    assert inputs.get("message") != "ls -la"
    assert diagnostics["schema_driven_command_grounding_policy_version"] == "bfcl_schema_driven_command_v1"
    assert diagnostics["command_like_arg_grounded_by_arg"] == {}

    command_tool = module.ToolSpec(
        tool_id="shell_executor",
        description="Execute terminal command in a shell.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["command"],
                "properties": {
                    "command": {"type": "string", "description": "The terminal command to execute."},
                },
            }
        },
    )
    inputs, diagnostics = module._bfcl_ground_serial_required_args(command_tool, "Please do the thing.", {})
    assert "command" not in inputs
    assert diagnostics["command_grounding_blocked_by_arg"]["command"] == "no_runtime_command_evidence"

    list_command_tool = module.ToolSpec(
        tool_id="cli_runner",
        description="Run CLI command arguments.",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["cmd"],
                "properties": {
                    "cmd": {"type": "array", "description": "CLI command to execute."},
                },
            }
        },
    )
    inputs, diagnostics = module._bfcl_ground_serial_required_args(list_command_tool, "Run `python -m pytest -q`.", {})
    assert inputs["cmd"] == ["python", "-m", "pytest", "-q"]
    assert "expected_call_count" not in json.dumps(diagnostics)
    assert "official_failure_bucket" not in json.dumps(diagnostics)
    assert "expected_function" not in json.dumps(diagnostics)


def test_bfcl_serial_required_grounder_avoids_scalar_span_reuse() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder_reuse", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="profile",
        description="Create profile",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["name", "nickname"],
                "properties": {
                    "name": {"type": "string", "description": "person name"},
                    "nickname": {"type": "string", "description": "person nickname"},
                },
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, 'Create a profile for name "Alice".', {})

    assert inputs["name"] == "Alice"
    assert "nickname" not in inputs
    assert diagnostics["ungrounded_required_args"] == ["nickname"]
    assert diagnostics["assignment_reason_by_arg"]["nickname"] in {
        "no_viable_candidate",
        "consumed_span_penalty",
        "low_confidence_assignment_blocked",
    }


def test_bfcl_serial_required_grounder_does_not_invent_without_query_cue() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder_negative", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="weather",
        description="Weather lookup",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["location"],
                "properties": {"location": {"type": "string"}},
            }
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, "Please help me.", {})

    assert inputs == {}
    assert diagnostics["grounded_required_args"] == []
    assert diagnostics["ungrounded_required_args"] == ["location"]
    assert diagnostics["grounding_source_by_arg"]["location"] == "unresolved"
    assert diagnostics["grounding_confidence_by_arg"]["location"] == 0.0


def test_bfcl_serial_grounding_metadata_is_runtime_safe_and_does_not_suppress_call() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_bfcl_serial_grounder_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    tool = module.ToolSpec(
        tool_id="weather_lookup",
        description="Look up weather by location",
        metadata={
            "parameters": {
                "type": "dict",
                "required": ["location"],
                "properties": {"location": {"type": "string"}},
            }
        },
    )
    task = {"query": "Look up the weather.", "metadata": {"bfcl_call_pattern": "serial", "bfcl_group": "non_live"}}

    specs = module._bfcl_seed_specs(task, [tool], "Look up the weather.")

    assert len(specs) == 1
    assert specs[0]["tool"].tool_id == "weather_lookup"
    diagnostics = specs[0]["selection_diagnostics"]
    assert diagnostics["trace_tool_call_expected_by_bfcl_serial"] is True
    assert diagnostics["serial_required_grounding_attempted"] is True
    assert diagnostics["ungrounded_required_args"] == ["location"]
    encoded = json.dumps(diagnostics)
    for forbidden in ("expected_function", "expected_call_count", "gold_tool", "official_failure_bucket"):
        assert forbidden not in encoded


def test_strict_overlay_system_specs_preserve_atomic_specs() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_strict_specs", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.SYSTEM_SPECS["a2_planner"].workflow_mode == "planner"
    assert module.SYSTEM_SPECS["s2_planner_overlay"].workflow_mode == "planner_overlay_admitted"
    assert module.SYSTEM_SPECS["s2_planner_overlay"].allow_repair is True
    assert module.SYSTEM_SPECS["s2_planner_overlay"].allow_fallback is True
    assert module.SYSTEM_SPECS["s2_planner_overlay"].allow_suffix_replan is True

    s3 = module.SYSTEM_SPECS["s3_interaction_overlay"]
    assert s3.workflow_mode == "planner_overlay_admitted"
    assert s3.execution_mode == "interaction"
    assert s3.allow_repair is True
    assert s3.allow_fallback is True
    assert s3.allow_suffix_replan is True
    assert s3.use_reuse is False

    s4 = module.SYSTEM_SPECS["s4_reuse_overlay"]
    assert s4.workflow_mode == "planner_overlay_admitted"
    assert s4.execution_mode == "interaction"
    assert s4.use_reuse is False
    assert s4.compile_on_success is False
    assert s4.allow_suffix_replan is True


def test_execute_system_strict_interaction_uses_overlay_seed(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_strict_interaction_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["benchmark"] = "toolsandbox"
    build_calls: list[str] = []
    shell_calls: list[dict[str, object]] = []

    def fake_build_workflow_from_task(task, mode="demo", spec=None, **kwargs):
        build_calls.append(mode)
        return workflow

    class _FakeShell:
        def run(self, **kwargs):
            shell_calls.append(kwargs)
            assert kwargs["seed_workflow"] is workflow
            Path(kwargs["output_path"]).write_text(
                json.dumps({"events": [], "metrics": {"success": True}, "metadata": {}}),
                encoding="utf-8",
            )
            return SimpleNamespace(workflow=workflow)

    monkeypatch.setattr(module, "build_workflow_from_task", fake_build_workflow_from_task)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: _FakeShell())
    monkeypatch.setattr(
        module,
        "row_from_trace",
        lambda **kwargs: SimpleNamespace(system=kwargs["system"], task_id=kwargs["task"]["task_id"]),
    )

    row = module.execute_system(
        spec=module.SYSTEM_SPECS["s3_interaction_overlay"],
        task={"task_id": "strict_interaction_seed_001", "query": "check weather"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=SimpleNamespace(executor=SimpleNamespace(run_until_blocked=lambda **kwargs: None)),
    )

    assert build_calls == ["planner_overlay_admitted"]
    assert shell_calls and shell_calls[0]["use_reuse"] is False
    assert row.system == "s3_interaction_overlay"


def test_execute_system_strict_reuse_overlay_keeps_shadow_no_execute_path(monkeypatch, tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_strict_reuse_seed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["benchmark"] = "toolsandbox"
    shell_calls: list[dict[str, object]] = []

    class _FakeShell:
        def run(self, **kwargs):
            shell_calls.append(kwargs)
            Path(kwargs["output_path"]).write_text(
                json.dumps({"events": [], "metrics": {"success": True}, "metadata": {}}),
                encoding="utf-8",
            )
            return SimpleNamespace(workflow=workflow)

    monkeypatch.setattr(module, "build_workflow_from_task", lambda *args, **kwargs: workflow)
    monkeypatch.setattr(module, "build_shell", lambda runtime, task: _FakeShell())
    monkeypatch.setattr(
        module,
        "row_from_trace",
        lambda **kwargs: {"system": kwargs["system"], "task_id": kwargs["task"]["task_id"]},
    )

    runtime = SimpleNamespace(
        executor=SimpleNamespace(run_until_blocked=lambda **kwargs: None),
    )
    row = module.execute_system(
        spec=module.SYSTEM_SPECS["s4_reuse_overlay"],
        task={"task_id": "strict_reuse_seed_001", "query": "retrieve and write"},
        task_index=1,
        traces_dir=tmp_path,
        runtime=runtime,
    )

    assert shell_calls and shell_calls[0]["use_reuse"] is False
    assert shell_calls[0]["seed_workflow"] is workflow
    assert row["system"] == "s4_reuse_overlay"


def test_build_workflow_from_task_strict_reuse_overlay_is_exact_only() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_s4_exact_guard", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = module.build_workflow_from_task(
        {
            "task_id": "toolsandbox_exact_reuse_guard_001",
            "scenario": "single_tool",
            "query": "Search my messages for the oldest text.",
            "tool_allow_list": ["end_conversation", "search_messages"],
            "candidate_tools": [
                {"tool_id": "end_conversation", "description": "End the conversation."},
                {"tool_id": "search_messages", "description": "Search text messages."},
            ],
            "metadata": {
                "benchmark": "toolsandbox",
                "toolsandbox_categories": ["single_tool"],
                "reuse_family_id": "toolsandbox_exact_reuse_guard",
            },
        },
        mode="planner_overlay_admitted",
        spec=module.SYSTEM_SPECS["s4_reuse_overlay"],
    )

    assert workflow.metadata["reuse_scope"] == "exact"
    assert workflow.metadata["reuse_allowed_modes"] == ["exact_reuse"]
    assert workflow.metadata["reuse_require_source_family_match"] is True
    assert workflow.metadata["reuse_claim_scope"] == "exact_match_cost_no_regression"
    assert workflow.metadata["reuse_overlay_runtime_mode"] == "shadow_no_execute"


def test_reuse_rollback_decision_falls_back_on_execution_failure() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_reuse_failure_rollback", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    workflow = Workflow.demo()
    workflow.metadata["reusable_context"] = {
        "reuse_mode": "exact_reuse",
        "resolved_asset_ids": ["asset_1"],
        "selected_match": {"asset_id": "asset_1", "reuse_mode": "exact_reuse"},
    }
    outcome = SimpleNamespace(workflow=workflow, success=False)

    rollback = module._reuse_rollback_decision(outcome, {"metrics": {"repair_actions": 0}, "events": []})

    assert rollback["reason"] == "reuse_path_execution_failure"
    assert rollback["fallback_behavior"] == "a3_interaction"
    assert rollback["selected_match"]["asset_id"] == "asset_1"



def test_strict_interaction_prefixes_force_probe_for_must_interact_success() -> None:
    from types import SimpleNamespace
    from toolclaw.interaction.irc import InteractionShell
    from toolclaw.schemas.workflow import Workflow

    workflow = Workflow.demo()
    workflow.metadata["toolsandbox_categories"] = ["multiple_user_turn"]
    outcome = SimpleNamespace(workflow=workflow, success=True, blocked=False)

    assert InteractionShell._should_force_interaction_probe(outcome=outcome, run_id="s3_task") is True
    assert InteractionShell._should_force_interaction_probe(outcome=outcome, run_id="s4_task") is True
    assert InteractionShell._should_force_interaction_probe(outcome=outcome, run_id="s2_task") is False


def test_strict_interaction_probe_is_not_for_non_interaction_tasks() -> None:
    from types import SimpleNamespace
    from toolclaw.interaction.irc import InteractionShell
    from toolclaw.schemas.workflow import Workflow

    workflow = Workflow.demo()
    workflow.metadata["toolsandbox_categories"] = ["single_tool"]
    outcome = SimpleNamespace(workflow=workflow, success=True, blocked=False)

    assert InteractionShell._should_force_interaction_probe(outcome=outcome, run_id="s3_task") is False
    assert InteractionShell._should_force_interaction_probe(outcome=outcome, run_id="s4_task") is False


def test_toolsandbox_visible_followup_turns_only_apply_to_interaction_specs() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_module_visible_followups", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)

    task = {
        "task_id": "toolsandbox_visible_followup_001",
        "query": "Send a message to the phone number I will provide.",
        "messages": [
            {"sender": "user", "content": "Send a message to the phone number I will provide."},
            {"sender": "assistant", "content": "What phone number and message should I use?"},
            {"sender": "user", "content": "Use +1 555-0100 saying: hello from visible turn"},
        ],
        "metadata": {
            "benchmark": "toolsandbox",
            "toolsandbox_categories": ["MULTIPLE_USER_TURN", "INSUFFICIENT_INFORMATION"],
        },
    }

    s2_task = module._apply_toolsandbox_visible_interaction_continuation(
        task,
        spec=module.SYSTEM_SPECS["s2_planner_overlay"],
    )
    s3_task = module._apply_toolsandbox_visible_interaction_continuation(
        task,
        spec=module.SYSTEM_SPECS["s3_interaction_overlay"],
    )

    assert "toolsandbox_pre_execution_interactions" not in s2_task
    assert s3_task["metadata"]["toolsandbox_visible_interaction_continuation"] is True
    assert "User clarification 1" in s3_task["query"]
    interaction = s3_task["toolsandbox_pre_execution_interactions"][0]
    assert interaction["payload"]["recipient_phone_number"] == "+15550100"
    assert interaction["payload"]["content"] == "hello from visible turn"


def test_interaction_shell_counts_visible_pre_execution_interaction_as_repair(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from toolclaw.execution.executor import ExecutionOutcome
    from toolclaw.interaction.irc import InteractionShell
    from toolclaw.main import ToolClawRuntime
    from toolclaw.schemas.workflow import Workflow

    workflow = Workflow.demo()
    workflow.metadata["toolsandbox_pre_execution_interactions"] = [
        {
            "turn_index": 1,
            "source_message_index": 2,
            "question": "What phone number and message should I use?",
            "reply_text": "Use +1 555-0100 saying: hello from visible turn",
            "payload": {"recipient_phone_number": "+15550100", "content": "hello from visible turn"},
        }
    ]
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "metadata": {},
                "metrics": {"success": True, "user_queries": 0},
                "events": [],
            }
        ),
        encoding="utf-8",
    )
    outcome = ExecutionOutcome(
        run_id="s3_visible",
        workflow=workflow,
        success=True,
        blocked=False,
        pending_interaction=None,
        final_state={},
        trace_path=str(trace_path),
    )
    runtime = SimpleNamespace(
        run_workflow=lambda **kwargs: outcome,
        repair_updater=None,
    )
    shell = InteractionShell(runtime=runtime)  # type: ignore[arg-type]
    request = SimpleNamespace(task=workflow.task, context=workflow.context, policy=workflow.policy)

    shell.run(request=request, run_id="s3_visible", output_path=str(trace_path), seed_workflow=workflow)
    payload = json.loads(trace_path.read_text(encoding="utf-8"))

    assert payload["metadata"]["pre_execution_interaction_count"] == 1
    assert payload["metrics"]["user_queries"] == 1
    query_event = next(event for event in payload["events"] if event["event_type"] == "user_query")
    reply_event = next(event for event in payload["events"] if event["event_type"] == "user_reply")
    assert query_event["metadata"]["query_metadata"]["pre_execution_interaction"] is True
    assert "interaction_probe" not in query_event["metadata"]["query_metadata"]
    assert reply_event["metadata"]["reply_metadata"]["pre_execution_interaction"] is True
