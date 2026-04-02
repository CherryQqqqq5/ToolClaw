from toolclaw.policy.policy_engine import PolicyEngine
from toolclaw.schemas.workflow import Workflow


def test_policy_engine_requires_confirmation_for_high_risk_or_explicit_approval() -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.requires_user_approval = True

    decision = PolicyEngine().evaluate_before_step(workflow.execution_plan[1], workflow, {})

    assert decision.allow is False
    assert decision.require_confirmation is True
    assert decision.reason == "approval_required"


def test_policy_engine_updates_budget_after_successful_step() -> None:
    workflow = Workflow.demo()
    decision = PolicyEngine().evaluate_after_step(workflow.execution_plan[0], workflow, {})

    assert decision.allow is True
    assert decision.state_patch["__budget_spent__"] > 0.0


def test_policy_engine_blocks_forbidden_actions() -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.forbidden_actions = ["write"]

    decision = PolicyEngine().evaluate_before_step(workflow.execution_plan[1], workflow, {})

    assert decision.allow is False
    assert decision.abort is True
    assert decision.reason == "forbidden_action"


def test_policy_engine_blocks_missing_permissions() -> None:
    workflow = Workflow.demo()
    workflow.context.environment.permissions.filesystem_write = False

    decision = PolicyEngine().evaluate_before_step(workflow.execution_plan[1], workflow, {})

    assert decision.allow is False
    assert decision.abort is True
    assert decision.reason == "permission_denied"


def test_policy_engine_blocks_when_time_limit_would_be_exceeded() -> None:
    workflow = Workflow.demo()
    workflow.task.constraints.time_limit = 100

    decision = PolicyEngine().evaluate_before_step(workflow.execution_plan[0], workflow, {})

    assert decision.allow is False
    assert decision.abort is True
    assert decision.reason == "time_limit_exceeded"
