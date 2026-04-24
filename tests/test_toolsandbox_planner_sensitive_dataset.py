import json
from collections import Counter
from pathlib import Path


DATASET = Path("data/toolsandbox_planner_sensitive_v1.jsonl")
DATASET_V2 = Path("data/toolsandbox_planner_sensitive_v2.jsonl")


def _rows():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_planner_sensitive_v1_dataset_shape_and_primary_guards():
    rows = _rows()
    assert len(rows) == 24
    assert Counter(row["family"] for row in rows) == {
        "retrieve_summarize_write": 6,
        "check_modify_verify": 6,
        "branch_select_execute": 6,
        "multi_source_merge_write": 6,
    }
    for row in rows:
        visible = row["planner_visible"]
        gold = row["scorer_gold"]
        assert row["planner_sensitive_protocol"] == "planner_sensitive_v1"
        assert "single_tool" not in visible.get("categories", [])
        assert visible.get("ideal_tool_calls") != 1
        assert "milestones" not in visible
        assert set(visible).isdisjoint(set(gold))
        assert len(visible["candidate_tools"]) > len(gold["expected_tool_sequence"])
        assert [tool["tool_id"] for tool in visible["candidate_tools"]] != gold["expected_tool_sequence"]


def test_planner_sensitive_manifest_records_anti_leakage_policy():
    manifest = json.loads(Path("data/toolsandbox_planner_sensitive_v1.manifest.json").read_text(encoding="utf-8"))
    assert manifest["protocol"] == "planner_sensitive_v1"
    assert manifest["sample_count"] == 24
    policy = manifest["anti_leakage_policy"]
    assert policy["scorer_gold_not_planner_visible"] is True
    assert policy["no_single_tool_primary_samples"] is True
    assert policy["no_ideal_tool_calls_one"] is True


def test_planner_sensitive_v2_dataset_is_family_balanced_and_guarded():
    rows = [json.loads(line) for line in DATASET_V2.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 40
    counts = Counter(row["family"] for row in rows)
    assert counts["retrieve_summarize_write"] <= 10
    assert counts["check_modify_verify"] >= 10
    assert counts["branch_select_execute"] >= 10
    assert counts["multi_source_merge_write"] >= 10
    for row in rows:
        visible = row["planner_visible"]
        gold = row["scorer_gold"]
        assert row["planner_sensitive_protocol"] == "planner_sensitive_v2"
        assert "single_tool" not in visible.get("categories", [])
        assert visible.get("ideal_tool_calls") != 1
        assert "milestones" not in visible
        assert set(visible).isdisjoint(set(gold))
