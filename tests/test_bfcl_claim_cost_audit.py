from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_bfcl_claim_cost_module",
        ROOT_DIR / "scripts" / "audit_bfcl_claim_cost.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bfcl_claim_cost_audit_flags_matrix_gate_mismatch_and_token_proxy() -> None:
    module = _load_module()
    audit = module.build_audit(
        comparison_rows=[
            {"system": "a0_baseline", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "token_cost": "0.25"},
            {"system": "a2_planner", "tool_calls": "2", "user_turns": "1", "repair_actions": "1", "token_cost": "0.75"},
        ],
        official_scoreboard={
            "per_system": {
                "a0_baseline": {
                    "num_rows": 2,
                    "official_bfcl_eval_success": 0.5,
                    "official_bfcl_eval_tool_selection_correctness": 0.8,
                    "official_bfcl_eval_argument_correctness": 0.5,
                    "official_bfcl_eval_structure_correctness": 0.7,
                },
                "a2_planner": {
                    "num_rows": 2,
                    "official_bfcl_eval_success": 0.4,
                    "official_bfcl_eval_tool_selection_correctness": 0.6,
                    "official_bfcl_eval_argument_correctness": 0.4,
                    "official_bfcl_eval_structure_correctness": 0.65,
                },
            }
        },
        claim_summary={
            "suite": "bfcl_fc_core",
            "headline_supported": False,
            "headline_blockers": ["a2_success_not_above_a0"],
            "bfcl_guard_claim_gates": {
                "reuse_claim_enabled_for_bfcl": False,
                "a4_interpreted_as_guarded_execution_variant_only": True,
                "full_suite_gates": {
                    "a2_tool_selection_ge_a0": False,
                    "a2_success_ge_a0": False,
                },
                "failure_bucket_counts_by_system": {
                    "a0_baseline": {"missing_required": 1, "wrong_func_name": 0},
                    "a2_planner": {"missing_required": 2, "wrong_func_name": 0},
                },
            },
        },
        claim_matrix={
            "claims": {
                "planner_binding_headline": {"status": "headline_not_supported_mechanism_only"},
                "bfcl_exact_function_guard": {"status": "unsupported_after_candidate_preservation_rerun_case_d"},
                "bfcl_missing_required_guarded_reduction": {"status": "unsupported_after_candidate_preservation_rerun_case_d"},
            },
            "suites": {
                "bfcl_fc_core": {
                    "status": "implemented",
                    "claim_strength": "limitation",
                    "paper_role": "limitation_with_candidate_coverage_diagnostic",
                    "reuse_claim_enabled_for_bfcl": False,
                    "a4_interpreted_as_guarded_execution_variant_only": True,
                    "guarded_rerun_observed": {
                        "a2_tool_selection_ge_a0": True,
                        "a2_success_ge_a0": False,
                    },
                }
            },
        },
        selected_correct_summary={
            "summary": {
                "selected_correct_failure_bucket_counts": {
                    "missing_required": 3,
                    "wrong_arg_value": 4,
                }
            },
            "by_system": {
                "a2_planner": {
                    "selected_correct_failure_bucket_counts": {
                        "missing_required": 2,
                        "wrong_arg_value": 1,
                    }
                }
            },
        },
    )

    assert audit["audit_only"] is True
    assert audit["token_cost_semantics"]["is_proxy"] is True
    assert "LLM tokens" in audit["token_cost_semantics"]["note"]
    assert audit["claim_summary_status"]["headline_blockers"] == ["a2_success_not_above_a0"]
    assert audit["gate_consistency"]["mismatch_count"] == 1
    rows = {row["gate"]: row for row in audit["gate_consistency"]["full_suite_gate_rows"]}
    assert rows["a2_tool_selection_ge_a0"]["consistent"] is False
    assert audit["failure_bucket_counts_by_system"]["a2_planner"]["missing_required"] == 2
    assert audit["selected_correct_failure_buckets"]["available"] is True
    assert audit["selected_correct_failure_buckets"]["summary_bucket_counts"]["wrong_arg_value"] == 4
    assert audit["selected_correct_failure_buckets"]["by_system_bucket_counts"]["a2_planner"]["missing_required"] == 2
    assert audit["per_system"]["a2_planner"]["missing_required_count"] == 2
    assert audit["per_system"]["a2_planner"]["avg_token_cost"] == 0.75
    assert "llm_tokens" not in json.dumps(audit).lower()


def test_bfcl_claim_cost_audit_cli_writes_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    comparison = tmp_path / "comparison.scored.csv"
    with comparison.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["system", "tool_calls", "user_turns", "repair_actions", "token_cost"])
        writer.writeheader()
        writer.writerow({"system": "a2_planner", "tool_calls": "1", "user_turns": "0", "repair_actions": "0", "token_cost": "0.1"})
    (tmp_path / "official_scoreboard.json").write_text(
        json.dumps(
            {
                "per_system": {
                    "a2_planner": {
                        "num_rows": 1,
                        "official_bfcl_eval_success": 0.0,
                        "official_bfcl_eval_tool_selection_correctness": 0.0,
                        "official_bfcl_eval_argument_correctness": 0.0,
                        "official_bfcl_eval_structure_correctness": 0.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "claim_summary.json").write_text(
        json.dumps(
            {
                "suite": "bfcl_fc_core",
                "headline_supported": False,
                "headline_blockers": ["a2_success_not_above_a0"],
                "bfcl_guard_claim_gates": {
                    "full_suite_gates": {"a2_success_ge_a0": False},
                    "failure_bucket_counts_by_system": {"a2_planner": {"missing_required": 1}},
                },
            }
        ),
        encoding="utf-8",
    )
    matrix = tmp_path / "paper_claim_matrix.yaml"
    matrix.write_text(
        json.dumps(
            {
                "claims": {"planner_binding_headline": {"status": "headline_not_supported_mechanism_only"}},
                "suites": {"bfcl_fc_core": {"guarded_rerun_observed": {"a2_success_ge_a0": False}}},
            }
        ),
        encoding="utf-8",
    )
    selected_correct = tmp_path / "bfcl_selected_correct_failure_summary.json"
    selected_correct.write_text(
        json.dumps(
            {
                "summary": {
                    "selected_correct_failure_bucket_counts": {
                        "selected_correct_success": 1,
                        "missing_required": 2,
                    }
                },
                "by_system": {
                    "a2_planner": {
                        "selected_correct_failure_bucket_counts": {
                            "missing_required": 2,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"

    monkeypatch.setattr(
        module.sys,
        "argv",
        [
            "audit_bfcl_claim_cost.py",
            "--comparison",
            str(comparison),
            "--official-scoreboard",
            str(tmp_path / "official_scoreboard.json"),
            "--claim-summary",
            str(tmp_path / "claim_summary.json"),
            "--claim-matrix",
            str(matrix),
            "--selected-correct-summary",
            str(selected_correct),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )

    module.main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["gate_consistency"]["all_consistent"] is True
    assert payload["failure_bucket_counts_by_system"]["a2_planner"]["missing_required"] == 1
    assert payload["selected_correct_failure_buckets"]["summary_bucket_counts"]["missing_required"] == 2
    markdown = output_md.read_text(encoding="utf-8")
    assert "avg_token_cost_proxy" in markdown
    assert "not raw LLM token count" in markdown
    assert "Failure Buckets by System" in markdown
    assert "| a2_planner | missing_required | 1 |" in markdown
    assert "Selected-Correct Arg/Shape Buckets" in markdown
    assert "| all | missing_required | 2 |" in markdown
