from dataclasses import dataclass
from typing import Dict, Optional

from toolclaw.integrations.tau3 import (
    FallbackAssistantMessage,
    FallbackMultiToolMessage,
    FallbackToolMessage,
    TAU3_BENCH_AVAILABLE,
    ParsedToolResult,
    Tau3BenchAdapter,
    ToolClawTau3Agent,
    ToolClawTau3TurnContext,
)
from toolclaw.schemas.error import ErrorCategory
from toolclaw.schemas.repair import RepairType
from toolclaw.schemas.workflow import (
    ActionType,
    ApprovalGate,
    CapabilityGraph,
    CapabilityNode,
    CheckpointPolicy,
    Phase,
    PolicyRule,
    ReusableTargets,
    RollbackPolicy,
    TaskConstraints,
    TaskSpec,
    ToolBinding,
    Workflow,
    WorkflowContext,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowPolicy,
    WorkflowStep,
)


@dataclass
class FakeTool:
    name: str
    description: str
    arg_map: Optional[Dict[str, str]] = None


def test_tau3_adapter_builds_planning_request_from_task_and_tools() -> None:
    adapter = Tau3BenchAdapter()
    request = adapter.build_request(
        task={
            "task_id": "tau3_demo_001",
            "instruction": "retrieve and write report",
            "constraints": {
                "requires_user_approval": True,
                "forbidden_actions": ["delete"],
                "risk_level": "high",
                "time_limit": 1000,
            },
        },
        tools=[
            FakeTool(name="search_tool", description="Search information"),
            FakeTool(name="write_tool", description="Write report"),
        ],
        domain_policy={"domain": "retail"},
    )

    assert request.task.task_id == "tau3_demo_001"
    assert request.task.user_goal == "retrieve and write report"
    assert request.task.constraints.requires_user_approval is True
    assert request.task.constraints.forbidden_actions == ["delete"]
    assert len(request.context.candidate_tools) == 2
    assert request.context.candidate_tools[0].tool_id == "search_tool"
    assert request.context.environment.permissions.filesystem_write is True
    assert request.workflow_overrides["steps"]["step_02"]["inputs"]["target_path"].endswith("tau3_demo_001.txt")


def test_tau3_agent_emits_tool_calls_turn_by_turn() -> None:
    agent = ToolClawTau3Agent(
        tools=[
            FakeTool(name="search_tool", description="Search information"),
            FakeTool(name="write_tool", description="Write report"),
        ],
        domain_policy={"domain": "retail"},
        task={"task_id": "tau3_smoke_001", "query": "retrieve and write report"},
        output_dir="outputs/tau3_agent_test",
    )

    state = agent.get_init_state(message_history=["retrieve and write report"])
    first_message, next_state = agent.generate_next_message("please continue", state)

    assert next_state.latest_request is not None
    assert next_state.workflow is not None
    assert next_state.waiting_step_id == "step_01"
    assert len(next_state.pending_tool_calls) == 1
    if TAU3_BENCH_AVAILABLE:
        assert hasattr(first_message, "tool_calls")
        assert len(first_message.tool_calls) == 1
    else:
        assert isinstance(first_message, FallbackAssistantMessage)
        assert len(first_message.tool_calls) == 1

    search_call = first_message.tool_calls[0]
    tool_result = FallbackToolMessage(
        id=search_call.id,
        content='{"payload": "retrieved data"}',
    )
    second_message, second_state = agent.generate_next_message(tool_result, next_state)
    assert second_state.final_state["retrieved_info"] == "retrieved data"
    assert second_state.waiting_step_id == "step_02"
    assert len(second_state.pending_tool_calls) == 1
    assert len(second_message.tool_calls) == 1

    write_call = second_message.tool_calls[0]
    final_result = FallbackToolMessage(
        id=write_call.id,
        content='{"payload": "report written"}',
    )
    final_message, final_state = agent.generate_next_message(final_result, second_state)
    assert final_state.finished is True
    assert final_state.latest_outcome is not None
    assert final_state.latest_outcome.success is True
    if TAU3_BENCH_AVAILABLE:
        assert hasattr(final_message, "content")
    else:
        assert isinstance(final_message, FallbackAssistantMessage)


def test_tau3_agent_strictly_parses_tool_message_content_shapes() -> None:
    agent = ToolClawTau3Agent(
        tools=[FakeTool(name="search_tool", description="Search information")],
        domain_policy={"domain": "retail"},
        task={"task_id": "tau3_parser_001", "query": "retrieve"},
    )

    parsed_json = agent._parse_single_tool_result(
        FallbackToolMessage(id="call_json", content='{"payload": {"value": 1}, "metadata": {"source": "tool"}}')
    )
    parsed_text = agent._parse_single_tool_result(
        FallbackToolMessage(id="call_text", content="plain text payload")
    )

    assert isinstance(parsed_json, ParsedToolResult)
    assert parsed_json.payload == {"value": 1}
    assert parsed_json.metadata["source"] == "tool"
    assert parsed_json.metadata["role"] == "tool"
    assert parsed_json.parse_error is None
    assert parsed_text.payload == "plain text payload"

    parsed_missing_id = agent._parse_single_tool_result(
        FallbackToolMessage(id="", content="missing id payload")
    )
    assert parsed_missing_id.error is True
    assert parsed_missing_id.parse_error == "missing_tool_call_id"


def test_tau3_agent_adapts_native_runtime_result_shapes() -> None:
    agent = ToolClawTau3Agent(
        tools=[
            FakeTool(name="search_tool", description="Search information"),
            FakeTool(name="write_tool", description="Write report"),
        ],
        domain_policy={"domain": "retail"},
        task={"task_id": "tau3_native_001", "query": "retrieve and write report"},
    )

    state = agent.get_init_state(message_history=["retrieve and write report"])
    first_message, next_state = agent.generate_next_message("start", state)
    search_call = first_message.tool_calls[0]

    native_result = {
        "tool_call_id": search_call.id,
        "output": {"rows": ["alpha", "beta"]},
        "status_code": 200,
        "metadata": {"source": "native_executor"},
    }
    second_message, second_state = agent.generate_next_message(native_result, next_state)

    assert second_state.final_state["retrieved_info"] == {"rows": ["alpha", "beta"]}
    assert second_state.pending_tool_calls
    assert len(second_message.tool_calls) == 1


def test_tau3_error_mapper_routes_native_executor_errors_to_recovery_categories() -> None:
    agent = ToolClawTau3Agent(
        tools=[FakeTool(name="write_tool", description="Write report")],
        domain_policy={"domain": "retail"},
        task={"task_id": "tau3_error_map_001", "query": "write report"},
    )
    state = agent.get_init_state(message_history=["write report"])
    request = agent.adapter.build_request(task=agent.task, tools=agent.tools, domain_policy=agent.domain_policy)
    state.workflow = Workflow(
        workflow_id="wf_tau3_error_map",
        version="0.1",
        phase=Phase.PHASE1_TRAINING_FREE,
        task=TaskSpec(task_id="tau3_error_map_001", user_goal="write report", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[]),
        execution_plan=[
            WorkflowStep(
                step_id="step_01",
                capability_id="cap_write",
                tool_id="write_tool",
                action_type=ActionType.TOOL_CALL,
                inputs={"target_path": "outputs/error.txt"},
                expected_output="write_result",
            )
        ],
    )
    context = ToolClawTau3TurnContext(
        incoming_message=None,
        state=state,
        request=request,
        runtime=agent.runtime,
        run_id="tau3_error_map_001",
        output_path="outputs/tau3_error_map.json",
    )
    step = state.workflow.execution_plan[0]

    binding_error = agent.tool_error_mapper.build_error(
        context=context,
        step=step,
        parsed_result=ParsedToolResult(
            tool_call_id="call_binding",
            content_raw="missing required field: target_path",
            content_value="missing required field: target_path",
            payload="missing required field: target_path",
            metadata={"missing_fields": ["target_path"]},
            error=True,
        ),
    )
    permission_error = agent.tool_error_mapper.build_error(
        context=context,
        step=step,
        parsed_result=ParsedToolResult(
            tool_call_id="call_permission",
            content_raw="permission denied",
            content_value="permission denied",
            payload="permission denied",
            metadata={"status_code": 403},
            error=True,
        ),
    )

    assert binding_error.category == ErrorCategory.BINDING_FAILURE
    assert binding_error.state_context.missing_assets == ["target_path"]
    assert agent.recovery_engine.plan_repair(binding_error).repair_type == RepairType.REBIND_ARGS

    assert permission_error.category == ErrorCategory.PERMISSION_FAILURE
    assert agent.recovery_engine.plan_repair(permission_error).repair_type == RepairType.REPLAN_SUFFIX


def test_tau3_agent_supports_multitool_parallel_batch_and_arg_mapping() -> None:
    tools = [
        FakeTool(name="search_tool", description="Search information", arg_map={"query": "query"}),
        FakeTool(name="write_tool", description="Write report", arg_map={"target_path": "target_path"}),
    ]
    agent = ToolClawTau3Agent(
        tools=tools,
        domain_policy={"domain": "retail"},
        task={"task_id": "tau3_parallel_001", "query": "parallel run"},
    )
    state = agent.get_init_state(message_history=["parallel run"])
    state.workflow = Workflow(
        workflow_id="wf_tau3_parallel",
        version="0.1",
        phase=Phase.PHASE1_TRAINING_FREE,
        task=TaskSpec(task_id="tau3_parallel_001", user_goal="parallel run", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[]),
        capability_graph=CapabilityGraph(
            capabilities=[
                CapabilityNode(capability_id="cap_search_a", description="search a"),
                CapabilityNode(capability_id="cap_search_b", description="search b"),
            ],
            edges=[],
        ),
        tool_bindings=[
            ToolBinding(capability_id="cap_search_a", primary_tool="search_tool", binding_confidence=1.0),
            ToolBinding(capability_id="cap_search_b", primary_tool="write_tool", binding_confidence=1.0),
        ],
        execution_plan=[
            WorkflowStep(
                step_id="step_01",
                capability_id="cap_search_a",
                tool_id="search_tool",
                action_type=ActionType.TOOL_CALL,
                inputs={"query": "alpha"},
                expected_output="alpha_result",
            ),
            WorkflowStep(
                step_id="step_02",
                capability_id="cap_search_b",
                tool_id="write_tool",
                action_type=ActionType.TOOL_CALL,
                inputs={"target_path": "outputs/demo.txt"},
                expected_output="beta_result",
            ),
        ],
        workflow_graph=WorkflowGraph(
            nodes=[
                WorkflowNode(
                    node_id="step_01",
                    capability_id="cap_search_a",
                    selected_tool="search_tool",
                    tool_candidates=["search_tool"],
                    inputs={"query": "alpha"},
                    expected_output="alpha_result",
                    checkpoint_policy=CheckpointPolicy(enabled=False),
                    rollback_policy=RollbackPolicy(),
                    approval_gate=ApprovalGate(required=False),
                ),
                WorkflowNode(
                    node_id="step_02",
                    capability_id="cap_search_b",
                    selected_tool="write_tool",
                    tool_candidates=["write_tool"],
                    inputs={"target_path": "outputs/demo.txt"},
                    expected_output="beta_result",
                    checkpoint_policy=CheckpointPolicy(enabled=False),
                    rollback_policy=RollbackPolicy(),
                    approval_gate=ApprovalGate(required=False),
                ),
            ],
            edges=[],
            entry_nodes=["step_01", "step_02"],
            exit_nodes=["step_01", "step_02"],
        ),
        policy=WorkflowPolicy(
            approval_rules=[PolicyRule(rule_id="apr", trigger="risk_level == high", action="ask_user")]
        ),
        reusable_targets=ReusableTargets(),
    )

    first_message, state = agent.generate_next_message("start", state)
    assert len(first_message.tool_calls) == 2
    first_args = {call.name: call.arguments for call in first_message.tool_calls}
    assert first_args["search_tool"] == {"query": "alpha"}
    assert first_args["write_tool"] == {"target_path": "outputs/demo.txt"}

    tool_result_message = FallbackMultiToolMessage(
        tool_messages=[
            FallbackToolMessage(id=first_message.tool_calls[0].id, content='{"payload": "alpha ok"}'),
            FallbackToolMessage(id=first_message.tool_calls[1].id, content='{"payload": "beta ok"}'),
        ]
    )
    final_message, final_state = agent.generate_next_message(tool_result_message, state)
    assert final_state.finished is True
    assert final_state.final_state["alpha_result"] == "alpha ok"
    assert final_state.final_state["beta_result"] == "beta ok"
    assert isinstance(final_message, FallbackAssistantMessage) or hasattr(final_message, "content")
