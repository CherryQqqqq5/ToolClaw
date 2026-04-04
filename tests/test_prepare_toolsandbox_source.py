import json
import os
import subprocess
import sys
from pathlib import Path


def test_prepare_toolsandbox_source_normalizes_raw_records_and_merges_results(tmp_path: Path) -> None:
    raw_source = tmp_path / "raw_toolsandbox.json"
    raw_source.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "name": "toolsandbox_raw_001",
                        "dialogue": [
                            {"role": "user", "text": "Find the details and send the update."},
                            {"role": "assistant", "text": "I will do that."},
                        ],
                        "allowed_tools": [{"name": "search_tool"}, {"name": "send_tool"}],
                        "tools": [{"name": "search_tool", "description": "Search"}, {"name": "send_tool"}],
                        "tags": ["Multiple Tool Call", "State Dependency"],
                        "expected_milestones": ["find details", "send update"],
                        "expected_turn_count": 3,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result_source = tmp_path / "results.jsonl"
    result_source.write_text(
        json.dumps(
            {
                "name": "toolsandbox_raw_001",
                "result_summary": {"similarity": 0.88, "milestone_mapping": [0, 1]},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "aligned.jsonl"
    cmd = [
        sys.executable,
        "scripts/prepare_toolsandbox_source.py",
        "--source",
        str(raw_source),
        "--result-source",
        str(result_source),
        "--out",
        str(out_path),
    ]
    completed = subprocess.run(
        cmd,
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert out_path.exists()

    rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["sample_id"] == "toolsandbox_raw_001"
    assert row["query"] == "Find the details and send the update."
    assert row["messages"][0]["sender"] == "user"
    assert row["tool_allow_list"] == ["search_tool", "send_tool"]
    assert row["candidate_tools"][0]["tool_id"] == "search_tool"
    assert row["categories"] == ["Multiple Tool Call", "State Dependency"]
    assert row["milestones"] == ["find details", "send update"]
    assert row["ideal_turn_count"] == 3
    assert row["result_summary"]["similarity"] == 0.88
