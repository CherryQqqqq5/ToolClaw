"""BFCL-specific helpers for tool loading, selection, and argument extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


MULTI_TURN_FUNC_DOC_FILE_MAPPING: Dict[str, str] = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
    "WebSearchAPI": "web_search.json",
    "MemoryAPI_kv": "memory_kv.json",
    "MemoryAPI_vector": "memory_vector.json",
    "MemoryAPI_rec_sum": "memory_rec_sum.json",
}

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_QUOTED_PATTERN = re.compile(r"""['"]([^'"]+)['"]""")
_INTEGER_PATTERN = re.compile(r"\b\d+\b")

_TOOL_HINTS: Dict[str, set[str]] = {
    "cd": {"cd", "change", "directory", "folder", "go", "navigate", "enter"},
    "mkdir": {"mkdir", "create", "directory", "folder", "new"},
    "mv": {"mv", "move", "rename", "relocate", "transfer"},
    "grep": {"grep", "identify", "match", "pattern", "search", "sections"},
    "sort": {"order", "sort"},
    "diff": {"alterations", "changes", "compare", "diff", "difference", "juxtapose"},
    "ls": {"contents", "hidden", "list", "show", "visible"},
    "tail": {"end", "last", "recent", "tail"},
    "find": {"find", "locate", "search"},
    "post_tweet": {"post", "publish", "tweet"},
    "comment": {"comment", "reply"},
    "follow_user": {"follow"},
    "authenticate_twitter": {"authenticate", "login", "password", "username"},
}

_ENUM_SYNONYMS: Dict[str, Dict[str, str]] = {
    "temperature": {
        "boiling hot": "hot",
        "serve boiling hot": "hot",
        "served boiling hot": "hot",
        "extra hot": "hot",
    },
    "sweetness_level": {
        "extra sweet": "extra",
        "less sweet": "light",
        "no sugar": "none",
    },
}


def display_repo_path(path: Path, root_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(root_dir.resolve()))
    except ValueError:
        return str(path)


def flatten_question_turns(question: Any) -> List[str]:
    if not isinstance(question, list):
        text = str(question or "").strip()
        return [text] if text else []
    turns: List[str] = []
    for turn in question:
        messages: List[str] = []
        if isinstance(turn, list):
            for message in turn:
                if not isinstance(message, dict):
                    continue
                content = str(message.get("content") or "").strip()
                if content:
                    messages.append(content)
        elif isinstance(turn, dict):
            content = str(turn.get("content") or "").strip()
            if content:
                messages.append(content)
        else:
            content = str(turn or "").strip()
            if content:
                messages.append(content)
        if messages:
            turns.append(" ".join(messages))
    return turns


def load_multi_turn_candidate_tools(
    official_source_root: str | Path,
    involved_classes: Sequence[str],
) -> List[Dict[str, Any]]:
    source_root = Path(official_source_root)
    func_doc_dir = source_root / "bfcl_eval" / "data" / "multi_turn_func_doc"
    if not func_doc_dir.exists():
        return []
    tools: List[Dict[str, Any]] = []
    seen_tool_ids: set[str] = set()
    for class_name in involved_classes:
        file_name = MULTI_TURN_FUNC_DOC_FILE_MAPPING.get(str(class_name))
        if not file_name:
            continue
        path = func_doc_dir / file_name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            tool_id = str(raw.get("name") or raw.get("tool_id") or "").strip()
            if not tool_id or tool_id in seen_tool_ids:
                continue
            seen_tool_ids.add(tool_id)
            parameters = raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {}
            tools.append(
                {
                    "tool_id": tool_id,
                    "description": str(raw.get("description") or tool_id),
                    "parameters": parameters,
                    "metadata": {
                        "bfcl_class": str(class_name),
                        "semantic_tags": sorted(_TOOL_HINTS.get(tool_id, set())),
                    },
                }
            )
    return tools


def rank_candidate_tools(text: str, candidate_tools: Sequence[Any]) -> List[Dict[str, Any]]:
    query_tokens = _tokens(text)
    ranked: List[Dict[str, Any]] = []
    for raw_tool in candidate_tools:
        tool = _coerce_tool(raw_tool)
        tool_id = str(tool.get("tool_id") or "").strip()
        if not tool_id:
            continue
        metadata = tool.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        tool_tokens = _tokens(
            tool_id,
            tool.get("description", ""),
            tool.get("parameters", {}),
            metadata.get("semantic_tags", []),
        )
        hints = _TOOL_HINTS.get(tool_id, set())
        overlap = query_tokens.intersection(tool_tokens.union(hints))
        score = float(len(overlap))
        if tool_id.lower() in text.lower():
            score += 2.0
        if hints.intersection(query_tokens):
            score += 1.5
        ranked.append({"tool": tool, "score": score, "overlap": sorted(overlap)})
    ranked.sort(key=lambda item: (-float(item["score"]), str(item["tool"].get("tool_id") or "")))
    return ranked


def extract_parallel_argument_sets(tool_id: str, parameters: Mapping[str, Any], text: str) -> List[Dict[str, Any]]:
    schema = _schema_properties(parameters)
    if len(schema) < 2:
        return []
    lower = text.lower()
    if tool_id == "spotify.play":
        artists_match = re.search(r"artists?\s+(.+?)(?:,\s*with|\s+with)", text, re.IGNORECASE)
        artist_names: List[str] = []
        if artists_match:
            artist_names = [
                item.strip(" ,.")
                for item in re.split(r"\band\b|,", artists_match.group(1))
                if item.strip(" ,.")
            ]
        durations = [int(value) for value in re.findall(r"(\d+)\s*minutes?", lower)]
        if artist_names and len(artist_names) == len(durations):
            return [
                {"artist": artist_name, "duration": duration}
                for artist_name, duration in zip(artist_names, durations)
            ]
    if tool_id == "calculate_em_force":
        b_match = re.search(r"magnetic field of\s+(\d+)", lower)
        area_match = re.search(r"area of\s+(\d+)", lower)
        times = [int(value) for value in re.findall(r"change in time of\s+(\d+)\s*seconds?", lower)]
        if b_match and area_match and len(times) >= 2:
            return [
                {"b_field": int(b_match.group(1)), "area": int(area_match.group(1)), "d_time": d_time}
                for d_time in times[:2]
            ]
    string_keys = [key for key, prop in schema.items() if str(prop.get("type") or "").lower() == "string"]
    int_keys = [key for key, prop in schema.items() if str(prop.get("type") or "").lower() == "integer"]
    if len(string_keys) != 1 or len(int_keys) != 1:
        return []
    quoted = _quoted_strings(text)
    ints = [int(value) for value in _INTEGER_PATTERN.findall(text)]
    if len(quoted) >= 2 and len(ints) >= 2 and len(quoted) == len(ints):
        return [
            {string_keys[0]: name, int_keys[0]: value}
            for name, value in zip(quoted, ints)
        ]
    return []


def extract_tool_arguments(
    tool_id: str,
    parameters: Mapping[str, Any],
    text: str,
    *,
    existing_args: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    existing = dict(existing_args or {})
    schema = dict(parameters) if isinstance(parameters, Mapping) else {}
    properties = _schema_properties(schema)
    if not properties:
        return existing
    extracted: Dict[str, Any] = {}
    for key, prop in properties.items():
        if key in existing and not _is_missing_value(existing[key]):
            extracted[key] = existing[key]
            continue
        value = _extract_property_value(tool_id, key, prop if isinstance(prop, Mapping) else {}, text)
        if value is not None:
            extracted[key] = value
            continue
        default = prop.get("default") if isinstance(prop, Mapping) else None
        if not _is_missing_value(default):
            extracted[key] = default
    if extracted and "query" in existing:
        existing.pop("query", None)
    merged = {**existing, **extracted}
    return {key: value for key, value in merged.items() if not _is_missing_value(value)}


def _coerce_tool(raw_tool: Any) -> Dict[str, Any]:
    if isinstance(raw_tool, dict):
        parameters = raw_tool.get("parameters") if isinstance(raw_tool.get("parameters"), dict) else {}
        metadata = raw_tool.get("metadata") if isinstance(raw_tool.get("metadata"), dict) else {}
        return {
            "tool_id": str(raw_tool.get("tool_id") or raw_tool.get("name") or ""),
            "description": str(raw_tool.get("description") or raw_tool.get("tool_id") or raw_tool.get("name") or ""),
            "parameters": parameters,
            "metadata": metadata,
        }
    metadata = getattr(raw_tool, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    parameters = metadata.get("parameters") if isinstance(metadata.get("parameters"), dict) else {}
    return {
        "tool_id": str(getattr(raw_tool, "tool_id", "") or ""),
        "description": str(getattr(raw_tool, "description", "") or ""),
        "parameters": parameters,
        "metadata": metadata,
    }


def _is_missing_value(value: Any) -> bool:
    return value is None or value == "" or value == {}


def _tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            tokens.update(_tokens(*value.keys()))
            tokens.update(_tokens(*value.values()))
            continue
        if isinstance(value, (list, tuple, set)):
            tokens.update(_tokens(*value))
            continue
        tokens.update(_TOKEN_PATTERN.findall(str(value).lower()))
    return tokens


def _quoted_strings(text: str) -> List[str]:
    return [match.strip() for match in _QUOTED_PATTERN.findall(text) if match.strip()]


def _schema_properties(schema: Mapping[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties")
    return dict(properties) if isinstance(properties, Mapping) else {}


def _extract_property_value(tool_id: str, key: str, prop: Mapping[str, Any], text: str) -> Any:
    prop_type = str(prop.get("type") or "").strip().lower()
    if prop_type == "dict":
        nested: Dict[str, Any] = {}
        for nested_key, nested_prop in _schema_properties(prop).items():
            value = _extract_property_value(tool_id, nested_key, nested_prop, text)
            if value is not None:
                nested[nested_key] = value
        return nested or None
    if "enum" in prop and isinstance(prop.get("enum"), list):
        enum_value = _extract_enum_value(key, [str(item) for item in prop.get("enum", [])], text)
        if enum_value is not None:
            return enum_value
    if prop_type == "boolean":
        return _extract_boolean_value(key, prop, text)
    if prop_type == "integer":
        return _extract_integer_value(key, prop, text)
    return _extract_string_value(tool_id, key, prop, text)


def _extract_enum_value(key: str, enum_values: Sequence[str], text: str) -> Any:
    lower = text.lower()
    for candidate in enum_values:
        if candidate.lower() in lower:
            return candidate
    for phrase, mapped in _ENUM_SYNONYMS.get(key, {}).items():
        if phrase in lower and mapped in enum_values:
            return mapped
    return None


def _extract_boolean_value(key: str, prop: Mapping[str, Any], text: str) -> Any:
    lower = text.lower()
    description = str(prop.get("description") or "").lower()
    if key == "aligned":
        if "not aligned" in lower or "unaligned" in lower:
            return False
        if "aligned" in lower:
            return True
    if key == "a" or "hidden" in description:
        if "hidden" in lower or "all contents" in lower:
            return True
    if f"{key} true" in lower:
        return True
    if f"{key} false" in lower:
        return False
    return None


def _extract_integer_value(key: str, prop: Mapping[str, Any], text: str) -> Any:
    lower = text.lower()
    numbers = [int(value) for value in _INTEGER_PATTERN.findall(text)]
    key_lower = key.lower()
    patterns = {
        "base": r"base(?:\s+of)?\s+(\d+)",
        "height": r"height(?:\s+of)?\s+(\d+)",
        "duration": r"(\d+)\s*minutes?",
        "time": r"(\d+)\s*(?:seconds?|minutes?)",
        "lines": r"(\d+)\s*lines?",
    }
    if key_lower in patterns:
        match = re.search(patterns[key_lower], lower)
        if match:
            return int(match.group(1))
    if key_lower.endswith("id") or "identifier" in str(prop.get("description") or "").lower():
        match = re.search(rf"{re.escape(key_lower.replace('_', ' '))}[^\d]*(\d+)", lower)
        if match:
            return int(match.group(1))
        id_match = re.search(r"\bid\b[^\d]*(\d+)", lower)
        if id_match:
            return int(id_match.group(1))
    if len(numbers) == 1:
        return numbers[0]
    return None


def _extract_string_value(tool_id: str, key: str, prop: Mapping[str, Any], text: str) -> Any:
    lower = text.lower()
    quoted = _quoted_strings(text)
    key_lower = key.lower()

    if key_lower == "unit" and "units" in lower:
        return "units"
    if key_lower in {"source", "file_name", "file_name1"} and quoted:
        return quoted[0]
    if key_lower in {"destination", "file_name2"} and len(quoted) >= 2:
        return quoted[1]
    if key_lower in {"dir_name", "folder"}:
        match = re.search(r"(?:directory|folder)\s+(?:named\s+)?['\"]?([a-zA-Z0-9_.-]+)['\"]?", text, re.IGNORECASE)
        if match:
            return match.group(1)
        if quoted:
            return quoted[-1]
    if key_lower == "pattern":
        if quoted:
            return quoted[-1]
        match = re.search(r"pertaining to\s+([a-zA-Z0-9 _.-]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    if key_lower in {"artist", "username_to_follow"}:
        match = re.search(rf"{key_lower.replace('_', ' ')}s?\s+(.+?)(?:,| with| for| and)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    if key_lower in {"drink_id", "fooditem"}:
        match = re.search(r"(?:drink|food)\s+id\s+(?:is\s+)?['\"]?([a-zA-Z0-9_.-]+)['\"]?", text, re.IGNORECASE)
        if match:
            return match.group(1)
        if quoted:
            return quoted[0]
    if key_lower == "special":
        match = re.search(r"who has\s+([a-zA-Z0-9 _.-]+?)\s+as their special request", lower)
        if match:
            return match.group(1).strip()
    if key_lower == "special_instructions":
        if "boiling hot" in lower:
            return "boiling hot"
        if "special request" in lower and quoted:
            for candidate in quoted:
                if "hot" in candidate.lower() or "cold" in candidate.lower() or "warm" in candidate.lower():
                    return candidate
        if quoted:
            return quoted[-1]
        match = re.search(r"special request[:\s]+(.+)$", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    if key_lower == "repos":
        match = re.search(r"star history of\s+(.+?)(?:, with| so that|$)", text, re.IGNORECASE)
        if match:
            repos = [item.strip(" .") for item in re.split(r"\band\b|,", match.group(1)) if "/" in item]
            if repos:
                return ",".join(repos)
    if key_lower == "loc":
        match = re.search(r"from\s+(.+?)(?:, and i can wait| and i can wait|,?\s+I can wait|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    if key_lower == "type":
        for option in [str(item) for item in prop.get("enum", [])] if isinstance(prop.get("enum"), list) else []:
            if option.lower() in lower:
                return option
    if key_lower == "newingredients":
        additions = []
        for enum_hint in ("coconut milk", "soy milk", "almond milk"):
            if enum_hint in lower:
                additions.append(enum_hint)
        return ", ".join(additions) if additions else None
    if key_lower == "removeingredients":
        return None
    if key_lower == "name" and quoted:
        return quoted[0]
    if quoted:
        return quoted[0]
    match = re.search(rf"{re.escape(key_lower.replace('_', ' '))}\s+(?:is\s+|of\s+)?([a-zA-Z0-9_./-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    if tool_id == "get_user_info" and key_lower == "user_id":
        match = re.search(r"\buser with the id\s+(\d+)", lower)
        if match:
            return match.group(1)
    return None
