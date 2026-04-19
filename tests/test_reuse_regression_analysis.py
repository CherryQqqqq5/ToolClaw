import json
from pathlib import Path

from toolclaw.benchmarks.reuse_regression_analysis import (
    analyze_outdir,
    classify_regression_case,
    metric_degradation,
)


def _write_trace(path: Path, *, preflight_missing_assets=None, user_queries=0, repair_types=None, tool_sequence=None, stop_reason="success_criteria_satisfied") -> None:
    preflight_missing_assets = list(preflight_missing_assets or [])
    repair_types = list(repair_types or [])
    tool_sequence = list(tool_sequence or ["search_tool", "write_tool"])
    events = [
        {
            "event_type": "preflight_check",
            "output": {"missing_assets": preflight_missing_assets},
        }
    ]
    for tool_id in tool_sequence:
        events.append({"event_type": "tool_call", "tool_id": tool_id})
    for _ in range(user_queries):
        events.append({"event_type": "user_query", "output": {"question": "patch?"}})
    for repair_type in repair_types:
        events.append(
            {
                "event_type": "repair_triggered",
                "output": {
                    "repair_type": repair_type,
                    "metadata": {"mapped_from_error_category": "ordering_failure" if repair_type == "replan_suffix" else "binding_failure" if repair_type == "rebind_args" else ""},
                },
            }
        )
    events.append({"event_type": "stop", "output": {"reason": stop_reason}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"events": events, "metrics": {"success": True}}), encoding="utf-8")


def _base_row(tmp_path: Path, *, system: str, trace_name: str, categories: str = '["insufficient_information"]', expected_recovery_path: str = "clarify_then_patch_then_retry", reused_artifact: str = "False") -> dict[str, str]:
    return {
        "run_index": "1",
        "task_id": "task_demo",
        "system": system,
        "execution_verified_success": "1.0",
        "success": "True",
        "milestone_similarity": "1.0",
        "hallucination_avoidance": "1.0",
        "state_dependency_score": "1.0",
        "interaction_efficiency": "1.0" if system == "a3_interaction" else "0.6",
        "tool_efficiency": "1.0",
        "turn_efficiency": "1.0" if system == "a3_interaction" else "0.6",
        "categories": categories,
        "expected_recovery_path": expected_recovery_path,
        "reused_artifact": reused_artifact,
        "trace_path": str((tmp_path / trace_name).relative_to(tmp_path)),
        "observed_error_type": "",
        "chosen_tool": "",
        "gold_tool": "",
    }


def test_classify_regression_case_marks_artifact_used_too_early(tmp_path: Path) -> None:
    _write_trace(tmp_path / "a3.json", preflight_missing_assets=["step_02.target_path"], repair_types=["rebind_args"])
    _write_trace(tmp_path / "a4.json", preflight_missing_assets=[])
    left = _base_row(tmp_path, system="a3_interaction", trace_name="a3.json")
    right = _base_row(tmp_path, system="a4_reuse", trace_name="a4.json", reused_artifact="True")

    case = classify_regression_case(outdir=tmp_path, left_row=left, right_row=right, degradation_metrics=metric_degradation(left, right))

    assert case.cause == "artifact_used_too_early"


def test_classify_regression_case_marks_interaction_override(tmp_path: Path) -> None:
    _write_trace(tmp_path / "a3.json", preflight_missing_assets=["step_02.target_path"], user_queries=1, repair_types=["ask_user"])
    _write_trace(tmp_path / "a4.json", preflight_missing_assets=[], user_queries=0)
    left = _base_row(tmp_path, system="a3_interaction", trace_name="a3.json", categories='["multiple_user_turn"]', expected_recovery_path="ask_user_then_retry")
    right = _base_row(tmp_path, system="a4_reuse", trace_name="a4.json", categories='["multiple_user_turn"]', expected_recovery_path="ask_user_then_retry", reused_artifact="True")

    case = classify_regression_case(outdir=tmp_path, left_row=left, right_row=right, degradation_metrics=metric_degradation(left, right))

    assert case.cause == "artifact_overrode_interaction_repair"


def test_classify_regression_case_marks_selected_wrong(tmp_path: Path) -> None:
    _write_trace(tmp_path / "a3.json", tool_sequence=["search_tool", "write_tool"])
    _write_trace(tmp_path / "a4.json", tool_sequence=["search_tool", "backup_write_tool"])
    left = _base_row(tmp_path, system="a3_interaction", trace_name="a3.json", categories='["canonicalization"]')
    right = _base_row(tmp_path, system="a4_reuse", trace_name="a4.json", categories='["canonicalization"]', reused_artifact="True")
    left["chosen_tool"] = "write_tool"
    right["chosen_tool"] = "backup_write_tool"
    right["gold_tool"] = "write_tool"

    case = classify_regression_case(outdir=tmp_path, left_row=left, right_row=right, degradation_metrics=metric_degradation(left, right))

    assert case.cause == "artifact_selected_wrong"


def test_classify_regression_case_marks_binding_or_ordering_regression(tmp_path: Path) -> None:
    _write_trace(tmp_path / "a3.json")
    _write_trace(tmp_path / "a4.json", repair_types=["replan_suffix"])
    left = _base_row(tmp_path, system="a3_interaction", trace_name="a3.json", categories='["state_dependency"]')
    right = _base_row(tmp_path, system="a4_reuse", trace_name="a4.json", categories='["state_dependency"]', reused_artifact="True")
    right["observed_error_type"] = "ordering_failure"

    case = classify_regression_case(outdir=tmp_path, left_row=left, right_row=right, degradation_metrics=metric_degradation(left, right))

    assert case.cause == "artifact_caused_binding_or_ordering"


def test_analyze_outdir_falls_back_to_comparison_csv(tmp_path: Path) -> None:
    _write_trace(tmp_path / "a3.json", preflight_missing_assets=["step_02.target_path"], repair_types=["rebind_args"])
    _write_trace(tmp_path / "a4.json", preflight_missing_assets=[])
    left = _base_row(tmp_path, system="a3_interaction", trace_name="a3.json")
    right = _base_row(tmp_path, system="a4_reuse", trace_name="a4.json", reused_artifact="True")
    comparison_path = tmp_path / "comparison.csv"
    comparison_path.write_text(
        "\n".join(
            [
                ",".join(left.keys()),
                ",".join(str(value) for value in left.values()),
                ",".join(str(value) for value in right.values()),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    analysis = analyze_outdir(tmp_path)

    assert analysis["paired_case_count"] == 1
    assert analysis["regression_case_count"] == 1
    assert analysis["cause_counts"] == {"artifact_used_too_early": 1}


def test_analyze_outdir_reads_comparison_from_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "run_02"
    _write_trace(run_dir / "a3.json", preflight_missing_assets=["step_02.target_path"], repair_types=["rebind_args"])
    _write_trace(run_dir / "a4.json", preflight_missing_assets=[])
    left = _base_row(tmp_path, system="a3_interaction", trace_name="runs/run_02/a3.json")
    right = _base_row(tmp_path, system="a4_reuse", trace_name="runs/run_02/a4.json", reused_artifact="True")
    comparison_path = run_dir / "comparison.csv"
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.write_text(
        "\n".join(
            [
                ",".join(left.keys()),
                ",".join(str(value) for value in left.values()),
                ",".join(str(value) for value in right.values()),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "experiment_manifest.json").write_text(
        json.dumps({"comparison_path": str(comparison_path.resolve())}),
        encoding="utf-8",
    )

    analysis = analyze_outdir(tmp_path)

    assert analysis["paired_case_count"] == 1
    assert analysis["regression_case_count"] == 1
    assert analysis["cause_counts"] == {"artifact_used_too_early": 1}
