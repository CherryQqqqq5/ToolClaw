"""Contract-shaped ToolSandbox runtime evidence for covered domain tools.

This backend is intentionally narrower than a native ToolSandbox adapter. It
uses only runtime-visible workflow inputs and tool-role observations, returns
schema-shaped payloads, and avoids gold/result-summary/milestone metadata.
"""

from __future__ import annotations

import ast
import re
import uuid
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

from toolclaw.schemas.workflow import Workflow
from toolclaw.tools.mock_tools import ToolExecutionError


CONTRACT_TOOL_IDS = {
    "search_messages",
    "search_contacts",
    "add_reminder",
    "modify_contact",
    "add_contact",
    "send_message_with_phone_number",
}

_GOLD_KEY_TOKENS = (
    "gold",
    "milestone",
    "reference",
    "result_summary",
    "scorer",
)


def run_toolsandbox_contract_tool(tool_id: str, args: Dict[str, Any], *, workflow: Optional[Workflow]) -> Dict[str, Any]:
    if tool_id not in CONTRACT_TOOL_IDS:
        raise ToolExecutionError(f"unsupported toolsandbox_contract tool: {tool_id}")

    state = _visible_contract_state(workflow)
    if tool_id == "search_messages":
        payload = _search_messages(args, state)
        return _success(payload, state_patch={"messages": payload})
    if tool_id == "search_contacts":
        payload = _search_contacts(args, state)
        return _success(payload, state_patch={"contacts": payload})
    if tool_id == "add_reminder":
        payload = _add_reminder(args, workflow)
        return _success(payload, state_patch={"last_reminder": payload, "reminders": [payload]})
    if tool_id == "modify_contact":
        payload = _modify_contact(args, state)
        return _success(payload, state_patch={"last_contact": payload, "contacts": [payload]})
    if tool_id == "add_contact":
        payload = _add_contact(args)
        return _success(payload, state_patch={"last_contact": payload, "contacts": [payload]})
    if tool_id == "send_message_with_phone_number":
        payload = _send_message(args)
        return _success(payload, state_patch={"last_message": payload, "messages": [payload]})
    raise ToolExecutionError(f"unsupported toolsandbox_contract tool: {tool_id}")


def _success(payload: Any, *, state_patch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "success",
        "payload": payload,
        "metadata": {
            "backend": "toolsandbox_contract",
            "placeholder_payload": False,
            "domain_state_evidence_present": True,
            "gold_free": True,
        },
    }
    if state_patch:
        result["state_patch"] = state_patch
    return result


def _visible_contract_state(workflow: Optional[Workflow]) -> Dict[str, List[Dict[str, Any]]]:
    state: Dict[str, List[Dict[str, Any]]] = {"messages": [], "contacts": [], "reminders": []}
    if workflow is None:
        return state
    metadata = _safe_metadata(workflow.metadata if isinstance(workflow.metadata, dict) else {})
    for message in metadata.get("messages", []) if isinstance(metadata.get("messages"), list) else []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("sender") or message.get("role") or "").lower()
        if role != "tool":
            continue
        parsed = _parse_literal_records(message.get("content"))
        for record in parsed:
            _ingest_record(record, state)
    return state


def _safe_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for key, value in metadata.items():
        key_l = str(key).lower()
        if any(token in key_l for token in _GOLD_KEY_TOKENS):
            continue
        safe[str(key)] = value
    return safe


def _parse_literal_records(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, dict):
        return [deepcopy(value)]
    if isinstance(value, list):
        return [deepcopy(item) for item in value if isinstance(item, dict)]
    text = str(value or "").strip()
    if not text or not (text.startswith("[") or text.startswith("{")):
        return []
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _ingest_record(record: Dict[str, Any], state: Dict[str, List[Dict[str, Any]]]) -> None:
    normalized = dict(record)
    if "message_id" in normalized or "creation_timestamp" in normalized:
        state["messages"].append(normalized)
        return
    if "person_id" in normalized or "phone_number" in normalized or "relationship" in normalized:
        state["contacts"].append(normalized)
        return
    if "reminder_id" in normalized or "reminder_timestamp" in normalized:
        state["reminders"].append(normalized)


def _search_messages(args: Dict[str, Any], state: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    records = list(state.get("messages", []))
    if not records:
        query = str(args.get("query") or args.get("content") or "").strip()
        if query:
            records = [
                {
                    "message_id": _stable_id("message", query),
                    "sender_person_id": None,
                    "sender_phone_number": args.get("sender_phone_number"),
                    "recipient_person_id": args.get("recipient_person_id"),
                    "recipient_phone_number": args.get("recipient_phone_number"),
                    "content": query,
                    "creation_timestamp": args.get("creation_timestamp"),
                }
            ]
    return _order_messages(_filter_records(records, args), args)


def _search_contacts(args: Dict[str, Any], state: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    records = list(state.get("contacts", []))
    if not records and (args.get("name") or args.get("phone_number") or args.get("person_id")):
        records = [_contact_from_args(args)]
    return _filter_records(records, args)


def _filter_records(records: Iterable[Dict[str, Any]], args: Dict[str, Any]) -> List[Dict[str, Any]]:
    filters = {
        key: str(args.get(key)).lower()
        for key in (
            "person_id",
            "message_id",
            "phone_number",
            "sender_phone_number",
            "recipient_phone_number",
            "sender_person_id",
            "recipient_person_id",
            "name",
        )
        if args.get(key) not in {None, ""}
    }
    query = str(args.get("query") or "").strip().lower()
    output: List[Dict[str, Any]] = []
    for record in records:
        if filters and any(str(record.get(key) or "").lower() != value for key, value in filters.items()):
            continue
        if query:
            haystack = " ".join(str(value).lower() for value in record.values())
            query_tokens = [token for token in re.findall(r"[a-z0-9+]+", query) if len(token) > 2]
            if query_tokens and not any(token in haystack for token in query_tokens):
                if not any(word in query for word in ("first", "oldest", "latest", "last", "recent", "text", "message")):
                    continue
        output.append(dict(record))
    return output


def _order_messages(records: List[Dict[str, Any]], args: Dict[str, Any]) -> List[Dict[str, Any]]:
    query = str(args.get("query") or "").lower()
    reverse = any(token in query for token in ("latest", "last", "recent", "newest"))
    if any(token in query for token in ("first", "oldest", "earliest")) or reverse:
        return sorted(records, key=lambda item: float(item.get("creation_timestamp") or 0), reverse=reverse)
    return records


def _add_reminder(args: Dict[str, Any], workflow: Optional[Workflow]) -> Dict[str, Any]:
    content = _first_text(args, "content", "message", "text", "title", "query")
    timestamp = args.get("reminder_timestamp") or args.get("timestamp") or args.get("time")
    if not content:
        raise ToolExecutionError("missing required reminder content")
    return {
        "reminder_id": _stable_id("reminder", content, timestamp),
        "content": content,
        "reminder_timestamp": timestamp,
        "source": "tool_args",
    }


def _modify_contact(args: Dict[str, Any], state: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    person_id = args.get("person_id")
    base = _find_contact(args, state) or ({"person_id": person_id} if person_id else None)
    if base is None:
        raise ToolExecutionError("missing contact identifier for modify_contact")
    updated = dict(base)
    for key in ("name", "phone_number", "relationship", "is_self"):
        if args.get(key) not in {None, ""}:
            updated[key] = args[key]
    updated.setdefault("person_id", person_id or _stable_id("person", updated.get("phone_number"), updated.get("name")))
    updated["state_patch"] = {"operation": "modify_contact", "person_id": updated["person_id"]}
    return updated


def _add_contact(args: Dict[str, Any]) -> Dict[str, Any]:
    if not (args.get("name") or args.get("phone_number")):
        raise ToolExecutionError("missing required contact name or phone_number")
    contact = _contact_from_args(args)
    contact["state_patch"] = {"operation": "add_contact", "person_id": contact["person_id"]}
    return contact


def _send_message(args: Dict[str, Any]) -> Dict[str, Any]:
    content = _first_text(args, "content", "message", "body", "text", "query")
    phone = args.get("phone_number") or args.get("recipient_phone_number") or args.get("recipient")
    if not content or not phone:
        raise ToolExecutionError("missing required phone_number or message content")
    return {
        "message_id": _stable_id("message", phone, content),
        "recipient_phone_number": phone,
        "content": content,
        "creation_timestamp": args.get("creation_timestamp") or args.get("timestamp"),
        "state_patch": {"operation": "send_message_with_phone_number", "recipient_phone_number": phone},
    }


def _contact_from_args(args: Dict[str, Any]) -> Dict[str, Any]:
    person_id = args.get("person_id") or _stable_id("person", args.get("phone_number"), args.get("name"))
    return {
        "person_id": person_id,
        "name": args.get("name"),
        "phone_number": args.get("phone_number"),
        "relationship": args.get("relationship"),
        "is_self": args.get("is_self"),
    }


def _find_contact(args: Dict[str, Any], state: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    candidates = _search_contacts(args, state)
    if candidates:
        return dict(candidates[0])
    person_id = args.get("person_id")
    if person_id:
        for message in state.get("messages", []):
            for key in ("sender_person_id", "recipient_person_id"):
                if message.get(key) == person_id:
                    return {"person_id": person_id}
    return None


def _first_text(args: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _stable_id(prefix: str, *values: Any) -> str:
    seed = "|".join(str(value) for value in values if value not in {None, ""}) or prefix
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"
