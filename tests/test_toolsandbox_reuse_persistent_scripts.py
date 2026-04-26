import importlib.util
import sys
from pathlib import Path


def _load_script(name: str):
    module_path = Path(__file__).resolve().parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reuse_persistent_derive_pairs_pass1_and_pass2() -> None:
    module = _load_script("derive_toolsandbox_reuse_persistent.py")
    rows = [
        {
            "name": "email_update__pass1",
            "messages": [{"role": "user", "content": "compile an email update"}],
            "candidate_tools": ["mail.search", "mail.send"],
            "categories": ["state_dependency"],
        },
        {
            "name": "email_update__pass2",
            "messages": [{"role": "user", "content": "send the similar email update"}],
            "candidate_tools": ["mail.search", "mail.send"],
            "categories": ["state_dependency"],
        },
    ]

    dataset, errors = module._pair_rows(rows)

    assert errors == []
    assert len(dataset) == 1
    pair = dataset[0]
    assert pair["family_id"] == "email_update"
    assert pair["pass1_compile"]["metadata"]["reuse_stage"] == "pass1_compile"
    assert pair["pass2_eval"]["metadata"]["reuse_stage"] == "pass2_eval"
    assert pair["anti_leakage"]["passed"] is True


def test_reuse_persistent_scorer_accepts_clean_warm_cost_reduction() -> None:
    module = _load_script("score_toolsandbox_reuse_persistent.py")
    rows = [
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_cold",
            "reuse_target_family": "email_update",
            "success": "true",
            "tool_calls": "3",
            "user_turns": "1",
            "repair_actions": "2",
            "wall_clock_ms": "30",
            "reused_artifact": "false",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_warm",
            "reuse_target_family": "email_update",
            "reuse_source_family": "email_update",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "wall_clock_ms": "10",
            "reused_artifact": "true",
            "reuse_tier": "exact_match_reuse",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_sham",
            "reuse_target_family": "email_update",
            "success": "true",
            "tool_calls": "3",
            "user_turns": "1",
            "repair_actions": "2",
            "wall_clock_ms": "30",
            "reused_artifact": "false",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a3_interaction",
            "reuse_target_family": "email_update",
            "success": "true",
            "tool_calls": "3",
            "user_turns": "1",
            "repair_actions": "2",
            "wall_clock_ms": "30",
            "reused_artifact": "false",
        },
    ]

    effects = module._pair_effects(rows)
    stats = module._stat_tests(effects)
    summary = module._claim_summary(
        rows=rows,
        effects=effects,
        stats=stats,
        manifest={"registry_preflight_passed": True, "family_count": 1, "statistical_claim_allowed": True},
    )

    assert len(effects) == 1
    assert effects[0]["repair_reduction"] == 2.0
    assert effects[0]["turn_reduction"] == 1.0
    assert effects[0]["tool_call_reduction"] == 2.0
    assert summary["paper_safe_reuse_evidence"] is True
    assert summary["reuse_scope"] == "exact"
    assert summary["headroom_filter_passed"] is True
    assert summary["warm_claim_reuse_hit_rate"] == 1.0
    assert summary["warm_reuse_hit_rate"] == 1.0
    assert summary["warm_exact_reuse_hit_rate"] == 1.0
    assert summary["warm_correct_source_match_rate"] == 1.0
    assert summary["sham_false_positive_rate"] == 0.0


def test_reuse_persistent_scorer_blocks_sham_false_positive() -> None:
    module = _load_script("score_toolsandbox_reuse_persistent.py")
    rows = [
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_cold",
            "reuse_target_family": "email_update",
            "success": "true",
            "tool_calls": "3",
            "user_turns": "1",
            "repair_actions": "2",
            "wall_clock_ms": "30",
            "reused_artifact": "false",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_warm",
            "reuse_target_family": "email_update",
            "reuse_source_family": "email_update",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "wall_clock_ms": "10",
            "reused_artifact": "true",
            "reuse_tier": "exact_match_reuse",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_sham",
            "reuse_target_family": "email_update",
            "reuse_source_family": "calendar_lookup",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "wall_clock_ms": "10",
            "reused_artifact": "true",
            "reuse_tier": "cross_family_transfer_reuse",
        },
    ]

    effects = module._pair_effects(rows)
    summary = module._claim_summary(
        rows=rows,
        effects=effects,
        stats=module._stat_tests(effects),
        manifest={"registry_preflight_passed": True, "family_count": 1, "statistical_claim_allowed": True},
    )

    assert summary["sham_false_positive_rate"] == 1.0
    assert summary["sham_transfer_reuse_hit_rate"] == 1.0
    assert summary["reuse_false_positive_rate"] == 1.0
    assert "sham_false_positive_rate_above_0.05" in summary["gate_failures"]
    assert summary["paper_safe_reuse_evidence"] is False


def test_reuse_persistent_scorer_blocks_no_headroom_pairs() -> None:
    module = _load_script("score_toolsandbox_reuse_persistent.py")
    rows = [
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_cold",
            "reuse_target_family": "holiday_time",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "reused_artifact": "false",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_warm",
            "reuse_target_family": "holiday_time",
            "reuse_source_family": "holiday_time",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "reused_artifact": "true",
            "reuse_tier": "exact_match_reuse",
        },
        {
            "stage": "pass2_eval",
            "run_index": "1",
            "system": "a4_reuse_sham",
            "reuse_target_family": "holiday_time",
            "success": "true",
            "tool_calls": "1",
            "user_turns": "0",
            "repair_actions": "0",
            "reused_artifact": "false",
        },
    ]

    effects = module._pair_effects(rows)
    summary = module._claim_summary(
        rows=rows,
        effects=effects,
        stats=module._stat_tests(effects),
        manifest={"registry_preflight_passed": True, "family_count": 1, "statistical_claim_allowed": True},
    )

    assert summary["headroom_pair_count"] == 0
    assert summary["headroom_filter_passed"] is False
    assert "cold_headroom_filter_failed" in summary["gate_failures"]
    assert summary["paper_safe_reuse_evidence"] is False



def test_reuse_v3_inventory_imports_official_scenarios() -> None:
    module = _load_script("derive_toolsandbox_reuse_persistent_v3.py")

    inventory = module.load_official_inventory()

    assert inventory["inventory_is_evidence"] is False
    assert inventory["scenario_count"] >= 100
    categories = inventory["category_counts"]
    assert categories["STATE_DEPENDENCY"] > 0
    assert categories["INSUFFICIENT_INFORMATION"] > 0
    assert any(row.get("tool_allow_list") for row in inventory["scenarios"])


def test_reuse_v3_candidates_are_not_formal_evidence_without_pilot() -> None:
    module = _load_script("derive_toolsandbox_reuse_persistent_v3.py")
    frozen_rows = [
        {
            "name": "turn_on_cellular_low_battery_mode",
            "query": "Turn on cellular service even though low battery blocks it.",
            "categories": ["MULTIPLE_TOOL_CALL", "Single User Turn", "State Dependency", "No Distraction Tools"],
            "tool_allow_list": ["get_cellular_service_status", "set_cellular_service_status", "get_low_battery_mode_status", "set_low_battery_mode_status"],
            "messages": [
                {"sender": "SYSTEM", "recipient": "AGENT", "content": "system"},
                {"sender": "USER", "recipient": "AGENT", "content": "Turn cellular on"},
                {"sender": "AGENT", "recipient": "EXECUTION_ENVIRONMENT", "content": "gold tool call"},
            ],
            "milestones": [{"gold": True}],
            "result_summary": {"similarity": 1.0},
        },
        {
            "name": "turn_on_cellular_low_battery_mode_implicit",
            "query": "I have no cell signal; get it back on.",
            "categories": ["MULTIPLE_TOOL_CALL", "Single User Turn", "State Dependency", "No Distraction Tools"],
            "tool_allow_list": ["get_cellular_service_status", "set_cellular_service_status", "get_low_battery_mode_status", "set_low_battery_mode_status"],
            "messages": [{"sender": "USER", "recipient": "AGENT", "content": "No cell signal"}],
            "milestones": [{"gold": True}],
        },
    ]

    candidates = module.build_candidates(frozen_rows)
    final = module.build_final(candidates)

    assert len(candidates) == 1
    row = candidates[0]
    assert row["claim_scope"] == "exact_match_cost"
    assert row["claim_inclusion"] is False
    assert row["claim_exclusion_reason"] == "awaiting_pilot_headroom_confirmation"
    assert row["runtime_visibility"]["full_messages_runtime_visible"] is False
    assert row["pass1_compile"]["messages"][-1]["sender"] == "USER"
    assert "milestones" not in row["pass1_compile"]
    assert row["scorer_gold"]["pass1"]["milestones"] == [{"gold": True}]
    assert final == []


def test_reuse_runner_sanitizes_v3_runtime_visibility_and_sets_version() -> None:
    module = _load_script("run_toolsandbox_reuse_persistent.py")
    task = {
        "query": "Turn cellular on",
        "messages": [
            {"sender": "SYSTEM", "recipient": "AGENT", "content": "system"},
            {"sender": "USER", "recipient": "AGENT", "content": "Turn cellular on"},
            {"sender": "AGENT", "recipient": "EXECUTION_ENVIRONMENT", "content": "gold tool call"},
        ],
        "milestones": [{"gold": True}],
        "reference_result_summary": {"gold": True},
        "scorer_gold": {"expected": True},
        "runtime_visibility": {
            "full_messages_runtime_visible": False,
            "milestones_runtime_visible": False,
            "scorer_gold_runtime_visible": False,
        },
    }

    staged = module._stage_task(
        task,
        family_id="state_repair_cellular",
        stage="eval",
        pass_index=2,
        reuse_version="toolsandbox_reuse_persistent_v3",
    )

    assert [message["sender"] for message in staged["messages"]] == ["SYSTEM", "USER"]
    assert staged["milestones"] == []
    assert "reference_result_summary" not in staged
    assert "scorer_gold" not in staged
    assert staged["metadata"]["reuse_persistent_version"] == "toolsandbox_reuse_persistent_v3"
    assert staged["metadata"]["reuse_pass2_compile_allowed"] is False


def test_reuse_scorer_v3_controls_do_not_affect_primary_gates() -> None:
    module = _load_script("score_toolsandbox_reuse_persistent.py")
    rows = [
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_cold", "reuse_target_family": "primary", "success": "true", "tool_calls": "3", "user_turns": "1", "repair_actions": "2", "wall_clock_ms": "30", "reused_artifact": "false"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_warm", "reuse_target_family": "primary", "reuse_source_family": "primary", "success": "true", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "wall_clock_ms": "10", "reused_artifact": "true", "reuse_tier": "exact_match_reuse"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_sham", "reuse_target_family": "primary", "success": "true", "tool_calls": "3", "user_turns": "1", "repair_actions": "2", "wall_clock_ms": "30", "reused_artifact": "false"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_cold", "reuse_target_family": "no_headroom", "success": "true", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "wall_clock_ms": "10", "reused_artifact": "false"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_warm", "reuse_target_family": "no_headroom", "reuse_source_family": "no_headroom", "success": "true", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "wall_clock_ms": "10", "reused_artifact": "true", "reuse_tier": "exact_match_reuse"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_sham", "reuse_target_family": "no_headroom", "success": "true", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "wall_clock_ms": "10", "reused_artifact": "false"},
    ]
    family_metadata = {
        "primary": {"claim_scope": "exact_match_cost", "claim_inclusion": True},
        "no_headroom": {"claim_scope": "control_no_headroom", "claim_inclusion": False},
    }

    effects = module._pair_effects(rows, family_metadata=family_metadata)
    summary = module._claim_summary(
        rows=rows,
        effects=effects,
        stats=module._stat_tests(effects),
        manifest={"registry_preflight_passed": True, "family_count": 2, "statistical_claim_allowed": True},
    )

    assert summary["paper_safe_reuse_evidence"] is True
    assert summary["family_count"] == 1
    assert summary["headroom_pair_count"] == 1
    assert summary["control_no_headroom_summary"]["family_count"] == 1
    assert summary["control_no_headroom_summary"]["reductions_mean"]["tool_call_reduction"] == 0.0


def test_reuse_scorer_v3_transfer_control_does_not_inflate_exact_metrics() -> None:
    module = _load_script("score_toolsandbox_reuse_persistent.py")
    rows = [
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_cold", "reuse_target_family": "transfer", "success": "true", "tool_calls": "3", "user_turns": "1", "repair_actions": "2", "wall_clock_ms": "30", "reused_artifact": "false"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_warm", "reuse_target_family": "transfer", "reuse_source_family": "other", "success": "true", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "wall_clock_ms": "10", "reused_artifact": "true", "reuse_tier": "cross_family_transfer_reuse"},
        {"stage": "pass2_eval", "run_index": "1", "system": "a4_reuse_sham", "reuse_target_family": "transfer", "success": "true", "tool_calls": "3", "user_turns": "1", "repair_actions": "2", "wall_clock_ms": "30", "reused_artifact": "false"},
    ]
    effects = module._pair_effects(rows, family_metadata={"transfer": {"claim_scope": "transfer_control", "claim_inclusion": False}})
    summary = module._claim_summary(
        rows=rows,
        effects=effects,
        stats=module._stat_tests(effects),
        manifest={"registry_preflight_passed": True, "family_count": 1, "statistical_claim_allowed": True},
    )

    assert summary["paper_safe_reuse_evidence"] is False
    assert summary["warm_exact_reuse_hit_rate"] == 0.0
    assert summary["transfer_control_summary"]["family_count"] == 1
    assert summary["overall_summary"]["by_system"]["a4_reuse_warm"]["transfer_reuse_hit_rate"] == 1.0
