#!/usr/bin/env python3
"""Extract aligned ToolSandbox source directly from an official ToolSandbox run directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_DATA_ROOT = Path("data/external/ToolSandbox/data")
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


def extract_milestones(scenario_export: Dict[str, Any], result_row: Dict[str, Any]) -> List[Any]:
    milestones = scenario_export.get("milestones")
    if isinstance(milestones, list) and milestones:
        return milestones
    mapping = result_row.get("milestone_mapping")
    if isinstance(mapping, dict):
        return [f"milestone_{key}" for key in sorted(mapping.keys(), key=lambda x: int(str(x)) if str(x).isdigit() else str(x))]
    if isinstance(mapping, list):
        return [f"milestone_{idx}" for idx, _ in enumerate(mapping)]
    return []


def iter_aligned_rows(run_dir: Path, result_summary: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for item in result_summary.get("per_scenario_results", []):
        if not isinstance(item, dict):
            continue
        scenario_name = str(item.get("name") or item.get("scenario_name") or "")
        if not scenario_name:
            continue
        conversation = load_conversation(run_dir, scenario_name)
        scenario_export = load_scenario_export(run_dir, scenario_name)
        tool_allow_list = extract_tool_allow_list(scenario_export)
        yield {
            "sample_id": scenario_name,
            "query": extract_query(conversation, scenario_name),
            "messages": conversation,
            "tool_allow_list": tool_allow_list,
            "candidate_tools": extract_candidate_tools(scenario_export, tool_allow_list),
            "categories": list(item.get("categories", [])),
            "milestones": extract_milestones(scenario_export, item),
            "ideal_turn_count": item.get("turn_count"),
            "ideal_tool_calls": scenario_export.get("ideal_tool_calls") or scenario_export.get("expected_tool_calls"),
            "result_summary": item,
            "metadata": {
                "source": "official_toolsandbox_run",
                "official_run_dir": str(run_dir.resolve()),
                "trajectory_dir": str((run_dir / 'trajectories' / scenario_name).resolve()),
                "result_summary_path": str((run_dir / 'result_summary.json').resolve()),
                "scenario_export_present": bool(scenario_export),
            },
        }


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
