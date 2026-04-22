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
