"""Tool execution routing for mock, semantic-mock, and future adapter-backed runtimes."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

from toolclaw.schemas.workflow import ToolSpec, Workflow
from toolclaw.tools.mock_tools import MOCK_TOOL_REGISTRY, ToolExecutionError, run_mock_tool

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_RETRIEVE_HINTS = {"retrieve", "search", "find", "lookup", "fetch", "query", "read", "get", "collect"}
_WRITE_HINTS = {"write", "writer", "save", "store", "persist", "report", "artifact", "draft", "create"}
_WRITE_VALIDATION_HINTS = {"write", "writer", "save", "store", "persist", "create"}
_MESSAGE_HINTS = {"message", "send", "reply", "email", "sms", "text", "notify"}
_STATE_HINTS = {"set", "toggle", "enable", "disable", "turn", "update", "status", "state"}
_ORDERING_HINTS = {"ordering", "legacy", "out_of_order", "order"}
_STRUCTURAL_PLANNER_HINTS = {
    "check",
    "checker",
    "inspect",
    "audit",
    "verify",
    "verifier",
    "validate",
    "assert",
    "test",
    "select",
    "selector",
    "branch",
    "route",
    "choose",
    "merge",
    "merger",
    "combine",
    "aggregate",
    "synthesize",
    "modify",
    "modifier",
    "patch",
    "execute",
    "executor",
}


def run_tool(tool_id: str, args: Dict[str, Any], *, workflow: Optional[Workflow] = None) -> Dict[str, Any]:
    spec = _resolve_tool_spec(workflow, tool_id)
    backend = _resolve_backend(tool_id, spec=spec, workflow=workflow)
    if backend == "mock":
        return run_mock_tool(tool_id, args)
    if backend == "semantic_mock":
        return _run_semantic_tool(tool_id, args, spec=spec)
    if backend == "bfcl_stub":
        return _run_bfcl_stub(tool_id, args, spec=spec)
    if backend == "hybrid":
        if tool_id in MOCK_TOOL_REGISTRY:
            return run_mock_tool(tool_id, args)
        return _run_semantic_tool(tool_id, args, spec=spec)
    raise ToolExecutionError(f"unsupported tool backend: {backend}")


def _resolve_tool_spec(workflow: Optional[Workflow], tool_id: str) -> Optional[ToolSpec]:
    if workflow is None:
        return None
    for tool in workflow.context.candidate_tools:
        if tool.tool_id == tool_id:
            return tool
    return None


def _resolve_backend(tool_id: str, *, spec: Optional[ToolSpec], workflow: Optional[Workflow]) -> str:
    spec_metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    workflow_metadata = workflow.metadata if workflow and isinstance(workflow.metadata, dict) else {}
    for candidate in (
        spec_metadata.get("execution_backend"),
        spec_metadata.get("tool_backend"),
        workflow_metadata.get("tool_execution_backend"),
    ):
        normalized = str(candidate or "").strip().lower()
        if normalized:
            return normalized
    if tool_id in MOCK_TOOL_REGISTRY:
        return "mock"
    return "semantic_mock"


def _tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            tokens.update(_tokens(*value))
            continue
        if isinstance(value, dict):
            tokens.update(_tokens(*value.keys()))
            tokens.update(_tokens(*value.values()))
            continue
        for token in _TOKEN_PATTERN.findall(str(value or "").lower()):
            tokens.add(token)
    return tokens


def _tool_tokens(tool_id: str, spec: Optional[ToolSpec]) -> set[str]:
    metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    return _tokens(
        tool_id,
        spec.description if spec else "",
        metadata.get("affordances", []),
        metadata.get("semantic_tags", []),
        metadata.get("preferred_capabilities", []),
        metadata.get("disallowed_capabilities", []),
        metadata.get("usage_notes"),
    )


def _primary_tool_kind(tool_id: str, spec: Optional[ToolSpec]) -> str:
    metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    explicit_kind = str(
        metadata.get("tool_kind")
        or metadata.get("operation_type")
        or metadata.get("primary_affordance")
        or ""
    ).strip().lower()
    if explicit_kind in {"retrieve", "search", "lookup", "write", "message", "state"}:
        return "retrieve" if explicit_kind in {"search", "lookup"} else explicit_kind

    id_tokens = _tokens(tool_id)
    metadata_tokens = _tokens(
        metadata.get("affordances", []),
        metadata.get("semantic_tags", []),
        metadata.get("preferred_capabilities", []),
        metadata.get("usage_notes"),
    )
    description_tokens = _tokens(spec.description if spec else "")

    def _score(hints: set[str]) -> int:
        return (
            3 * len(id_tokens.intersection(hints))
            + 2 * len(metadata_tokens.intersection(hints))
            + len(description_tokens.intersection(hints))
        )

    retrieve_score = _score(_RETRIEVE_HINTS)
    write_score = _score(_WRITE_VALIDATION_HINTS)
    message_score = _score(_MESSAGE_HINTS)
    state_score = _score(_STATE_HINTS)

    if message_score > 0 and message_score >= max(write_score, retrieve_score, state_score):
        return "message"
    if state_score > 0 and state_score >= max(write_score, retrieve_score):
        return "state"
    if retrieve_score > 0 and retrieve_score >= write_score:
        return "retrieve"
    if write_score > 0:
        return "write"
    return "unknown"


def _run_semantic_tool(tool_id: str, args: Dict[str, Any], *, spec: Optional[ToolSpec]) -> Dict[str, Any]:
    metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    tool_tokens = _tool_tokens(tool_id, spec)
    if args.get("force_environment_failure"):
        raise ToolExecutionError("environment unavailable for tool operation")
    if metadata.get("always_fail"):
        raise ToolExecutionError(str(metadata.get("failure_message") or f"tool execution failed: {tool_id}"))
    if _ORDERING_HINTS.intersection(tool_tokens) and not metadata.get("allow_ordering_execution", False):
        raise ToolExecutionError(str(metadata.get("failure_message") or "dependency order violated for tool operation"))

    _validate_semantic_args(tool_id, args, spec=spec, tool_tokens=tool_tokens)

    expected_target_path = args.get("expected_target_path")
    target_path = args.get("target_path")
    if expected_target_path and target_path and expected_target_path != target_path:
        raise ToolExecutionError(f"write target mismatch: expected target_path={expected_target_path}")

    payload_template = str(metadata.get("success_payload_template") or "").strip()
    if payload_template:
        payload = payload_template.format(tool_id=tool_id, **{key: value for key, value in args.items() if value is not None})
    else:
        payload = _default_payload(tool_id, args, tool_tokens=tool_tokens)

    result: Dict[str, Any] = {"status": "success", "payload": payload}
    state_patch = metadata.get("state_patch")
    if isinstance(state_patch, dict):
        result["state_patch"] = {
            str(key): (str(value).format(tool_id=tool_id, **args) if isinstance(value, str) else value)
            for key, value in state_patch.items()
        }
    return result


def _run_bfcl_stub(tool_id: str, args: Dict[str, Any], *, spec: Optional[ToolSpec]) -> Dict[str, Any]:
    metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    return {
        "status": "success",
        "payload": {
            "tool_id": tool_id,
            "arguments": dict(args),
            "schema": dict(metadata.get("parameters", {})) if isinstance(metadata.get("parameters"), dict) else {},
            "backend": "bfcl_stub",
        },
    }


def _validate_semantic_args(tool_id: str, args: Dict[str, Any], *, spec: Optional[ToolSpec], tool_tokens: set[str]) -> None:
    metadata = spec.metadata if spec and isinstance(spec.metadata, dict) else {}
    explicit_required = metadata.get("required_inputs")
    if isinstance(explicit_required, list):
        required_any = [str(item) for item in explicit_required if str(item)]
        missing = [key for key in required_any if args.get(key) is None or args.get(key) == ""]
        if missing:
            raise ToolExecutionError(f"missing required field(s): {', '.join(missing)}")
        return

    if _is_structural_planner_tool(spec):
        return

    primary_kind = _primary_tool_kind(tool_id, spec)
    if primary_kind == "message":
        if not _has_any_value(args, ("content", "message", "body", "text", "recipient", "phone_number", "email")):
            raise ToolExecutionError("missing required field: content")
        return
    if primary_kind == "state":
        if not _has_any_value(args, ("value", "enabled", "status", "state", "mode")):
            raise ToolExecutionError("missing required field: state")
        return
    if primary_kind == "write":
        if not _has_any_value(args, ("target_path", "content", "body", "text", "value")):
            raise ToolExecutionError(f"missing required field for write-like tool: {tool_id}")


def _is_structural_planner_tool(spec: Optional[ToolSpec]) -> bool:
    if spec is None:
        return False
    metadata = spec.metadata if isinstance(spec.metadata, dict) else {}
    metadata_tokens = _tokens(
        metadata.get("semantic_tags", []),
        metadata.get("preferred_capabilities", []),
        metadata.get("affordances", []),
    )
    capability_tokens = {
        "cap_check",
        "cap_modify",
        "cap_verify",
        "cap_select",
        "cap_merge",
    }
    return bool(metadata_tokens.intersection(_STRUCTURAL_PLANNER_HINTS) or metadata_tokens.intersection(capability_tokens))


def _has_any_value(args: Dict[str, Any], keys: Iterable[str]) -> bool:
    for key in keys:
        value = args.get(key)
        if value is not None and value != "":
            return True
    return False


def _default_payload(tool_id: str, args: Dict[str, Any], *, tool_tokens: set[str]) -> str:
    id_tokens = _tokens(tool_id)
    if "diff" in id_tokens and ("timestamp" in id_tokens or "time" in id_tokens):
        start_value = args.get("start_timestamp") or args.get("start_time") or args.get("start")
        end_value = args.get("end_timestamp") or args.get("end_time") or args.get("end")
        if start_value is not None and end_value is not None:
            return f"time difference between {start_value} and {end_value}"
    if "timestamp" in id_tokens and ("current" in id_tokens or "now" in id_tokens):
        return "current timestamp"
    if _RETRIEVE_HINTS.intersection(tool_tokens):
        query_like = args.get("query") or args.get("name") or args.get("phone_number") or args.get("person_id") or tool_id
        return f"summary for: {query_like}"
    if _WRITE_HINTS.intersection(tool_tokens):
        if _MESSAGE_HINTS.intersection(tool_tokens):
            recipient = args.get("recipient") or args.get("phone_number") or args.get("email") or "recipient"
            return f"sent message to {recipient}"
        if _STATE_HINTS.intersection(tool_tokens):
            state_value = args.get("enabled")
            if state_value is None:
                state_value = args.get("status", args.get("state", args.get("value", "updated")))
            return f"updated state to {state_value}"
        target_path = args.get("target_path")
        if target_path:
            return f"wrote artifact to {target_path}"
        return f"write success for {tool_id}"
    if _STATE_HINTS.intersection(tool_tokens):
        state_value = args.get("enabled")
        if state_value is None:
            state_value = args.get("status", args.get("state", args.get("value", "updated")))
        return f"updated state to {state_value}"
    return f"tool {tool_id} executed successfully"
