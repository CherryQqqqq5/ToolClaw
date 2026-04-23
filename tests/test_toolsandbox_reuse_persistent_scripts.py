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
    assert summary["warm_reuse_hit_rate"] == 1.0
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
    assert summary["reuse_false_positive_rate"] == 1.0
    assert summary["paper_safe_reuse_evidence"] is False
