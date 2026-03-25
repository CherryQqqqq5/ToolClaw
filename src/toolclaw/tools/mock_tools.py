from __future__ import annotations

from typing import Any, Callable, Dict


class ToolExecutionError(RuntimeError):
    pass


def _search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query")
    if not query:
        raise ToolExecutionError("missing required field: query")
    return {
        "status": "success",
        "payload": f"summary for: {query}",
    }


def _write_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    target_path = args.get("target_path")
    if not target_path:
        raise ToolExecutionError("missing required field: target_path")
    if args.get("force_environment_failure"):
        raise ToolExecutionError("environment unavailable for write operation")
    return {
        "status": "success",
        "payload": f"wrote artifact to {target_path}",
    }


def _backup_write_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    target_path = args.get("target_path")
    if not target_path:
        raise ToolExecutionError("missing required field: target_path")
    return {
        "status": "success",
        "payload": f"backup write success at {target_path}",
    }


MOCK_TOOL_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "search_tool": _search_tool,
    "write_tool": _write_tool,
    "backup_write_tool": _backup_write_tool,
}


def run_mock_tool(tool_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if tool_id not in MOCK_TOOL_REGISTRY:
        raise ToolExecutionError(f"unknown tool_id: {tool_id}")
    return MOCK_TOOL_REGISTRY[tool_id](args)
