#!/usr/bin/env python3
"""Prepare protocol-defined BFCL subsets for ToolClaw benchmark runs."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, Iterator, List, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.bfcl_runtime import (
    display_repo_path,
    flatten_question_turns,
    load_multi_turn_candidate_tools,
)


CORE_GROUPS = {"non_live", "live", "multi_turn"}
AGENTIC_EXT_GROUPS = {"web_search", "memory", "format_sensitivity"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare BFCL source subsets for ToolClaw")
    parser.add_argument("--source", required=True, help="Raw BFCL JSON or JSONL source export")
    parser.add_argument("--outdir", default="data/bfcl", help="Output directory")
    parser.add_argument(
        "--official-evaluator-script",
        default=None,
        help="Optional wrapper script for the upstream BFCL evaluator",
    )
    parser.add_argument(
        "--multilingual-official-eval-supported",
        action="store_true",
        help="Include non-English fc_core rows only when the official evaluator path is validated",
    )
    return parser.parse_args()


def _normalize_group(raw: Dict[str, Any]) -> str:
    candidates = [
        raw.get("bfcl_group"),
        raw.get("group"),
        raw.get("benchmark_group"),
        raw.get("category"),
        raw.get("track"),
        raw.get("metadata", {}).get("bfcl_group") if isinstance(raw.get("metadata"), dict) else None,
    ]
    for candidate in candidates:
        value = str(candidate or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not value:
            continue
        if value in {"nonlive"}:
            return "non_live"
        if value in {"websearch"}:
            return "web_search"
        if value in {"formatsensitivity"}:
            return "format_sensitivity"
        return value
    return "unknown"


def _normalize_language(raw: Dict[str, Any]) -> str:
    candidates = [
        raw.get("bfcl_language"),
        raw.get("language"),
        raw.get("lang"),
        raw.get("metadata", {}).get("bfcl_language") if isinstance(raw.get("metadata"), dict) else None,
    ]
    for candidate in candidates:
        value = str(candidate or "").strip().lower()
        if value:
            return value
    return "en"


def _normalize_call_pattern(raw: Dict[str, Any]) -> str:
    candidates = [
        raw.get("bfcl_call_pattern"),
        raw.get("call_pattern"),
        raw.get("pattern"),
        raw.get("metadata", {}).get("bfcl_call_pattern") if isinstance(raw.get("metadata"), dict) else None,
    ]
    for candidate in candidates:
        value = str(candidate or "").strip().lower().replace("-", "_").replace(" ", "_")
        if value in {"parallel", "serial"}:
            return value
    structure = raw.get("expected_call_structure", {})
    if isinstance(structure, dict) and str(structure.get("pattern") or "").strip().lower() == "parallel":
        return "parallel"
    return "serial"


def _normalize_candidate_tools(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_tools = raw.get("candidate_tools") or raw.get("tools") or raw.get("function") or []
    if not isinstance(raw_tools, list):
        return []
    tools: List[Dict[str, Any]] = []
    for idx, raw_tool in enumerate(raw_tools, start=1):
        if isinstance(raw_tool, str):
            tools.append({"tool_id": raw_tool, "description": raw_tool, "parameters": {}})
            continue
        if isinstance(raw_tool, dict):
            parameters = raw_tool.get("parameters") or raw_tool.get("schema") or {}
            tools.append(
                {
                    "tool_id": str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                    "description": str(raw_tool.get("description") or raw_tool.get("tool_id") or raw_tool.get("name") or "tool"),
                    "parameters": parameters if isinstance(parameters, dict) else {},
                }
            )
    return tools


def _normalize_expected_call_structure(raw: Dict[str, Any], call_pattern: str) -> Dict[str, Any]:
    structure = raw.get("expected_call_structure")
    if isinstance(structure, dict):
        normalized = dict(structure)
        normalized.setdefault("pattern", call_pattern)
        return normalized
    if isinstance(structure, list):
        return {"pattern": call_pattern, "calls": [row for row in structure if isinstance(row, dict)]}
    calls = raw.get("expected_calls")
    if isinstance(calls, list):
        return {"pattern": call_pattern, "calls": [row for row in calls if isinstance(row, dict)]}
    return {"pattern": call_pattern, "calls": []}


def _normalize_row(
    raw: Dict[str, Any],
    *,
    official_evaluator_script: str | None,
    multilingual_supported: bool,
    source_path: Path,
    idx: int,
) -> Tuple[Dict[str, Any], str, List[str]]:
    raw_metadata = dict(raw.get("metadata", {})) if isinstance(raw.get("metadata"), dict) else {}
    group = _normalize_group(raw)
    language = _normalize_language(raw)
    call_pattern = _normalize_call_pattern(raw)
    tools = _normalize_candidate_tools(raw)
    expected_structure = _normalize_expected_call_structure(raw, call_pattern)
    sample_id = str(raw.get("sample_id") or raw.get("task_id") or raw.get("id") or f"bfcl_sample_{idx:05d}")
    route = "excluded"
    exclusion_reasons: List[str] = []

    if group in AGENTIC_EXT_GROUPS:
        route = "agentic_ext"
    elif group in CORE_GROUPS:
        if language != "en" and not multilingual_supported:
            exclusion_reasons.append("multilingual_requires_validated_official_evaluator")
        elif call_pattern not in {"serial", "parallel"}:
            exclusion_reasons.append("unsupported_call_pattern")
        else:
            route = "fc_core"
    else:
        exclusion_reasons.append("group_not_in_protocol_subset")

    normalized = {
        "sample_id": sample_id,
        "scenario": "bfcl",
        "query": str(raw.get("query") or raw.get("instruction") or raw.get("prompt") or raw.get("user_goal") or "complete the benchmark task"),
        "candidate_tools": tools,
        "milestones": list(raw.get("milestones", [])) if isinstance(raw.get("milestones"), list) else [],
        "constraints": dict(raw.get("constraints", {})) if isinstance(raw.get("constraints"), dict) else {},
        "ideal_tool_calls": len(expected_structure.get("calls", [])) if isinstance(expected_structure.get("calls"), list) else None,
        "expected_call_structure": expected_structure,
        "metadata": {
            "benchmark": "bfcl",
            "bfcl_group": group,
            "bfcl_call_pattern": call_pattern,
            "bfcl_language": language,
            "bfcl_track": route if route != "excluded" else "",
            "protocol_source": display_repo_path(source_path, ROOT_DIR),
            "official_evaluator_script": official_evaluator_script or "",
            "official_evaluator_supported": bool(official_evaluator_script) and (language == "en" or multilingual_supported),
            "protocol_exclusion_reasons": exclusion_reasons,
            **raw_metadata,
        },
    }
    return normalized, route, exclusion_reasons


def _load_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if path.is_dir():
        yield from _load_official_bfcl_directory(path)
        return

    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                yield raw
        return

    raw_text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        for line in raw_text.splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                yield raw
        return

    if isinstance(payload, list):
        for raw in payload:
            if isinstance(raw, dict):
                yield raw
        return
    if isinstance(payload, dict):
        if isinstance(payload.get("samples"), list):
            for raw in payload["samples"]:
                if isinstance(raw, dict):
                    yield raw
            return
        yield payload
        return
    raise ValueError(f"Unsupported BFCL source payload: {path}")


def _official_data_dir(path: Path) -> Path:
    if (path / "bfcl_eval" / "data").exists():
        return path / "bfcl_eval" / "data"
    if (path / "data").exists():
        return path / "data"
    raise ValueError(f"Unsupported BFCL official directory layout: {path}")


def _load_jsonlike_records(path: Path) -> List[Dict[str, Any]]:
    return [row for row in _load_rows(path) if isinstance(row, dict)]


def _official_group_for_category(category: str) -> str:
    if category.startswith("live_"):
        return "live"
    if category.startswith("multi_turn_"):
        return "multi_turn"
    if category == "web_search":
        return "web_search"
    if category == "memory":
        return "memory"
    if category == "format_sensitivity":
        return "format_sensitivity"
    return "non_live"


def _official_language_for_category(category: str) -> str:
    if category == "simple_java":
        return "java"
    if category == "simple_javascript":
        return "javascript"
    return "en"


def _official_call_pattern_for_category(category: str) -> str:
    return "parallel" if "parallel" in category else "serial"


def _stringify_question(question: Any) -> str:
    turns = flatten_question_turns(question)
    return "\n".join(turns) if turns else "complete the benchmark task"


def _value_from_ground_truth(values: Any) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return values


def _call_name_from_ast(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name_from_ast(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_from_ast(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal_from_ast(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return [_literal_from_ast(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            str(_literal_from_ast(key)): _literal_from_ast(value)
            for key, value in zip(node.keys, node.values)
        }
    return ast.unparse(node) if hasattr(ast, "unparse") else ""


def _parse_call_expression(expr: str) -> Dict[str, Any] | None:
    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call):
        return None
    tool_name = _call_name_from_ast(node.func)
    arguments: Dict[str, Any] = {}
    for idx, arg in enumerate(node.args, start=1):
        arguments[f"arg{idx}"] = _literal_from_ast(arg)
    for keyword in node.keywords:
        if keyword.arg:
            arguments[keyword.arg] = _literal_from_ast(keyword.value)
    return {"tool_name": tool_name, "arguments": arguments}


def _expected_structure_from_ground_truth(ground_truth: Any, call_pattern: str) -> Dict[str, Any]:
    if isinstance(ground_truth, list) and all(isinstance(item, dict) for item in ground_truth):
        calls: List[Dict[str, Any]] = []
        for item in ground_truth:
            if not item:
                continue
            tool_name, argument_map = next(iter(item.items()))
            arguments = {}
            if isinstance(argument_map, dict):
                arguments = {str(key): _value_from_ground_truth(value) for key, value in argument_map.items()}
            calls.append({"tool_name": str(tool_name), "arguments": arguments})
        return {"pattern": call_pattern, "calls": calls}
    if isinstance(ground_truth, list) and all(isinstance(item, list) for item in ground_truth):
        flattened: List[Dict[str, Any]] = []
        for turn in ground_truth:
            for expr in turn:
                if not isinstance(expr, str):
                    continue
                parsed = _parse_call_expression(expr)
                if parsed:
                    flattened.append(parsed)
        return {"pattern": "serial", "calls": flattened}
    return {"pattern": call_pattern, "calls": []}


def _remove_prefix(value: str, prefix: str) -> str:
    return value[len(prefix):] if value.startswith(prefix) else value


def _possible_answer_lookup(data_dir: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
    possible_answer_dir = data_dir / "possible_answer"
    if not possible_answer_dir.exists():
        return lookup
    for path in sorted(possible_answer_dir.glob("BFCL_v4_*.json")):
        category = _remove_prefix(path.stem, "BFCL_v4_")
        rows = _load_jsonlike_records(path)
        lookup[category] = {
            str(row.get("id") or ""): row
            for row in rows
            if str(row.get("id") or "")
        }
    return lookup


def _placeholder_tools_from_classes(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    classes = raw.get("involved_classes")
    if not isinstance(classes, list):
        return []
    return [
        {
            "tool_id": str(class_name),
            "description": f"Official BFCL placeholder tool for {class_name}",
            "parameters": {},
        }
        for class_name in classes
        if str(class_name or "").strip()
    ]


def _load_official_bfcl_directory(path: Path) -> Iterator[Dict[str, Any]]:
    data_dir = _official_data_dir(path)
    possible_answers = _possible_answer_lookup(data_dir)
    base_rows_by_id: Dict[str, Dict[str, Any]] = {}

    for dataset_path in sorted(data_dir.glob("BFCL_v4_*.json")):
        category = _remove_prefix(dataset_path.stem, "BFCL_v4_")
        if category == "format_sensitivity":
            continue
        for raw in _load_jsonlike_records(dataset_path):
            sample_id = str(raw.get("id") or "").strip()
            if not sample_id:
                continue
            call_pattern = _official_call_pattern_for_category(category)
            possible_answer = possible_answers.get(category, {}).get(sample_id, {})
            question_turns = flatten_question_turns(raw.get("question"))
            involved_classes = list(raw.get("involved_classes", [])) if isinstance(raw.get("involved_classes"), list) else []
            candidate_tools = _normalize_candidate_tools(raw)
            if not candidate_tools and category.startswith("multi_turn_"):
                candidate_tools = load_multi_turn_candidate_tools(path, involved_classes)
            if not candidate_tools:
                candidate_tools = _placeholder_tools_from_classes(raw)
            base_row = {
                "id": sample_id,
                "group": _official_group_for_category(category),
                "language": _official_language_for_category(category),
                "call_pattern": call_pattern,
                "query": "\n".join(question_turns) if question_turns else "complete the benchmark task",
                "milestones": list(question_turns),
                "candidate_tools": candidate_tools,
                "constraints": {},
                "expected_call_structure": _expected_structure_from_ground_truth(possible_answer.get("ground_truth"), call_pattern),
                "metadata": {
                    "official_dataset_category": category,
                    "official_dataset_file": dataset_path.name,
                    "official_source_root": display_repo_path(path, ROOT_DIR),
                    "official_possible_answer_present": bool(possible_answer),
                    "involved_classes": involved_classes,
                    "bfcl_turn_texts": list(question_turns),
                    "bfcl_candidate_tool_source": "official_multi_turn_func_doc" if category.startswith("multi_turn_") and candidate_tools else "raw_function_list",
                },
            }
            if "initial_config" in raw:
                base_row["metadata"]["initial_config"] = raw["initial_config"]
            if "path" in raw:
                base_row["metadata"]["path"] = raw["path"]
            if "excluded_function" in raw:
                base_row["metadata"]["excluded_function"] = raw["excluded_function"]
            if "scenario" in raw:
                base_row["metadata"]["official_scenario"] = raw["scenario"]

            base_rows_by_id[sample_id] = base_row
            yield base_row

    format_sensitivity_path = data_dir / "BFCL_v4_format_sensitivity.json"
    if not format_sensitivity_path.exists():
        return
    format_mapping = json.loads(format_sensitivity_path.read_text(encoding="utf-8"))
    if not isinstance(format_mapping, dict):
        return
    for source_category, sample_ids in sorted(format_mapping.items()):
        if not isinstance(sample_ids, list):
            continue
        for sample_id in sample_ids:
            base_row = base_rows_by_id.get(str(sample_id))
            if not base_row:
                continue
            cloned = json.loads(json.dumps(base_row))
            cloned["id"] = f"format_sensitivity::{sample_id}"
            cloned["group"] = "format_sensitivity"
            cloned["metadata"]["format_sensitivity_source_id"] = str(sample_id)
            cloned["metadata"]["format_sensitivity_source_category"] = str(source_category)
            cloned["metadata"]["official_dataset_category"] = "format_sensitivity"
            cloned["metadata"]["official_dataset_file"] = format_sensitivity_path.name
            yield cloned


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    if not source_path.exists():
        raise FileNotFoundError(f"BFCL source not found: {source_path}")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fc_core_rows: List[Dict[str, Any]] = []
    agentic_ext_rows: List[Dict[str, Any]] = []
    excluded_rows: List[Dict[str, Any]] = []

    official_script = args.official_evaluator_script
    if official_script:
        official_script = display_repo_path(Path(official_script), ROOT_DIR)

    for idx, raw in enumerate(_load_rows(source_path), start=1):
        normalized, route, exclusion_reasons = _normalize_row(
            raw,
            official_evaluator_script=official_script,
            multilingual_supported=bool(args.multilingual_official_eval_supported),
            source_path=source_path,
            idx=idx,
        )
        if route == "fc_core":
            fc_core_rows.append(normalized)
        elif route == "agentic_ext":
            agentic_ext_rows.append(normalized)
        else:
            excluded_rows.append(
                {
                    "sample_id": normalized["sample_id"],
                    "bfcl_group": normalized["metadata"]["bfcl_group"],
                    "bfcl_language": normalized["metadata"]["bfcl_language"],
                    "bfcl_call_pattern": normalized["metadata"]["bfcl_call_pattern"],
                    "reasons": exclusion_reasons,
                }
            )

    fc_core_path = outdir / "bfcl_v4.fc_core.aligned.jsonl"
    agentic_ext_path = outdir / "bfcl_v4.agentic_ext.aligned.jsonl"
    with fc_core_path.open("w", encoding="utf-8") as handle:
        for row in fc_core_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with agentic_ext_path.open("w", encoding="utf-8") as handle:
        for row in agentic_ext_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "benchmark": "bfcl_v4",
        "source": display_repo_path(source_path, ROOT_DIR),
        "outputs": {
            "fc_core": display_repo_path(fc_core_path, ROOT_DIR),
            "agentic_ext": display_repo_path(agentic_ext_path, ROOT_DIR),
        },
        "protocol_subset": {
            "fc_core": {
                "included_groups": sorted(CORE_GROUPS),
                "excluded_groups": sorted(AGENTIC_EXT_GROUPS),
                "language_rule": "english_only_unless_validated_multilingual_official_evaluator",
                "call_pattern_rule": "serial_and_parallel_only",
                "official_evaluator_coverage": {
                    "serial": True,
                    "parallel": True,
                    "multilingual": bool(args.multilingual_official_eval_supported),
                },
            },
            "agentic_ext": {
                "included_groups": sorted(AGENTIC_EXT_GROUPS),
                "excluded_groups": sorted(CORE_GROUPS),
            },
        },
        "official_evaluator_script": official_script or "",
        "counts": {
            "fc_core": len(fc_core_rows),
            "agentic_ext": len(agentic_ext_rows),
            "excluded": len(excluded_rows),
        },
        "excluded_rows": excluded_rows,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"wrote: {fc_core_path}")
    print(f"wrote: {agentic_ext_path}")
    print(f"wrote: {outdir / 'manifest.json'}")


if __name__ == "__main__":
    main()
