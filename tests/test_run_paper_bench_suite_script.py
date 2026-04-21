import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=check,
    )


def _write_official_bfcl_wrapper(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--prepared-taskset", required=True)
parser.add_argument("--comparison", required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

with Path(args.comparison).open("r", encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))

results = []
for row in rows:
    task_id = row["task_id"]
    results.append(
        {
            "run_index": int(row["run_index"]),
            "task_id": task_id,
            "system": row["system"],
            "success": 1.0,
            "tool_selection_correctness": 1.0,
            "argument_correctness": 1.0,
            "structure_correctness": 1.0,
            "paper_safe": task_id != "unsupported_case",
            "unsupported_reasons": [] if task_id != "unsupported_case" else ["unsupported_case"],
        }
    )

payload = {
    "results": results,
    "unsupported_strata": [],
}
Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
""",
        encoding="utf-8",
    )


def _write_bfcl_source_dir(root: Path) -> Path:
    source_dir = root / "bfcl_source"
    source_dir.mkdir(parents=True, exist_ok=True)
    evaluator = source_dir / "official_bfcl_eval.py"
    _write_official_bfcl_wrapper(evaluator)

    fc_core = source_dir / "bfcl_v4.fc_core.aligned.jsonl"
    fc_core.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "sample_id": "bfcl_core_case",
                        "scenario": "bfcl",
                        "query": "Call weather_lookup with city=Paris.",
                        "candidate_tools": [
                            {
                                "tool_id": "weather_lookup",
                                "description": "Look up weather by city",
                                "parameters": {"city": "string"},
                            },
                            {
                                "tool_id": "calendar_lookup",
                                "description": "Look up calendar events",
                                "parameters": {"date": "string"},
                            },
                        ],
                        "constraints": {"max_tool_calls": 1},
                        "ideal_tool_calls": 1,
                        "expected_call_structure": {
                            "pattern": "serial",
                            "calls": [
                                {
                                    "tool_name": "weather_lookup",
                                    "arguments": {"city": "Paris"},
                                }
                            ],
                        },
                        "metadata": {
                            "benchmark": "bfcl",
                            "bfcl_track": "fc_core",
                            "bfcl_group": "non_live",
                            "bfcl_call_pattern": "serial",
                            "bfcl_language": "en",
                            "official_evaluator_supported": True,
                        },
                    }
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    agentic_ext = source_dir / "bfcl_v4.agentic_ext.aligned.jsonl"
    agentic_ext.write_text(
        json.dumps(
            {
                "sample_id": "bfcl_agentic_case",
                "scenario": "bfcl",
                "query": "Search the web for the latest weather note about Paris.",
                "candidate_tools": [
                    {
                        "tool_id": "web_search",
                        "description": "Search the web",
                        "parameters": {"query": "string"},
                    }
                ],
                "constraints": {"max_tool_calls": 1},
                "ideal_tool_calls": 1,
                "expected_call_structure": {
                    "pattern": "serial",
                    "calls": [
                        {
                            "tool_name": "web_search",
                            "arguments": {"query": "latest weather Paris"},
                        }
                    ],
                },
                "metadata": {
                    "benchmark": "bfcl",
                    "bfcl_track": "agentic_ext",
                    "bfcl_group": "web_search",
                    "bfcl_call_pattern": "serial",
                    "bfcl_language": "en",
                    "official_evaluator_supported": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = {
        "benchmark": "bfcl_v4",
        "source": "tests-fixture",
        "outputs": {
            "fc_core": str(fc_core),
            "agentic_ext": str(agentic_ext),
        },
        "protocol_subset": {
            "fc_core": {
                "included_groups": ["live", "multi_turn", "non_live"],
                "excluded_groups": ["format_sensitivity", "memory", "web_search"],
                "language_rule": "english_only_unless_validated_multilingual_official_evaluator",
                "call_pattern_rule": "serial_and_parallel_only",
                "official_evaluator_coverage": {
                    "serial": True,
                    "parallel": True,
                    "multilingual": False,
                },
            },
            "agentic_ext": {
                "included_groups": ["format_sensitivity", "memory", "web_search"],
                "excluded_groups": ["live", "multi_turn", "non_live"],
            },
        },
        "official_evaluator_script": str(evaluator),
        "counts": {
            "fc_core": 1,
            "agentic_ext": 1,
            "excluded": 0,
        },
        "excluded_rows": [],
    }
    (source_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return source_dir


def test_paper_claim_matrix_is_json_compatible() -> None:
    payload = json.loads((ROOT_DIR / "configs" / "paper_claim_matrix.yaml").read_text(encoding="utf-8"))
    assert set(payload["claims"]) == {
        "interaction_headline",
        "planner_binding_headline",
        "bfcl_agentic_supporting",
        "dual_control_interaction",
        "tau_bench_supporting",
        "reuse_exact_match_cost",
    }
    assert set(payload["suites"]) == {
        "toolsandbox_official",
        "bfcl_fc_core_smoke",
        "bfcl_fc_core",
        "bfcl_agentic_ext",
        "tau2_dual_control",
        "tau_bench_supporting",
        "tau_bench_headline",
        "reuse_exact_match",
    }


def test_run_paper_bench_suite_toolsandbox_official(tmp_path: Path) -> None:
    source_path = tmp_path / "toolsandbox.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "name": "toolsandbox_cli_001",
                    "query": "retrieve and write report",
                    "messages": [{"sender": "user", "recipient": "agent", "content": "Retrieve the data and save the report."}],
                    "tool_allow_list": ["search_tool", "write_tool"],
                    "candidate_tools": [
                        {"tool_id": "search_tool", "description": "Search information"},
                        {"tool_id": "write_tool", "description": "Write report"},
                    ],
                    "categories": ["State Dependency", "Multiple Tool Call"],
                    "milestones": ["retrieve data", "write artifact"],
                    "ideal_turn_count": 2,
                    "ideal_tool_calls": 2,
                }
            ]
        ),
        encoding="utf-8",
    )
    out_root = tmp_path / "paper_suite"
    completed = _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "toolsandbox_official",
            "--source",
            str(source_path),
            "--out-root",
            str(out_root),
            "--num-runs",
            "1",
        ]
    )
    assert completed.returncode == 0
    suite_outdir = out_root / "toolsandbox_official"
    assert (suite_outdir / "manifest.json").exists()
    assert (suite_outdir / "claim_summary.json").exists()
    assert (suite_outdir / "comparison.raw.csv").exists()
    assert (suite_outdir / "comparison.scored.csv").exists()
    claim_summary = json.loads((suite_outdir / "claim_summary.json").read_text(encoding="utf-8"))
    assert claim_summary["suite"] == "toolsandbox_official"
    assert claim_summary["claims"][0]["claim_id"] == "interaction_headline"


def test_run_paper_bench_suite_tau2_and_reuse(tmp_path: Path) -> None:
    source_path = tmp_path / "tau2.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "sample_id": "tau2_dual_control_cli_001",
                    "scenario": "dual_control",
                    "query": "retrieve and write report",
                    "candidate_tools": ["search_tool", "write_tool", "backup_write_tool"],
                    "primary_failtax": "ordering",
                    "failtaxes": ["ordering", "recovery"],
                    "task_family": "t3_must_interact",
                    "state_slots": ["query", "target_path", "approved"],
                    "dependency_edges": [
                        {"source": "step_01", "target": "step_02", "type": "state"},
                        {"source": "policy", "target": "step_02", "type": "approval"},
                    ],
                    "gold_recovery_class": "ask_approval_then_retry",
                    "budget_profile": {"max_tool_calls": 4, "max_user_turns": 1, "max_repair_attempts": 1, "max_recovery_budget": 1.0},
                    "constraints": {
                        "requires_user_approval": True,
                        "risk_level": "high",
                        "max_tool_calls": 4,
                        "max_user_turns": 1,
                        "max_repair_attempts": 1,
                        "max_recovery_budget": 1.0,
                    },
                    "backup_tool_map": {"write_tool": "backup_write_tool"},
                    "simulated_policy": {"mode": "cooperative"},
                    "expected_repairs": 1,
                    "expected_user_turns": 1,
                },
                {
                    "sample_id": "tau2_binding_auto_001",
                    "scenario": "binding_failure",
                    "query": "retrieve and write report",
                    "candidate_tools": ["search_tool", "write_tool"],
                    "primary_failtax": "selection",
                    "failtaxes": ["selection"],
                    "task_family": "t1_static_recovery",
                    "state_slots": ["query", "target_path"],
                    "dependency_edges": [{"source": "step_01", "target": "step_02", "type": "state"}],
                    "gold_recovery_class": "rebind_or_switch_then_retry",
                    "budget_profile": {"max_tool_calls": 3, "max_user_turns": 0, "max_repair_attempts": 1, "max_recovery_budget": 1.0},
                    "constraints": {"max_tool_calls": 3, "max_user_turns": 0, "max_repair_attempts": 1, "max_recovery_budget": 1.0},
                    "expected_repairs": 1,
                    "expected_user_turns": 0,
                },
            ]
        ),
        encoding="utf-8",
    )

    out_root = tmp_path / "paper_suite"
    _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "tau2_dual_control",
            "--source",
            str(source_path),
            "--out-root",
            str(out_root),
            "--num-runs",
            "1",
        ]
    )
    dual_control_outdir = out_root / "tau2_dual_control"
    assert (dual_control_outdir / "manifest.json").exists()
    assert (dual_control_outdir / "comparison.raw.csv").exists()
    assert (dual_control_outdir / "comparison.scored.csv").exists()
    dual_claim_summary = json.loads((dual_control_outdir / "claim_summary.json").read_text(encoding="utf-8"))
    assert dual_claim_summary["claims"][0]["claim_id"] == "dual_control_interaction"

    _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "reuse_exact_match",
            "--source",
            str(source_path),
            "--out-root",
            str(out_root),
            "--num-runs",
            "1",
        ]
    )
    reuse_outdir = out_root / "reuse_exact_match"
    assert (reuse_outdir / "manifest.json").exists()
    assert (reuse_outdir / "comparison.raw.csv").exists()
    assert (reuse_outdir / "comparison.scored.csv").exists()
    assert (reuse_outdir / "reuse_strata_analysis.json").exists()
    assert (reuse_outdir / "reuse_headroom_analysis.json").exists()
    reuse_claim_summary = json.loads((reuse_outdir / "claim_summary.json").read_text(encoding="utf-8"))
    assert reuse_claim_summary["claims"][0]["claim_id"] == "reuse_exact_match_cost"


def test_run_paper_bench_suite_bfcl_fc_core_smoke(tmp_path: Path) -> None:
    source_dir = _write_bfcl_source_dir(tmp_path)
    out_root = tmp_path / "paper_suite"
    _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "bfcl_fc_core_smoke",
            "--source",
            str(source_dir / "bfcl_v4.fc_core.aligned.jsonl"),
            "--out-root",
            str(out_root),
            "--systems",
            "a0_baseline",
            "--num-runs",
            "1",
        ]
    )
    suite_outdir = out_root / "bfcl_fc_core_smoke"
    claim_summary = json.loads((suite_outdir / "claim_summary.json").read_text(encoding="utf-8"))
    assert claim_summary["suite"] == "bfcl_fc_core_smoke"
    assert "official_bfcl_eval" in claim_summary
    assert "toolclaw_diagnostics" in claim_summary


def test_run_paper_bench_suite_bfcl_fc_core_requires_formal_source(tmp_path: Path) -> None:
    source_dir = _write_bfcl_source_dir(tmp_path)
    out_root = tmp_path / "paper_suite"
    completed = _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "bfcl_fc_core",
            "--source",
            str(source_dir / "bfcl_v4.fc_core.aligned.jsonl"),
            "--out-root",
            str(out_root),
            "--systems",
            "a0_baseline",
            "--num-runs",
            "1",
        ],
        check=False,
    )
    assert completed.returncode != 0
    assert "formal suite" in completed.stderr or "formal suite" in completed.stdout or "mismatch" in completed.stderr or "mismatch" in completed.stdout


def test_run_paper_bench_suite_tau_headline_is_blocked(tmp_path: Path) -> None:
    out_root = tmp_path / "paper_suite"
    completed = _run(
        [
            sys.executable,
            "scripts/run_paper_bench_suite.py",
            "tau_bench_headline",
            "--out-root",
            str(out_root),
        ],
        check=False,
    )
    assert completed.returncode != 0
    assert "blocked" in completed.stderr or "blocked" in completed.stdout
