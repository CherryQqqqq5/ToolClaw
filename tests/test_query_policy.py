from toolclaw.interaction.query_policy import QueryPolicy
from toolclaw.interaction.uncertainty_detector import UncertaintyReport


def test_query_policy_builds_approval_query() -> None:
    plan = QueryPolicy().decide_query(UncertaintyReport(primary_label="policy_approval", confidence=0.9))
    assert plan.ask is True
    assert plan.question_type == "approval"


def test_query_policy_skips_query_when_not_needed() -> None:
    plan = QueryPolicy().decide_query(UncertaintyReport(primary_label="recoverable_runtime_error", confidence=0.6))
    assert plan.ask is False


def test_query_policy_builds_missing_asset_query() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="missing_asset",
            confidence=0.9,
            metadata={"missing_input_keys": ["target_path"], "missing_assets": ["target_path"]},
        )
    )
    assert plan.ask is True
    assert plan.question_type == "target_path_patch"
    assert plan.patch_targets == {"target_path": "step.inputs.target_path"}


def test_query_policy_builds_branch_disambiguation_query() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="branch_disambiguation",
            confidence=0.8,
            metadata={"branch_options": ["primary_path", "fallback_path"]},
        )
    )
    assert plan.ask is True
    assert plan.question_type == "branch_choice"
    assert plan.response_schema["required"] == ["branch_choice"]
    assert plan.patch_targets == {"branch_choice": "state.selected_branch"}


def test_query_policy_does_not_build_branch_choice_without_branch_options() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="branch_disambiguation",
            confidence=0.8,
            metadata={"branch_options": [], "error_category": "environment_failure"},
        )
    )
    assert plan.ask is True
    assert plan.question_type == "tool_or_asset_hint"
    assert "branch_choice" not in plan.response_schema["properties"]
    assert plan.patch_targets["fallback_execution_path"] == "step.inputs.target_path"


def test_query_policy_builds_tool_switch_query() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="tool_mismatch",
            confidence=0.8,
            metadata={"alternative_tool_ids": ["backup_write_tool"]},
        )
    )
    assert plan.ask is True
    assert plan.question_type == "tool_switch"
    assert plan.response_schema["required"] == ["tool_id"]
    assert plan.patch_targets == {"tool_id": "binding.primary_tool"}


def test_query_policy_builds_environment_resolution_query() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="environment_unavailable",
            confidence=0.7,
            metadata={"alternative_tool_ids": ["backup_write_tool"]},
        )
    )
    assert plan.ask is True
    assert plan.question_type == "environment_resolution"
    assert "clear_failure_flag" in plan.response_schema["properties"]


def test_query_policy_builds_compound_approval_and_target_path_query() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="policy_approval",
            confidence=0.95,
            metadata={
                "missing_input_keys": ["target_path"],
                "missing_assets": ["target_path"],
                "constraint_requires_approval": True,
            },
        )
    )

    assert plan.ask is True
    assert plan.question_type == "approval_and_patch"
    assert plan.response_schema["required"] == ["approved", "target_path"]
    assert plan.patch_targets == {
        "target_path": "step.inputs.target_path",
        "approved": "policy.approved",
    }


def test_query_policy_builds_compound_approval_and_state_slot_query_on_last_turn() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="policy_approval",
            confidence=0.95,
            metadata={
                "missing_assets": ["approval_note"],
                "constraint_requires_approval": True,
                "remaining_user_turns": 1,
            },
        )
    )

    assert plan.ask is True
    assert plan.question_type == "approval_and_patch"
    assert plan.response_schema["required"] == ["approved", "approval_note"]
    assert plan.patch_targets == {
        "approval_note": "state.approval_note",
        "approved": "policy.approved",
    }
    assert plan.urgency == "critical"


def test_query_policy_keeps_approval_only_when_no_concrete_repair_payload_exists() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="policy_approval",
            confidence=0.95,
            metadata={
                "alternative_tool_ids": ["write_tool"],
                "constraint_requires_approval": True,
            },
        )
    )

    assert plan.ask is True
    assert plan.question_type == "approval"
    assert plan.response_schema["required"] == ["approved"]
    assert plan.patch_targets == {"approved": "policy.approved"}


def test_query_policy_wraps_tool_switch_with_approval_when_required() -> None:
    plan = QueryPolicy().decide_query(
        UncertaintyReport(
            primary_label="tool_mismatch",
            confidence=0.82,
            metadata={
                "alternative_tool_ids": ["backup_write_tool"],
                "constraint_requires_approval": True,
            },
        )
    )

    assert plan.ask is True
    assert plan.question_type == "approval_and_patch"
    assert "approved" in plan.response_schema["required"]
    assert "tool_id" in plan.response_schema["properties"]
    assert plan.patch_targets["approved"] == "policy.approved"
