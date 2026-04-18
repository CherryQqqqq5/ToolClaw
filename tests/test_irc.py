import json
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


def test_user_simulator_prefers_suggested_values_for_binding_repairs() -> None:
    request = InteractionRequest(
        interaction_id="int_binding_001",
        question="Provide `target_path` so the blocked write step can continue.",
        expected_answer_type="target_path_patch",
        allowed_response_schema={
            "type": "object",
            "properties": {"target_path": {"type": "string"}},
            "required": ["target_path"],
            "additionalProperties": False,
        },
        metadata={
            "patch_targets": {"target_path": "step.inputs.target_path"},
            "suggested_values": {"target_path": "outputs/reports/recovered.txt"},
        },
    )

    reply = UserSimulator(SimulatedPolicy()).reply(request)

    assert reply.accepted is True
    assert reply.payload["target_path"] == "outputs/reports/recovered.txt"


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


def test_interaction_shell_preserves_structured_reply_payload_and_decoded_metadata() -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(runtime=runtime)
    request = InteractionRequest(
        interaction_id="int_tool_switch_002",
        question="Provide replacement tool_id",
        expected_answer_type="tool_switch",
        allowed_response_schema={
            "type": "object",
            "properties": {"tool_id": {"type": "string", "enum": ["backup_write_tool"]}},
            "required": ["tool_id"],
            "additionalProperties": False,
        },
        metadata={"patch_targets": {"tool_id": "binding.primary_tool"}},
    )

    raw_reply = UserSimulator(SimulatedPolicy()).reply(request)
    decoded_reply = shell._decode_to_user_reply(request, raw_reply)

    assert decoded_reply.payload == {"tool_id": "backup_write_tool"}
    assert decoded_reply.metadata["decoded_intent_type"] == "action_confirm"
    assert decoded_reply.metadata["decoded_slot_updates"] == {"tool_id": "backup_write_tool"}


def test_interaction_shell_prefers_structured_slot_payload_over_raw_text_for_trace_metadata() -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(runtime=runtime)
    request = InteractionRequest(
        interaction_id="int_target_path_001",
        question="Provide target_path",
        expected_answer_type="target_path_patch",
        allowed_response_schema={
            "type": "object",
            "properties": {"target_path": {"type": "string"}},
            "required": ["target_path"],
            "additionalProperties": False,
        },
        metadata={"patch_targets": {"target_path": "step.inputs.target_path"}},
    )

    raw_reply = UserSimulator(SimulatedPolicy(missing_arg_values={"target_path": "outputs/reports/recovered.txt"})).reply(request)
    decoded_reply = shell._decode_to_user_reply(request, raw_reply)

    assert decoded_reply.payload == {"target_path": "outputs/reports/recovered.txt"}
    assert decoded_reply.metadata["decoded_intent_type"] == "slot_fill"
    assert decoded_reply.metadata["decoded_slot_updates"] == {"target_path": "outputs/reports/recovered.txt"}


def test_interaction_trace_records_compiled_patch_and_resume_request(tmp_path: Path) -> None:
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
            simulator_policy=SimulatedPolicy(missing_arg_values={"target_path": "outputs/reports/recovered.txt"}),
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
    trace_path = tmp_path / "compiled_patch_trace.json"

    outcome = shell.run(
        request=request,
        run_id="a3_compiled_patch_trace_001",
        output_path=str(trace_path),
        compile_on_success=False,
    )

    assert outcome.success is True
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    patch_event = next(event for event in payload["events"] if event["event_type"] == "patch_compiled")
    resume_event = next(event for event in payload["events"] if event["event_type"] == "resume_requested")
    final_write_call = next(
        event
        for event in reversed(payload["events"])
        if event["event_type"] == "tool_call" and event.get("tool_id") == "write_tool"
    )

    assert patch_event["metadata"]["interaction_kind"] == "repair"
    assert patch_event["metadata"]["decoded_slot_updates"] == {"fallback_execution_path": "auto-reply"}
    assert patch_event["output"]["state_updates"]["target_path"] == "outputs/reports/recovered.txt"
    assert resume_event["metadata"]["interaction_kind"] == "repair"
    assert resume_event["output"]["resume_step_id"] == "step_02"
    assert final_write_call["tool_args"]["target_path"] == patch_event["output"]["state_updates"]["target_path"]


def test_interaction_probe_does_not_emit_placeholder_patch_target(tmp_path: Path) -> None:
    registry = InMemoryAssetRegistry()
    runtime = ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )
    shell = InteractionShell(runtime=runtime, config=InteractionLoopConfig(max_turns=1, simulator_policy=SimulatedPolicy()))

    demo = Workflow.demo()
    request = PlanningRequest(task=demo.task, context=demo.context, policy=demo.policy)
    request.hints.user_style["task_family"] = "t3_must_interact"
    trace_path = tmp_path / "interaction_probe_trace.json"

    outcome = shell.run(
        request=request,
        run_id="a3_probe_no_placeholder_001",
        output_path=str(trace_path),
        compile_on_success=False,
    )

    assert outcome.success is True
    payload = __import__("json").loads(trace_path.read_text(encoding="utf-8"))
    query_event = next(event for event in payload["events"] if event["event_type"] == "user_query")
    reply_event = next(event for event in payload["events"] if event["event_type"] == "user_reply")
    assert query_event["metadata"]["patch_targets"] == {}
    assert query_event["metadata"]["interaction_kind"] == "probe"
    assert reply_event["metadata"]["interaction_kind"] == "probe"
    assert reply_event["metadata"]["reply_metadata"]["decoded_intent_type"] == "interaction_probe"
    assert reply_event["metadata"]["reply_metadata"]["decoded_slot_updates"] == {}
    assert payload["metrics"]["probe_user_queries"] == 1
    assert payload["metrics"]["repair_user_queries"] == 0
    assert payload["metrics"]["probe_user_replies"] == 1
    assert payload["metrics"]["repair_user_replies"] == 0


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


def test_interaction_shell_skips_probe_for_single_turn_approval_tasks(tmp_path: Path) -> None:
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
            simulator_policy=SimulatedPolicy(),
        ),
    )

    demo = Workflow.demo()
    demo.task.constraints.max_user_turns = 1
    overrides = {
        "steps": {
            "step_02": {
                "inputs": dict(demo.execution_plan[1].inputs),
                "tool_id": demo.execution_plan[1].tool_id,
                "requires_user_confirmation": True,
            }
        }
    }
    trace_path = tmp_path / "single_turn_approval_trace.json"

    outcome = shell.run(
        request=PlanningRequest(
            task=demo.task,
            context=demo.context,
            policy=demo.policy,
            workflow_overrides=overrides,
        ),
        run_id="a3_single_turn_approval_001",
        output_path=str(trace_path),
    )

    assert outcome.success is True
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    event_types = [event["event_type"] for event in payload["events"]]
    assert "approval_request" in event_types
    assert "approval_response" in event_types
    assert "interaction_probe" not in event_types
    assert "user_query" not in event_types


def test_interaction_shell_compiles_approval_and_target_path_patch_in_one_turn(tmp_path: Path) -> None:
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
            simulator_policy=SimulatedPolicy(missing_arg_values={"target_path": "outputs/reports/approved_once.txt"}),
        ),
    )

    demo = Workflow.demo()
    demo.task.constraints.max_user_turns = 1
    overrides = {
        "steps": {
            "step_02": {
                "inputs": {
                    key: value
                    for key, value in demo.execution_plan[1].inputs.items()
                    if key != "target_path"
                },
                "tool_id": demo.execution_plan[1].tool_id,
                "requires_user_confirmation": True,
            },
        }
    }
    trace_path = tmp_path / "binding_plus_approval_trace.json"

    outcome = shell.run(
        request=PlanningRequest(task=demo.task, context=demo.context, policy=demo.policy, workflow_overrides=overrides),
        run_id="a3_binding_plus_approval_001",
        output_path=str(trace_path),
        compile_on_success=False,
    )

    assert outcome.success is True
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    patch_event = next(event for event in payload["events"] if event["event_type"] == "patch_compiled")
    write_call = next(
        event
        for event in reversed(payload["events"])
        if event["event_type"] == "tool_call" and event.get("tool_id") == "write_tool"
    )

    assert patch_event["output"]["policy_updates"] == {"approved": True}
    assert patch_event["output"]["state_updates"]["target_path"] == "outputs/reports/approved_once.txt"
    assert write_call["tool_args"]["target_path"] == "outputs/reports/approved_once.txt"
