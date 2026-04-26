import importlib.util
import sys
from pathlib import Path


def _load_script(name: str):
    module_path = Path(__file__).resolve().parents[1] / "scripts" / name
    scripts_dir = str(module_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
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

def test_toolsandbox_official_inventory_imports_source_and_external_flags() -> None:
    module = _load_script("inventory_toolsandbox_official_scenarios.py")

    inventory = module.build_inventory()

    assert inventory["inventory_is_evidence"] is False
    assert inventory["scenario_count"] >= 100
    assert inventory["requires_external_api_count"] > 0
    assert "search_weather_around_lat_lon" in inventory["rapidapi_tool_names"]
    assert inventory["category_counts"]["STATE_DEPENDENCY"] > 0
    assert any(row.get("initial_user_query") for row in inventory["scenarios"])
    assert any(row.get("scenario_source_file") for row in inventory["scenarios"])


def test_toolsandbox_coverage_ledger_tracks_export_and_external_dependency() -> None:
    module = _load_script("inventory_toolsandbox_official_scenarios.py")
    inventory = {
        "source_commit": "official-sha",
        "scenarios": [
            {
                "scenario_name": "included_native",
                "categories": ["SINGLE_TOOL_CALL"],
                "tool_allow_list": ["add_contact"],
                "tool_augmentation_list": [],
                "requires_external_api": False,
                "external_dependency_status": "python_native",
                "rapidapi_or_external_api_reason": "python_native_or_local_tools",
            },
            {
                "scenario_name": "missing_rapidapi",
                "categories": ["STATE_DEPENDENCY"],
                "tool_allow_list": ["search_weather_around_lat_lon"],
                "tool_augmentation_list": [],
                "requires_external_api": True,
                "external_dependency_status": "rapidapi",
                "rapidapi_or_external_api_reason": "rapidapi_backed_tools:search_weather_around_lat_lon",
            },
        ],
    }
    frozen_rows = [
        {
            "name": "included_native",
            "metadata": {"trajectory_dir": "traj/included_native", "result_summary_path": "result_summary.json"},
            "result_summary": {"traceback": None, "exception_type": None},
        },
        {"name": "unmatched_legacy_row", "metadata": {}},
    ]

    ledger = module.build_coverage_ledger(inventory, frozen_rows)

    assert ledger["manifest"]["inventory_count"] == 2
    assert ledger["manifest"]["frozen_export_count"] == 2
    assert ledger["manifest"]["included_in_frozen_export_count"] == 1
    assert ledger["manifest"]["excluded_from_frozen_export_count"] == 1
    assert ledger["manifest"]["coverage_ledger_is_evidence"] is False
    missing = next(row for row in ledger["scenarios"] if row["scenario_name"] == "missing_rapidapi")
    assert missing["excluded_reason"] == "external_api_or_not_in_legacy_frozen_export"
    assert missing["requires_external_api"] is True
    assert ledger["unmatched_frozen_export_rows"][0]["name"] == "unmatched_legacy_row"


def test_toolsandbox_coverage_doc_warns_legacy_subset_not_complete() -> None:
    module = _load_script("inventory_toolsandbox_official_scenarios.py")
    inventory = {"scenarios": []}
    ledger = {
        "manifest": {
            "inventory_count": 2,
            "frozen_export_count": 1,
            "included_in_frozen_export_count": 1,
            "excluded_from_frozen_export_count": 1,
            "coverage_rate": 0.5,
            "requires_external_api_count": 1,
            "unmatched_frozen_export_row_count": 0,
        },
        "scenarios": [
            {"scenario_name": "a", "categories": ["SINGLE_TOOL_CALL"], "included_in_frozen_export": True, "requires_external_api": False},
            {"scenario_name": "b", "categories": ["STATE_DEPENDENCY"], "included_in_frozen_export": False, "requires_external_api": True, "rapidapi_or_external_api_reason": "rapidapi_backed_tools:search_stock"},
        ],
    }

    doc = module.render_coverage_doc(inventory, ledger)

    assert "not experimental evidence" in doc
    assert "Do not call the current frozen export a complete official ToolSandbox benchmark" in doc
    assert "legacy frozen official-run subset" in doc
    assert "rapidapi_backed_tools:search_stock" in doc

def test_reuse_v3_candidate_rejection_audit_counts_buckets() -> None:
    module = _load_script("audit_toolsandbox_reuse_v3_candidates.py")
    inventory = {"scenario_count": 4, "scenarios": []}
    ledger = {
        "scenarios": [
            {"scenario_name": "included_a", "included_in_frozen_export": True, "requires_external_api": False},
            {"scenario_name": "included_b", "included_in_frozen_export": True, "requires_external_api": False},
            {"scenario_name": "external_missing", "included_in_frozen_export": False, "requires_external_api": True, "rapidapi_or_external_api_reason": "rapidapi_backed_tools:search_stock"},
            {"scenario_name": "native_missing", "included_in_frozen_export": False, "requires_external_api": False},
        ],
        "unmatched_frozen_export_rows": [],
    }
    frozen_rows = [
        {"name": "included_a", "tool_allow_list": ["tool.a"], "categories": ["STATE_DEPENDENCY", "MULTIPLE_TOOL_CALL"], "result_summary": {"success": True}},
        {"name": "included_b", "tool_allow_list": ["tool.a"], "categories": ["STATE_DEPENDENCY", "MULTIPLE_TOOL_CALL"], "result_summary": {"success": True}},
        {"name": "singleton", "tool_allow_list": ["tool.b"], "categories": ["SINGLE_TOOL_CALL"], "result_summary": {"success": True}},
        {"name": "no_signature", "tool_allow_list": [], "categories": ["SINGLE_TOOL_CALL"], "result_summary": {}},
    ]
    candidates = [
        {"family_id": "exact", "claim_scope": "exact_match_cost", "claim_inclusion": False, "claim_exclusion_reason": "awaiting_pilot_headroom_confirmation", "signature_key": "sig"},
        {"family_id": "control", "claim_scope": "control_no_headroom", "claim_inclusion": False, "signature_key": "sig2"},
        {"family_id": "transfer", "claim_scope": "transfer_control", "claim_inclusion": False, "pair_type": "same_pattern_transfer", "signature_key": "sig3"},
    ]

    audit = module.build_audit(
        inventory=inventory,
        ledger=ledger,
        frozen_rows=frozen_rows,
        candidates=candidates,
        final_rows=[],
        candidates_manifest={"family_count": 3, "potential_exact_candidate_count": 1},
        final_manifest={"formal_source_status": "awaiting_pilot_confirmation", "statistical_claim_allowed": False},
    )

    assert audit["audit_is_evidence"] is False
    assert audit["summary"]["inventory_count"] == 4
    assert audit["summary"]["candidate_family_count"] == 3
    assert audit["summary"]["selected_exact_candidates"] == 1
    assert audit["summary"]["selected_no_headroom_controls"] == 1
    assert audit["summary"]["selected_transfer_controls"] == 1
    assert audit["summary"]["final_formal_family_count"] == 0
    assert audit["rejection_bucket_counts"]["external_api_only_no_trace"] == 1
    assert audit["rejection_bucket_counts"]["rejected_no_headroom_static"] == 1
    assert audit["rejection_bucket_counts"]["transfer_only"] == 1
    assert audit["rejection_bucket_counts"]["awaiting_pilot"] == 1
    assert audit["rejection_bucket_counts"]["final_source_empty_pending_pilot"] == 1
    assert audit["gate_gaps"]["potential_exact_candidate_gap_before_pilot"] == 11


def test_reuse_v3_candidate_rejection_markdown_keeps_claim_pending() -> None:
    module = _load_script("audit_toolsandbox_reuse_v3_candidates.py")
    audit = {
        "summary": {
            "inventory_count": 1032,
            "frozen_export_count": 88,
            "matched_frozen_rows": 88,
            "candidate_family_count": 34,
            "selected_exact_candidates": 7,
            "selected_no_headroom_controls": 26,
            "selected_transfer_controls": 1,
            "final_formal_family_count": 0,
            "formal_source_status": "awaiting_pilot_confirmation",
        },
        "rejection_bucket_counts": {"awaiting_pilot": 7, "rejected_no_headroom_static": 26},
        "gate_gaps": {"final_exact_claim_family_gap": 12, "pilot_confirmed_headroom_gap": 10},
    }

    md = module.render_markdown(audit)

    assert "not benchmark evidence" in md
    assert "final formal families: `0`" in md
    assert "No reuse claim should be marked supported" in md
    assert "core reproducible official-run export" in md

def test_toolsandbox_core_reproducible_filter_excludes_external_and_unresolvable() -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")
    inventory = {
        "scenarios": [
            {"scenario_name": "native_ok", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": ["add_contact"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "rapidapi", "requires_external_api": True, "external_dependency_status": "rapidapi", "tool_allow_list": ["search_stock"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "missing_tool", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": [], "milestone_count": 1, "categories": []},
            {"scenario_name": "unresolvable", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": ["add_contact"], "milestone_count": 1, "categories": []},
        ]
    }

    payload = module.core_filter_rows(inventory, resolvable_names={"native_ok"})

    assert payload["filter_is_evidence"] is False
    assert payload["inventory_count"] == 4
    assert payload["eligible_core_candidate_count"] == 1
    assert payload["core_candidate_count"] == 1
    assert payload["selected_count_after_limit"] == 1
    assert payload["selected_scenarios"][0]["scenario_name"] == "native_ok"
    assert payload["limit_applied"] is False
    assert payload["limit_truncated_candidate_count"] == 0
    assert payload["true_excluded_count"] == 3
    assert payload["excluded_count"] == payload["true_excluded_count"]
    assert payload["excluded_reason_counting"] == "multi_label_non_exclusive"
    assert payload["excluded_reason_counts"]["requires_external_api"] == 1
    assert payload["excluded_reason_counts"]["missing_tool_allow_list"] == 1
    assert payload["excluded_reason_counts"]["official_scenario_unresolvable"] == 3
    assert payload["primary_excluded_reason_counts"] == {
        "missing_tool_allow_list": 1,
        "official_scenario_unresolvable": 1,
        "requires_external_api": 1,
    }
    assert sum(payload["primary_excluded_reason_counts"].values()) == payload["excluded_count"]


def test_toolsandbox_core_reproducible_filter_limit_tracks_truncated_candidates() -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")
    inventory = {
        "scenarios": [
            {"scenario_name": "native_a", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": ["add_contact"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "native_b", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": ["add_contact"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "native_c", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": ["add_contact"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "rapidapi", "requires_external_api": True, "external_dependency_status": "rapidapi", "tool_allow_list": ["search_stock"], "milestone_count": 1, "categories": ["SINGLE_TOOL_CALL"]},
            {"scenario_name": "missing_tool", "requires_external_api": False, "external_dependency_status": "python_native", "tool_allow_list": [], "milestone_count": 1, "categories": []},
        ]
    }

    payload = module.core_filter_rows(
        inventory,
        resolvable_names={"native_a", "native_b", "native_c", "rapidapi", "missing_tool"},
        limit=1,
    )

    assert payload["inventory_count"] == 5
    assert payload["eligible_core_candidate_count"] == 3
    assert payload["core_candidate_count"] == 3
    assert payload["selected_count_after_limit"] == 1
    assert len(payload["selected_scenarios"]) == 1
    assert payload["limit_applied"] is True
    assert payload["limit_truncated_candidate_count"] == 2
    assert payload["true_excluded_count"] == 2
    assert payload["excluded_count"] == 2
    assert payload["primary_excluded_reason_counts"] == {
        "missing_tool_allow_list": 1,
        "requires_external_api": 1,
    }
    assert sum(payload["primary_excluded_reason_counts"].values()) == payload["excluded_count"]



def test_toolsandbox_core_reproducible_rejects_missing_execution_python(tmp_path) -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")

    missing_python = tmp_path / "missing-python"
    try:
        module._validate_toolsandbox_python(missing_python)
    except ValueError as exc:
        assert "ToolSandbox execution Python not found" in str(exc)
    else:
        raise AssertionError("missing execution Python should fail preflight")

def test_toolsandbox_core_reproducible_manifest_marks_dry_run_not_evidence() -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")
    manifest = module.build_manifest(
        filter_payload={"inventory_count": 4, "core_candidate_count": 1},
        export_rows=[],
        dry_run=True,
        run_dir=None,
        run_mode="new",
        out_prefix=module.ROOT_DIR / "data" / "toolsandbox.official_core_reproducible",
    )

    assert manifest["dry_run"] is True
    assert manifest["dataset_status"] == "dry_run_empty_export"
    assert manifest["requires_execute_before_benchmark"] is True
    assert manifest["core_export_is_evidence"] is False
    assert manifest["result_summary_present"] is False
    assert manifest["export_row_count"] == 0
    assert "no headline or reuse claim" in manifest["claim_boundary"]
    assert manifest["execution_environment"]["toolclaw_python_version"]
    assert manifest["execution_environment"]["openai_api_key_recorded"] is False


def test_toolsandbox_core_reproducible_manifest_requires_run_artifacts_for_evidence(tmp_path) -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")
    run_dir = tmp_path / "official_run"
    (run_dir / "trajectories").mkdir(parents=True)
    (run_dir / "result_summary.json").write_text("{}", encoding="utf-8")

    manifest = module.build_manifest(
        filter_payload={"inventory_count": 4, "core_candidate_count": 1},
        export_rows=[{"name": "native_ok"}],
        dry_run=False,
        run_dir=run_dir,
        run_mode="existing",
        out_prefix=module.ROOT_DIR / "data" / "toolsandbox.official_core_reproducible",
    )

    assert manifest["core_export_is_evidence"] is True
    assert manifest["dataset_status"] == "executed_core_export"
    assert manifest["requires_execute_before_benchmark"] is False
    assert manifest["result_summary_present"] is True
    assert manifest["trajectories_present"] is True
    assert manifest["export_row_count"] == 1


def test_toolsandbox_core_reproducible_manifest_marks_limited_execute_as_smoke(tmp_path) -> None:
    module = _load_script("export_toolsandbox_core_reproducible.py")
    run_dir = tmp_path / "official_run"
    (run_dir / "trajectories").mkdir(parents=True)
    (run_dir / "result_summary.json").write_text("{}", encoding="utf-8")

    manifest = module.build_manifest(
        filter_payload={"inventory_count": 4, "core_candidate_count": 3, "limit_applied": True},
        export_rows=[{"name": "native_ok"}],
        dry_run=False,
        run_dir=run_dir,
        run_mode="new",
        out_prefix=module.ROOT_DIR / "data" / "toolsandbox.official_core_reproducible",
    )

    assert manifest["dataset_status"] == "executed_core_smoke_export"
    assert manifest["core_export_is_evidence"] is False
    assert manifest["requires_execute_before_benchmark"] is True
    assert manifest["full_trajectory_messages_runtime_visible"] is False


def test_toolsandbox_formal_export_separates_runtime_and_scorer_messages() -> None:
    module = _load_script("prepare_toolsandbox_formal_dataset.py")
    row = {
        "sample_id": "scenario_a",
        "query": "Please add a contact.",
        "messages": [
            {"sender": "system", "recipient": "agent", "content": "You are an agent."},
            {"sender": "user", "recipient": "agent", "content": "Please add a contact."},
            {"sender": "assistant", "recipient": "tool", "content": "tool call"},
            {"sender": "tool", "recipient": "assistant", "content": "tool result"},
        ],
        "tool_allow_list": ["add_contact"],
        "candidate_tools": ["add_contact"],
        "categories": ["single_tool"],
        "normalized_categories": ["single_tool"],
        "milestones": [{"snapshot_constraint": "contact exists"}],
        "result_summary": {"similarity": 1.0},
        "reference_result_summary": {"similarity": 1.0},
        "has_ground_truth_messages": True,
        "has_ground_truth_milestones": True,
        "has_ground_truth_tools": True,
        "metadata": {"trajectory_dir": "/tmp/traj", "result_summary_path": "/tmp/result_summary.json"},
    }

    record = module.aligned_row_to_formal_record(row)

    assert record["messages"] == row["messages"][:2]
    assert record["runtime_messages"] == row["messages"][:2]
    assert record["scorer_gold_messages"] == row["messages"]
    assert record["runtime_visibility"]["full_messages_runtime_visible"] is False
    assert record["runtime_visibility"]["scorer_gold_runtime_visible"] is False


def test_toolsandbox_adapter_uses_runtime_messages_when_full_transcript_is_hidden() -> None:
    from toolclaw.benchmarks.adapters import ToolSandboxAdapter

    adapter = ToolSandboxAdapter()
    sample = adapter._make_sample(
        {
            "name": "scenario_a",
            "query": "Please add a contact.",
            "messages": [
                {"sender": "user", "recipient": "agent", "content": "Please add a contact."},
                {"sender": "assistant", "recipient": "tool", "content": "leaked tool call"},
            ],
            "runtime_messages": [{"sender": "user", "recipient": "agent", "content": "Please add a contact."}],
            "scorer_gold_messages": [
                {"sender": "user", "recipient": "agent", "content": "Please add a contact."},
                {"sender": "assistant", "recipient": "tool", "content": "leaked tool call"},
            ],
            "runtime_visibility": {"full_messages_runtime_visible": False, "scorer_gold_runtime_visible": False},
            "tool_allow_list": ["add_contact"],
            "candidate_tools": ["add_contact"],
            "categories": ["single_tool"],
            "milestones": [{"snapshot_constraint": "contact exists"}],
        },
        1,
    )

    task = adapter.to_eval_task(sample)

    assert task["messages"] == [{"sender": "user", "recipient": "agent", "content": "Please add a contact."}]
    assert task["metadata"]["messages"] == task["messages"]
    assert "leaked tool call" not in str(task)


def test_toolsandbox_core_export_validator_rejects_dry_run_and_accepts_executed_export() -> None:
    module = _load_script("validate_toolsandbox_core_export.py")
    row = {
        "name": "scenario_a",
        "query": "Please add a contact.",
        "messages": [{"sender": "user", "recipient": "agent", "content": "Please add a contact."}],
        "runtime_messages": [{"sender": "user", "recipient": "agent", "content": "Please add a contact."}],
        "scorer_gold_messages": [
            {"sender": "user", "recipient": "agent", "content": "Please add a contact."},
            {"sender": "assistant", "recipient": "tool", "content": "tool call"},
        ],
        "runtime_visibility": {"full_messages_runtime_visible": False, "scorer_gold_runtime_visible": False},
        "tool_allow_list": ["add_contact"],
        "candidate_tools": ["add_contact"],
        "milestones": [{"snapshot_constraint": "contact exists"}],
        "result_summary": {"similarity": 1.0},
        "metadata": {"trajectory_dir": "/tmp/traj", "result_summary_path": "/tmp/result_summary.json"},
    }
    dry_manifest = {
        "dry_run": True,
        "dataset_status": "dry_run_empty_export",
        "core_export_is_evidence": False,
        "result_summary_present": False,
        "trajectories_present": False,
        "export_row_count": 0,
        "requires_execute_before_benchmark": True,
        "full_trajectory_messages_runtime_visible": False,
    }
    executed_manifest = {
        "dry_run": False,
        "dataset_status": "executed_core_export",
        "core_export_is_evidence": True,
        "result_summary_present": True,
        "trajectories_present": True,
        "export_row_count": 1,
        "requires_execute_before_benchmark": False,
        "full_trajectory_messages_runtime_visible": False,
    }
    smoke_manifest = dict(executed_manifest, dataset_status="executed_core_smoke_export", core_export_is_evidence=False, requires_execute_before_benchmark=True)

    dry_result = module.validate_core_export([], dry_manifest)
    executed_result = module.validate_core_export([row], executed_manifest)
    smoke_result = module.validate_core_export([row], smoke_manifest)
    smoke_allowed_result = module.validate_core_export([row], smoke_manifest, allow_smoke=True)

    assert dry_result["pipeline_valid"] is False
    assert dry_result["freeze_ready"] is False
    assert "dry_run_export_not_freeze_ready" in dry_result["errors"]
    assert executed_result["pipeline_valid"] is True
    assert executed_result["freeze_ready"] is True
    assert smoke_result["pipeline_valid"] is False
    assert smoke_result["freeze_ready"] is False
    assert "limited_smoke_export_not_claim_evidence" in smoke_result["warnings"]
    assert smoke_allowed_result["pipeline_valid"] is True
    assert smoke_allowed_result["freeze_ready"] is False
    assert "limited_smoke_export_not_claim_evidence" in smoke_allowed_result["warnings"]
