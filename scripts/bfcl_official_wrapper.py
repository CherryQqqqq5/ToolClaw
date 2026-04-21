#!/usr/bin/env python3
"""Bridge ToolClaw BFCL traces into the upstream BFCL checker interfaces."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
OFFICIAL_MODEL_NAME = "toolclaw_official_eval"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the upstream BFCL checker over ToolClaw traces")
    parser.add_argument("--prepared-taskset", required=True, help="Prepared BFCL taskset JSON emitted by run_bfcl_bench.py")
    parser.add_argument("--comparison", required=True, help="comparison.raw.csv emitted by run_bfcl_bench.py")
    parser.add_argument("--out", required=True, help="Output JSON path")
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_jsonlike_rows(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        rows: List[Dict[str, Any]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        return rows
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _install_model_config_stub() -> None:
    if "bfcl_eval.constants.model_config" in sys.modules:
        return
    module = types.ModuleType("bfcl_eval.constants.model_config")

    class _ModelConfig:
        underscore_to_dot = False

    model_config = _ModelConfig()
    module.MODEL_CONFIG_MAPPING = {
        OFFICIAL_MODEL_NAME: model_config,
        OFFICIAL_MODEL_NAME.replace("_", "/"): model_config,
        OFFICIAL_MODEL_NAME.replace("_", "."): model_config,
    }
    sys.modules["bfcl_eval.constants.model_config"] = module


def _load_official_modules(official_root: Path) -> Tuple[Any, Any, Any]:
    for module_name in list(sys.modules):
        if module_name == "bfcl_eval" or module_name.startswith("bfcl_eval."):
            del sys.modules[module_name]
    package_root = official_root.resolve()
    if (package_root / "bfcl_eval").exists():
        sys.path.insert(0, str(package_root))
    elif package_root.name == "bfcl_eval" and (package_root / "constants").exists():
        sys.path.insert(0, str(package_root.parent))
    else:
        sys.path.insert(0, str(package_root))
    _install_model_config_stub()
    from bfcl_eval.constants.enums import Language  # type: ignore
    from bfcl_eval.eval_checker.ast_eval.ast_checker import ast_checker  # type: ignore
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import multi_turn_checker  # type: ignore

    return Language, ast_checker, multi_turn_checker


def _task_lookup(path: Path) -> Dict[str, Dict[str, Any]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        return {}
    return {str(task.get("task_id") or ""): task for task in payload if isinstance(task, dict)}


def _trace_lookup(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[int, str, str], Path]:
    lookup: Dict[Tuple[int, str, str], Path] = {}
    for row in rows:
        trace_path = Path(row["trace_path"])
        if not trace_path.is_absolute():
            trace_path = ROOT_DIR / trace_path
        lookup[(int(row.get("run_index", "0") or 0), row["task_id"], row["system"])] = trace_path
    return lookup


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _load_official_prompt_entry(task: Dict[str, Any], cache: Dict[Path, Dict[str, Dict[str, Any]]]) -> Dict[str, Any] | None:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    source_root = str(metadata.get("official_source_root") or "").strip()
    dataset_file = str(metadata.get("official_dataset_file") or "").strip()
    sample_id = str(task.get("task_id") or "")
    if not source_root or not dataset_file or not sample_id:
        return None
    prompt_path = ROOT_DIR / source_root / "bfcl_eval" / "data" / dataset_file
    if prompt_path not in cache:
        cache[prompt_path] = {str(row.get("id") or ""): row for row in _load_jsonlike_rows(prompt_path)}
    return cache[prompt_path].get(sample_id)


def _load_official_ground_truth(task: Dict[str, Any], cache: Dict[Path, Dict[str, Dict[str, Any]]]) -> Dict[str, Any] | None:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    source_root = str(metadata.get("official_source_root") or "").strip()
    dataset_file = str(metadata.get("official_dataset_file") or "").strip()
    sample_id = str(task.get("task_id") or "")
    if not source_root or not dataset_file or not sample_id:
        return None
    answer_path = ROOT_DIR / source_root / "bfcl_eval" / "data" / "possible_answer" / dataset_file
    if not answer_path.exists():
        return None
    if answer_path not in cache:
        cache[answer_path] = {str(row.get("id") or ""): row for row in _load_jsonlike_rows(answer_path)}
    return cache[answer_path].get(sample_id)


def _extract_actual_calls(trace_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = trace_payload.get("events", [])
    if not isinstance(events, list):
        return []
    calls: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict) or event.get("event_type") != "tool_call":
            continue
        tool_id = str(event.get("tool_id") or "").strip()
        tool_args = event.get("tool_args")
        calls.append(
            {
                "tool_id": tool_id,
                "arguments": dict(tool_args) if isinstance(tool_args, dict) else {},
            }
        )
    return calls


def _actual_ast_calls(actual_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{call["tool_id"]: dict(call.get("arguments", {}))} for call in actual_calls if call.get("tool_id")]


def _expected_tools_from_ground_truth(ground_truth: Any) -> List[str]:
    if not isinstance(ground_truth, list):
        return []
    tools: List[str] = []
    for item in ground_truth:
        if isinstance(item, dict) and item:
            tools.append(str(next(iter(item.keys()))))
    return tools


def _tool_overlap(expected_tools: List[str], actual_tools: List[str]) -> float:
    expected_counter = Counter(tool for tool in expected_tools if tool)
    actual_counter = Counter(tool for tool in actual_tools if tool)
    if not expected_counter:
        return 0.0
    matched = sum(min(expected_counter[tool], actual_counter.get(tool, 0)) for tool in expected_counter)
    return matched / max(sum(expected_counter.values()), 1)


def _structure_correctness(category: str, expected_tools: List[str], actual_tools: List[str]) -> float:
    if "parallel" in category:
        return 1.0 if Counter(expected_tools) == Counter(actual_tools) and len(expected_tools) == len(actual_tools) else 0.0
    return 1.0 if expected_tools == actual_tools else 0.0


def _language_enum(Language: Any, language: str) -> Any:
    normalized = str(language or "en").strip().lower()
    if normalized == "java":
        return Language.JAVA
    if normalized in {"javascript", "js"}:
        return Language.JAVASCRIPT
    return Language.PYTHON


def _python_literal(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_python_literal(item) for item in value) + "]"
    if isinstance(value, tuple):
        inner = ", ".join(_python_literal(item) for item in value)
        if len(value) == 1:
            inner += ","
        return f"({inner})"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{repr(str(key))}: {_python_literal(val)}" for key, val in value.items()) + "}"
    return repr(value)


def _call_to_exec_string(call: Dict[str, Any]) -> str:
    tool_id = str(call.get("tool_id") or "").strip()
    if not tool_id:
        return ""
    arguments = call.get("arguments", {})
    if not isinstance(arguments, dict) or not arguments:
        return f"{tool_id}()"
    argument_str = ", ".join(f"{key}={_python_literal(value)}" for key, value in arguments.items())
    return f"{tool_id}({argument_str})"


def _chunk_actual_calls_by_ground_truth(
    actual_calls: List[Dict[str, Any]],
    ground_truth_turns: List[List[str]],
) -> List[List[List[str]]]:
    actual_strings = [call_str for call_str in (_call_to_exec_string(call) for call in actual_calls) if call_str]
    chunked: List[List[List[str]]] = []
    cursor = 0
    for turn in ground_truth_turns:
        if not isinstance(turn, list):
            chunked.append([[]])
            continue
        turn_count = len(turn)
        if turn_count <= 0:
            chunked.append([[]])
            continue
        current = actual_strings[cursor : cursor + turn_count]
        cursor += turn_count
        chunked.append([current] if current else [[]])
    if actual_strings[cursor:] and chunked:
        tail = list(chunked[-1][0]) if chunked[-1] else []
        tail.extend(actual_strings[cursor:])
        chunked[-1] = [tail]
    return chunked


def _score_relevance(category: str, actual_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    actual_has_call = any(str(call.get("tool_id") or "").strip() for call in actual_calls)
    success = not actual_has_call if "irrelevance" in category else actual_has_call
    score = float(success)
    return {
        "success": score,
        "tool_selection_correctness": score,
        "argument_correctness": score,
        "structure_correctness": score,
        "paper_safe": True,
        "unsupported_reasons": [],
    }


def _score_ast(
    *,
    Language: Any,
    ast_checker: Any,
    task: Dict[str, Any],
    prompt_entry: Dict[str, Any],
    ground_truth_entry: Dict[str, Any],
    actual_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    category = str(metadata.get("official_dataset_category") or "")
    language = _language_enum(Language, str(metadata.get("bfcl_language") or "en"))
    actual_model_output = _actual_ast_calls(actual_calls)
    possible_answer = ground_truth_entry.get("ground_truth", [])
    checker_result = ast_checker(
        prompt_entry.get("function", []),
        actual_model_output,
        possible_answer,
        language,
        category,
        OFFICIAL_MODEL_NAME,
    )
    expected_tools = _expected_tools_from_ground_truth(possible_answer)
    actual_tools = [str(call.get("tool_id") or "").strip() for call in actual_calls if str(call.get("tool_id") or "").strip()]
    success = bool(checker_result.get("valid"))
    return {
        "success": float(success),
        "tool_selection_correctness": _tool_overlap(expected_tools, actual_tools),
        "argument_correctness": float(success),
        "structure_correctness": _structure_correctness(category, expected_tools, actual_tools),
        "paper_safe": True,
        "unsupported_reasons": [] if success else [str(checker_result.get("error_type") or "official_ast_checker_failed")],
    }


def _score_multi_turn(
    *,
    multi_turn_checker: Any,
    task: Dict[str, Any],
    prompt_entry: Dict[str, Any],
    ground_truth_entry: Dict[str, Any],
    actual_calls: List[Dict[str, Any]],
) -> Dict[str, Any]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    category = str(metadata.get("official_dataset_category") or "")
    ground_truth_turns = ground_truth_entry.get("ground_truth", [])
    if not isinstance(ground_truth_turns, list):
        return {
            "success": 0.0,
            "tool_selection_correctness": 0.0,
            "argument_correctness": 0.0,
            "structure_correctness": 0.0,
            "paper_safe": False,
            "unsupported_reasons": ["missing_multi_turn_ground_truth"],
        }
    chunked_actual = _chunk_actual_calls_by_ground_truth(actual_calls, ground_truth_turns)
    try:
        checker_result = multi_turn_checker(
            chunked_actual,
            ground_truth_turns,
            prompt_entry,
            category,
            OFFICIAL_MODEL_NAME,
        )
    except ModuleNotFoundError as exc:
        missing = str(getattr(exc, "name", "") or type(exc).__name__)
        return {
            "success": 0.0,
            "tool_selection_correctness": 0.0,
            "argument_correctness": 0.0,
            "structure_correctness": 0.0,
            "paper_safe": False,
            "unsupported_reasons": [f"missing_multi_turn_dependency:{missing}"],
        }
    except Exception as exc:
        return {
            "success": 0.0,
            "tool_selection_correctness": 0.0,
            "argument_correctness": 0.0,
            "structure_correctness": 0.0,
            "paper_safe": False,
            "unsupported_reasons": [f"official_multi_turn_runtime_error:{type(exc).__name__}"],
        }
    success = bool(checker_result.get("valid"))
    return {
        "success": float(success),
        "tool_selection_correctness": float(success),
        "argument_correctness": float(success),
        "structure_correctness": float(success),
        "paper_safe": True,
        "unsupported_reasons": [] if success else [str(checker_result.get("error_type") or "official_multi_turn_checker_failed")],
    }


def _score_row(
    *,
    Language: Any,
    ast_checker: Any,
    multi_turn_checker: Any,
    task: Dict[str, Any],
    trace_payload: Dict[str, Any],
    prompt_entry: Dict[str, Any] | None,
    ground_truth_entry: Dict[str, Any] | None,
) -> Dict[str, Any]:
    metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
    category = str(metadata.get("official_dataset_category") or "")
    actual_calls = _extract_actual_calls(trace_payload)

    if not prompt_entry:
        return {
            "success": 0.0,
            "tool_selection_correctness": 0.0,
            "argument_correctness": 0.0,
            "structure_correctness": 0.0,
            "paper_safe": False,
            "unsupported_reasons": ["missing_official_prompt_entry"],
        }
    if "irrelevance" in category or "relevance" in category:
        return _score_relevance(category, actual_calls)
    if "multi_turn" in category:
        if not ground_truth_entry:
            return {
                "success": 0.0,
                "tool_selection_correctness": 0.0,
                "argument_correctness": 0.0,
                "structure_correctness": 0.0,
                "paper_safe": False,
                "unsupported_reasons": ["missing_official_ground_truth"],
            }
        return _score_multi_turn(
            multi_turn_checker=multi_turn_checker,
            task=task,
            prompt_entry=prompt_entry,
            ground_truth_entry=ground_truth_entry,
            actual_calls=actual_calls,
        )
    if not ground_truth_entry:
        return {
            "success": 0.0,
            "tool_selection_correctness": 0.0,
            "argument_correctness": 0.0,
            "structure_correctness": 0.0,
            "paper_safe": False,
            "unsupported_reasons": ["missing_official_ground_truth"],
        }
    return _score_ast(
        Language=Language,
        ast_checker=ast_checker,
        task=task,
        prompt_entry=prompt_entry,
        ground_truth_entry=ground_truth_entry,
        actual_calls=actual_calls,
    )


def main() -> None:
    args = parse_args()
    prepared_taskset = Path(args.prepared_taskset)
    comparison_path = Path(args.comparison)
    out_path = Path(args.out)

    task_lookup = _task_lookup(prepared_taskset)
    rows = _load_csv(comparison_path)
    if not rows:
        payload = {"results": [], "unsupported_strata": [{"stratum": "all", "reason": "empty_comparison", "paper_safe": False}]}
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return

    first_task = task_lookup.get(rows[0]["task_id"], {})
    first_metadata = first_task.get("metadata", {}) if isinstance(first_task.get("metadata"), dict) else {}
    official_source_root = str(first_metadata.get("official_source_root") or "data/external/bfcl_official").strip()
    official_root = ROOT_DIR / official_source_root
    Language, ast_checker, multi_turn_checker = _load_official_modules(official_root)

    prompt_cache: Dict[Path, Dict[str, Dict[str, Any]]] = {}
    ground_truth_cache: Dict[Path, Dict[str, Dict[str, Any]]] = {}
    trace_paths = _trace_lookup(rows)
    unsupported_by_category: Dict[str, set[str]] = defaultdict(set)
    results: List[Dict[str, Any]] = []

    for row in rows:
        key = (int(row.get("run_index", "0") or 0), row["task_id"], row["system"])
        task = task_lookup.get(row["task_id"])
        if not task:
            unsupported_by_category["unknown"].add("missing_prepared_task")
            results.append(
                {
                    "run_index": key[0],
                    "task_id": row["task_id"],
                    "system": row["system"],
                    "success": 0.0,
                    "tool_selection_correctness": 0.0,
                    "argument_correctness": 0.0,
                    "structure_correctness": 0.0,
                    "paper_safe": False,
                    "unsupported_reasons": ["missing_prepared_task"],
                }
            )
            continue
        trace_payload = _load_json(trace_paths[key])
        prompt_entry = _load_official_prompt_entry(task, prompt_cache)
        ground_truth_entry = _load_official_ground_truth(task, ground_truth_cache)
        try:
            score = _score_row(
                Language=Language,
                ast_checker=ast_checker,
                multi_turn_checker=multi_turn_checker,
                task=task,
                trace_payload=trace_payload,
                prompt_entry=prompt_entry,
                ground_truth_entry=ground_truth_entry,
            )
        except Exception as exc:
            score = {
                "success": 0.0,
                "tool_selection_correctness": 0.0,
                "argument_correctness": 0.0,
                "structure_correctness": 0.0,
                "paper_safe": False,
                "unsupported_reasons": [f"official_wrapper_row_error:{type(exc).__name__}"],
            }
        metadata = task.get("metadata", {}) if isinstance(task.get("metadata"), dict) else {}
        category = str(metadata.get("official_dataset_category") or "unknown")
        for reason in score.get("unsupported_reasons", []):
            if not score.get("paper_safe", False):
                unsupported_by_category[category].add(str(reason))
        results.append(
            {
                "run_index": key[0],
                "task_id": row["task_id"],
                "system": row["system"],
                "success": float(score["success"]),
                "tool_selection_correctness": float(score["tool_selection_correctness"]),
                "argument_correctness": float(score["argument_correctness"]),
                "structure_correctness": float(score["structure_correctness"]),
                "paper_safe": bool(score["paper_safe"]),
                "unsupported_reasons": list(score.get("unsupported_reasons", [])),
            }
        )

    unsupported_strata = [
        {
            "stratum": category,
            "reason": ", ".join(sorted(reasons)),
            "paper_safe": False,
        }
        for category, reasons in sorted(unsupported_by_category.items())
        if reasons
    ]
    out_path.write_text(json.dumps({"results": results, "unsupported_strata": unsupported_strata}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
