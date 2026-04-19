from pathlib import Path

from toolclaw.benchmarks.tau2_compound_approval_repair import run_compound_ablation


def test_tau2_compound_approval_repair_ablation_shows_before_after_gap(tmp_path: Path) -> None:
    analysis = run_compound_ablation(tmp_path)

    assert analysis["aggregate"]["before"]["success_rate"] < analysis["aggregate"]["after"]["success_rate"]
    assert analysis["aggregate"]["before"]["max_user_turns_exceeded_rate"] > analysis["aggregate"]["after"]["max_user_turns_exceeded_rate"]
    assert analysis["aggregate"]["after"]["compound_query_rate"] > analysis["aggregate"]["before"]["compound_query_rate"]
    assert analysis["aggregate"]["after"]["compound_reply_rate"] > analysis["aggregate"]["before"]["compound_reply_rate"]

    case_map = {item["case_id"]: item for item in analysis["case_deltas"]}
    for case_id in (
        "tau2_compound_approval_target_path_001",
        "tau2_compound_approval_state_slot_001",
        "tau2_compound_approval_tool_switch_001",
    ):
        assert case_map[case_id]["before"]["success"] is False
        assert case_map[case_id]["after"]["success"] is True
        assert case_map[case_id]["after"]["compound_query_count"] == 1
        assert case_map[case_id]["after"]["compound_reply_count"] == 1

    control = case_map["tau2_compound_approval_only_control_001"]
    assert control["before"]["success"] is True
    assert control["after"]["success"] is True
