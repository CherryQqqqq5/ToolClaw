#!/usr/bin/env python3
"""Normalize raw ToolSandbox-style scenario/result exports into ToolClaw-compatible JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare ToolClaw ToolSandbox source JSONL from raw ToolSandbox-style JSON / JSONL exports."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to a JSON/JSONL file or a directory containing raw ToolSandbox-style exports.",
    )
    parser.add_argument(
        "--result-source",
        default=None,
        help="Optional JSON/JSONL file or directory with result summaries to merge by sample id.",
    )
    parser.add_argument(
        "--out",
        default="data/toolsandbox/toolsandbox.aligned.jsonl",
        help="Output JSONL path for scripts/run_toolsandbox_bench.py --source",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of aligned samples written.")
    return parser.parse_args()


def _iter_records(source: Path) -> Iterable[Dict[str, Any]]:
    if source.is_dir():
        for child in sorted(source.rglob("*")):
            if child.suffix.lower() not in {".json", ".jsonl"}:
                continue
            yield from _iter_records(child)
        return

    if source.suffix.lower() == ".jsonl":
        for line in source.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payload = json.loads(line)
                if isinstance(payload, dict):
                    yield payload
        return

    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        if isinstance(payload.get("samples"), list):
            for item in payload["samples"]:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(payload.get("scenarios"), list):
            for item in payload["scenarios"]:
                if isinstance(item, dict):
                    yield item
            return
        yield payload


def _coerce_messages(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_messages = (
        raw.get("messages")
        or raw.get("conversation")
        or raw.get("dialog")
        or raw.get("dialogue")
        or raw.get("history")
        or []
    )
    messages: List[Dict[str, Any]] = []
    if not isinstance(raw_messages, list):
        return messages
    for item in raw_messages:
        if isinstance(item, str):
            messages.append({"sender": "user", "recipient": "agent", "content": item})
            continue
        if isinstance(item, dict):
            sender = item.get("sender") or item.get("role") or item.get("speaker") or "user"
            recipient = item.get("recipient") or item.get("to") or ("agent" if str(sender).lower() == "user" else "user")
            content = item.get("content") or item.get("text") or item.get("message") or item.get("utterance") or ""
            messages.append(
                {
                    "sender": str(sender),
                    "recipient": str(recipient),
                    "content": str(content),
                }
            )
    return messages


def _extract_query(raw: Dict[str, Any], messages: Sequence[Dict[str, Any]]) -> str:
    for key in ("query", "user_goal", "instruction", "prompt"):
        value = raw.get(key)
        if value:
            return str(value)
    for message in messages:
        if str(message.get("sender", "")).lower() == "user":
            content = message.get("content")
            if content:
                return str(content)
    return "complete ToolSandbox scenario"


def _extract_categories(raw: Dict[str, Any]) -> List[str]:
    raw_categories = raw.get("categories") or raw.get("category") or raw.get("tags") or []
    categories: List[str] = []
    if isinstance(raw_categories, str):
        categories = [raw_categories]
    elif isinstance(raw_categories, list):
        categories = [str(item) for item in raw_categories if item]
    elif isinstance(raw_categories, dict):
        categories = [str(key) for key, enabled in raw_categories.items() if enabled]
    return categories


def _extract_tool_allow_list(raw: Dict[str, Any]) -> List[str]:
    raw_tools = (
        raw.get("tool_allow_list")
        or raw.get("allowed_tools")
        or raw.get("available_tools")
        or raw.get("tool_names")
        or []
    )
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


def _extract_candidate_tools(raw: Dict[str, Any], tool_allow_list: Sequence[str]) -> List[Any]:
    raw_tools = raw.get("candidate_tools") or raw.get("tools") or raw.get("available_tool_specs")
    if isinstance(raw_tools, list) and raw_tools:
        candidate_tools: List[Any] = []
        for item in raw_tools:
            if isinstance(item, str):
                candidate_tools.append(item)
            elif isinstance(item, dict):
                candidate_tools.append(
                    {
                        "tool_id": str(item.get("tool_id") or item.get("name") or "tool"),
                        "description": str(item.get("description") or item.get("tool_id") or item.get("name") or "tool"),
                    }
                )
        if candidate_tools:
            return candidate_tools
    return list(tool_allow_list)


def _extract_milestones(raw: Dict[str, Any]) -> List[Any]:
    raw_milestones = raw.get("milestones") or raw.get("expected_milestones") or raw.get("checkpoints") or []
    if isinstance(raw_milestones, list):
        return raw_milestones
    return []


def _extract_result_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("result_summary", "toolsandbox_result", "evaluation", "eval_result"):
        value = raw.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _sample_id(raw: Dict[str, Any], index: int) -> str:
    return str(
        raw.get("sample_id")
        or raw.get("name")
        or raw.get("scenario_id")
        or raw.get("task_id")
        or raw.get("id")
        or f"toolsandbox_{index:05d}"
    )


def _normalize_row(raw: Dict[str, Any], index: int, source_path: Path) -> Dict[str, Any]:
    messages = _coerce_messages(raw)
    tool_allow_list = _extract_tool_allow_list(raw)
    return {
        "sample_id": _sample_id(raw, index),
        "query": _extract_query(raw, messages),
        "messages": messages,
        "tool_allow_list": tool_allow_list,
        "candidate_tools": _extract_candidate_tools(raw, tool_allow_list),
        "categories": _extract_categories(raw),
        "milestones": _extract_milestones(raw),
        "ideal_turn_count": raw.get("ideal_turn_count") or raw.get("expected_turn_count") or raw.get("turn_count"),
        "ideal_tool_calls": raw.get("ideal_tool_calls") or raw.get("expected_tool_calls"),
        "result_summary": _extract_result_summary(raw),
        "metadata": {
            "source_path": str(source_path),
            "source_name": source_path.name,
        },
    }


def _result_index(source: Path | None) -> Dict[str, Dict[str, Any]]:
    if source is None:
        return {}
    result_map: Dict[str, Dict[str, Any]] = {}
    for record in _iter_records(source):
        sample_id = _sample_id(record, len(result_map) + 1)
        summary = _extract_result_summary(record)
        if summary:
            result_map[sample_id] = summary
    return result_map


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    if not source_path.exists():
        raise FileNotFoundError(f"ToolSandbox source not found: {source_path}")
    result_source = Path(args.result_source) if args.result_source else None
    if result_source is not None and not result_source.exists():
        raise FileNotFoundError(f"ToolSandbox result source not found: {result_source}")

    result_map = _result_index(result_source)
    rows: List[Dict[str, Any]] = []
    for idx, raw in enumerate(_iter_records(source_path), start=1):
        row = _normalize_row(raw, idx, source_path)
        if not row["result_summary"] and row["sample_id"] in result_map:
            row["result_summary"] = result_map[row["sample_id"]]
        rows.append(row)
        if args.limit is not None and len(rows) >= args.limit:
            break

    if not rows:
        raise RuntimeError(f"No ToolSandbox-style records found in {source_path}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote aligned toolsandbox source: {out_path}")
    print(f"total samples: {len(rows)}")


if __name__ == "__main__":
    main()
