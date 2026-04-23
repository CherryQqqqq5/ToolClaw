#!/usr/bin/env python3
"""Extract aligned ToolSandbox source directly from an official ToolSandbox run directory."""

from __future__ import annotations

import argparse
import ast
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("data/external/ToolSandbox/data")
VENDORED_SCENARIO_ROOT = REPO_ROOT / "data/external/ToolSandbox/tool_sandbox/scenarios"
BUNDLED_SOURCE_CANDIDATES = (
    REPO_ROOT / "data/toolsandbox.formal.json",
    REPO_ROOT / "data/toolsandbox.formal.eval.json",
    REPO_ROOT / "data/toolsandbox.formal.train.json",
)
SCENARIO_EXPORT_CANDIDATES = (
    "scenario_export.json",
    "scenario.json",
    "metadata.json",
    "scenario_metadata.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare ToolClaw ToolSandbox source from an official ToolSandbox run directory")
    parser.add_argument(
        "--run-dir",
        default="latest",
        help="Official ToolSandbox run directory, or 'latest' to auto-discover the newest run under the data root",
    )
    parser.add_argument(
        "--data-root",
        default=str(DEFAULT_DATA_ROOT),
        help="Root directory containing official ToolSandbox run directories",
    )
    parser.add_argument(
        "--out",
        default="data/toolsandbox/toolsandbox.official.aligned.jsonl",
        help="Output JSONL path",
    )
    return parser.parse_args()


def resolve_run_dir(run_dir: str, data_root: Path) -> Path:
    if run_dir != "latest":
        path = Path(run_dir)
        if not path.exists():
            raise FileNotFoundError(f"official ToolSandbox run directory not found: {path}")
        return path
    if not data_root.exists():
        raise FileNotFoundError(f"official ToolSandbox data root not found: {data_root}")
    candidates = [path.parent for path in data_root.rglob("result_summary.json")]
    if not candidates:
        raise FileNotFoundError(f"no ToolSandbox result_summary.json found under: {data_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_result_summary(run_dir: Path) -> Dict[str, Any]:
    path = run_dir / "result_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"result_summary.json not found in official ToolSandbox run directory: {run_dir}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("per_scenario_results"), list):
        raise ValueError(f"unexpected official ToolSandbox result_summary format: {path}")
    return payload


def normalize_messages(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    messages: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            messages.append({"sender": "user", "recipient": "agent", "content": item})
            continue
        if not isinstance(item, dict):
            continue
        sender = item.get("sender") or item.get("role") or item.get("speaker") or item.get("visible_to") or "unknown"
        recipient = item.get("recipient") or item.get("to") or item.get("target") or "unknown"
        content = item.get("content") or item.get("text") or item.get("message") or item.get("utterance") or ""
        messages.append({
            "sender": str(sender),
            "recipient": str(recipient),
            "content": str(content),
        })
    return messages


def extract_query(messages: List[Dict[str, Any]], scenario_name: str) -> str:
    for message in messages:
        sender = str(message.get("sender", "")).lower()
        recipient = str(message.get("recipient", "")).lower()
        if sender in {"user", "roletype.user"} and recipient in {"agent", "roletype.agent", "unknown", ""}:
            content = message.get("content")
            if content:
                return str(content)
    for message in messages:
        if str(message.get("sender", "")).lower() in {"user", "roletype.user"} and message.get("content"):
            return str(message["content"])
    return scenario_name


def load_conversation(run_dir: Path, scenario_name: str) -> List[Dict[str, Any]]:
    path = run_dir / "trajectories" / scenario_name / "conversation.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        for key in ("messages", "conversation", "history"):
            if key in payload:
                return normalize_messages(payload[key])
    return normalize_messages(payload)


def load_scenario_export(run_dir: Path, scenario_name: str) -> Dict[str, Any]:
    scenario_dir = run_dir / "trajectories" / scenario_name
    for filename in SCENARIO_EXPORT_CANDIDATES:
        path = scenario_dir / filename
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
    return {}


def extract_tool_allow_list(scenario_export: Dict[str, Any]) -> List[str]:
    raw_tools = scenario_export.get("tool_allow_list") or scenario_export.get("allowed_tools") or []
    if not isinstance(raw_tools, list):
        return []
    tools: List[str] = []
    for item in raw_tools:
        if isinstance(item, str):
            tools.append(item)
        elif isinstance(item, dict):
            tool_id = item.get("tool_id") or item.get("name")
            if tool_id:
                tools.append(str(tool_id))
    return tools


def extract_candidate_tools(scenario_export: Dict[str, Any], tool_allow_list: List[str]) -> List[Any]:
    raw_tools = scenario_export.get("candidate_tools") or scenario_export.get("tools") or []
    if isinstance(raw_tools, list) and raw_tools:
        tools: List[Any] = []
        for item in raw_tools:
            if isinstance(item, str):
                tools.append(item)
            elif isinstance(item, dict):
                tools.append({
                    "tool_id": str(item.get("tool_id") or item.get("name") or "tool"),
                    "description": str(item.get("description") or item.get("tool_id") or item.get("name") or "tool"),
                })
        if tools:
            return tools
    return list(tool_allow_list)


def extract_milestones(scenario_export: Dict[str, Any], result_row: Dict[str, Any], ground_truth: Dict[str, Any]) -> List[Any]:
    milestones = scenario_export.get("milestones")
    if isinstance(milestones, list) and milestones:
        return milestones
    ground_truth_milestones = ground_truth.get("milestones")
    if isinstance(ground_truth_milestones, list) and ground_truth_milestones:
        return list(ground_truth_milestones)
    mapping = result_row.get("milestone_mapping")
    if isinstance(mapping, dict):
        return [f"milestone_{key}" for key in sorted(mapping.keys(), key=lambda x: int(str(x)) if str(x).isdigit() else str(x))]
    if isinstance(mapping, list):
        return [f"milestone_{idx}" for idx, _ in enumerate(mapping)]
    return []


def _normalize_category_value(raw_value: Any) -> str:
    return str(raw_value).strip().lower().replace("-", " ").replace("_", " ")


def normalized_categories(categories: Any) -> List[str]:
    if not isinstance(categories, list):
        return []
    values: List[str] = []
    for category in categories:
        normalized = " ".join(_normalize_category_value(category).split())
        if not normalized:
            continue
        snake = normalized.replace(" ", "_")
        if snake not in values:
            values.append(snake)
    return values


def infer_execution_scenario(scenario_export: Dict[str, Any], result_row: Dict[str, Any]) -> Tuple[str | None, str]:
    raw_value = scenario_export.get("execution_scenario")
    if raw_value is not None:
        normalized = str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")
        return (normalized or None, "scenario_export")
    raw_value = (
        result_row.get("execution_scenario")
        or result_row.get("scenario")
        or result_row.get("scenario_type")
    )
    if raw_value is not None:
        normalized = str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")
        return (normalized or None, "result_row")
    category_set = set(normalized_categories(result_row.get("categories")))
    if "insufficient_information" in category_set:
        return ("insufficient_information", "category_fallback")
    if "multiple_user_turn" in category_set:
        return ("multiple_user_turn", "category_fallback")
    if "state_dependency" in category_set:
        return ("state_dependency", "category_fallback")
    if "canonicalization" in category_set:
        return ("canonicalization", "category_fallback")
    if "single_user_turn" in category_set:
        return ("single_user_turn", "category_fallback")
    return (None, "missing")


def build_official_reference_summary(result_row: Dict[str, Any]) -> Dict[str, Any]:
    def _coerce_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        return None

    def _infer_success(summary: Dict[str, Any]) -> Optional[bool]:
        for key in ("success", "is_success", "completed", "solved"):
            parsed = _coerce_bool(summary.get(key))
            if parsed is not None:
                return parsed
        matched = summary.get("matched_milestones")
        total = summary.get("total_milestones")
        try:
            if total is not None and int(total) > 0:
                return int(matched or 0) >= int(total)
        except (TypeError, ValueError):
            pass
        mapping = summary.get("milestone_mapping")
        if isinstance(mapping, list) and mapping:
            return all(item is not None and item != -1 for item in mapping)
        if isinstance(mapping, dict) and mapping:
            return all(value is not None and value != -1 for value in mapping.values())
        for key in ("similarity", "milestone_similarity"):
            value = summary.get(key)
            try:
                if value is not None:
                    return float(value) >= 0.999
            except (TypeError, ValueError):
                continue
        return None

    summary = dict(result_row)
    summary["source"] = "official_toolsandbox_run"
    inferred_success = _infer_success(summary)
    if inferred_success is not None:
        summary["success"] = inferred_success
    return summary


def _ast_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_ast_value(item) for item in node.elts if not isinstance(item, ast.Starred)]
    if isinstance(node, ast.Tuple):
        return [_ast_value(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        payload: Dict[str, Any] = {}
        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                continue
            key = _ast_value(key_node)
            if key is None:
                continue
            payload[str(key)] = _ast_value(value_node)
        return payload
    rendered = _ast_render(node)
    return rendered if rendered is not None else ast.dump(node)


def _ast_render(node: ast.AST) -> str | None:
    unparse = getattr(ast, "unparse", None)
    if callable(unparse):
        return str(unparse(node))
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _ast_render(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Call):
        return _ast_render(node.func)
    if isinstance(node, ast.Subscript):
        return _ast_render(node.value)
    return None


def _ast_string_list(node: ast.AST | None) -> List[str]:
    if not isinstance(node, ast.List):
        return []
    values: List[str] = []
    for item in node.elts:
        if isinstance(item, ast.Starred):
            continue
        value = _ast_value(item)
        if isinstance(value, str) and value:
            values.append(value)
    return values


def _ast_message_list(node: ast.AST | None) -> List[Dict[str, Any]]:
    if not isinstance(node, ast.List):
        return []
    messages: List[Dict[str, Any]] = []
    for item in node.elts:
        if isinstance(item, ast.Starred):
            continue
        value = _ast_value(item)
        if isinstance(value, dict):
            messages.append(value)
    return normalize_messages(messages)


def _ast_milestones(node: ast.AST | None) -> List[Any]:
    if not isinstance(node, ast.List):
        return []
    milestones: List[Any] = []
    for item in node.elts:
        if isinstance(item, ast.Starred):
            continue
        rendered = _ast_render(item)
        milestones.append(rendered if rendered is not None else ast.dump(item))
    return milestones


@lru_cache(maxsize=1)
def load_vendored_ground_truth_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    if not VENDORED_SCENARIO_ROOT.exists():
        return index
    for path in sorted(VENDORED_SCENARIO_ROOT.glob("*_scenarios.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if func_name != "ScenarioExtension":
                continue
            kwargs = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
            name = _ast_value(kwargs.get("name")) if kwargs.get("name") is not None else None
            if not isinstance(name, str) or not name:
                continue
            tool_allow_list = _ast_string_list(kwargs.get("tool_allow_list"))
            index[name] = {
                "messages": _ast_message_list(kwargs.get("messages")),
                "tool_allow_list": tool_allow_list,
                "candidate_tools": list(tool_allow_list),
                "milestones": _ast_milestones(kwargs.get("milestones")),
                "ground_truth_source": "vendored_scenario_source",
                "ground_truth_source_path": str(path.resolve()),
            }
    return index


@lru_cache(maxsize=1)
def load_bundled_ground_truth_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for path in BUNDLED_SOURCE_CANDIDATES:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        for row in payload:
            if not isinstance(row, dict):
                continue
            sample_id = row.get("sample_id") or row.get("name")
            if not sample_id:
                continue
            entry = index.setdefault(
                str(sample_id),
                {
                    "messages": [],
                    "tool_allow_list": [],
                    "candidate_tools": [],
                    "milestones": [],
                    "ground_truth_source": "bundled_formal_source",
                    "ground_truth_source_path": str(path.resolve()),
                },
            )
            for field in ("messages", "tool_allow_list", "candidate_tools", "milestones"):
                value = row.get(field)
                if isinstance(value, list) and value and not entry[field]:
                    entry[field] = list(value)
    return index


def resolve_ground_truth(scenario_name: str) -> Dict[str, Any]:
    for index in (load_vendored_ground_truth_index(), load_bundled_ground_truth_index()):
        entry = index.get(scenario_name)
        if entry:
            return {
                "messages": list(entry.get("messages", [])),
                "tool_allow_list": list(entry.get("tool_allow_list", [])),
                "candidate_tools": list(entry.get("candidate_tools", [])),
                "milestones": list(entry.get("milestones", [])),
                "ground_truth_source": entry.get("ground_truth_source"),
                "ground_truth_source_path": entry.get("ground_truth_source_path"),
            }
    return {
        "messages": [],
        "tool_allow_list": [],
        "candidate_tools": [],
        "milestones": [],
        "ground_truth_source": None,
        "ground_truth_source_path": None,
    }


def iter_aligned_rows(run_dir: Path, result_summary: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    official_run_git_sha = result_summary.get("git_sha")
    for item in result_summary.get("per_scenario_results", []):
        if not isinstance(item, dict):
            continue
        scenario_name = str(item.get("name") or item.get("scenario_name") or "")
        if not scenario_name:
            continue
        conversation = load_conversation(run_dir, scenario_name)
        scenario_export = load_scenario_export(run_dir, scenario_name)
        ground_truth = resolve_ground_truth(scenario_name)
        messages = conversation or list(ground_truth["messages"])
        tool_allow_list = extract_tool_allow_list(scenario_export) or list(ground_truth["tool_allow_list"])
        candidate_tools = extract_candidate_tools(scenario_export, tool_allow_list)
        if not candidate_tools:
            candidate_tools = list(ground_truth["candidate_tools"]) or list(tool_allow_list)
        milestones = extract_milestones(scenario_export, item, ground_truth)
        execution_scenario, execution_scenario_source = infer_execution_scenario(scenario_export, item)
        row_categories = list(item.get("categories", []))
        official_summary = build_official_reference_summary(item)
        has_ground_truth_messages = bool(messages)
        has_ground_truth_milestones = bool(milestones)
        has_ground_truth_tools = bool(tool_allow_list) or bool(candidate_tools)
        row = {
            "sample_id": scenario_name,
            "query": extract_query(messages, scenario_name),
            "messages": messages,
            "tool_allow_list": tool_allow_list,
            "candidate_tools": candidate_tools,
            "categories": row_categories,
            "normalized_categories": normalized_categories(row_categories),
            "milestones": milestones,
            "ideal_turn_count": item.get("turn_count"),
            "ideal_tool_calls": scenario_export.get("ideal_tool_calls") or scenario_export.get("expected_tool_calls"),
            "result_summary": official_summary,
            "reference_result_summary": official_summary,
            "official_milestone_mapping": item.get("milestone_mapping"),
            "official_similarity": item.get("similarity"),
            "official_milestone_similarity": item.get("milestone_similarity"),
            "official_turn_count": item.get("turn_count"),
            "official_exception_type": item.get("exception_type") or item.get("error_type"),
            "official_traceback": item.get("traceback"),
            "has_ground_truth_messages": has_ground_truth_messages,
            "has_ground_truth_milestones": has_ground_truth_milestones,
            "has_ground_truth_tools": has_ground_truth_tools,
            "metadata": {
                "source": "official_toolsandbox_run",
                "official_run_git_sha": official_run_git_sha,
                "official_run_dir": str(run_dir.resolve()),
                "trajectory_dir": str((run_dir / 'trajectories' / scenario_name).resolve()),
                "result_summary_path": str((run_dir / 'result_summary.json').resolve()),
                "conversation_present": bool(conversation),
                "scenario_export_present": bool(scenario_export),
                "has_ground_truth_messages": has_ground_truth_messages,
                "has_ground_truth_milestones": has_ground_truth_milestones,
                "has_ground_truth_tools": has_ground_truth_tools,
                "ground_truth_backfill_source": ground_truth.get("ground_truth_source"),
                "ground_truth_backfill_path": ground_truth.get("ground_truth_source_path"),
                "execution_scenario_source": execution_scenario_source,
            },
        }
        if execution_scenario:
            row["execution_scenario"] = execution_scenario
        yield row


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root)
    run_dir = resolve_run_dir(args.run_dir, data_root)
    result_summary = load_result_summary(run_dir)
    rows = list(iter_aligned_rows(run_dir, result_summary))
    if not rows:
        raise RuntimeError(f"no per-scenario results found in official ToolSandbox run: {run_dir}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f"official ToolSandbox run: {run_dir}")
    print(f"wrote aligned toolsandbox source: {out_path}")
    print(f"total samples: {len(rows)}")


if __name__ == '__main__':
    main()
