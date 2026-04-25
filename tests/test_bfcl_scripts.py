from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from toolclaw.benchmarks.adapters import BFCLAdapter
from toolclaw.bfcl_runtime import (
    extract_parallel_argument_sets,
    extract_tool_arguments,
    rank_candidate_tools,
    select_candidate_tool,
    should_abstain_from_tools,
)


ROOT_DIR = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=True,
    )


def _write_raw_bfcl_source(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "id": "fc_core_serial_en",
                    "group": "Non-Live",
                    "language": "en",
                    "call_pattern": "serial",
                    "query": "Call weather_lookup with city=Paris.",
                    "tools": [
                        {
                            "name": "weather_lookup",
                            "description": "Look up weather by city",
                            "parameters": {"city": "string"},
                        },
                        {
                            "name": "calendar_lookup",
                            "description": "Look up a calendar event",
                            "parameters": {"date": "string"},
                        },
                    ],
                    "expected_call_structure": {
                        "pattern": "serial",
                        "calls": [
                            {
                                "tool_name": "weather_lookup",
                                "arguments": {"city": "Paris"},
                            }
                        ],
                    },
                },
                {
                    "id": "fc_core_parallel_es",
                    "group": "Live",
                    "language": "es",
                    "call_pattern": "parallel",
                    "query": "Consulta el clima de Paris y Berlin.",
                    "tools": [
                        {
                            "name": "weather_lookup",
                            "description": "Look up weather by city",
                            "parameters": {"city": "string"},
                        }
                    ],
                    "expected_call_structure": {
                        "pattern": "parallel",
                        "calls": [
                            {
                                "tool_name": "weather_lookup",
                                "arguments": {"city": "Paris"},
                            },
                            {
                                "tool_name": "weather_lookup",
                                "arguments": {"city": "Berlin"},
                            },
                        ],
                    },
                },
                {
                    "id": "agentic_web_search",
                    "group": "Web Search",
                    "language": "en",
                    "call_pattern": "serial",
                    "query": "Search the web for the latest weather note about Paris.",
                    "tools": [
                        {
                            "name": "web_search",
                            "description": "Search the web",
                            "parameters": {"query": "string"},
                        }
                    ],
                    "expected_call_structure": {
                        "pattern": "serial",
                        "calls": [
                            {
                                "tool_name": "web_search",
                                "arguments": {"query": "latest weather Paris"},
                            }
                        ],
                    },
                },
                {
                    "id": "memory_case",
                    "group": "Memory",
                    "language": "en",
                    "call_pattern": "serial",
                    "query": "Remember the user's preferred city.",
                    "tools": [
                        {
                            "name": "save_memory",
                            "description": "Save a memory item",
                            "parameters": {"key": "string", "value": "string"},
                        }
                    ],
                    "expected_call_structure": {
                        "pattern": "serial",
                        "calls": [
                            {
                                "tool_name": "save_memory",
                                "arguments": {"key": "preferred_city", "value": "Paris"},
                            }
                        ],
                    },
                },
            ]
        ),
        encoding="utf-8",
    )


def _write_official_wrapper(path: Path) -> None:
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
    results.append(
        {
            "run_index": int(row["run_index"]),
            "task_id": row["task_id"],
            "system": row["system"],
            "success": 1.0,
            "tool_selection_correctness": 1.0,
            "argument_correctness": 1.0,
            "structure_correctness": 1.0,
            "paper_safe": True,
            "unsupported_reasons": [],
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


def _write_official_bfcl_dir(root: Path) -> Path:
    package_root = root / "bfcl_official" / "bfcl_eval"
    data_dir = root / "bfcl_official" / "bfcl_eval" / "data"
    possible_dir = data_dir / "possible_answer"
    multi_turn_doc_dir = data_dir / "multi_turn_func_doc"
    constants_dir = package_root / "constants"
    ast_eval_dir = package_root / "eval_checker" / "ast_eval"
    multi_turn_eval_dir = package_root / "eval_checker" / "multi_turn_eval"
    data_dir.mkdir(parents=True, exist_ok=True)
    possible_dir.mkdir(parents=True, exist_ok=True)
    multi_turn_doc_dir.mkdir(parents=True, exist_ok=True)
    constants_dir.mkdir(parents=True, exist_ok=True)
    ast_eval_dir.mkdir(parents=True, exist_ok=True)
    multi_turn_eval_dir.mkdir(parents=True, exist_ok=True)

    for package_dir in [package_root, constants_dir, package_root / "eval_checker", ast_eval_dir, multi_turn_eval_dir]:
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (constants_dir / "enums.py").write_text(
        "from enum import Enum\n\n"
        "class Language(Enum):\n"
        "    PYTHON = 'python'\n"
        "    JAVA = 'java'\n"
        "    JAVASCRIPT = 'javascript'\n",
        encoding="utf-8",
    )
    (ast_eval_dir / "ast_checker.py").write_text(
        "def _normalize(value):\n"
        "    if isinstance(value, list) and value:\n"
        "        return _normalize(value[0])\n"
        "    if isinstance(value, dict):\n"
        "        return {k: _normalize(v) for k, v in value.items()}\n"
        "    return value\n\n"
        "def ast_checker(functions, actual_model_output, possible_answer, language, category, model_name):\n"
        "    return {'valid': _normalize(actual_model_output) == _normalize(possible_answer), 'error_type': 'mock_ast_mismatch'}\n",
        encoding="utf-8",
    )
    (multi_turn_eval_dir / "multi_turn_checker.py").write_text(
        "def multi_turn_checker(chunked_actual, ground_truth_turns, prompt_entry, category, model_name):\n"
        "    actual = [turn[0] if turn else [] for turn in chunked_actual]\n"
        "    return {'valid': actual == ground_truth_turns, 'error_type': 'mock_multi_turn_mismatch'}\n",
        encoding="utf-8",
    )

    (data_dir / "BFCL_v4_simple_python.json").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "simple_python_0",
                        "question": [[{"role": "user", "content": "Call weather_lookup with city=Paris."}]],
                        "function": [
                            {
                                "name": "weather_lookup",
                                "description": "Look up weather by city",
                                "parameters": {"type": "dict", "properties": {"city": {"type": "string"}}, "required": ["city"]},
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "id": "simple_python_1",
                        "question": [[{"role": "user", "content": "Call calendar_lookup with date=2026-01-01."}]],
                        "function": [
                            {
                                "name": "calendar_lookup",
                                "description": "Look up a calendar event",
                                "parameters": {"type": "dict", "properties": {"date": {"type": "string"}}, "required": ["date"]},
                            }
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (possible_dir / "BFCL_v4_simple_python.json").write_text(
        "\n".join(
            [
                json.dumps({"id": "simple_python_0", "ground_truth": [{"weather_lookup": {"city": ["Paris"]}}]}),
                json.dumps({"id": "simple_python_1", "ground_truth": [{"calendar_lookup": {"date": ["2026-01-01"]}}]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (data_dir / "BFCL_v4_parallel.json").write_text(
        json.dumps(
            {
                "id": "parallel_0",
                "question": [[{"role": "user", "content": "Call weather_lookup for Paris and Berlin."}]],
                "function": [
                    {
                        "name": "weather_lookup",
                        "description": "Look up weather by city",
                        "parameters": {"type": "dict", "properties": {"city": {"type": "string"}}, "required": ["city"]},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (possible_dir / "BFCL_v4_parallel.json").write_text(
        json.dumps(
            {
                "id": "parallel_0",
                "ground_truth": [
                    {"weather_lookup": {"city": ["Paris"]}},
                    {"weather_lookup": {"city": ["Berlin"]}},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (data_dir / "BFCL_v4_multi_turn_base.json").write_text(
        json.dumps(
            {
                "id": "multi_turn_base_0",
                "question": [
                    [{"role": "user", "content": "Create a new directory 'archive'."}],
                    [{"role": "user", "content": "Move 'log.txt' into 'archive'."}],
                ],
                "involved_classes": ["GorillaFileSystem"],
                "path": ["GorillaFileSystem.mkdir", "GorillaFileSystem.mv"],
                "excluded_function": ["cp"],
                "initial_config": {"cwd": "workspace"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (possible_dir / "BFCL_v4_multi_turn_base.json").write_text(
        json.dumps(
            {
                "id": "multi_turn_base_0",
                "ground_truth": [
                    ["mkdir(dir_name='archive')"],
                    ["mv(source='log.txt', destination='archive')"],
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (multi_turn_doc_dir / "gorilla_file_system.json").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "name": "mkdir",
                        "description": "Create a directory in the current working directory.",
                        "parameters": {
                            "type": "dict",
                            "properties": {"dir_name": {"type": "string"}},
                            "required": ["dir_name"],
                        },
                    }
                ),
                json.dumps(
                    {
                        "name": "mv",
                        "description": "Move a file or directory to a destination in the current working directory.",
                        "parameters": {
                            "type": "dict",
                            "properties": {
                                "source": {"type": "string"},
                                "destination": {"type": "string"},
                            },
                            "required": ["source", "destination"],
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (data_dir / "BFCL_v4_web_search.json").write_text(
        json.dumps(
            {
                "id": "web_search_0",
                "question": [[{"role": "user", "content": "Find the latest weather in Paris."}]],
                "involved_classes": ["WebSearchAPI"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (possible_dir / "BFCL_v4_web_search.json").write_text(
        json.dumps(
            {
                "id": "web_search_0",
                "ground_truth": ["Paris weather"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (data_dir / "BFCL_v4_format_sensitivity.json").write_text(
        json.dumps({"simple_python": ["simple_python_0"]}, indent=2),
        encoding="utf-8",
    )
    return root / "bfcl_official"


def test_prepare_bfcl_source_routes_rows_and_writes_manifest(tmp_path: Path) -> None:
    raw_source = tmp_path / "bfcl_raw.json"
    evaluator = tmp_path / "official_eval.py"
    _write_raw_bfcl_source(raw_source)
    _write_official_wrapper(evaluator)
    outdir = tmp_path / "prepared"

    _run(
        [
            sys.executable,
            "scripts/prepare_bfcl_source.py",
            "--source",
            str(raw_source),
            "--outdir",
            str(outdir),
            "--official-evaluator-script",
            str(evaluator),
        ]
    )

    fc_core_rows = [
        json.loads(line)
        for line in (outdir / "bfcl_v4.fc_core.aligned.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    agentic_rows = [
        json.loads(line)
        for line in (outdir / "bfcl_v4.agentic_ext.aligned.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))

    assert [row["sample_id"] for row in fc_core_rows] == ["fc_core_serial_en"]
    assert {row["sample_id"] for row in agentic_rows} == {"agentic_web_search", "memory_case"}
    assert manifest["counts"] == {"fc_core": 1, "agentic_ext": 2, "excluded": 1}
    assert manifest["protocol_subset"]["fc_core"]["language_rule"] == "english_only_unless_validated_multilingual_official_evaluator"
    assert manifest["protocol_subset"]["fc_core"]["official_evaluator_coverage"]["multilingual"] is False
    assert manifest["excluded_rows"][0]["sample_id"] == "fc_core_parallel_es"


def test_prepare_bfcl_source_reads_official_directory_layout(tmp_path: Path) -> None:
    official_root = _write_official_bfcl_dir(tmp_path)
    outdir = tmp_path / "prepared_official"

    _run(
        [
            sys.executable,
            "scripts/prepare_bfcl_source.py",
            "--source",
            str(official_root),
            "--outdir",
            str(outdir),
        ]
    )

    fc_core_rows = [
        json.loads(line)
        for line in (outdir / "bfcl_v4.fc_core.aligned.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    agentic_rows = [
        json.loads(line)
        for line in (outdir / "bfcl_v4.agentic_ext.aligned.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert {row["sample_id"] for row in fc_core_rows} == {"simple_python_0", "simple_python_1", "parallel_0", "multi_turn_base_0"}
    assert {row["sample_id"] for row in agentic_rows} == {"web_search_0", "format_sensitivity::simple_python_0"}
    parallel_row = next(row for row in fc_core_rows if row["sample_id"] == "parallel_0")
    assert parallel_row["metadata"]["official_dataset_category"] == "parallel"
    assert parallel_row["expected_call_structure"]["pattern"] == "parallel"
    assert len(parallel_row["expected_call_structure"]["calls"]) == 2
    multi_turn_row = next(row for row in fc_core_rows if row["sample_id"] == "multi_turn_base_0")
    assert multi_turn_row["metadata"]["official_dataset_category"] == "multi_turn_base"
    assert multi_turn_row["milestones"] == ["Create a new directory 'archive'.", "Move 'log.txt' into 'archive'."]
    assert {tool["tool_id"] for tool in multi_turn_row["candidate_tools"]} == {"mkdir", "mv"}
    format_row = next(row for row in agentic_rows if row["sample_id"] == "format_sensitivity::simple_python_0")
    assert format_row["metadata"]["official_dataset_category"] == "format_sensitivity"
    assert format_row["metadata"]["format_sensitivity_source_id"] == "simple_python_0"


def test_run_and_score_bfcl_scripts_generate_protocol_outputs(tmp_path: Path) -> None:
    raw_source = tmp_path / "bfcl_raw.json"
    evaluator = tmp_path / "official_eval.py"
    _write_raw_bfcl_source(raw_source)
    _write_official_wrapper(evaluator)
    prepared = tmp_path / "prepared"
    run_outdir = tmp_path / "bfcl_run"

    _run(
        [
            sys.executable,
            "scripts/prepare_bfcl_source.py",
            "--source",
            str(raw_source),
            "--outdir",
            str(prepared),
            "--official-evaluator-script",
            str(evaluator),
        ]
    )

    _run(
        [
            sys.executable,
            "scripts/run_bfcl_bench.py",
            "--source",
            str(prepared / "bfcl_v4.fc_core.aligned.jsonl"),
            "--outdir",
            str(run_outdir),
            "--track",
            "fc_core",
            "--systems",
            "a0_baseline",
            "--num-runs",
            "1",
        ]
    )

    raw_manifest = json.loads((run_outdir / "experiment_manifest.json").read_text(encoding="utf-8"))
    raw_rows = list(csv.DictReader((run_outdir / "comparison.raw.csv").open("r", encoding="utf-8", newline="")))
    assert raw_manifest["experiment_metadata"]["raw_only"] is True
    assert raw_manifest["track"] == "fc_core"
    assert raw_rows

    _run(
        [
            sys.executable,
            "scripts/score_bfcl_outputs.py",
            "--outdir",
            str(run_outdir),
            "--official-eval",
            "true",
            "--toolclaw-diagnostics",
            "true",
        ]
    )

    official = json.loads((run_outdir / "official_scoreboard.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((run_outdir / "toolclaw_diagnostics.json").read_text(encoding="utf-8"))
    claim_summary = json.loads((run_outdir / "claim_summary.json").read_text(encoding="utf-8"))
    scored_rows = list(csv.DictReader((run_outdir / "comparison.scored.csv").open("r", encoding="utf-8", newline="")))

    assert official["namespace"] == "official_bfcl_eval"
    assert diagnostics["namespace"] == "toolclaw_diagnostics"
    assert claim_summary["suite"] == "bfcl_fc_core"
    assert claim_summary["claims"][0]["claim_id"] == "planner_binding_headline"
    assert claim_summary["paper_safe_for_claim"] is True
    assert "toolclaw_diagnostics_repair_overhead" in scored_rows[0]
    assert "toolclaw_diagnostics_missing_required_arg_rate" in scored_rows[0]
    assert "toolclaw_diagnostics_preflight_interception_rate" in scored_rows[0]
    assert "toolclaw_diagnostics_repair_success_rate" in scored_rows[0]
    assert "toolclaw_diagnostics_exec_verified" in scored_rows[0]
    assert "toolclaw_diagnostics_avg_tool_calls" in scored_rows[0]
    assert "toolclaw_diagnostics_avg_user_queries" in scored_rows[0]
    assert "repair_overhead" not in claim_summary["claims"][0]["metric_snapshot"]
    assert "toolclaw_diagnostics_missing_required_arg_rate" in diagnostics["per_system"]["a0_baseline"]
    assert "toolclaw_diagnostics_preflight_interception_rate" in diagnostics["per_system"]["a0_baseline"]
    assert "toolclaw_diagnostics_exec_verified" in diagnostics["per_system"]["a0_baseline"]


def test_run_bfcl_full_v4_track_merges_protocol_files(tmp_path: Path) -> None:
    raw_source = tmp_path / "bfcl_raw.json"
    _write_raw_bfcl_source(raw_source)
    prepared = tmp_path / "prepared"

    _run(
        [
            sys.executable,
            "scripts/prepare_bfcl_source.py",
            "--source",
            str(raw_source),
            "--outdir",
            str(prepared),
        ]
    )

    run_outdir = tmp_path / "bfcl_full_v4"
    _run(
        [
            sys.executable,
            "scripts/run_bfcl_bench.py",
            "--source",
            str(prepared),
            "--outdir",
            str(run_outdir),
            "--track",
            "full_v4",
            "--systems",
            "a0_baseline",
            "--num-runs",
            "1",
        ]
    )

    normalized = json.loads((run_outdir / "prepared" / "bfcl.normalized.json").read_text(encoding="utf-8"))
    task_ids = {row["task_id"] for row in normalized}
    assert {"fc_core_serial_en", "agentic_web_search", "memory_case"} <= task_ids


def test_bfcl_official_wrapper_scores_supported_ast_row(tmp_path: Path) -> None:
    official_root = _write_official_bfcl_dir(tmp_path)
    prepared = tmp_path / "prepared_official"

    _run(
        [
            sys.executable,
            "scripts/prepare_bfcl_source.py",
            "--source",
            str(official_root),
            "--outdir",
            str(prepared),
            "--official-evaluator-script",
            "scripts/bfcl_official_wrapper.py",
        ]
    )

    fc_core_row = None
    for line in (prepared / "bfcl_v4.fc_core.aligned.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["sample_id"] == "simple_python_0":
            fc_core_row = row
            break
    assert fc_core_row is not None
    expected_call = fc_core_row["expected_call_structure"]["calls"][0]
    prepared_taskset = tmp_path / "prepared_taskset.json"
    prepared_taskset.write_text(
        json.dumps(
            [
                {
                    "task_id": fc_core_row["sample_id"],
                    "query": fc_core_row["query"],
                    "candidate_tools": fc_core_row["candidate_tools"],
                    "metadata": fc_core_row["metadata"],
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                    "events": [
                        {
                            "event_type": "tool_call",
                            "tool_id": expected_call["tool_name"],
                            "tool_args": expected_call["arguments"],
                        }
                    ],
                "metrics": {"success": False},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    comparison_path = tmp_path / "comparison.raw.csv"
    with comparison_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_index", "task_id", "system", "trace_path"])
        writer.writeheader()
        writer.writerow(
            {
                "run_index": "1",
                "task_id": fc_core_row["sample_id"],
                "system": "a0_baseline",
                "trace_path": str(trace_path),
            }
        )

    wrapper_out = tmp_path / "wrapper_out.json"
    _run(
        [
            sys.executable,
            "scripts/bfcl_official_wrapper.py",
            "--prepared-taskset",
            str(prepared_taskset),
            "--comparison",
            str(comparison_path),
            "--out",
            str(wrapper_out),
        ]
    )

    payload = json.loads(wrapper_out.read_text(encoding="utf-8"))
    assert payload["unsupported_strata"] == []
    assert len(payload["results"]) == 1
    assert payload["results"][0]["success"] == 1.0
    assert payload["results"][0]["paper_safe"] is True


def test_bfcl_adapter_scores_tool_args_payloads() -> None:
    adapter = BFCLAdapter()
    sample = adapter.load_samples_from_tasks(
        [
            {
                "task_id": "triangle_case",
                "query": "Find the area of a triangle with a base of 10 units and height of 5 units.",
                "candidate_tools": [
                    {
                        "tool_id": "calculate_triangle_area",
                        "description": "Calculate the area of a triangle.",
                        "parameters": {
                            "type": "dict",
                            "properties": {
                                "base": {"type": "integer"},
                                "height": {"type": "integer"},
                                "unit": {"type": "string"},
                            },
                            "required": ["base", "height"],
                        },
                    }
                ],
                "metadata": {
                    "benchmark": "bfcl",
                    "expected_call_structure": {
                        "pattern": "serial",
                        "calls": [
                            {
                                "tool_name": "calculate_triangle_area",
                                "arguments": {"base": 10, "height": 5, "unit": "units"},
                            }
                        ],
                    },
                },
            }
        ]
    )[0]
    trace_payload = {
        "metrics": {"success": True, "repair_actions": 0},
        "events": [
            {
                "event_type": "tool_call",
                "tool_id": "calculate_triangle_area",
                "tool_args": {"base": 10, "height": 5, "unit": "units"},
            }
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is True
    assert score.metrics["parameter_fill_ratio"] == 1.0


def test_bfcl_adapter_records_preflight_grounding_diagnostics() -> None:
    adapter = BFCLAdapter()
    sample = adapter.load_samples_from_tasks(
        [
            {
                "task_id": "weather_case",
                "query": "Get weather of Ha Noi for me",
                "candidate_tools": [
                    {
                        "tool_id": "api.weather",
                        "description": "Get weather by location",
                        "parameters": {
                            "type": "dict",
                            "properties": {"loc": {"type": "string"}, "unit": {"type": "string"}},
                            "required": ["loc"],
                        },
                    }
                ],
                "metadata": {
                    "benchmark": "bfcl",
                    "expected_call_structure": {
                        "pattern": "serial",
                        "calls": [
                            {
                                "tool_name": "api.weather",
                                "arguments": {"loc": "Ha Noi, Vietnam"},
                            }
                        ],
                    },
                },
            }
        ]
    )[0]
    trace_payload = {
        "metrics": {"success": False, "repair_actions": 1, "tool_calls": 0, "user_queries": 1},
        "events": [
            {
                "event_type": "preflight_check",
                "step_id": "step_01",
                "tool_id": "api.weather",
                "output": {
                    "reason": "missing_required_input",
                    "missing_required_inputs": ["loc"],
                },
                "metadata": {"required_input_keys": ["loc", "unit"]},
            },
            {
                "event_type": "repair_applied",
                "step_id": "step_01",
                "tool_id": "api.weather",
                "output": {"status": "patched"},
            },
        ],
    }

    score = adapter.score_trace(sample, trace_payload)

    assert score.success is False
    assert score.metrics["missing_required_arg_rate"] == 0.5
    assert score.metrics["preflight_interception_rate"] == 1.0
    assert score.metrics["repair_success_rate"] == 0.0
    assert score.metrics["repair_applied_count"] == 1.0
    assert score.metrics["repair_success_count"] == 0.0
    assert score.metrics["exec_verified"] == 0.0
    assert score.metrics["avg_tool_calls"] == 0.0
    assert score.metrics["avg_user_queries"] == 1.0


def test_bfcl_runtime_extract_tool_arguments_keeps_benchmark_logic_out_of_executor() -> None:
    extracted = extract_tool_arguments(
        "calculate_triangle_area",
        {
            "type": "dict",
            "properties": {
                "base": {"type": "integer"},
                "height": {"type": "integer"},
                "unit": {"type": "string"},
            },
            "required": ["base", "height"],
        },
        "Find the area of a triangle with a base of 10 units and height of 5 units.",
    )

    assert extracted == {"base": 10, "height": 5, "unit": "units"}


def test_score_bfcl_outputs_prefers_py39_plus_for_official_eval(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module.sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(
        module,
        "_python_version",
        lambda executable: {
            "/usr/bin/python3": (3, 8, 10),
            "/opt/python3.13": (3, 13, 0),
        }.get(executable),
    )
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda binary: "/opt/python3.13" if binary == "python3.13" else None,
    )

    selected, version = module._discover_official_python()

    assert selected == "/opt/python3.13"
    assert version == (3, 13, 0)


def test_bfcl_official_wrapper_multi_turn_dependency_failure_is_row_local() -> None:
    spec = importlib.util.spec_from_file_location(
        "bfcl_official_wrapper_module",
        ROOT_DIR / "scripts" / "bfcl_official_wrapper.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def _raise_missing_dependency(*args, **kwargs):
        raise ModuleNotFoundError("No module named mpmath")

    score = module._score_multi_turn(
        multi_turn_checker=_raise_missing_dependency,
        task={"metadata": {"official_dataset_category": "multi_turn_base"}},
        prompt_entry={"prompt": "ignored"},
        ground_truth_entry={"ground_truth": [["math_api.add(a=1,b=2)"]]},
        actual_calls=[{"tool_id": "add", "arguments": {"a": 1, "b": 2}}],
    )

    assert score["paper_safe"] is False
    assert score["success"] == 0.0
    assert score["unsupported_reasons"] == ["missing_multi_turn_dependency:ModuleNotFoundError"]



def test_bfcl_runtime_supports_numbered_integer_keys() -> None:
    extracted = extract_tool_arguments(
        "triangle_properties.get",
        {
            "type": "dict",
            "properties": {
                "side1": {"type": "integer"},
                "side2": {"type": "integer"},
                "side3": {"type": "integer"},
            },
            "required": ["side1", "side2", "side3"],
        },
        "The three sides are 5 units, 4 units and 3 units long.",
    )

    assert extracted["side1"] == 5
    assert extracted["side2"] == 4
    assert extracted["side3"] == 3



def test_bfcl_runtime_abstains_for_mismatched_single_tool_query() -> None:
    should_abstain = should_abstain_from_tools(
        "Calculate the area of a triangle given the base is 10 meters and height is 5 meters.",
        [
            {
                "tool_id": "determine_body_mass_index",
                "description": "Calculate body mass index given weight and height.",
                "parameters": {
                    "type": "dict",
                    "properties": {
                        "weight": {"type": "float"},
                        "height": {"type": "float"},
                    },
                    "required": ["weight", "height"],
                },
            }
        ],
    )

    assert should_abstain is True



def test_bfcl_runtime_prefers_high_confidence_tool_over_bad_preferred_tool() -> None:
    selected = select_candidate_tool(
        "update my latte to a large size with coconut milk and make it extra sweet; make it boiling hot. The drink id is latte.",
        [
            {
                "tool_id": "ChaFod",
                "description": "Changes the food item based on the customer's request.",
                "parameters": {
                    "type": "dict",
                    "required": ["foodItem"],
                    "properties": {"foodItem": {"type": "string"}},
                },
            },
            {
                "tool_id": "ChaDri.change_drink",
                "description": "Modifies the existing drink order according to updated drink preferences.",
                "parameters": {
                    "type": "dict",
                    "required": ["new_preferences"],
                    "properties": {
                        "drink_id": {"type": "string"},
                        "new_preferences": {
                            "type": "dict",
                            "properties": {
                                "size": {"type": "string", "enum": ["small", "medium", "large"]},
                                "sweetness_level": {"type": "string", "enum": ["none", "light", "regular", "extra"]},
                                "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                                "temperature": {"type": "string", "enum": ["cold", "warm", "hot"]},
                            },
                        },
                    },
                },
            },
        ],
        preferred_tool_id="ChaFod",
    )

    assert selected is not None
    assert selected["tool_id"] == "ChaDri.change_drink"


def test_bfcl_runtime_omits_unmatched_nested_enum_fields() -> None:
    extracted = extract_tool_arguments(
        "ChaDri.change_drink",
        {
            "type": "dict",
            "properties": {
                "drink_id": {"type": "string"},
                "new_preferences": {
                    "type": "dict",
                    "properties": {
                        "size": {"type": "string", "enum": ["small", "medium", "large"]},
                        "milk_type": {"type": "string", "enum": ["regular", "soy", "almond", "coconut"]},
                        "sweetness_level": {"type": "string", "enum": ["none", "light", "regular", "extra"]},
                        "temperature": {"type": "string", "enum": ["cold", "warm", "hot"]},
                        "special_instructions": {"type": "string"},
                    },
                },
            },
        },
        'Update drink id "1234" to no sweetness and hot.',
        include_defaults=False,
    )

    assert extracted["drink_id"] == "1234"
    assert extracted["new_preferences"] == {
        "sweetness_level": "none",
        "temperature": "hot",
    }


def test_bfcl_runtime_extracts_parallel_multiple_numeric_arguments() -> None:
    sum_args = extract_tool_arguments(
        "math_toolkit.sum_of_multiples",
        {
            "type": "dict",
            "properties": {
                "lower_limit": {"type": "integer"},
                "upper_limit": {"type": "integer"},
                "multiples": {"type": "array", "items": {"type": "integer"}},
            },
        },
        "Find the sum of multiples of 3 and 5 between 1 and 1000.",
        include_defaults=False,
    )
    prime_args = extract_tool_arguments(
        "math_toolkit.product_of_primes",
        {
            "type": "dict",
            "properties": {
                "count": {"type": "integer"},
            },
        },
        "Also compute the product of the first five prime numbers.",
        include_defaults=False,
    )

    assert sum_args == {"lower_limit": 1, "upper_limit": 1000, "multiples": [3, 5]}
    assert prime_args == {"count": 5}


def test_bfcl_runtime_extracts_live_multiple_grounding_arguments() -> None:
    weather_args = extract_tool_arguments(
        "api.weather",
        {
            "type": "dict",
            "properties": {"loc": {"type": "string"}},
            "required": ["loc"],
        },
        "Get weather of Ha Noi for me",
        include_defaults=False,
    )
    search_args = extract_tool_arguments(
        "HNA_WQA.search",
        {
            "type": "dict",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"],
        },
        "what is Imjin war",
        include_defaults=False,
    )
    command_args = extract_tool_arguments(
        "ControlAppliance.execute",
        {
            "type": "dict",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
        "Could you stop the washing machine in the utility room?",
        include_defaults=False,
    )
    add_args = extract_tool_arguments(
        "add",
        {
            "type": "dict",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        "You are a helpful assistant If I have 100$ and I donated 40. How much do I have now?",
        include_defaults=False,
    )

    assert weather_args == {"loc": "Ha Noi, Vietnam"}
    assert search_args == {"keyword": "Imjin war"}
    assert command_args == {"command": "다용도실, 통돌이, 중지"}
    assert add_args == {"a": 100, "b": -40}


def test_bfcl_runtime_extracts_repeated_parallel_argument_sets() -> None:
    arg_sets = extract_parallel_argument_sets(
        "spotify.play",
        {
            "type": "dict",
            "properties": {
                "artist": {"type": "string"},
                "duration": {"type": "integer"},
            },
        },
        "Play songs by artists Taylor Swift and Ed Sheeran, with durations 3 minutes and 4 minutes.",
    )

    assert arg_sets == [
        {"artist": "Taylor Swift", "duration": 3},
        {"artist": "Ed Sheeran", "duration": 4},
    ]


def test_bfcl_runtime_extracts_parallel_location_argument_sets() -> None:
    arg_sets = extract_parallel_argument_sets(
        "get_current_weather",
        {
            "type": "dict",
            "required": ["location"],
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string"},
            },
        },
        "Could you tell me the current weather conditions for Boston, MA and also for San Francisco?",
    )

    assert arg_sets == [
        {"location": "Boston, MA"},
        {"location": "San Francisco"},
    ]


def test_bfcl_runtime_extracts_parallel_numeric_id_argument_sets() -> None:
    arg_sets = extract_parallel_argument_sets(
        "records.fetch",
        {
            "type": "dict",
            "required": ["record_id"],
            "properties": {"record_id": {"type": "integer", "description": "record identifier"}},
        },
        "Fetch record IDs 101, 202, and 303.",
    )

    assert arg_sets == [
        {"record_id": 101},
        {"record_id": 202},
        {"record_id": 303},
    ]


def test_bfcl_runtime_extracts_parallel_email_argument_sets() -> None:
    arg_sets = extract_parallel_argument_sets(
        "mailer.send",
        {
            "type": "dict",
            "required": ["recipient_email"],
            "properties": {"recipient_email": {"type": "string", "description": "recipient email address"}},
        },
        "Send the notification to alice@example.com and bob@example.com.",
    )

    assert arg_sets == [
        {"recipient_email": "alice@example.com"},
        {"recipient_email": "bob@example.com"},
    ]


def test_bfcl_runtime_extracts_parallel_quoted_string_argument_sets() -> None:
    arg_sets = extract_parallel_argument_sets(
        "archive.item",
        {
            "type": "dict",
            "required": ["item_name"],
            "properties": {"item_name": {"type": "string", "description": "item name"}},
        },
        'Archive "alpha" and "beta".',
    )

    assert arg_sets == [{"item_name": "alpha"}, {"item_name": "beta"}]


def test_bfcl_runtime_parallel_extraction_requires_observable_parallel_cue() -> None:
    arg_sets = extract_parallel_argument_sets(
        "archive.item",
        {
            "type": "dict",
            "required": ["item_name"],
            "properties": {"item_name": {"type": "string", "description": "item name"}},
        },
        "Archive alpha today.",
    )

    assert arg_sets == []


def test_bfcl_runtime_prefers_general_search_for_general_information_query() -> None:
    selected = select_candidate_tool(
        "what is Imjin war",
        [
            {
                "tool_id": "ControlAppliance.execute",
                "description": "Control a home appliance and check its status.",
                "parameters": {
                    "type": "dict",
                    "required": ["command"],
                    "properties": {"command": {"type": "string"}},
                },
            },
            {
                "tool_id": "HNA_WQA.search",
                "description": "Retrieve up-to-date information by searching the web using keywords.",
                "parameters": {
                    "type": "dict",
                    "required": ["keyword"],
                    "properties": {"keyword": {"type": "string"}},
                },
            },
            {
                "tool_id": "HNA_NEWS.search",
                "description": "Searches for recent events and news based on the specified keyword.",
                "parameters": {
                    "type": "dict",
                    "required": ["keyword"],
                    "properties": {"keyword": {"type": "string"}},
                },
            },
        ],
        preferred_tool_id="HNA_NEWS.search",
    )

    assert selected is not None
    assert selected["tool_id"] == "HNA_WQA.search"


def test_bfcl_runtime_prefers_news_search_for_explicit_news_query() -> None:
    selected = select_candidate_tool(
        "최근 박지성에 관한 뉴스를 찾아줘.",
        [
            {
                "tool_id": "HNA_WQA.search",
                "description": "Retrieve up-to-date information by searching the web using keywords.",
                "parameters": {
                    "type": "dict",
                    "required": ["keyword"],
                    "properties": {"keyword": {"type": "string"}},
                },
            },
            {
                "tool_id": "HNA_NEWS.search",
                "description": "Searches for recent events and news based on the specified keyword.",
                "parameters": {
                    "type": "dict",
                    "required": ["keyword"],
                    "properties": {"keyword": {"type": "string"}},
                },
            },
        ],
        preferred_tool_id="HNA_WQA.search",
    )

    assert selected is not None
    assert selected["tool_id"] == "HNA_NEWS.search"


def test_bfcl_runtime_extracts_uber_address_and_time_from_multilingual_query() -> None:
    arguments = extract_tool_arguments(
        "uber.ride",
        {
            "type": "dict",
            "required": ["loc", "type", "time"],
            "properties": {
                "loc": {"type": "string"},
                "type": {"type": "string", "enum": ["plus", "comfort", "black"]},
                "time": {"type": "integer"},
            },
        },
        "Tôi cần một chuyến xe Uber loại 'Plus' từ địa chỉ '2150 Shattuck Ave, Berkeley, CA' và tôi có thể chờ tối đa 10 phút.",
        include_defaults=False,
    )

    assert arguments == {
        "loc": "2150 Shattuck Ave, Berkeley, CA",
        "type": "plus",
        "time": 10,
    }


def test_bfcl_runtime_extracts_string_identifier_from_agent_query() -> None:
    arguments = extract_tool_arguments(
        "host_agent_api.HostAgentApi.get_agent_snapshot",
        {
            "type": "dict",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "to": {"type": "string"},
                "windowSize": {"type": "integer"},
            },
        },
        "Give the snapshot for host agent zzwzeem, up to the current time",
        include_defaults=False,
    )

    assert arguments["id"] == "zzwzeem"


def test_bfcl_runtime_extracts_email_and_column_arrays() -> None:
    email_args = extract_tool_arguments(
        "update_user_profile",
        {
            "type": "dict",
            "required": ["profile_data"],
            "properties": {
                "profile_data": {
                    "type": "dict",
                    "properties": {
                        "email": {"type": "array", "items": {"type": "string"}},
                    },
                }
            },
        },
        "I need to update my profile with my new email, john.doe@example.com, and my new age, 30.",
        include_defaults=False,
    )
    column_args = extract_tool_arguments(
        "database.modify_columns",
        {
            "type": "dict",
            "required": ["columns"],
            "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
            },
        },
        "I need to delete some columns from my employees database on personal_data table. I want to remove their email addresses and social security numbers to respect privacy.",
        include_defaults=False,
    )

    assert email_args == {"profile_data": {"email": ["john.doe@example.com"]}}
    assert column_args == {"columns": ["email", "ssn"]}


def test_bfcl_runtime_extracts_node_and_pod_integer_ids() -> None:
    arguments = extract_tool_arguments(
        "telemetry.flowrules.interfaceInfo.get",
        {
            "type": "dict",
            "required": ["fabricName", "nodeId", "podId"],
            "properties": {
                "fabricName": {"type": "string"},
                "nodeId": {"type": "integer"},
                "podId": {"type": "integer"},
            },
        },
        "Can you retrieve the status information for the Ethernet interface on fabric 'Global-Fabric', node 1200, and pod 3?",
        include_defaults=False,
    )

    assert arguments["nodeId"] == 1200
    assert arguments["podId"] == 3


def test_bfcl_runtime_extracts_weight_and_travel_destination() -> None:
    bmi_arguments = extract_tool_arguments(
        "calculate_bmi",
        {
            "type": "dict",
            "required": ["weight", "height"],
            "properties": {
                "weight": {"type": "integer"},
                "height": {"type": "integer"},
            },
        },
        "Calculate the Body Mass Index (BMI) of a person with a weight of 85 kilograms and height of 180 cm.",
        include_defaults=False,
    )
    travel_arguments = extract_tool_arguments(
        "Hotels_2_SearchHouse",
        {
            "type": "dict",
            "required": ["where_to", "number_of_adults"],
            "properties": {
                "where_to": {"type": "string"},
                "number_of_adults": {"type": "integer"},
            },
        },
        "Search for a house accommodation in Delhi that has a review rating of at least 4.6 for two?",
        include_defaults=False,
    )

    assert bmi_arguments["weight"] == 85
    assert travel_arguments["where_to"] == "Delhi"


def test_bfcl_runtime_extracts_explicit_ticker_symbol() -> None:
    arguments = extract_tool_arguments(
        "stock_price.get",
        {
            "type": "dict",
            "required": ["ticker"],
            "properties": {
                "ticker": {"type": "string"},
                "exchange": {"type": "string"},
            },
        },
        "What is the price for ticker AAPL on NYSE?",
        include_defaults=False,
    )

    assert arguments["ticker"] == "AAPL"


def test_bfcl_function_selection_audit_adds_gold_only_after_execution(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_audit_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    runtime_diagnostic = {
        "planner_tool_id": "wrong_tool",
        "schema_top_5": [
            {"tool_id": "right_tool", "score": 4.0},
            {"tool_id": "wrong_tool", "score": 4.0},
        ],
        "schema_top_tool_id": "right_tool",
        "schema_top_score": 4.0,
        "planner_score": 4.0,
        "score_margin": 0.0,
        "selected_tool_id": "right_tool",
        "selected_reason": "planner_tie_dropped",
        "planner_required_argument_coverage": 0.0,
        "selected_required_argument_coverage": 1.0,
        "planner_missing_required_args": ["missing_value"],
        "selected_missing_required_args": [],
    }
    trace_path.write_text(
        json.dumps({"metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}}}),
        encoding="utf-8",
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task_1",
            "system": "a2_planner",
            "gold_tool": "right_tool",
            "chosen_tool": "wrong_tool",
            "trace_path": str(trace_path),
            "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"]),
            "official_bfcl_eval_success": 0.0,
        }
    ]

    audit = module._bfcl_function_selection_audit(rows)

    assert audit["audit_schema_version"] == "bfcl_function_selection_audit_v1"
    assert audit["guard_policy_version"] == "strict_schema_top1_tie_drop_v1"
    assert audit["gold_fields_added_after_execution"] is True
    assert audit["runtime_diagnostics_gold_free"] is True
    assert audit["rows"][0]["expected_function"] == "right_tool"
    assert audit["rows"][0]["guardability_flags"]["planner_wrong_schema_top1_expected"] is True
    assert audit["rows"][0]["guardability_flags"]["planner_tie_dropped_correct"] is True


def test_bfcl_guard_claim_gates_fail_on_wrong_function_regression() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_gate_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = [
        {"run_index": "1", "task_id": "base_missing", "system": "a0_baseline", "official_bfcl_eval_unsupported_reasons": json.dumps(["missing_required"]), "official_bfcl_eval_success": 0.0},
        {"run_index": "1", "task_id": "base_missing", "system": "a2_planner", "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"]), "official_bfcl_eval_success": 0.0},
        {"run_index": "1", "task_id": "base_wrong", "system": "a0_baseline", "official_bfcl_eval_unsupported_reasons": json.dumps([]), "official_bfcl_eval_success": 1.0},
        {"run_index": "1", "task_id": "base_wrong", "system": "a2_planner", "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"]), "official_bfcl_eval_success": 0.0},
    ]
    official_scoreboard = {
        "per_system": {
            "a0_baseline": {"official_bfcl_eval_success": 0.5, "official_bfcl_eval_tool_selection_correctness": 1.0},
            "a2_planner": {"official_bfcl_eval_success": 0.0, "official_bfcl_eval_tool_selection_correctness": 0.0},
        }
    }

    gates = module._bfcl_guard_claim_gates(rows, official_scoreboard)

    assert gates["full_suite_gates"]["a2_wrong_func_name_le_a0"] is False
    assert gates["full_suite_supporting_ready"] is False
    assert gates["baseline_missing_required_slice"]["slice_id"] == "baseline_missing_required_slice"
    assert gates["missing_required_guarded_reduction_ready"] is False
    assert gates["reuse_claim_enabled_for_bfcl"] is False
    assert gates["a4_interpreted_as_guarded_execution_variant_only"] is True


def test_bfcl_guard_claim_gates_allow_diagnostic_supporting_case_b() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_case_b_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = [
        {"run_index": "1", "task_id": "same_missing", "system": "a0_baseline", "official_bfcl_eval_unsupported_reasons": json.dumps(["missing_required"]), "official_bfcl_eval_success": 0.0},
        {"run_index": "1", "task_id": "same_missing", "system": "a2_planner", "official_bfcl_eval_unsupported_reasons": json.dumps(["missing_required"]), "official_bfcl_eval_success": 0.0},
        {"run_index": "1", "task_id": "same_success", "system": "a0_baseline", "official_bfcl_eval_unsupported_reasons": json.dumps([]), "official_bfcl_eval_success": 1.0},
        {"run_index": "1", "task_id": "same_success", "system": "a2_planner", "official_bfcl_eval_unsupported_reasons": json.dumps([]), "official_bfcl_eval_success": 1.0},
    ]
    rows.extend(
        {
            "run_index": row["run_index"],
            "task_id": row["task_id"],
            "system": system,
            "official_bfcl_eval_unsupported_reasons": row["official_bfcl_eval_unsupported_reasons"],
            "official_bfcl_eval_success": row["official_bfcl_eval_success"],
        }
        for system in ("a1_recovery", "a3_interaction", "a4_reuse")
        for row in rows[:2]
    )
    for row in rows:
        row["official_bfcl_eval_paper_safe"] = True
    official_scoreboard = {
        "per_system": {
            system: {"official_bfcl_eval_success": 0.5, "official_bfcl_eval_tool_selection_correctness": 0.75}
            for system in ("a0_baseline", "a1_recovery", "a2_planner", "a3_interaction", "a4_reuse")
        }
    }

    gates = module._bfcl_guard_claim_gates(rows, official_scoreboard)
    claim_summary = module._claim_summary(
        suite="bfcl_fc_core",
        track="fc_core",
        official_scoreboard=official_scoreboard,
        toolclaw_diagnostics={"per_system": {}},
        scored_rows=rows,
        unsupported=[],
    )
    exact_claim = next(claim for claim in claim_summary["claims"] if claim["claim_id"] == "bfcl_exact_function_guard")
    missing_claim = next(claim for claim in claim_summary["claims"] if claim["claim_id"] == "bfcl_missing_required_guarded_reduction")

    assert gates["wrong_function_non_regression_ready"] is True
    assert gates["missing_required_reduction_ready"] is False
    assert gates["full_suite_supporting_ready"] is False
    assert exact_claim["claim_strength"] == "diagnostic_supporting"
    assert exact_claim["diagnostic_supporting_ready"] is True
    assert missing_claim["claim_strength"] == "unsupported"
    assert missing_claim["supporting_ready"] is False


def test_bfcl_guardability_schema_ranker_buckets() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_bucket_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    top1_flags = module._guardability_flags(
        expected="expected_tool",
        planner="planner_tool",
        selected_reason="schema_top1_no_planner",
        top_ids=["expected_tool", "other_tool"],
    )
    top5_flags = module._guardability_flags(
        expected="expected_tool",
        planner="planner_tool",
        selected_reason="schema_score_higher",
        top_ids=["wrong_top1", "expected_tool", "other_tool"],
    )
    absent_flags = module._guardability_flags(
        expected="expected_tool",
        planner="planner_tool",
        selected_reason="schema_score_higher",
        top_ids=["wrong_top1", "wrong_top2", "wrong_top3"],
    )

    assert top1_flags["schema_top1_expected"] is True
    assert top1_flags["schema_top1_wrong_expected_in_top5"] is False
    assert top1_flags["expected_absent_from_schema_top5"] is False
    assert top5_flags["schema_top1_expected"] is False
    assert top5_flags["schema_top1_wrong_expected_in_top5"] is True
    assert top5_flags["expected_absent_from_schema_top5"] is False
    assert absent_flags["schema_top1_expected"] is False
    assert absent_flags["schema_top1_wrong_expected_in_top5"] is False
    assert absent_flags["expected_absent_from_schema_top5"] is True


def test_bfcl_prepare_preserves_original_function_provenance() -> None:
    spec = importlib.util.spec_from_file_location(
        "prepare_bfcl_source_provenance_module",
        ROOT_DIR / "scripts" / "prepare_bfcl_source.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tools = module._normalize_candidate_tools(
        {
            "candidate_tools": [
                "plain_lookup",
                {
                    "name": "Namespace.originalFunction",
                    "tool_id": "internal_tool_id",
                    "description": "Original function description",
                    "parameters": {"type": "dict"},
                },
            ]
        }
    )

    assert tools[0]["metadata"]["bfcl_original_function_name"] == "plain_lookup"
    assert tools[0]["metadata"]["bfcl_original_index"] == 1
    assert tools[1]["tool_id"] == "internal_tool_id"
    assert tools[1]["metadata"]["bfcl_original_function_name"] == "Namespace.originalFunction"
    assert tools[1]["metadata"]["bfcl_original_index"] == 2
    assert "prepare_bfcl_source.normalize_candidate_tool" in tools[1]["metadata"]["normalization_trace"]


def test_bfcl_candidate_coverage_drop_stage_classifier() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_coverage_stage_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cases = [
        ({"expected": "tool", "expected_in_raw": False, "expected_in_prepared": False, "expected_in_runtime": False, "expected_in_ranker": False, "expected_in_top5": False, "expected_is_top1": False, "selected_is_expected": False, "success": False}, "raw_absent"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": False, "expected_in_runtime": False, "expected_in_ranker": False, "expected_in_top5": False, "expected_is_top1": False, "selected_is_expected": False, "success": False}, "raw_to_prepared_drop"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": True, "expected_in_runtime": False, "expected_in_ranker": False, "expected_in_top5": False, "expected_is_top1": False, "selected_is_expected": False, "success": False}, "prepared_to_runtime_drop"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": True, "expected_in_runtime": True, "expected_in_ranker": True, "expected_in_top5": False, "expected_is_top1": False, "selected_is_expected": False, "success": False}, "runtime_to_top5_rank_drop"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": True, "expected_in_runtime": True, "expected_in_ranker": True, "expected_in_top5": True, "expected_is_top1": False, "selected_is_expected": False, "success": False}, "top5_to_top1_rank_error"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": True, "expected_in_runtime": True, "expected_in_ranker": True, "expected_in_top5": True, "expected_is_top1": True, "selected_is_expected": False, "success": False}, "top1_to_selected_guard_error"),
        ({"expected": "tool", "expected_in_raw": True, "expected_in_prepared": True, "expected_in_runtime": True, "expected_in_ranker": True, "expected_in_top5": True, "expected_is_top1": True, "selected_is_expected": True, "success": False}, "selected_correct_arg_or_shape_error"),
    ]
    for kwargs, expected_stage in cases:
        stage, _reason = module._bfcl_coverage_drop_stage(**kwargs)
        assert stage == expected_stage


def test_bfcl_candidate_coverage_audit_generates_funnel_rows(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_coverage_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    runtime_diagnostic = {
        "runtime_candidate_count": 2,
        "runtime_candidate_tool_ids": ["expected_tool", "other_tool"],
        "runtime_candidate_original_function_names": ["expected_tool", "other_tool"],
        "ranker_candidate_count": 2,
        "ranker_candidate_tool_ids": ["expected_tool", "other_tool"],
        "ranker_candidate_original_function_names": ["expected_tool", "other_tool"],
        "schema_top_5": [{"tool_id": "other_tool", "bfcl_original_function_name": "other_tool", "score": 3.0}],
        "selected_tool_id": "other_tool",
        "selected_reason": "schema_score_higher",
    }
    trace_path.write_text(
        json.dumps({"metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}}}),
        encoding="utf-8",
    )
    rows = [
        {
            "run_index": "1",
            "task_id": "task_1",
            "system": "a2_planner",
            "bfcl_group": "non_live",
            "bfcl_call_pattern": "serial",
            "gold_tool": "expected_tool",
            "chosen_tool": "other_tool",
            "candidate_tools": json.dumps(
                [
                    {"tool_id": "expected_tool", "metadata": {"bfcl_original_function_name": "expected_tool"}},
                    {"tool_id": "other_tool", "metadata": {"bfcl_original_function_name": "other_tool"}},
                ]
            ),
            "trace_path": str(trace_path),
            "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"]),
            "official_bfcl_eval_success": 0.0,
        }
    ]

    audit = module._bfcl_candidate_coverage_audit(rows)
    row = audit["rows"][0]

    assert audit["audit_schema_version"] == "bfcl_candidate_coverage_audit_v1"
    assert row["expected_in_raw_function_docs"] is True
    assert row["expected_in_prepared_schema"] is True
    assert row["expected_in_runtime_candidates"] is True
    assert row["expected_in_schema_top5"] is False
    assert row["drop_stage"] == "runtime_to_top5_rank_drop"
    assert audit["summary"]["coverage_runtime"] == 1.0
    assert audit["summary"]["coverage_top5"] == 0.0


def test_bfcl_candidate_coverage_audit_keeps_gold_out_of_runtime_diagnostics(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_coverage_gold_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    runtime_diagnostic = {
        "runtime_candidate_tool_ids": ["safe_tool"],
        "runtime_candidate_original_function_names": ["safe_tool"],
        "ranker_candidate_tool_ids": ["safe_tool"],
        "ranker_candidate_original_function_names": ["safe_tool"],
        "schema_top_5": [{"tool_id": "safe_tool", "bfcl_original_function_name": "safe_tool"}],
        "selected_tool_id": "safe_tool",
        "selected_reason": "schema_top1_no_planner",
    }
    trace_path.write_text(json.dumps({"metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}}}), encoding="utf-8")
    row = {
        "run_index": "1",
        "task_id": "task_1",
        "system": "a2_planner",
        "gold_tool": "safe_tool",
        "candidate_tools": json.dumps([{"tool_id": "safe_tool"}]),
        "trace_path": str(trace_path),
        "official_bfcl_eval_unsupported_reasons": json.dumps([]),
        "official_bfcl_eval_success": 1.0,
    }

    audit = module._bfcl_candidate_coverage_audit([row])
    runtime_text = json.dumps(module._first_bfcl_selection_diagnostic(row))

    assert "expected_function" not in runtime_text
    assert "gold_tool" not in runtime_text
    assert audit["rows"][0]["expected_function"] == "safe_tool"


def test_bfcl_candidate_coverage_marks_abstain_elision_as_intentional() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_module_candidate_pool_exception",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    stage, reason = module._bfcl_coverage_drop_stage(
        expected="expected_tool",
        expected_in_raw=True,
        expected_in_prepared=True,
        expected_in_runtime=False,
        expected_in_ranker=False,
        expected_in_top5=False,
        expected_is_top1=False,
        selected_is_expected=False,
        success=False,
        candidate_pool_exception="bfcl_abstain",
    )

    assert stage == "bfcl_abstain_candidate_elision"
    assert "abstain" in reason.lower()


def test_bfcl_candidate_coverage_splits_abstain_substages(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_module_abstain_substages",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "task_annotations": {
                        "bfcl_rerank_diagnostics": [
                            {
                                "candidate_pool_exception": "bfcl_abstain",
                                "abstain_reason": "irrelevance_classifier",
                                "abstain_policy_version": "bfcl_abstain_policy_v2",
                                "abstain_due_to_irrelevance_classifier": True,
                                "abstain_due_to_no_viable_schema_top1": False,
                                "abstain_due_to_no_groundable_required_args": False,
                                "abstain_due_to_planner_noop": False,
                                "abstain_due_to_parallel_shape_guard": False,
                                "abstain_with_schema_top1_available": True,
                                "abstain_with_operation_cues_present": True,
                                "operation_cues_present": True,
                                "runtime_candidate_tool_ids": [],
                                "runtime_candidate_original_function_names": [],
                                "runtime_candidate_count": 0,
                                "ranker_candidate_tool_ids": ["expected_tool"],
                                "ranker_candidate_original_function_names": ["expected_tool"],
                                "ranker_candidate_count": 1,
                                "schema_top_5": [
                                    {"tool_id": "expected_tool", "bfcl_original_function_name": "expected_tool"}
                                ],
                                "selected_tool_id": "",
                                "selected_reason": "bfcl_abstain",
                            }
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    row = {
        "run_index": 1,
        "task_id": "abstain_substage",
        "system": "a2_planner",
        "bfcl_group": "live",
        "bfcl_call_pattern": "serial",
        "gold_tool": "expected_tool",
        "chosen_tool": "",
        "official_bfcl_eval_success": 0.0,
        "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_count"]),
        "candidate_tools": json.dumps(
            [
                {
                    "tool_id": "expected_tool",
                    "metadata": {"bfcl_original_function_name": "expected_tool"},
                }
            ]
        ),
        "trace_path": str(trace_path),
    }

    audit = module._bfcl_candidate_coverage_audit([row])
    summary = audit["summary"]
    assert summary["drop_stage_counts"]["bfcl_abstain_candidate_elision"] == 1
    assert summary["abstain_substage_counts"]["abstain_due_to_irrelevance_classifier"] == 1
    assert summary["abstain_substage_counts"]["abstain_with_schema_top1_available"] == 1
    assert summary["abstain_substage_counts"]["abstain_with_operation_cues_present"] == 1
    assert audit["rows"][0]["abstain_reason"] == "irrelevance_classifier"


def test_bfcl_selected_correct_failure_audit_classifies_argument_and_shape_buckets(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_selected_correct_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def row_for(
        *,
        task_id: str,
        expected_calls: list[dict],
        emitted_calls: list[dict],
        reasons: list[str],
        success: float = 0.0,
        call_pattern: str = "serial",
        group: str = "non_live",
        candidate_tools: list[dict] | None = None,
    ) -> dict:
        trace_path = tmp_path / f"{task_id}.json"
        events = [
            {
                "event_type": "tool_call",
                "tool_id": call["tool_name"],
                "tool_args": call.get("arguments", {}),
            }
            for call in emitted_calls
        ]
        selected_tool = expected_calls[0]["tool_name"] if expected_calls else "expected_tool"
        runtime_diagnostic = {
            "runtime_candidate_tool_ids": [selected_tool],
            "runtime_candidate_original_function_names": [selected_tool],
            "ranker_candidate_tool_ids": [selected_tool],
            "ranker_candidate_original_function_names": [selected_tool],
            "schema_top_5": [{"tool_id": selected_tool, "bfcl_original_function_name": selected_tool}],
            "selected_tool_id": selected_tool,
            "selected_reason": "schema_top1_no_planner",
        }
        trace_path.write_text(
            json.dumps(
                {
                    "metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}},
                    "events": events,
                }
            ),
            encoding="utf-8",
        )
        tools = candidate_tools or [
            {
                "tool_id": selected_tool,
                "metadata": {"bfcl_original_function_name": selected_tool},
                "parameters": {
                    "type": "dict",
                    "required": ["city"],
                    "properties": {"city": {"type": "string"}},
                },
            }
        ]
        return {
            "run_index": "1",
            "task_id": task_id,
            "system": "a2_planner",
            "bfcl_group": group,
            "bfcl_call_pattern": call_pattern,
            "gold_tool": selected_tool,
            "chosen_tool": selected_tool,
            "candidate_tools": json.dumps(tools),
            "expected_call_structure": json.dumps({"pattern": call_pattern, "calls": expected_calls}),
            "trace_path": str(trace_path),
            "official_bfcl_eval_unsupported_reasons": json.dumps(reasons),
            "official_bfcl_eval_success": success,
        }

    rows = [
        row_for(
            task_id="selected_success",
            expected_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            emitted_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            reasons=[],
            success=1.0,
        ),
        row_for(
            task_id="missing_required",
            expected_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            emitted_calls=[{"tool_name": "weather", "arguments": {}}],
            reasons=["missing_required"],
        ),
        row_for(
            task_id="wrong_type",
            expected_calls=[{"tool_name": "counter", "arguments": {"count": 2}}],
            emitted_calls=[{"tool_name": "counter", "arguments": {"count": "two"}}],
            reasons=["value_error"],
            candidate_tools=[
                {
                    "tool_id": "counter",
                    "metadata": {"bfcl_original_function_name": "counter"},
                    "parameters": {
                        "type": "dict",
                        "required": ["count"],
                        "properties": {"count": {"type": "integer"}},
                    },
                }
            ],
        ),
        row_for(
            task_id="wrong_value",
            expected_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            emitted_calls=[{"tool_name": "weather", "arguments": {"city": "London"}}],
            reasons=["value_error"],
        ),
        row_for(
            task_id="wrong_structure",
            expected_calls=[{"tool_name": "nested", "arguments": {"payload": {"city": "Paris"}}}],
            emitted_calls=[{"tool_name": "nested", "arguments": {"payload": "Paris"}}],
            reasons=["value_error"],
            candidate_tools=[
                {
                    "tool_id": "nested",
                    "metadata": {"bfcl_original_function_name": "nested"},
                    "parameters": {
                        "type": "dict",
                        "required": ["payload"],
                        "properties": {"payload": {"type": "object"}},
                    },
                }
            ],
        ),
        row_for(
            task_id="wrong_count",
            expected_calls=[
                {"tool_name": "weather", "arguments": {"city": "Paris"}},
                {"tool_name": "weather", "arguments": {"city": "Berlin"}},
            ],
            emitted_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            reasons=["wrong_count"],
            call_pattern="serial",
        ),
        row_for(
            task_id="parallel_shape",
            expected_calls=[
                {"tool_name": "weather", "arguments": {"city": "Paris"}},
                {"tool_name": "weather", "arguments": {"city": "Berlin"}},
            ],
            emitted_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            reasons=["wrong_count"],
            call_pattern="parallel",
        ),
        row_for(
            task_id="multi_turn",
            expected_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            emitted_calls=[{"tool_name": "weather", "arguments": {"city": "Paris"}}],
            reasons=["multi_turn_mismatch"],
            group="multi_turn",
        ),
        row_for(
            task_id="wrong_order",
            expected_calls=[
                {"tool_name": "tool_a", "arguments": {"city": "Paris"}},
                {"tool_name": "tool_b", "arguments": {"city": "Paris"}},
            ],
            emitted_calls=[
                {"tool_name": "tool_b", "arguments": {"city": "Paris"}},
                {"tool_name": "tool_a", "arguments": {"city": "Paris"}},
            ],
            reasons=["wrong_order"],
            candidate_tools=[
                {
                    "tool_id": "tool_a",
                    "metadata": {"bfcl_original_function_name": "tool_a"},
                    "parameters": {"type": "dict", "required": ["city"], "properties": {"city": {"type": "string"}}},
                },
                {
                    "tool_id": "tool_b",
                    "metadata": {"bfcl_original_function_name": "tool_b"},
                    "parameters": {"type": "dict", "required": ["city"], "properties": {"city": {"type": "string"}}},
                },
            ],
        ),
    ]

    audit = module._bfcl_selected_correct_failure_audit(rows)
    summary = audit["summary"]
    buckets = summary["selected_correct_failure_bucket_counts"]

    assert audit["audit_schema_version"] == "bfcl_selected_correct_failure_audit_v1"
    assert summary["selected_is_expected_count"] == len(rows)
    assert summary["success_given_selected_is_expected"] == 1
    assert summary["missing_required_given_selected_is_expected"] == 1
    assert summary["wrong_arg_type_given_selected_is_expected"] == 1
    assert summary["wrong_arg_value_given_selected_is_expected"] == 1
    assert summary["wrong_arg_structure_given_selected_is_expected"] == 1
    assert summary["wrong_call_count_given_selected_is_expected"] == 1
    assert summary["wrong_call_order_given_selected_is_expected"] == 1
    assert summary["parallel_shape_error_given_selected_is_expected"] == 1
    assert summary["multi_turn_state_error_given_selected_is_expected"] == 1
    assert summary["wrong_call_count_missing_calls"] == 2
    assert summary["wrong_call_count_extra_calls"] == 0
    assert summary["wrong_call_count_zero_emitted"] == 0
    assert summary["wrong_call_count_single_for_multiple"] == 2
    assert summary["wrong_call_count_multiple_for_single"] == 0
    assert summary["parallel_expected_but_serial_emitted"] == 1
    assert summary["serial_expected_but_parallel_emitted"] == 0
    assert summary["parallel_call_count_correct_but_grouping_wrong"] == 0
    assert summary["parallel_order_only_mismatch"] == 0
    assert summary["call_count_delta_counts"]["-1"] == 2
    assert buckets["selected_correct_success"] == 1


def test_bfcl_selected_correct_failure_audit_keeps_gold_out_of_runtime_diagnostics(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_selected_correct_gold_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    runtime_diagnostic = {
        "runtime_candidate_tool_ids": ["weather"],
        "runtime_candidate_original_function_names": ["weather"],
        "ranker_candidate_tool_ids": ["weather"],
        "ranker_candidate_original_function_names": ["weather"],
        "schema_top_5": [{"tool_id": "weather", "bfcl_original_function_name": "weather"}],
        "selected_tool_id": "weather",
        "selected_reason": "schema_top1_no_planner",
    }
    trace_path.write_text(
        json.dumps(
            {
                "metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}},
                "events": [{"event_type": "tool_call", "tool_id": "weather", "tool_args": {"city": "Paris"}}],
            }
        ),
        encoding="utf-8",
    )
    row = {
        "run_index": "1",
        "task_id": "task_1",
        "system": "a2_planner",
        "bfcl_group": "non_live",
        "bfcl_call_pattern": "serial",
        "gold_tool": "weather",
        "candidate_tools": json.dumps([{"tool_id": "weather", "metadata": {"bfcl_original_function_name": "weather"}}]),
        "expected_call_structure": json.dumps({"pattern": "serial", "calls": [{"tool_name": "weather", "arguments": {"city": "Paris"}}]}),
        "trace_path": str(trace_path),
        "official_bfcl_eval_unsupported_reasons": json.dumps([]),
        "official_bfcl_eval_success": 1.0,
    }

    audit = module._bfcl_selected_correct_failure_audit([row])
    runtime_text = json.dumps(module._first_bfcl_selection_diagnostic(row))

    assert audit["runtime_diagnostics_gold_free"] is True
    assert "expected_call_count" not in runtime_text
    assert "official_failure_bucket" not in runtime_text
    assert audit["rows"][0]["expected_call_count"] == 1
    assert audit["rows"][0]["official_failure_bucket"] == "official_success_or_safe_failure"


def test_bfcl_selected_correct_failure_audit_matches_candidate_coverage_selected_count(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_selected_correct_regression_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "task_annotations": {
                        "bfcl_rerank_diagnostics": [
                            {
                                "runtime_candidate_tool_ids": ["weather"],
                                "runtime_candidate_original_function_names": ["weather"],
                                "ranker_candidate_tool_ids": ["weather"],
                                "ranker_candidate_original_function_names": ["weather"],
                                "schema_top_5": [{"tool_id": "weather", "bfcl_original_function_name": "weather"}],
                                "selected_tool_id": "weather",
                                "selected_reason": "schema_top1_no_planner",
                            }
                        ]
                    }
                },
                "events": [{"event_type": "tool_call", "tool_id": "weather", "tool_args": {"city": "Paris"}}],
            }
        ),
        encoding="utf-8",
    )
    row = {
        "run_index": "1",
        "task_id": "task_1",
        "system": "a2_planner",
        "bfcl_group": "non_live",
        "bfcl_call_pattern": "serial",
        "gold_tool": "weather",
        "candidate_tools": json.dumps([{"tool_id": "weather", "metadata": {"bfcl_original_function_name": "weather"}}]),
        "expected_call_structure": json.dumps({"pattern": "serial", "calls": [{"tool_name": "weather", "arguments": {"city": "Paris"}}]}),
        "trace_path": str(trace_path),
        "official_bfcl_eval_unsupported_reasons": json.dumps([]),
        "official_bfcl_eval_success": 1.0,
    }

    coverage = module._bfcl_candidate_coverage_audit([row])
    selected_correct = module._bfcl_selected_correct_failure_audit([row])

    assert coverage["summary"]["selected_is_expected"] == 1
    assert selected_correct["summary"]["selected_is_expected_count"] == coverage["summary"]["selected_is_expected"]


def test_bfcl_selected_correct_summary_splits_zero_emitted_sources() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_zero_emitted_sources_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = [
        {
            "selected_is_expected": False,
            "selected_correct_failure_bucket": "not_selected_expected",
            "zero_emitted_due_to_abstain_classifier": True,
        },
        {
            "selected_is_expected": True,
            "selected_correct_failure_bucket": "wrong_call_count",
            "wrong_call_count_zero_emitted": True,
            "zero_emitted_after_schema_selection": True,
            "zero_emitted_due_to_call_shape_canonicalizer": True,
            "zero_emitted_due_to_no_grounded_args": True,
            "call_count_delta": -1,
        },
        {
            "selected_is_expected": True,
            "selected_correct_failure_bucket": "parallel_shape_error",
            "parallel_or_multiple_shape_mismatch": True,
            "wrong_call_count_zero_emitted": True,
            "zero_emitted_after_schema_selection": True,
            "zero_emitted_due_to_parallel_clause_drop": True,
            "parallel_argument_sets_extracted": True,
            "parallel_argument_set_count": 3,
            "parallel_clause_materialized_count": 2,
            "parallel_clause_drop_count": 1,
            "parallel_collapsed_to_serial": True,
            "call_count_delta": -2,
        },
    ]

    summary = module._selected_correct_summary_for_rows(rows)

    assert summary["zero_emitted_due_to_abstain_classifier"] == 1
    assert summary["zero_emitted_after_schema_selection"] == 2
    assert summary["zero_emitted_due_to_call_shape_canonicalizer"] == 1
    assert summary["zero_emitted_due_to_parallel_clause_drop"] == 1
    assert summary["zero_emitted_due_to_no_grounded_args"] == 1
    assert summary["parallel_argument_sets_extracted"] == 1
    assert summary["parallel_argument_set_count"] == 3
    assert summary["parallel_clause_materialized_count"] == 2
    assert summary["parallel_clause_drop_count"] == 1
    assert summary["parallel_collapsed_to_serial"] == 1


def test_bfcl_candidate_coverage_summary_counts_serial_abstain_blocked_rows() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_serial_abstain_blocked_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = [
        {
            "selected_is_expected": True,
            "expected_in_runtime_candidates": True,
            "expected_is_schema_top1": True,
            "official_success": False,
            "drop_stage": "selected_correct_arg_or_shape_error",
            "abstain_blocked_by_serial_schema_top1": True,
            "serial_positive_call_forced": True,
            "irrelevance_abstain_allowed": False,
        }
    ]

    summary = module._coverage_summary_for_rows(rows)

    assert summary["abstain_substage_counts"]["abstain_blocked_by_serial_schema_top1"] == 1
    assert summary["abstain_substage_counts"]["serial_positive_call_forced"] == 1
    assert summary["abstain_substage_counts"]["irrelevance_abstain_allowed"] == 0


def test_bfcl_selected_correct_audit_classifies_serial_post_selection_no_call(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_serial_post_selection_no_call_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "zero_trace.json"
    runtime_diagnostic = {
        "runtime_candidate_tool_ids": ["weather"],
        "runtime_candidate_original_function_names": ["weather"],
        "ranker_candidate_tool_ids": ["weather"],
        "ranker_candidate_original_function_names": ["weather"],
        "schema_top_5": [{"tool_id": "weather", "bfcl_original_function_name": "weather"}],
        "selected_tool_id": "weather",
        "selected_reason": "schema_top1_no_planner",
        "trace_tool_call_expected_by_bfcl_serial": True,
        "serial_selected_top1_materialized": True,
        "serial_selected_top1_materialization_blocked": False,
        "serial_materialization_block_reason": "",
        "selected_required_argument_coverage": 0.0,
    }
    trace_path.write_text(
        json.dumps({"metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}}, "events": [], "metrics": {"tool_calls": 0}}),
        encoding="utf-8",
    )
    row = {
        "run_index": "1",
        "task_id": "serial_no_call",
        "system": "a2_planner",
        "bfcl_group": "non_live",
        "bfcl_call_pattern": "serial",
        "gold_tool": "weather",
        "chosen_tool": "weather",
        "candidate_tools": json.dumps([{"tool_id": "weather", "metadata": {"bfcl_original_function_name": "weather"}}]),
        "expected_call_structure": json.dumps({"pattern": "serial", "calls": [{"tool_name": "weather", "arguments": {"city": "Paris"}}]}),
        "trace_path": str(trace_path),
        "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_count"]),
        "official_bfcl_eval_success": 0.0,
    }

    audit = module._bfcl_selected_correct_failure_audit([row])
    audit_row = audit["rows"][0]
    summary = audit["summary"]
    assert audit_row["selected_top1_but_no_emitted_call"] is True
    assert audit_row["selected_top1_but_serial_call_missing_args_and_suppressed"] is True
    assert summary["selected_top1_but_no_emitted_call"] == 1
    assert summary["selected_top1_but_serial_call_missing_args_and_suppressed"] == 1


def test_bfcl_selected_correct_audit_classifies_trace_parser_drop(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_trace_parser_drop_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    trace_path = tmp_path / "parser_drop_trace.json"
    runtime_diagnostic = {
        "runtime_candidate_tool_ids": ["weather"],
        "runtime_candidate_original_function_names": ["weather"],
        "ranker_candidate_tool_ids": ["weather"],
        "ranker_candidate_original_function_names": ["weather"],
        "schema_top_5": [{"tool_id": "weather", "bfcl_original_function_name": "weather"}],
        "selected_tool_id": "weather",
        "selected_reason": "schema_top1_no_planner",
        "trace_tool_call_expected_by_bfcl_serial": True,
    }
    trace_path.write_text(
        json.dumps({"metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [runtime_diagnostic]}}, "events": [], "metrics": {"tool_calls": 1}}),
        encoding="utf-8",
    )
    row = {
        "run_index": "1",
        "task_id": "parser_drop",
        "system": "a2_planner",
        "bfcl_group": "non_live",
        "bfcl_call_pattern": "serial",
        "gold_tool": "weather",
        "chosen_tool": "weather",
        "candidate_tools": json.dumps([{"tool_id": "weather", "metadata": {"bfcl_original_function_name": "weather"}}]),
        "expected_call_structure": json.dumps({"pattern": "serial", "calls": [{"tool_name": "weather", "arguments": {"city": "Paris"}}]}),
        "trace_path": str(trace_path),
        "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_count"]),
        "official_bfcl_eval_success": 0.0,
    }

    audit_row = module._bfcl_selected_correct_failure_audit([row])["rows"][0]
    assert audit_row["selected_top1_but_trace_has_call_not_in_final_answer"] is True
    assert audit_row["selected_top1_but_final_answer_parser_drops_call"] is True


def test_bfcl_guard_gates_separate_wrong_function_bucket_from_claim_readiness() -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_guard_gate_names_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rows = [
        {"system": "a0_baseline", "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"])},
        {"system": "a2_planner", "official_bfcl_eval_unsupported_reasons": json.dumps(["wrong_func_name"])},
    ]
    scoreboard = {
        "per_system": {
            "a0_baseline": {
                "official_bfcl_eval_tool_selection_correctness": 0.6,
                "official_bfcl_eval_success": 0.5,
            },
            "a2_planner": {
                "official_bfcl_eval_tool_selection_correctness": 0.6,
                "official_bfcl_eval_success": 0.4,
            },
        }
    }
    gates = module._bfcl_guard_claim_gates(rows, scoreboard)
    assert gates["wrong_function_bucket_non_regression"] is True
    assert gates["exact_function_guard_claim_ready"] is False
    assert gates["wrong_function_non_regression_ready"] is False


def test_bfcl_selected_correct_audit_splits_missing_required_subcauses(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "score_bfcl_outputs_missing_required_subcauses_module",
        ROOT_DIR / "scripts" / "score_bfcl_outputs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def row_for(task_id: str, diagnostic: dict, expected_arg: str = "city") -> dict:
        trace_path = tmp_path / f"{task_id}.json"
        trace_path.write_text(
            json.dumps(
                {
                    "metadata": {"task_annotations": {"bfcl_rerank_diagnostics": [diagnostic]}},
                    "events": [{"event_type": "tool_call", "tool_id": "weather", "tool_args": {}}],
                    "metrics": {"tool_calls": 1},
                }
            ),
            encoding="utf-8",
        )
        return {
            "run_index": "1",
            "task_id": task_id,
            "system": "a2_planner",
            "bfcl_group": "non_live",
            "bfcl_call_pattern": "serial",
            "gold_tool": "weather",
            "chosen_tool": "weather",
            "candidate_tools": json.dumps(
                [
                    {
                        "tool_id": "weather",
                        "metadata": {"bfcl_original_function_name": "weather"},
                        "parameters": {
                            "type": "dict",
                            "required": ["city"],
                            "properties": {"city": {"type": "string"}},
                        },
                    }
                ]
            ),
            "expected_call_structure": json.dumps(
                {"pattern": "serial", "calls": [{"tool_name": "weather", "arguments": {expected_arg: "Paris"}}]}
            ),
            "trace_path": str(trace_path),
            "official_bfcl_eval_unsupported_reasons": json.dumps(["missing_required"]),
            "official_bfcl_eval_success": 0.0,
        }

    base_diag = {
        "runtime_candidate_tool_ids": ["weather"],
        "runtime_candidate_original_function_names": ["weather"],
        "ranker_candidate_tool_ids": ["weather"],
        "ranker_candidate_original_function_names": ["weather"],
        "schema_top_5": [{"tool_id": "weather", "bfcl_original_function_name": "weather"}],
        "selected_tool_id": "weather",
        "selected_reason": "schema_top1_no_planner",
        "trace_tool_call_expected_by_bfcl_serial": True,
    }
    rows = [
        row_for("grounder_not_attempted", dict(base_diag)),
        row_for(
            "no_query_cue",
            {
                **base_diag,
                "serial_required_grounding_attempted": True,
                "required_args": ["city"],
                "grounded_required_args": [],
                "ungrounded_required_args": ["city"],
                "grounding_source_by_arg": {"city": "unresolved"},
                "grounding_confidence_by_arg": {"city": 0.0},
            },
        ),
        row_for(
            "serializer_drop",
            {
                **base_diag,
                "serial_required_grounding_attempted": True,
                "required_args": ["city"],
                "grounded_required_args": ["city"],
                "ungrounded_required_args": [],
                "grounding_source_by_arg": {"city": "quoted_span"},
                "grounding_confidence_by_arg": {"city": 0.88},
            },
        ),
        row_for(
            "schema_alias",
            {
                **base_diag,
                "serial_required_grounding_attempted": True,
                "required_args": ["city"],
                "grounded_required_args": [],
                "ungrounded_required_args": ["city"],
                "grounding_source_by_arg": {"city": "unresolved"},
                "grounding_confidence_by_arg": {"city": 0.0},
            },
            expected_arg="location",
        ),
        row_for(
            "value_filtered",
            {
                **base_diag,
                "serial_required_grounding_attempted": True,
                "required_args": ["city"],
                "grounded_required_args": [],
                "ungrounded_required_args": [],
                "grounding_source_by_arg": {"city": "value_filtered"},
                "grounding_confidence_by_arg": {"city": 0.4},
            },
        ),
    ]

    audit = module._bfcl_selected_correct_failure_audit(rows)
    summary = audit["summary"]

    assert summary["missing_required_given_selected_is_expected"] == 5
    assert summary["missing_required_due_to_grounder_not_attempted"] == 1
    assert summary["missing_required_due_to_no_query_cue"] == 1
    assert summary["missing_required_due_to_final_answer_serializer_drop"] == 1
    assert summary["missing_required_due_to_schema_alias_mismatch"] == 1
    assert summary["missing_required_due_to_value_filtered"] == 1
    assert all(row["selected_correct_failure_bucket"] == "missing_required" for row in audit["rows"])
    assert audit["runtime_diagnostics_gold_free"] is True


def _load_run_eval_grounding_module():
    module_name = "run_eval_bfcl_serial_grounding_module"
    spec = importlib.util.spec_from_file_location(
        module_name,
        ROOT_DIR / "scripts" / "run_eval.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _bfcl_grounding_tool(module, required: list[str], properties: dict) -> object:
    return module.ToolSpec(
        tool_id="test_tool",
        description="Test BFCL tool",
        metadata={
            "parameters": {
                "type": "dict",
                "required": required,
                "properties": properties,
            }
        },
    )


def test_bfcl_serial_assignment_disambiguates_city_and_user_name() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["city", "user_name"],
        {
            "city": {"type": "string", "description": "Destination city"},
            "user_name": {"type": "string", "description": "Name of the user"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Book "Paris". The user name is "Alice".',
        {},
    )

    assert inputs["city"] == "Paris"
    assert inputs["user_name"] == "Alice"
    assert diagnostics["consumed_candidate_span_by_arg"]["city"] != diagnostics["consumed_candidate_span_by_arg"]["user_name"]
    assert diagnostics["value_validation_by_arg"]["city"] == "accepted"
    assert diagnostics["value_validation_by_arg"]["user_name"] == "accepted"


def test_bfcl_serial_assignment_uses_prepositions_for_source_and_target() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["source", "target"],
        {
            "source": {"type": "string", "description": "Source folder"},
            "target": {"type": "string", "description": "Target folder"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Move the file from "downloads" to "backup".',
        {},
    )

    assert inputs["source"] == "downloads"
    assert inputs["target"] == "backup"
    assert diagnostics["descriptor_match_by_arg"]["source"] == "preposition_from"
    assert diagnostics["descriptor_match_by_arg"]["target"] == "preposition_to"


def test_bfcl_serial_assignment_exact_from_to_parameter_names_prefer_prepositions() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["from", "to"],
        {
            "from": {"type": "string", "description": "Starting folder"},
            "to": {"type": "string", "description": "Ending folder"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Copy the file from "downloads" to "backup".',
        {},
    )

    assert inputs["from"] == "downloads"
    assert inputs["to"] == "backup"
    assert diagnostics["high_evidence_assignment_allowed_by_arg"]["from"] is True
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["from"] == "parameter_from_preposition"
    assert diagnostics["high_evidence_assignment_allowed_by_arg"]["to"] is True
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["to"] == "parameter_to_preposition"


def test_bfcl_serial_assignment_descriptor_preposition_relaxes_non_obvious_keys() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["folder_a", "folder_b"],
        {
            "folder_a": {"type": "string", "description": "Origin source folder"},
            "folder_b": {"type": "string", "description": "Destination target folder"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Move records from "archive" to "warehouse".',
        {},
    )

    assert inputs["folder_a"] == "archive"
    assert inputs["folder_b"] == "warehouse"
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["folder_a"] == "descriptor_from_preposition"
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["folder_b"] == "descriptor_to_preposition"


def test_bfcl_serial_assignment_strong_type_cues_survive_validation() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["mode", "recipient_email", "count"],
        {
            "mode": {"type": "string", "enum": ["fast", "safe"]},
            "recipient_email": {"type": "string", "description": "Recipient email address"},
            "count": {"type": "integer", "description": "Number of retries"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        "Use safe mode, send to ops@example.com, and retry 3 times.",
        {},
    )

    assert inputs["mode"] == "safe"
    assert inputs["recipient_email"] == "ops@example.com"
    assert inputs["count"] == 3
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["mode"] == "enum_exact_mention"
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["recipient_email"] == "email_type_cue"
    assert diagnostics["high_evidence_assignment_reason_by_arg"]["count"] == "numeric_type_cue"


def test_bfcl_serial_assignment_keeps_weak_person_text_quoted_span_blocked() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["user_name", "payload"],
        {
            "user_name": {"type": "string", "description": "Name of the user"},
            "payload": {"type": "string", "description": "Opaque request payload"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Book "Paris" for tomorrow.',
        {},
    )

    assert "user_name" not in inputs
    assert "payload" not in inputs
    assert diagnostics["ambiguous_alias_blocked_by_arg"]["user_name"] is True
    assert diagnostics["value_validation_by_arg"]["payload"] in {"ambiguous_alias_blocked", "low_confidence_assignment_blocked"}


def test_bfcl_serial_assignment_blocks_ambiguous_target_quoted_span() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["target"],
        {"target": {"type": "string", "description": "Target entity"}},
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Process "Paris" for user "Alice".',
        {},
    )

    assert "target" not in inputs
    assert diagnostics["ungrounded_required_args"] == ["target"]
    assert diagnostics["ambiguous_alias_blocked_by_arg"]["target"] is True
    assert diagnostics["value_validation_by_arg"]["target"] == "ambiguous_alias_blocked"


def test_bfcl_serial_assignment_does_not_treat_no_later_than_as_boolean_false() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["include_archived"],
        {"include_archived": {"type": "boolean", "description": "Whether to include archived records"}},
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        "Find events no later than five days from now.",
        {},
    )

    assert "include_archived" not in inputs
    assert diagnostics["ungrounded_required_args"] == ["include_archived"]
    assert diagnostics["low_confidence_assignment_blocked_by_arg"]["include_archived"] is False


def test_bfcl_serial_assignment_uses_schema_descriptor_for_destination() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["code"],
        {"code": {"type": "string", "description": "Destination city for the booking"}},
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        "Send the package to Paris.",
        {},
    )

    assert inputs["code"] == "Paris"
    assert diagnostics["alias_match_by_arg"]["code"] in {"location", "destination"}
    assert diagnostics["descriptor_match_by_arg"]["code"] in {"schema_descriptor", "preposition_to"}


def test_bfcl_serial_assignment_array_uses_local_list_cue_only() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["city", "guests"],
        {
            "city": {"type": "string", "description": "Destination city"},
            "guests": {"type": "array", "items": {"type": "string"}, "description": "Guest names"},
        },
    )

    inputs, diagnostics = module._bfcl_ground_serial_required_args(
        tool,
        'Book "Paris". Guests are "Alice" and "Bob".',
        {},
    )

    assert inputs["city"] == "Paris"
    assert inputs["guests"] == ["Alice", "Bob"]
    assert "Paris" not in inputs["guests"]
    assert diagnostics["value_validation_by_arg"]["guests"] == "accepted"


def test_bfcl_serial_assignment_diagnostics_are_gold_free() -> None:
    module = _load_run_eval_grounding_module()
    tool = _bfcl_grounding_tool(
        module,
        ["target"],
        {"target": {"type": "string", "description": "Target entity"}},
    )

    _inputs, diagnostics = module._bfcl_ground_serial_required_args(tool, 'Process "Paris".', {})

    forbidden = {"expected_function", "expected_args", "official_failure_bucket", "expected_call_count", "gold_order"}
    assert forbidden.isdisjoint(diagnostics)
    assert "value_validation_by_arg" in diagnostics
    assert "descriptor_match_by_arg" in diagnostics
    assert "high_evidence_assignment_allowed_by_arg" in diagnostics
    assert "high_evidence_assignment_reason_by_arg" in diagnostics
    assert diagnostics["validation_relaxation_policy_version"] == "bfcl_serial_high_evidence_assignment_v1"
