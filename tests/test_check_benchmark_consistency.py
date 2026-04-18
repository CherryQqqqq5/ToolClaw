import importlib.util
import sys
from pathlib import Path


def test_check_rows_uses_benchmark_scored_success_when_available() -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "check_benchmark_consistency.py"
    spec = importlib.util.spec_from_file_location("check_benchmark_consistency_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    scoreboard = {
        "systems": ["a1_recovery"],
        "num_samples": 1,
        "num_runs": 1,
        "runs": [
            {
                "system": "a1_recovery",
                "task_id": "tau2_approval_gate_001",
                "success": True,
                "score": {"success": False},
            }
        ],
    }
    per_system = {"a1_recovery": {"mean_success_rate": 0.0}}
    rows = [
        {
            "system": "a1_recovery",
            "task_id": "tau2_approval_gate_001",
            "run_index": "1",
            "success": "True",
        }
    ]
    errors: list[str] = []

    module._check_rows(rows, scoreboard, per_system, errors)

    assert errors == []
