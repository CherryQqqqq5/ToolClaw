from pathlib import Path

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.schemas.workflow import Workflow


def test_executor_blocks_on_ask_user_and_returns_pending_interaction(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    outcome = SequentialExecutor().run_until_blocked(
        workflow=workflow,
        run_id="run_blocked_001",
        output_path=str(tmp_path / "blocked_trace.json"),
        backup_tool_map={},
    )

    assert outcome.blocked is True
    assert outcome.pending_interaction is not None


def test_repair_updater_ingests_reply_and_resumes_workflow(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    executor = SequentialExecutor()
    blocked = executor.run_until_blocked(
        workflow=workflow,
        run_id="run_blocked_002",
        output_path=str(tmp_path / "blocked_trace_2.json"),
        backup_tool_map={},
    )
    assert blocked.pending_interaction is not None

    updater = RepairUpdater()
    request = updater.build_query(workflow, blocked.pending_interaction.repair, blocked.final_state)
    reply = UserSimulator(SimulatedPolicy(missing_arg_values={"target_path": "outputs/reports/recovered.txt"})).reply(request)
    assert updater.validate_reply(request, reply)

    resume_patch = updater.ingest_reply(workflow, blocked.pending_interaction.repair, reply, blocked.final_state)
    assert resume_patch.base_state["retrieved_info"] == blocked.final_state["retrieved_info"]
    assert "retrieved_info" not in resume_patch.state_updates
    assert resume_patch.state_updates["target_path"] == "outputs/reports/recovered.txt"
    assert resume_patch.state_updates["force_environment_failure"] is False
    workflow.execution_plan[1].inputs.pop("force_environment_failure", None)

    resumed = executor.resume_from_patch(
        workflow=workflow,
        run_id="run_resumed_002",
        output_path=str(tmp_path / "resumed_trace.json"),
        resume_patch=resume_patch,
    )

    assert resumed.success is True
    assert resumed.blocked is False
    assert resumed.final_state["retrieved_info"] == blocked.final_state["retrieved_info"]


def test_repair_updater_accepts_fallback_path_and_tool_switch_reply() -> None:
    workflow = Workflow.demo()
    updater = RepairUpdater()
    repair = __import__("toolclaw.execution.recovery", fromlist=["RecoveryEngine"]).RecoveryEngine()._repair_environment_failure(
        __import__("toolclaw.schemas.error", fromlist=["ToolClawError", "ErrorCategory", "ErrorEvidence", "StateContext", "Recoverability", "ErrorSeverity", "ErrorStage"]).ToolClawError(
            error_id="err_test_env",
            run_id="run_test_env",
            workflow_id=workflow.workflow_id,
            step_id="step_02",
            category=__import__("toolclaw.schemas.error", fromlist=["ErrorCategory"]).ErrorCategory.ENVIRONMENT_FAILURE,
            subtype="tool_execution_error",
            severity=__import__("toolclaw.schemas.error", fromlist=["ErrorSeverity"]).ErrorSeverity.MEDIUM,
            stage=__import__("toolclaw.schemas.error", fromlist=["ErrorStage"]).ErrorStage.EXECUTION,
            symptoms=["environment unavailable for write operation"],
            evidence=__import__("toolclaw.schemas.error", fromlist=["ErrorEvidence"]).ErrorEvidence(tool_id="write_tool"),
            root_cause_hypothesis=["tool invocation failed"],
            state_context=__import__("toolclaw.schemas.error", fromlist=["StateContext"]).StateContext(active_step_id="step_02"),
            recoverability=__import__("toolclaw.schemas.error", fromlist=["Recoverability"]).Recoverability(recoverable=True),
            failtax_label="environment_failure",
        )
    )
    repair.metadata["backup_tool_id"] = "backup_write_tool"
    reply = __import__("toolclaw.interaction.repair_updater", fromlist=["UserReply"]).UserReply(
        interaction_id=f"int_{repair.repair_id}",
        payload={
            "use_backup_tool": True,
            "fallback_execution_path": "outputs/reports/fallback.txt",
            "input_patch": {"target_path": "outputs/reports/override.txt"},
        },
    )

    resume_patch = updater.ingest_reply(workflow, repair, reply, {"retrieved_info": "summary"})
    assert resume_patch.binding_patch["tool_id"] == "backup_write_tool"
    assert resume_patch.state_updates["target_path"] == "outputs/reports/override.txt"
    assert resume_patch.state_updates["force_environment_failure"] is False


def test_user_reject_reply_causes_safe_stop(tmp_path: Path) -> None:
    workflow = Workflow.demo()
    workflow.execution_plan[1].inputs["force_environment_failure"] = True

    executor = SequentialExecutor()
    blocked = executor.run_until_blocked(
        workflow=workflow,
        run_id="run_blocked_003",
        output_path=str(tmp_path / "blocked_trace_3.json"),
        backup_tool_map={},
    )
    assert blocked.pending_interaction is not None

    updater = RepairUpdater()
    request = updater.build_query(workflow, blocked.pending_interaction.repair, blocked.final_state)
    reject_reply = UserSimulator(SimulatedPolicy(mode="abortive")).reply(request)

    assert updater.validate_reply(request, reject_reply) is False
