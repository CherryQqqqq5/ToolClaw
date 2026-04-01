from toolclaw.interaction.query_policy import QueryPolicy
from toolclaw.interaction.uncertainty_detector import UncertaintyReport


def test_query_policy_builds_approval_query() -> None:
    plan = QueryPolicy().decide_query(UncertaintyReport(primary_label="approval_needed", confidence=0.9))
    assert plan.ask is True
    assert plan.question_type == "approval"


def test_query_policy_skips_query_when_not_needed() -> None:
    plan = QueryPolicy().decide_query(UncertaintyReport(primary_label="recoverable_runtime_error", confidence=0.6))
    assert plan.ask is False
