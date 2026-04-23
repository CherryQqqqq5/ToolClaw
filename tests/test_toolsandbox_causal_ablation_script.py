import importlib.util
import sys
from pathlib import Path


def test_toolsandbox_causal_ablation_analyzer_outputs_verdicts() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "analyze_toolsandbox_causal_ablation.py"
    spec = importlib.util.spec_from_file_location("toolsandbox_causal_ablation", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    rows = [
        {
            "system": "a3_full_interaction",
            "strict_scored_success_rate": "1.0",
            "execution_verified_success_rate": "1.0",
            "raw_execution_success_rate": "1.0",
            "repair_scored_success_rate": "0.5",
            "interaction_contract_satisfied": "1.0",
            "mean_user_queries": "1.0",
        },
        {
            "system": "a3_no_query",
            "strict_scored_success_rate": "0.0",
            "execution_verified_success_rate": "0.75",
            "raw_execution_success_rate": "0.75",
            "repair_scored_success_rate": "0.0",
            "interaction_contract_satisfied": "0.0",
            "mean_user_queries": "0.0",
        },
        {
            "system": "a3_noisy_user",
            "strict_scored_success_rate": "0.25",
            "execution_verified_success_rate": "0.25",
            "raw_execution_success_rate": "0.25",
            "repair_scored_success_rate": "0.0",
            "interaction_contract_satisfied": "1.0",
            "mean_user_queries": "1.0",
        },
        {
            "system": "a2_planner",
            "strict_scored_success_rate": "0.25",
            "execution_verified_success_rate": "0.25",
            "raw_execution_success_rate": "0.25",
            "repair_scored_success_rate": "0.0",
            "interaction_contract_satisfied": "1.0",
            "mean_user_queries": "0.0",
        },
    ]
    scoreboard = {
        "per_system_summary": {
            "a1_recovery": {
                "per_failtax": {
                    "ordering": {"success_rate": 0.5, "num_rows": 2},
                    "state": {"success_rate": 0.5, "num_rows": 2},
                }
            },
            "a2_planner": {
                "per_failtax": {
                    "ordering": {"success_rate": 0.75, "num_rows": 2},
                    "state": {"success_rate": 0.75, "num_rows": 2},
                }
            },
        }
    }

    summary = module.analyze(rows, scoreboard)

    assert summary["verdicts"]["interaction_query_contribution_supported"] is True
    assert summary["verdicts"]["interaction_not_cheating_supported"] is True
    assert summary["verdicts"]["htgp_structural_reduction_supported"] is True
