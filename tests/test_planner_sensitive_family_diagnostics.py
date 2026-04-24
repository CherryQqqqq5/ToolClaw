import importlib.util
from pathlib import Path


_SCORER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "score_toolsandbox_planner_sensitive.py"
_SPEC = importlib.util.spec_from_file_location("score_toolsandbox_planner_sensitive", _SCORER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_SCORER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SCORER)
family_diagnostics = _SCORER.family_diagnostics


def test_family_diagnostics_handles_missing_trace_and_partial_sequences():
    scored = [
        {
            "task_id": "planner_sensitive_check_01",
            "run_index": 1,
            "system": "a2_planner",
            "family": "check_modify_verify",
            "strict_scored_success": 0.0,
            "expected_capability_order": ["cap_check", "cap_modify", "cap_verify"],
            "actual_capability_order": ["cap_check"],
            "expected_tool_sequence": ["state_checker", "state_modifier", "change_verifier"],
            "actual_tool_sequence": ["state_checker"],
            "planner_observability": {
                "selected_capability_order_initial": ["cap_check"],
                "selected_capability_order_final": ["cap_check"],
                "bound_tool_order": ["state_checker"],
                "unresolved_capabilities": ["cap_modify"],
            },
            "planner_bypass": "false",
            "planner_bypass_source": "structured",
            "trace_status": "ok",
            "tool_sequence_match": 0.0,
        },
        {
            "task_id": "planner_sensitive_check_02",
            "run_index": 1,
            "system": "a1_recovery",
            "family": "check_modify_verify",
            "strict_scored_success": 0.0,
            "expected_capability_order": ["cap_check", "cap_modify", "cap_verify"],
            "actual_capability_order": [],
            "expected_tool_sequence": ["state_checker", "state_modifier", "change_verifier"],
            "actual_tool_sequence": [],
            "planner_observability": {},
            "planner_bypass": "unknown",
            "planner_bypass_source": "trace_missing",
            "trace_status": "trace_missing",
            "tool_sequence_match": 0.0,
        },
    ]

    report = family_diagnostics(scored)

    a2 = report["families"]["check_modify_verify"]["a2_planner"]
    assert a2["classification_counts"]["capability_intent_gap"] == 1
    assert a2["recommended_fix_scope_counts"]["capability_intent_rules"] == 1
    assert a2["examples"][0]["unresolved_capabilities"] == ["cap_modify"]

    a1 = report["families"]["check_modify_verify"]["a1_recovery"]
    assert a1["classification_counts"]["runtime_execution_gap"] == 1
    assert a1["recommended_fix_scope_counts"]["runtime_semantic_mock"] == 1
