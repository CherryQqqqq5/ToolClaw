from types import SimpleNamespace

from toolclaw.planner.htgp import (
    HTGPPlanner,
    PlanningHints,
    PlanningRequest,
    PolicyInjector,
    RuleBasedCapabilitySelector,
)
from toolclaw.planner.binder import ToolBinder
from toolclaw.planner.capability_graph import CapabilityTemplateRegistry, RuleBasedCapabilityGraphBuilder
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.error import ErrorCategory, ErrorEvidence, ErrorSeverity, ErrorStage, Recoverability, StateContext, ToolClawError
from toolclaw.compiler.swpc import WorkflowSnippet
from toolclaw.schemas.workflow import PolicyRule, RiskLevel, TaskConstraints, TaskSpec, ToolSpec, WorkflowContext, WorkflowPolicy


def build_planner(asset_registry=None) -> HTGPPlanner:
    return HTGPPlanner(
        capability_selector=RuleBasedCapabilitySelector(),
        graph_builder=RuleBasedCapabilityGraphBuilder(CapabilityTemplateRegistry()),
        binder=ToolBinder(),
        policy_injector=PolicyInjector(),
        asset_registry=asset_registry,
    )


def test_planner_builds_linear_plan_for_simple_task() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) >= 2
    assert result.workflow.execution_plan[0].capability_id == "cap_retrieve"
    assert result.workflow.execution_plan[1].capability_id == "cap_write"
    assert result.workflow.execution_plan[0].rollback_to is None
    assert result.workflow.execution_plan[1].rollback_to == "step_01"


def test_planner_emits_unresolved_capability_when_no_tool_matches() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_002", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[ToolSpec(tool_id="unknown_tool", description="unknown")]
        ),
        hints=PlanningHints(forbidden_tools=["unknown_tool"]),
    )

    result = planner.plan(request)

    assert len(result.diagnostics.unresolved_capabilities) > 0


def test_planner_injects_checkpoint_and_policy_gates() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_003", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    result = planner.plan(request)

    assert all(step.checkpoint for step in result.workflow.execution_plan)
    assert all("policy_gate" in step.metadata for step in result.workflow.execution_plan)


def test_planner_injects_approval_gate_from_policy_expression() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(
            task_id="task_004",
            user_goal="retrieve and write report",
            constraints=TaskConstraints(risk_level=RiskLevel.HIGH),
        ),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        policy=WorkflowPolicy(
            approval_rules=[PolicyRule(rule_id="apr_high_risk", trigger="risk_level == high", action="ask_user")]
        ),
    )

    result = planner.plan(request)

    assert all(step.requires_user_confirmation for step in result.workflow.execution_plan)
    assert all(step.metadata["requires_approval"] is True for step in result.workflow.execution_plan)


def test_planner_applies_bypass_for_single_tool_benchmark_hints() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_005", user_goal="save the final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "ideal_turn_count": 1,
                "milestones": ["save artifact"],
            }
        ),
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) == 1
    assert result.workflow.execution_plan[0].tool_id == "write_tool"
    assert result.diagnostics.overplanning_risk["bypass_applied"] is True
    assert "tool_allow_list" in result.diagnostics.benchmark_hints_used


def test_selector_can_infer_single_write_step_from_tool_semantics_without_benchmark_hints() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_semantic_write_001", user_goal="enable cellular service", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(
                    tool_id="set_cellular_service_status",
                    description="Enable or disable cellular service status on the device.",
                    metadata={"affordances": ["set", "update", "enable"]},
                )
            ]
        ),
    )

    result = planner.plan(request)

    assert len(result.workflow.execution_plan) == 1
    assert result.workflow.execution_plan[0].capability_id == "cap_write"
    assert result.workflow.execution_plan[0].tool_id == "set_cellular_service_status"


def test_planner_preserves_retrieve_then_send_chain_for_toolsandbox_message_state_dependency() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(
            task_id="task_toolsandbox_message_001",
            user_goal="Send a message",
            constraints=TaskConstraints(max_tool_calls=2, max_user_turns=1, max_repair_attempts=1, max_recovery_budget=1.0),
        ),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_contacts", description="Search contacts by name."),
                ToolSpec(tool_id="send_message_with_phone_number", description="Send a message to a phone number."),
                ToolSpec(
                    tool_id="set_cellular_service_status",
                    description="Enable or disable cellular service status on the device.",
                    metadata={"affordances": ["set", "enable", "update"]},
                ),
                ToolSpec(
                    tool_id="get_cellular_service_status",
                    description="Get the current cellular service status.",
                    metadata={"affordances": ["get", "status", "retrieve"]},
                ),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["state_dependency", "multiple_tool", "multiple_user_turn", "no_distraction_tools"],
                "tool_allow_list": [
                    "search_contacts",
                    "send_message_with_phone_number",
                    "set_cellular_service_status",
                    "get_cellular_service_status",
                ],
                "milestones": [
                    "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SETTING, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'cellular': True}))])",
                    "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SANDBOX, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'sender': RoleType.EXECUTION_ENVIRONMENT, 'recipient': RoleType.AGENT, 'tool_trace': json.dumps({'tool_name': 'search_contacts', 'arguments': {'name': 'Fredrik Thordendal'}}, ensure_ascii=False)}))], guardrail_database_exclusion_list=[DatabaseNamespace.SETTING])",
                    "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.MESSAGING, snapshot_constraint=addition_similarity, target_dataframe=pl.DataFrame({'recipient_phone_number': '+12453344098', 'content': \"How's the new album coming along\"}), reference_milestone_node_index=0)], guardrail_database_exclusion_list=[DatabaseNamespace.SETTING])",
                    "Milestone(snapshot_constraints=[SnapshotConstraint(database_namespace=DatabaseNamespace.SANDBOX, snapshot_constraint=snapshot_similarity, target_dataframe=pl.DataFrame({'sender': RoleType.AGENT, 'recipient': RoleType.USER, 'content': \"Your message to Fredrik Thordendal has been sent saying: How's the new album coming along\"}))])",
                ],
                "state_slots": ["messages", "cellular_service_status"],
                "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
                "ideal_turn_count": 30,
                "ideal_tool_calls": None,
            }
        ),
    )

    result = planner.plan(request)

    assert [step.capability_id for step in result.workflow.execution_plan] == ["cap_retrieve", "cap_write"]
    assert [step.tool_id for step in result.workflow.execution_plan] == [
        "search_contacts",
        "send_message_with_phone_number",
    ]
    assert result.workflow.execution_plan[0].inputs["name"] == "Fredrik Thordendal"
    assert result.workflow.execution_plan[1].inputs["content"] == "How's the new album coming along"
    assert result.workflow.execution_plan[1].inputs["recipient"] == "Fredrik Thordendal"
    assert "set_cellular_service_status" in result.workflow.execution_plan[1].metadata["allowed_tools"]
    assert result.workflow.execution_plan[1].metadata["required_state_slots"] == ["retrieved_info", "cellular_service_status"]
    assert result.workflow.execution_plan[1].metadata["ordering_sensitive"] is True
    assert result.workflow.execution_plan[1].metadata["preflight_state_policy"]["state_slot"] == "cellular_service_status"
    write_node = next(node for node in result.workflow.workflow_graph.nodes if node.node_id == "step_02")
    assert write_node.dependencies == ["step_01"]
    assert sorted(req.asset_key for req in write_node.preflight_requirements) == ["cellular_service_status", "retrieved_info"]


def test_planner_records_overplanning_risk_when_steps_exceed_ideal() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_006", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["multiple_user_turn"],
                "tool_allow_list": ["search_tool", "write_tool"],
                "ideal_tool_calls": 1,
            }
        ),
    )

    result = planner.plan(request)

    assert result.diagnostics.overplanning_risk["steps_exceed_ideal"] is True
    assert "overplanning_risk:steps_exceed_ideal_tool_calls" in result.diagnostics.warnings


def test_binder_prefers_primary_writer_over_backup_and_ordering_distractors() -> None:
    binder = ToolBinder()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_write_pref_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="write_tool", description="Primary standard writer used after retrieval to save the final artifact."),
                ToolSpec(tool_id="backup_write_tool", description="Fallback backup writer reserved for outage recovery only."),
                ToolSpec(tool_id="ordering_write_tool", description="Legacy ordering writer that violates dependency order."),
            ]
        ),
    )

    planner = build_planner()
    result = planner.plan(request)
    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    write_binding = next(binding for binding in result.workflow.tool_bindings if binding.capability_id == "cap_write")

    assert write_step.tool_id == "write_tool"
    assert write_binding.primary_tool == "write_tool"
    assert "ordering_write_tool" in write_binding.backup_tools


def test_planner_ranks_declared_backup_tool_below_primary_during_binding() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_backup_rank_001", user_goal="write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="write_tool", description="Write the final artifact."),
                ToolSpec(tool_id="backup_write_tool", description="Primary standard approved writer for the final artifact."),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool", "backup_write_tool"],
                "backup_tool_map": {"write_tool": "backup_write_tool"},
                "ideal_tool_calls": 1,
                "milestones": ["write report"],
            }
        ),
    )

    result = planner.plan(request)

    assert result.workflow.execution_plan[0].tool_id == "write_tool"
    binding = next(binding for binding in result.workflow.tool_bindings if binding.capability_id == "cap_write")
    assert binding.primary_tool == "write_tool"
    assert binding.backup_tools[0] == "backup_write_tool"


def test_binder_uses_state_preconditions_to_penalize_state_admin_writer_distractor() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_state_admin_001", user_goal="Send a message", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_contacts", description="Search contacts by name."),
                ToolSpec(tool_id="send_message_with_phone_number", description="Send a message to a phone number."),
                ToolSpec(
                    tool_id="update_message_delivery_status",
                    description="Update cellular service status for outbound message delivery.",
                    metadata={"affordances": ["update", "status", "cellular"]},
                ),
                ToolSpec(
                    tool_id="get_cellular_service_status",
                    description="Get the current cellular service status.",
                    metadata={"affordances": ["get", "status", "retrieve"]},
                ),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "benchmark": "toolsandbox",
                "categories": ["state_dependency", "multiple_user_turn"],
                "tool_allow_list": [
                    "search_contacts",
                    "send_message_with_phone_number",
                    "update_message_delivery_status",
                    "get_cellular_service_status",
                ],
                "milestones": ["retrieve contact", "send message"],
                "primary_failtax": "state",
                "state_slots": ["messages", "cellular_service_status"],
                "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
            }
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    write_binding = next(binding for binding in result.workflow.tool_bindings if binding.capability_id == "cap_write")
    assert write_step.tool_id == "send_message_with_phone_number"
    assert write_binding.primary_tool == "send_message_with_phone_number"


def test_binder_uses_tool_metadata_to_avoid_lexical_distractors() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_write_metadata_001", user_goal="write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(
                    tool_id="writer_tool",
                    description="Legacy fallback writer for emergency use only.",
                    metadata={"disallowed_capabilities": ["cap_write"]},
                ),
                ToolSpec(
                    tool_id="finalize_artifact_tool",
                    description="Finalize the artifact for normal report generation.",
                    metadata={"affordances": ["write", "report"], "preferred_capabilities": ["cap_write"]},
                ),
            ]
        ),
    )

    result = planner.plan(request)
    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")

    assert write_step.tool_id == "finalize_artifact_tool"


def test_benchmark_preferred_bindings_avoids_allow_list_order_bias_for_multi_match_capability() -> None:
    candidate_tools = [
        ToolSpec(tool_id="search_tool", description="Retrieve relevant information."),
        ToolSpec(tool_id="ordering_write_tool", description="Legacy ordering writer that should not be preferred."),
        ToolSpec(tool_id="write_tool", description="Compliant primary writer for final report output."),
    ]
    preferred = HTGPPlanner._benchmark_preferred_bindings(
        candidate_tools,
        {"tool_allow_list": ["search_tool", "ordering_write_tool", "write_tool"]},
    )

    assert preferred.get("cap_retrieve") == "search_tool"
    assert "cap_write" not in preferred


def test_planner_can_round_trip_request_context_from_workflow_metadata() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_007", user_goal="save final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            preferred_capabilities=["cap_write"],
            forbidden_tools=["deprecated_tool"],
            reusable_asset_ids=["asset_001"],
            prior_failures=["binding_failure"],
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "milestones": ["save answer"],
            },
        ),
        planner_mode="benchmark_aware",
        workflow_overrides={
            "steps": {
                "step_01": {
                    "inputs": {"target_path": "outputs/custom.txt"},
                    "metadata": {"required_state_slots": ["retrieved_info"]},
                }
            }
        },
    )

    result = planner.plan(request)
    restored = planner.request_from_workflow(result.workflow)

    assert restored.planner_mode == "benchmark_aware"
    assert restored.hints.reusable_asset_ids == ["asset_001"]
    assert restored.hints.prior_failures == ["binding_failure"]
    assert restored.hints.user_style["tool_allow_list"] == ["write_tool"]
    assert restored.workflow_overrides["steps"]["step_01"]["inputs"]["target_path"] == "outputs/custom.txt"
    assert restored.workflow_overrides["steps"]["step_01"]["metadata"]["required_state_slots"] == ["retrieved_info"]


def test_planner_passthrough_metadata_preserves_toolsandbox_annotations() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_passthrough_001", user_goal="Send a message", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_contacts", description="Search contacts by name."),
                ToolSpec(tool_id="send_message_with_phone_number", description="Send a message to a phone number."),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "benchmark": "toolsandbox",
                "messages": [{"sender": "system", "content": "full instruction"}],
                "categories": ["state_dependency", "multiple_user_turn"],
                "tool_allow_list": ["search_contacts", "send_message_with_phone_number"],
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
        ),
    )

    result = planner.plan(request)

    assert result.workflow.metadata["benchmark"] == "toolsandbox"
    assert result.workflow.metadata["messages"] == [{"sender": "system", "content": "full instruction"}]
    assert result.workflow.metadata["toolsandbox_categories"] == ["state_dependency", "multiple_user_turn"]
    assert result.workflow.metadata["primary_failtax"] == "state"
    assert result.workflow.metadata["dependency_edges"] == [{"source": "step_01", "target": "step_02", "type": "state"}]
    assert result.workflow.metadata["tool_execution_backend"] == "semantic_mock"


def test_reusable_hints_do_not_leak_foreign_toolsandbox_target_path_when_overriding_existing_value() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="toolsandbox_reuse_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    workflow = planner.plan(request).workflow
    workflow.metadata["benchmark"] = "toolsandbox"
    workflow.metadata["reuse_override_inputs"] = {"cap_write": ["target_path"]}
    write_step = next(step for step in workflow.execution_plan if step.capability_id == "cap_write")
    write_step.inputs["target_path"] = "outputs/toolsandbox/reports/foreign_task.txt"
    write_step.metadata["repair_default_inputs"] = {"target_path": "outputs/toolsandbox/reports/toolsandbox_reuse_001.txt"}

    HTGPPlanner._apply_reusable_hints(
        workflow,
        {
            "recommended_inputs": {
                "cap_write": {"target_path": "outputs/toolsandbox/reports/foreign_task.txt"}
            }
        },
    )

    assert write_step.inputs["target_path"] == "outputs/toolsandbox/reports/toolsandbox_reuse_001.txt"


def test_reusable_hints_do_not_prefill_repair_sensitive_target_path() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="toolsandbox_reuse_002", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "benchmark": "toolsandbox",
                "categories": ["insufficient_information", "single_user_turn"],
                "expected_recovery_path": "patch_then_retry",
            }
        ),
    )

    workflow = planner.plan(request).workflow
    workflow.metadata["benchmark"] = "toolsandbox"
    workflow.metadata["toolsandbox_categories"] = ["insufficient_information", "single_user_turn"]
    workflow.metadata["expected_recovery_path"] = "patch_then_retry"
    workflow.metadata["reuse_override_inputs"] = {"cap_write": ["target_path"]}
    write_step = next(step for step in workflow.execution_plan if step.capability_id == "cap_write")
    write_step.metadata["repair_default_inputs"] = {"target_path": "outputs/toolsandbox/reports/toolsandbox_reuse_002.txt"}
    write_step.inputs.pop("target_path", None)

    HTGPPlanner._apply_reusable_hints(
        workflow,
        {
            "recommended_inputs": {
                "cap_write": {"target_path": "outputs/toolsandbox/reports/toolsandbox_reuse_002.txt"}
            }
        },
    )

    assert "target_path" not in write_step.inputs
    assert workflow.metadata["reusable_context"]["suppressed_inputs"] == [
        {
            "step_id": write_step.step_id,
            "capability_id": "cap_write",
            "input_key": "target_path",
            "reason": "repair_sensitive_missing_input",
        }
    ]


def test_reusable_hints_can_still_apply_safe_nonrepair_input() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_safe_reuse_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
    )

    workflow = planner.plan(request).workflow
    retrieve_step = next(step for step in workflow.execution_plan if step.capability_id == "cap_retrieve")

    HTGPPlanner._apply_reusable_hints(
        workflow,
        {
            "recommended_inputs": {
                "cap_retrieve": {"result_key": "cached_result"}
            }
        },
    )

    assert retrieve_step.inputs["result_key"] == "cached_result"


def test_exact_match_auto_repair_replay_can_prefill_missing_target_path() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_auto_patch_reuse_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "benchmark": "toolsandbox",
                "categories": ["insufficient_information", "single_user_turn"],
                "expected_recovery_path": "patch_then_retry",
            }
        ),
    )

    workflow = planner.plan(request).workflow
    workflow.metadata["benchmark"] = "toolsandbox"
    workflow.metadata["toolsandbox_categories"] = ["insufficient_information", "single_user_turn"]
    workflow.metadata["expected_recovery_path"] = "patch_then_retry"
    write_step = next(step for step in workflow.execution_plan if step.capability_id == "cap_write")
    write_step.metadata["repair_default_inputs"] = {"target_path": "outputs/toolsandbox/reports/task_auto_patch_reuse_001.txt"}
    write_step.inputs.pop("target_path", None)

    HTGPPlanner._apply_reusable_hints(
        workflow,
        {
            "reuse_application": "continuation_prior",
            "auto_continuation_replay": True,
            "auto_patch_input_keys": {"cap_write": ["target_path"]},
            "recommended_inputs": {
                "cap_write": {"target_path": "outputs/toolsandbox/reports/foreign_task.txt"}
            },
        },
    )

    assert write_step.inputs["target_path"] == "outputs/toolsandbox/reports/task_auto_patch_reuse_001.txt"
    assert workflow.metadata["reusable_context"]["auto_continuation_replay"] is True
    assert workflow.metadata["reusable_context"]["suppressed_inputs"] == []


def test_exact_match_auto_repair_replay_promotes_backup_tool_to_primary_binding() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_auto_replay_backup_001",
            task_signature="phase1::family=tau2_env_backup_001::caps=cap_retrieve+cap_write::fail=environment_failure::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={},
            continuation_hints=[
                {
                    "kind": "fallback_to_backup_then_resume",
                    "trigger_repair_type": "switch_tool",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "backup_tool_id": "backup_write_tool",
                }
            ],
            metadata={
                "failure_context": "environment_failure",
                "required_state_slots": [],
                "task_family": "tau2_env_backup_001",
                "reuse_family_id": "tau2_env_backup_001",
                "semantic_reuse_family": "tau2_env_backup",
                "utility_profile": {
                    "observed_tool_calls": 3,
                    "observed_user_queries": 0,
                    "observed_repair_actions": 1,
                    "auto_repair_replay_eligible": True,
                    "utility_gain_score": 0.0,
                    "reuse_application_hint": "binding_prior",
                },
                "reuse_application_hint": "binding_prior",
                "utility_gain_score": 0.0,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="tau2_env_backup_001__pass2", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="backup writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "task_family": "tau2_env_backup_001",
                "failure_type": "environment_failure",
                "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert write_step.tool_id == "backup_write_tool"
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "continuation_prior"
    assert result.workflow.metadata["reusable_context"]["auto_continuation_replay"] is True


def test_exact_match_auto_repair_replay_loads_recommended_inputs_from_binding_prior_asset() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_auto_replay_patch_001",
            task_signature="phase1::family=tau2_binding_auto_001::caps=cap_retrieve+cap_write::fail=binding_failure::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={
                "cap_write": {
                    "target_path": "outputs/reports/planned_report.txt",
                    "retrieved_info": "summary for: retrieve and write report",
                }
            },
            continuation_hints=[
                {
                    "kind": "patch_then_retry_same_step",
                    "trigger_repair_type": "rebind_args",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "patched_input_keys": ["target_path"],
                }
            ],
            metadata={
                "failure_context": "binding_failure",
                "required_state_slots": [],
                "task_family": "tau2_binding_auto_001",
                "reuse_family_id": "tau2_binding_auto_001",
                "semantic_reuse_family": "tau2_binding_auto",
                "utility_profile": {
                    "observed_tool_calls": 3,
                    "observed_user_queries": 0,
                    "observed_repair_actions": 1,
                    "auto_repair_replay_eligible": True,
                    "utility_gain_score": 0.0,
                    "reuse_application_hint": "binding_prior",
                },
                "reuse_application_hint": "binding_prior",
                "utility_gain_score": 0.0,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="tau2_binding_auto_001__pass2", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "task_family": "tau2_binding_auto_001",
                "failure_type": "binding_failure",
                "tool_allow_list": ["search_tool", "write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert write_step.inputs["target_path"] == "outputs/reports/planned_report.txt"
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "continuation_prior"
    assert result.workflow.metadata["reusable_context"]["auto_continuation_replay"] is True


def test_exact_match_auto_repair_replay_derives_semantic_family_from_reuse_family_id() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_auto_replay_fallback_family_001",
            task_signature="phase1::family=tau2_env_backup_001::caps=cap_retrieve+cap_write::fail=environment_failure::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={},
            continuation_hints=[
                {
                    "kind": "fallback_to_backup_then_resume",
                    "trigger_repair_type": "switch_tool",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "backup_tool_id": "backup_write_tool",
                }
            ],
            metadata={
                "failure_context": "environment_failure",
                "required_state_slots": [],
                "task_family": "tau2_env_backup_001",
                "reuse_family_id": "tau2_env_backup_001",
                "semantic_reuse_family": "",
                "utility_profile": {
                    "observed_tool_calls": 3,
                    "observed_user_queries": 0,
                    "observed_repair_actions": 1,
                    "auto_repair_replay_eligible": True,
                    "utility_gain_score": 0.0,
                    "reuse_application_hint": "binding_prior",
                },
                "reuse_application_hint": "binding_prior",
                "utility_gain_score": 0.0,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="tau2_env_backup_001__pass2", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="backup writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "task_family": "tau2_env_backup_001",
                "failure_type": "environment_failure",
                "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert write_step.tool_id == "backup_write_tool"
    assert (
        result.workflow.metadata["reusable_context"]["selected_match"]["source_semantic_reuse_family"]
        == "tau2_env_backup"
    )
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "continuation_prior"


def test_exact_match_auto_repair_replay_uses_target_reuse_family_not_generic_task_family() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        WorkflowSnippet(
            snippet_id="ws_env_backup_exact",
            task_signature="phase1::family=t4_repeated_reusable::caps=cap_retrieve+cap_write::fail=environment_failure::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "backup_write_tool"},
            recommended_inputs={
                "cap_write": {
                    "target_path": "outputs/reports/planned_report.txt",
                    "retrieved_info": "summary for: retrieve and write report",
                }
            },
            continuation_hints=[
                {
                    "kind": "fallback_to_backup_then_resume",
                    "trigger_repair_type": "switch_tool",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "backup_tool_id": "backup_write_tool",
                    "resume_policy": "retry_same_step",
                }
            ],
            quality_score=0.95,
            metadata={
                "utility_profile": {
                    "utility_gain_score": 0.0,
                    "reuse_application_hint": "binding_prior",
                    "auto_repair_replay_eligible": True,
                },
                "source_task_id": "tau2_env_backup_001__pass1",
                "reuse_family_id": "tau2_env_backup_001",
                "semantic_reuse_family": "tau2_env_backup",
                "failure_context": "environment_failure",
                "required_state_slots": ["query", "retrieved_info"],
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="tau2_env_backup_001__pass2", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="backup writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "task_family": "t4_repeated_reusable",
                "reuse_family_id": "tau2_env_backup_001",
                "semantic_reuse_family": "tau2_env_backup",
                "failure_type": "environment_failure",
                "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert write_step.tool_id == "backup_write_tool"
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "continuation_prior"


def test_replan_from_error_inherits_workflow_request_context_when_request_is_sparse() -> None:
    planner = build_planner()
    original_request = PlanningRequest(
        task=TaskSpec(task_id="task_008", user_goal="save final answer", constraints=TaskConstraints()),
        context=WorkflowContext(candidate_tools=[ToolSpec(tool_id="write_tool", description="write")]),
        hints=PlanningHints(
            reusable_asset_ids=["asset_002"],
            prior_failures=["environment_failure"],
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool"],
                "ideal_tool_calls": 1,
                "ideal_turn_count": 1,
            },
        ),
    )
    planned = planner.plan(original_request).workflow
    sparse_request = PlanningRequest(task=planned.task, context=planned.context, policy=planned.policy)
    error = ToolClawError(
        error_id="err_replan_ctx_001",
        run_id="run_replan_ctx_001",
        workflow_id=planned.workflow_id,
        step_id="step_01",
        category=ErrorCategory.ORDERING_FAILURE,
        subtype="dependency_error",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=["ordering failed"],
        evidence=ErrorEvidence(tool_id=None, raw_message="ordering failed"),
        root_cause_hypothesis=["synthetic test"],
        state_context=StateContext(active_step_id="step_01"),
        recoverability=Recoverability(recoverable=True, requires_rollback=True),
        failtax_label="ordering_failure",
    )

    replanned = planner.replan_from_error(
        request=sparse_request,
        failed_workflow=planned,
        error=error,
        state_values={"retrieved_info": "cached"},
    )

    assert replanned.diagnostics.overplanning_risk["bypass_applied"] is True
    assert "tool_allow_list" in replanned.diagnostics.benchmark_hints_used
    assert replanned.workflow.metadata["replan_context"]["reusable_asset_ids"] == ["asset_002"]
    assert "ordering_failure" in replanned.workflow.metadata["replan_context"]["prior_failures"]


def test_planner_prunes_capabilities_from_milestones_before_execution_plan() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_009", user_goal="retrieve summarize and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="summarize_tool", description="summarize"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["multiple_tool"],
                "tool_allow_list": ["search_tool", "write_tool"],
                "milestones": ["retrieve data", "write report"],
                "ideal_tool_calls": 2,
            }
        ),
    )

    result = planner.plan(request)

    assert [step.capability_id for step in result.workflow.execution_plan] == ["cap_retrieve", "cap_write"]
    assert result.workflow.execution_plan[0].metadata["milestone_hint"] == "retrieve data"
    assert result.workflow.execution_plan[1].metadata["milestone_hint"] == "write report"
    assert result.workflow.capability_graph.metadata["overplanning_objective"]["applied"] is True


def test_planner_filters_bindings_to_tool_allow_list() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_010", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="write backup"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["multiple_tool"],
                "tool_allow_list": ["search_tool", "write_tool"],
                "ideal_tool_calls": 2,
            }
        ),
    )

    result = planner.plan(request)

    assert all(step.tool_id in {"search_tool", "write_tool"} for step in result.workflow.execution_plan if step.tool_id)
    write_node = next(node for node in result.workflow.workflow_graph.nodes if node.capability_id == "cap_write")
    assert "backup_write_tool" not in write_node.tool_candidates


def test_branch_options_shape_workflow_graph_and_replanned_suffix() -> None:
    planner = build_planner()
    request = PlanningRequest(
        task=TaskSpec(task_id="task_011", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["multiple_tool"],
                "tool_allow_list": ["search_tool", "write_tool"],
                "milestones": ["retrieve data", "write report"],
                "branch_options": ["primary_path", "fallback_path"],
                "ideal_tool_calls": 2,
            }
        ),
    )

    planned = planner.plan(request).workflow
    assert planned.execution_plan[-1].metadata["branch_options"] == ["primary_path", "fallback_path"]
    assert any(edge.condition == "on_branch_resolved" for edge in planned.workflow_graph.edges)
    assert any(edge.condition == "on_branch:primary_path" for edge in planned.workflow_graph.edges)

    sparse_request = PlanningRequest(task=planned.task, context=planned.context, policy=planned.policy)
    error = ToolClawError(
        error_id="err_replan_ctx_003",
        run_id="run_replan_ctx_003",
        workflow_id=planned.workflow_id,
        step_id="step_02",
        category=ErrorCategory.ORDERING_FAILURE,
        subtype="dependency_error",
        severity=ErrorSeverity.MEDIUM,
        stage=ErrorStage.EXECUTION,
        symptoms=["ordering failed"],
        evidence=ErrorEvidence(tool_id="write_tool", raw_message="ordering failed"),
        root_cause_hypothesis=["synthetic test"],
        state_context=StateContext(active_step_id="step_02"),
        recoverability=Recoverability(recoverable=True, requires_rollback=True),
        failtax_label="ordering_failure",
    )
    planned.execution_plan[1].rollback_to = "step_01"

    replanned = planner.replan_from_error(
        request=sparse_request,
        failed_workflow=planned,
        error=error,
        state_values={"retrieved_info": "cached"},
    )

    assert replanned.workflow.execution_plan[-1].metadata["branch_options"] == ["primary_path", "fallback_path"]
    assert any(edge.condition == "on_branch_resolved" for edge in replanned.workflow.workflow_graph.edges)


def test_replanned_suffix_objective_preserves_branch_sensitive_terminal_step() -> None:
    planner = build_planner()
    benchmark_hints = {
        "categories": ["multiple_tool"],
        "tool_allow_list": ["search_tool", "write_tool"],
        "ideal_tool_calls": 3,
        "milestones": ["retrieve data", "write report"],
        "branch_options": ["primary_path", "fallback_path"],
    }
    failed_workflow = planner.plan(
        PlanningRequest(
            task=TaskSpec(task_id="task_012", user_goal="retrieve and write report", constraints=TaskConstraints()),
            context=WorkflowContext(
                candidate_tools=[
                    ToolSpec(tool_id="search_tool", description="search"),
                    ToolSpec(tool_id="write_tool", description="write"),
                ]
            ),
            hints=PlanningHints(user_style=benchmark_hints),
        )
    ).workflow

    suffix = [
        failed_workflow.execution_plan[0],
        failed_workflow.execution_plan[1],
        failed_workflow.execution_plan[1].__class__(
            step_id="step_03",
            capability_id="cap_write",
            tool_id="write_tool",
            action_type=failed_workflow.execution_plan[1].action_type,
            inputs=dict(failed_workflow.execution_plan[1].inputs),
            expected_output=failed_workflow.execution_plan[1].expected_output,
            checkpoint=True,
            rollback_to=None,
            requires_user_confirmation=False,
            metadata={
                **dict(failed_workflow.execution_plan[1].metadata),
                "milestone_index": 1,
                "branch_sensitive": True,
                "branch_options": ["primary_path", "fallback_path"],
            },
        ),
    ]

    pruned = HTGPPlanner._prune_replanned_suffix(
        failed_workflow=failed_workflow,
        replanned_steps=suffix,
        failed_index=0,
        benchmark_hints=benchmark_hints,
    )

    assert len(pruned) == 2
    assert pruned[-1].metadata["branch_sensitive"] is True


def test_reusable_profile_respects_overplanning_objective_tool_allow_list() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_retrieve": "search_tool", "cap_write": "backup_write_tool"},
            recommended_inputs={"cap_retrieve": {"result_key": "cached_result"}},
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_013", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="write backup"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "tool_allow_list": ["search_tool", "write_tool"],
                "milestones": ["retrieve data", "write report"],
                "ideal_tool_calls": 2,
            }
        ),
    )

    result = planner.plan(request)

    assert all(step.tool_id in {"search_tool", "write_tool"} for step in result.workflow.execution_plan if step.tool_id)
    assert result.workflow.execution_plan[0].inputs["result_key"] == "cached_result"


def test_planner_does_not_load_reuse_profile_when_reuse_is_disabled() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_disabled_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={"cap_retrieve": {"result_key": "cached_result"}},
            metadata={
                "failure_context": "none",
                "required_state_slots": [],
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_013b", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=False,
            user_style={
                "tool_allow_list": ["search_tool", "write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    assert result.workflow.metadata["reusable_context"]["profile_loaded"] is False
    assert result.workflow.metadata["reusable_context"]["resolved_asset_ids"] == []
    assert "result_key" not in result.workflow.execution_plan[0].inputs


def test_binder_uses_objective_constrained_reusable_binding_as_preference() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_002",
            task_signature="phase1::family=t0_general::caps=cap_write::fail=none::goal=write_report",
            capability_skeleton=["cap_write"],
            recommended_bindings={"cap_write": "writer_tool"},
            recommended_inputs={},
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_014", user_goal="write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="writer_tool", description="writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": ["write_tool", "writer_tool"],
                "ideal_tool_calls": 1,
                "milestones": ["write report"],
            }
        ),
    )

    result = planner.plan(request)

    assert result.workflow.execution_plan[0].tool_id == "writer_tool"


def test_binding_prior_reuse_keeps_binding_preference_without_injecting_inputs() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_binding_prior_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "writer_tool"},
            recommended_inputs={"cap_retrieve": {"result_key": "cached_result"}},
            metadata={
                "failure_context": "none",
                "required_state_slots": [],
                "reuse_application_hint": "binding_prior",
                "utility_gain_score": 0.0,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_binding_prior_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="writer_tool", description="writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            user_style={
                "tool_allow_list": ["search_tool", "write_tool", "writer_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    assert next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write").tool_id == "writer_tool"
    assert "result_key" not in next(step for step in result.workflow.execution_plan if step.capability_id == "cap_retrieve").inputs
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "binding_prior"
    assert result.workflow.metadata["reusable_context"]["utility_gain_score"] == 0.0


def test_continuation_prior_reuse_attaches_structured_step_hints() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_continuation_prior_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={},
            continuation_hints=[
                {
                    "kind": "patch_then_retry_same_step",
                    "trigger_repair_type": "rebind_args",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "patched_input_keys": ["target_path"],
                },
                {
                    "kind": "fallback_to_backup_then_resume",
                    "trigger_repair_type": "switch_tool",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "backup_tool_id": "backup_write_tool",
                },
            ],
            metadata={
                "failure_context": "none",
                "required_state_slots": [],
                "semantic_reuse_family": "contact_edit",
                "reuse_application_hint": "continuation_prior",
                "utility_gain_score": 0.3,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_continuation_prior_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="backup writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            reusable_asset_ids=["asset_ws_continuation_prior_001"],
            user_style={
                "task_family": "contact_edit__pair00",
                "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert result.workflow.metadata["reusable_context"]["reuse_application"] == "continuation_prior"
    assert write_step.metadata["continuation_missing_input_keys"] == ["target_path"]
    assert write_step.metadata["continuation_backup_tool_id"] == "backup_write_tool"
    assert len(write_step.metadata["continuation_hints"]) == 2


def test_cross_family_transfer_reuse_does_not_attach_continuation_hints() -> None:
    asset_registry = InMemoryAssetRegistry()
    asset_registry.upsert(
        SimpleNamespace(
            snippet_id="asset_ws_continuation_cross_family_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={},
            continuation_hints=[
                {
                    "kind": "fallback_to_backup_then_resume",
                    "trigger_repair_type": "switch_tool",
                    "capability_id": "cap_write",
                    "tool_id": "write_tool",
                    "backup_tool_id": "backup_write_tool",
                }
            ],
            metadata={
                "failure_context": "none",
                "required_state_slots": [],
                "semantic_reuse_family": "contact_edit",
                "reuse_application_hint": "continuation_prior",
                "utility_gain_score": 0.3,
            },
        )
    )
    planner = build_planner(asset_registry=asset_registry)
    request = PlanningRequest(
        task=TaskSpec(task_id="task_cross_family_continuation_001", user_goal="retrieve and write report", constraints=TaskConstraints()),
        context=WorkflowContext(
            candidate_tools=[
                ToolSpec(tool_id="search_tool", description="search"),
                ToolSpec(tool_id="write_tool", description="write"),
                ToolSpec(tool_id="backup_write_tool", description="backup writer"),
            ]
        ),
        hints=PlanningHints(
            allow_reuse=True,
            reusable_asset_ids=["asset_ws_continuation_cross_family_001"],
            user_style={
                "task_family": "holiday_time__pair00",
                "tool_allow_list": ["search_tool", "write_tool", "backup_write_tool"],
                "ideal_tool_calls": 2,
            },
        ),
    )

    result = planner.plan(request)

    write_step = next(step for step in result.workflow.execution_plan if step.capability_id == "cap_write")
    assert "continuation_hints" not in write_step.metadata
    reusable_context = result.workflow.metadata.get("reusable_context", {})
    assert reusable_context.get("continuation_hints", []) == []
