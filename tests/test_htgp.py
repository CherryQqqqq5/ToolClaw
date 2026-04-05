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
        workflow_overrides={"steps": {"step_01": {"inputs": {"target_path": "outputs/custom.txt"}}}},
    )

    result = planner.plan(request)
    restored = planner.request_from_workflow(result.workflow)

    assert restored.planner_mode == "benchmark_aware"
    assert restored.hints.reusable_asset_ids == ["asset_001"]
    assert restored.hints.prior_failures == ["binding_failure"]
    assert restored.hints.user_style["tool_allow_list"] == ["write_tool"]
    assert restored.workflow_overrides["steps"]["step_01"]["inputs"]["target_path"] == "outputs/custom.txt"


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
