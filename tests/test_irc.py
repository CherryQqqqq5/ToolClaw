from pathlib import Path
import time

from toolclaw.execution.executor import SequentialExecutor
from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.query_policy import QueryPolicy
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.uncertainty_detector import UncertaintyReport
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.main import ToolClawRuntime
from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.workflow import Workflow
from toolclaw.interaction.repair_updater import InteractionRequest


class SlowReplyProvider:
    def __init__(self, delay_s: float) -> None:
        self.delay_s = delay_s

    def reply(self, request: InteractionRequest):
        time.sleep(self.delay_s)
        return UserSimulator(SimulatedPolicy()).reply(request)


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

    assert reject_reply.status == "deny"
    assert updater.validate_reply(request, reject_reply) is True


def test_query_policy_uses_one_shot_target_path_patch_schema() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="missing_info",
            confidence=0.9,
            metadata={"missing_input_keys": ["target_path"], "error_category": "binding_failure"},
        )
    )

    assert plan.ask is True
    assert plan.question_type == "target_path_patch"
    assert plan.response_schema["required"] == ["target_path"]
    assert plan.patch_targets == {"target_path": "step.inputs.target_path"}


def test_repair_updater_does_not_default_branch_choice_patch_without_branch_options() -> None:
    workflow = Workflow.demo()
    repair = __import__("toolclaw.schemas.repair", fromlist=["Repair"]).Repair.demo()
    repair.repair_type = __import__("toolclaw.schemas.repair", fromlist=["RepairType"]).RepairType.REROUTE_BRANCH
    repair.metadata["branch_options"] = []

    request = RepairUpdater().build_query(workflow, repair, {})

    assert request.metadata["branch_options"] == []
    assert "branch_choice" not in request.metadata["patch_targets"]


def test_interaction_shell_aborts_after_repeated_same_failure_signature(tmp_path: Path) -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            max_turns=3,
            simulator_policy=SimulatedPolicy(constraint_overrides={"clear_failure_flag": False}),
        ),
    )

    demo = Workflow.demo()
    overrides = {
        "steps": {
            "step_01": {"inputs": dict(demo.execution_plan[0].inputs), "tool_id": demo.execution_plan[0].tool_id},
            "step_02": {
                "inputs": {**demo.execution_plan[1].inputs, "force_environment_failure": True},
                "tool_id": demo.execution_plan[1].tool_id,
            },
        }
    }
    request = PlanningRequest(
        task=demo.task,
        context=demo.context,
        policy=demo.policy,
        workflow_overrides=overrides,
    )

    outcome = shell.run(
        request=request,
        run_id="run_repeat_abort_001",
        output_path=str(tmp_path / "repeat_abort_trace.json"),
        backup_tool_map={},
        use_reuse=False,
        compile_on_success=False,
    )

    assert outcome.success is False
    assert outcome.metadata["stopped_reason"] == "repeat_failure_abort"


def test_interaction_shell_treats_abortive_reply_as_safe_abort_success(tmp_path: Path) -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            max_turns=2,
            simulator_policy=SimulatedPolicy(mode="abortive"),
        ),
    )

    demo = Workflow.demo()
    demo.task.constraints.requires_user_approval = True
    request = PlanningRequest(task=demo.task, context=demo.context, policy=demo.policy)
    outcome = shell.run(
        request=request,
        run_id="run_safe_abort_001",
        output_path=str(tmp_path / "safe_abort_trace.json"),
    )

    assert outcome.success is True
    assert outcome.metadata["stopped_reason"] == "safe_abort_success"


def test_user_simulator_prefers_tool_id_for_tool_switch_schema() -> None:
    request = InteractionRequest(
        interaction_id="int_tool_switch_001",
        question="Provide replacement tool_id",
        expected_answer_type="tool_switch",
        allowed_response_schema={
            "type": "object",
            "properties": {
                "tool_id": {
                    "type": "string",
                    "enum": ["get_current_timestamp", "timestamp_diff"],
                }
            },
            "required": ["tool_id"],
            "additionalProperties": False,
        },
        metadata={
            "patch_targets": {"tool_id": "binding.primary_tool"},
            "clear_failure_flag_recommended": True,
        },
    )
    reply = UserSimulator(SimulatedPolicy()).reply(request)
    assert reply.accepted is True
    assert reply.payload.get("tool_id") == "get_current_timestamp"
    assert "clear_failure_flag" not in reply.payload


def test_interaction_shell_reply_timeout_abstains_instead_of_hanging(tmp_path: Path) -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            max_turns=2,
            reply_timeout_s=0.01,
            simulator_policy=SimulatedPolicy(),
        ),
        reply_provider=SlowReplyProvider(delay_s=0.2),
    )

    demo = Workflow.demo()
    overrides = {
        "steps": {
            "step_01": {"inputs": dict(demo.execution_plan[0].inputs), "tool_id": demo.execution_plan[0].tool_id},
            "step_02": {
                "inputs": {**demo.execution_plan[1].inputs, "force_environment_failure": True},
                "tool_id": demo.execution_plan[1].tool_id,
            },
        }
    }
    request = PlanningRequest(
        task=demo.task,
        context=demo.context,
        policy=demo.policy,
        workflow_overrides=overrides,
    )
    outcome = shell.run(
        request=request,
        run_id="run_timeout_guard_001",
        output_path=str(tmp_path / "timeout_guard_trace.json"),
    )

    assert outcome.success is False
    assert outcome.metadata.get("stopped_reason") in {"policy_compliant_stop", "repeat_failure_abort", "interaction_turn_limit"}
