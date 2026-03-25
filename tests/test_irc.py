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
    assert "retrieved_info" not in resume_patch.state_updates
    workflow.execution_plan[1].inputs.pop("force_environment_failure", None)

    resumed = executor.resume_from_patch(
        workflow=workflow,
        run_id="run_resumed_002",
        output_path=str(tmp_path / "resumed_trace.json"),
        resume_patch=resume_patch,
    )

    assert resumed.success is True
    assert resumed.blocked is False


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
