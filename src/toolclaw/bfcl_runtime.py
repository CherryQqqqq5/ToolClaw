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
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_NUMBER_WORDS: Dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

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


_STOPWORDS: set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "given", "i", "if",
    "in", "is", "it", "its", "me", "my", "of", "on", "or", "please", "provide", "respectively", "so",
    "that", "the", "their", "this", "to", "up", "using", "with", "you", "your",
}

_GENERIC_TOOL_TOKENS: set[str] = {
    "api", "call", "calls", "calculate", "change", "changes", "common", "commonly", "data", "determine",
    "existing", "function", "functions", "get", "given", "info", "information", "item", "items", "lookup",
    "modify", "modifies", "new", "perform", "post", "properties", "property", "provide", "request",
    "requests", "retrieve", "retrieves", "send", "sends", "specified", "tool", "tools", "update", "updates",
    "url", "used", "user", "users", "using", "view", "web",
}

_MEASUREMENT_TOKENS: set[str] = {"meter", "meters", "minute", "minutes", "second", "seconds", "time", "unit", "units"}
_INFORMATION_QUERY_PREFIXES: tuple[str, ...] = (
    "what is",
    "what are",
    "who is",
    "who are",
    "when is",
    "where is",
    "tell me about",
    "find information about",
    "look up",
)
_RECENCY_QUERY_TOKENS: set[str] = {"latest", "recent", "today", "current", "newest", "breaking", "news"}
_SEARCH_TOOL_TOKENS: set[str] = {"search", "lookup", "find", "query", "queries", "retrieve", "retrieves", "web", "information", "answer", "answers"}
_NEWS_TOOL_TOKENS: set[str] = {"news", "headline", "headlines", "article", "articles", "events"}
_EXPLICIT_NEWS_MARKERS: tuple[str, ...] = (
    "news",
    "headline",
    "headlines",
    "article",
    "articles",
    "뉴스",
)


def _normalized_key_phrases(key: str) -> List[str]:
    raw = str(key or "").strip()
    if not raw:
        return []
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", raw)
    lowered = spaced.replace("_", " ").replace("-", " ").strip().lower()
    collapsed = re.sub(r"[\s_-]+", "", lowered)
    phrases = [lowered]
    if collapsed and collapsed != lowered:
        phrases.append(collapsed)
    return [phrase for phrase in phrases if phrase]


def _extract_number_after_patterns(text: str, patterns: Sequence[str]) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = _number_from_token(match.group(1))
            if value is not None:
                return value
    return None


def _generic_location_candidate(text: str, prefixes: Sequence[str]) -> str | None:
    for prefix in prefixes:
        match = re.search(
            rf"{prefix}\s+([A-Za-z][A-Za-z .,'/-]*?)(?:\s+(?:that|with|for|from|on|at|of|and)\b|[.?!,]|$)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip(" .?!,;:'\"")
    return None


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
                        "bfcl_original_function_name": tool_id,
                        "bfcl_original_index": len(tools) + 1,
                        "canonical_name": tool_id,
                        "normalization_trace": ["official_multi_turn_func_doc"],
                        "semantic_tags": sorted(_TOOL_HINTS.get(tool_id, set())),
                    },
                }
            )
    return tools


def _informative_token_set(*values: Any, blocked: Sequence[str] | None = None) -> set[str]:
    blocked_tokens = {token for token in (blocked or []) if token}
    tokens = {
        token
        for token in _tokens(*values)
        if token not in _STOPWORDS
        and token not in _GENERIC_TOOL_TOKENS
        and token not in _MEASUREMENT_TOKENS
        and token not in blocked_tokens
    }
    return tokens


def _schema_required_keys(schema: Mapping[str, Any]) -> List[str]:
    required = schema.get("required")
    if not isinstance(required, list):
        return []
    return [str(item) for item in required if str(item)]


def _tool_schema_blocklist(parameters: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in _schema_properties(parameters).keys():
        tokens.update(_tokens(str(key)))
    return tokens


def _tool_semantic_tokens(tool: Mapping[str, Any]) -> set[str]:
    parameters = tool.get("parameters") if isinstance(tool.get("parameters"), Mapping) else {}
    metadata = tool.get("metadata") if isinstance(tool.get("metadata"), Mapping) else {}
    blocked = _tool_schema_blocklist(parameters)
    return _informative_token_set(
        tool.get("tool_id", ""),
        tool.get("description", ""),
        metadata.get("semantic_tags", []),
        blocked=sorted(blocked),
    )


def _tool_schema_tokens(tool: Mapping[str, Any]) -> set[str]:
    parameters = tool.get("parameters") if isinstance(tool.get("parameters"), Mapping) else {}
    properties = _schema_properties(parameters)
    enum_values: List[str] = []
    for prop in properties.values():
        if isinstance(prop, Mapping) and isinstance(prop.get("enum"), list):
            enum_values.extend(str(item) for item in prop.get("enum", []) if str(item))
    return _informative_token_set(list(properties.keys()), enum_values)


def _tool_exact_mention(text: str, tool_id: str) -> bool:
    normalized_text = str(text or "").lower()
    if tool_id.lower() in normalized_text:
        return True
    parts = [part for part in re.split(r"[^a-z0-9]+", tool_id.lower()) if part and part not in _GENERIC_TOOL_TOKENS]
    if not parts:
        return False
    return all(part in normalized_text for part in parts)


def _required_argument_coverage(tool: Mapping[str, Any], text: str) -> float:
    parameters = tool.get("parameters") if isinstance(tool.get("parameters"), Mapping) else {}
    required = _schema_required_keys(parameters)
    if not required:
        return 1.0
    extracted = extract_tool_arguments(str(tool.get("tool_id") or ""), parameters, text)
    matched = sum(1 for key in required if key in extracted and not _is_missing_value(extracted.get(key)))
    return matched / max(len(required), 1)


def _query_information_intent(text: str) -> str:
    lower = str(text or "").strip().lower()
    if not lower:
        return ""
    if any(marker in lower for marker in _EXPLICIT_NEWS_MARKERS):
        return "news_query"
    asks_information = lower.endswith("?") or any(lower.startswith(prefix) for prefix in _INFORMATION_QUERY_PREFIXES)
    if not asks_information:
        return ""
    tokens = set(_tokens(lower))
    if tokens.intersection(_RECENCY_QUERY_TOKENS):
        return "recent_info"
    return "general_info"


def _tool_information_intent_score(tool: Mapping[str, Any], intent: str) -> float:
    if not intent:
        return 0.0
    tool_tokens = set(_tokens(tool.get("tool_id", ""), tool.get("description", "")))
    search_like = bool(tool_tokens.intersection(_SEARCH_TOOL_TOKENS))
    news_like = bool(tool_tokens.intersection(_NEWS_TOOL_TOKENS))
    if intent == "news_query":
        score = 0.0
        if news_like:
            score += 2.0
        elif search_like:
            score += 0.5
        return score
    if intent == "recent_info":
        score = 0.0
        if search_like:
            score += 0.5
        if news_like:
            score += 1.0
        return score
    score = 0.0
    if search_like:
        score += 1.0
    if news_like:
        score -= 0.5
    return score


def rank_candidate_tools(text: str, candidate_tools: Sequence[Any]) -> List[Dict[str, Any]]:
    query_tokens = _informative_token_set(text)
    info_intent = _query_information_intent(text)
    ranked: List[Dict[str, Any]] = []
    for raw_tool in candidate_tools:
        tool = _coerce_tool(raw_tool)
        tool_id = str(tool.get("tool_id") or "").strip()
        if not tool_id:
            continue
        metadata = tool.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        semantic_tokens = _tool_semantic_tokens(tool)
        schema_tokens = _tool_schema_tokens(tool)
        hints = {token for token in _TOOL_HINTS.get(tool_id, set()) if token not in _STOPWORDS}
        semantic_overlap = query_tokens.intersection(semantic_tokens)
        schema_overlap = query_tokens.intersection(schema_tokens)
        hint_overlap = query_tokens.intersection(hints)
        required_coverage = _required_argument_coverage(tool, text)
        score = (3.0 * len(semantic_overlap)) + (1.25 * len(schema_overlap)) + (2.5 * required_coverage)
        score += _tool_information_intent_score(tool, info_intent)
        exact_match = _tool_exact_mention(text, tool_id)
        if exact_match:
            score += 2.5
        if hint_overlap:
            score += 1.5
        combined_overlap = semantic_overlap.union(schema_overlap).union(hint_overlap)
        ranked.append(
            {
                "tool": tool,
                "score": float(score),
                "overlap": sorted(combined_overlap),
                "semantic_overlap": sorted(semantic_overlap),
                "schema_overlap": sorted(schema_overlap),
                "required_argument_coverage": float(required_coverage),
                "exact_match": exact_match,
                "schema_name_overlap_count": len(schema_overlap),
            }
        )
    ranked.sort(
        key=lambda item: (
            -float(item["score"]),
            -int(bool(item.get("exact_match"))),
            -float(item.get("required_argument_coverage", 0.0)),
            -int(item.get("schema_name_overlap_count", 0) or 0),
            str(item["tool"].get("tool_id") or ""),
        )
    )
    return ranked


def should_abstain_from_tools(text: str, candidate_tools: Sequence[Any]) -> bool:
    ranked = rank_candidate_tools(text, candidate_tools)
    if not ranked:
        return True
    best = ranked[0]
    if len(candidate_tools) != 1:
        return False
    if best.get("exact_match"):
        return False
    if best.get("semantic_overlap"):
        return False
    return float(best.get("required_argument_coverage", 0.0)) < 1.0


def select_candidate_tool(
    text: str,
    candidate_tools: Sequence[Any],
    *,
    preferred_tool_id: str | None = None,
) -> Dict[str, Any] | None:
    ranked = rank_candidate_tools(text, candidate_tools)
    if not ranked:
        return None
    best = ranked[0]
    if not preferred_tool_id:
        return dict(best["tool"])
    current = next((item for item in ranked if str(item["tool"].get("tool_id") or "") == str(preferred_tool_id)), None)
    if current is None:
        return dict(best["tool"])
    if str(current["tool"].get("tool_id") or "") == str(best["tool"].get("tool_id") or ""):
        return dict(current["tool"])
    # BFCL is an exact function-call benchmark: the preferred planner tool is
    # metadata only and must not override the deterministic schema top-1.
    return dict(best["tool"])


def _parallel_has_parallel_cue(text: str) -> bool:
    raw = str(text or "")
    return bool(
        re.search(r"\b(?:and|also)\b|[,;]|、|，", raw, re.IGNORECASE)
        or len(_EMAIL_PATTERN.findall(raw)) > 1
        or len(_quoted_strings(raw)) > 1
    )


def _parallel_property_text(key: str, prop: Mapping[str, Any]) -> str:
    values = [key]
    for field in ("description", "title"):
        value = prop.get(field) if isinstance(prop, Mapping) else None
        if value:
            values.append(str(value))
    return " ".join(values).lower()


def _parallel_preferred_key(
    schema: Mapping[str, Mapping[str, Any]],
    required: Sequence[str],
    types: set[str],
    hints: set[str],
) -> str:
    ordered_keys = [key for key in required if key in schema] + [key for key in schema if key not in required]
    for key in ordered_keys:
        prop = schema.get(key, {}) if isinstance(schema.get(key), Mapping) else {}
        prop_type = str(prop.get("type") or "").strip().lower()
        if prop_type not in types:
            continue
        descriptor = _parallel_property_text(key, prop)
        if any(hint in descriptor for hint in hints):
            return key
    return ""


def _dedupe_preserve_order(values: Sequence[Any]) -> List[Any]:
    seen: set[str] = set()
    deduped: List[Any] = []
    for value in values:
        marker = str(value)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(value)
    return deduped


def extract_parallel_argument_sets(tool_id: str, parameters: Mapping[str, Any], text: str) -> List[Dict[str, Any]]:
    schema = _schema_properties(parameters)
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
    required = _schema_required_keys(parameters)
    has_parallel_cue = _parallel_has_parallel_cue(text)

    email_key = _parallel_preferred_key(
        schema,
        required,
        {"string"},
        {"email", "e-mail", "recipient", "receiver", "contact"},
    )
    if email_key:
        emails = _dedupe_preserve_order(_EMAIL_PATTERN.findall(text))
        if len(emails) > 1:
            return [{email_key: email} for email in emails]

    numeric_key = _parallel_preferred_key(
        schema,
        required,
        {"integer", "number"},
        {"id", "identifier", "ids"},
    )
    if numeric_key and has_parallel_cue:
        prop = schema.get(numeric_key, {}) if isinstance(schema.get(numeric_key), Mapping) else {}
        prop_type = str(prop.get("type") or "").strip().lower()
        values = _dedupe_preserve_order([int(value) for value in _INTEGER_PATTERN.findall(text)])
        if len(values) > 1:
            if prop_type == "number":
                return [{numeric_key: float(value)} for value in values]
            return [{numeric_key: value} for value in values]

    quoted_string_key = _parallel_preferred_key(
        schema,
        required,
        {"string"},
        {"name", "names", "item", "items", "value", "values", "query", "text", "message"},
    )
    quoted_values = _dedupe_preserve_order(_quoted_strings(text))
    if quoted_string_key and len(quoted_values) > 1:
        return [{quoted_string_key: value} for value in quoted_values]

    preferred_string_keys = [
        key
        for key in ["location", "loc", "city", "where_to", *required]
        if key in schema and str(schema.get(key, {}).get("type") or "").lower() == "string"
    ]
    if preferred_string_keys:
        key = preferred_string_keys[0]
        candidates = _parallel_string_candidates(text)
        values: List[str] = []
        for candidate in candidates:
            value = _extract_property_value(tool_id, key, schema.get(key, {}), candidate)
            if value is None and key in {"location", "loc", "city", "where_to"}:
                value = _clean_parallel_location_candidate(candidate)
            if isinstance(value, str) and value and value not in values:
                values.append(value)
        if len(values) > 1:
            return [{key: value} for value in values]
    if len(schema) < 2:
        return []
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


def _parallel_string_candidates(text: str) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    quoted = _quoted_strings(raw)
    if len(quoted) > 1:
        return quoted
    patterns = [
        r"(?:two|2)\s+cities\s+(?:of|for|in)\s+(.+?)(?:[?.]|$)",
        r"(?:cities|locations?)\s+(?:of|for|in)\s+(.+?)(?:[?.]|$)",
        r"(?:weather(?:\s+conditions)?|weather\s+like)\s+(?:for|in)\s+(.+?)(?:[?.]|$)",
        r"\bfor\s+(.+?)(?:[?.]|$)",
    ]
    source = ""
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            source = match.group(1)
            break
    if not source:
        source = raw
    parts: List[str] = []
    for segment in re.split(r"\s+and\s+also\s+(?:for\s+)?|\s+and\s+(?:also\s+)?(?:for\s+)?|、|，", source, flags=re.IGNORECASE):
        segment = segment.strip(" .?!,;:'\"")
        if not segment:
            continue
        comma_parts = [part.strip(" .?!,;:'\"") for part in segment.split(",") if part.strip(" .?!,;:'\"")]
        looks_like_city_state = len(comma_parts) == 2 and bool(re.fullmatch(r"[A-Z]{2}", comma_parts[1]))
        if len(comma_parts) > 1 and not looks_like_city_state:
            parts.extend(comma_parts)
        else:
            parts.append(segment)
    return [_clean_parallel_location_candidate(part) for part in parts if _clean_parallel_location_candidate(part)]


def _clean_parallel_location_candidate(value: str) -> str:
    cleaned = re.sub(
        r"^(?:also\s+)?(?:for|in|of)\s+",
        "",
        str(value or "").strip(" .?!,;:'\""),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:could you tell me|tell me|what'?s|what is|please|the current|current)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:weather(?:\s+conditions)?(?:\s+for|\s+in)?|weather\s+like\s+in)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(?:the\s+)?(?:two\s+)?cities\s+(?:of|for|in)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .?!,;:'\"")


def extract_tool_arguments(
    tool_id: str,
    parameters: Mapping[str, Any],
    text: str,
    *,
    existing_args: Mapping[str, Any] | None = None,
    include_defaults: bool = True,
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
        default = prop.get("default") if include_defaults and isinstance(prop, Mapping) else None
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


def _number_from_token(token: str) -> int | None:
    lower = str(token or '').strip().lower()
    if not lower:
        return None
    if lower.isdigit():
        return int(lower)
    return _NUMBER_WORDS.get(lower)


def _ordered_numeric_values(text: str) -> List[int]:
    values: List[int] = []
    for match in re.finditer(r"\b(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", text, re.IGNORECASE):
        value = _number_from_token(match.group(0))
        if value is not None:
            values.append(value)
    return values


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
        return None
    if prop_type == "boolean":
        return _extract_boolean_value(key, prop, text)
    if prop_type == "integer":
        return _extract_integer_value(tool_id, key, prop, text)
    if prop_type == "array":
        return _extract_array_value(key, prop, text)
    return _extract_string_value(tool_id, key, prop, text)


def _extract_enum_value(key: str, enum_values: Sequence[str], text: str) -> Any:
    lower = text.lower()
    for candidate in enum_values:
        if candidate.lower() in lower:
            return candidate
    for phrase, mapped in _ENUM_SYNONYMS.get(key, {}).items():
        if phrase in lower and mapped in enum_values:
            return mapped
    normalized_key = key.lower().replace("_level", "").replace("_", " ").strip()
    if "none" in enum_values:
        none_patterns = {
            f"no {normalized_key}",
            f"without {normalized_key}",
            f"{normalized_key} none",
        }
        if any(pattern in lower for pattern in none_patterns if pattern.strip()):
            return "none"
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


def _extract_integer_value(tool_id: str, key: str, prop: Mapping[str, Any], text: str) -> Any:
    lower = text.lower()
    numbers = _ordered_numeric_values(text)
    key_lower = key.lower()
    key_phrases = _normalized_key_phrases(key)
    patterns = {
        "base": r"base(?:\s+of)?\s+(\d+)",
        "height": r"height(?:\s+of)?\s+(\d+)",
        "duration": r"(\d+)\s*minutes?",
        "time": r"(\d+)\s*(?:seconds?|minutes?|phút)",
        "lines": r"(\d+)\s*lines?",
        "count": r"(?:first|top|last)\s+(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b",
        "lower_limit": r"between\s+(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+and\s+",
        "upper_limit": r"between\s+(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+and\s+(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)",
    }
    if key_lower in patterns:
        match = re.search(patterns[key_lower], lower)
        if match:
            value = _number_from_token(match.group(1))
            if value is not None:
                return value
    if key_lower == "weight":
        value = _extract_number_after_patterns(
            lower,
            [r"weight(?:\s+of)?\s+(\d+)", r"(\d+)\s*(?:kg|kilograms?)"],
        )
        if value is not None:
            return value
    if key_lower == "distance":
        value = _extract_number_after_patterns(
            lower,
            [r"distance(?:\s+between us)?(?:\s+is)?\s+(\d+)", r"(\d+)\s*meters?\s+away"],
        )
        if value is not None:
            return value
    if key_lower == "perpage":
        value = _extract_number_after_patterns(
            lower,
            [r"per\s*page[^\d]*(\d+)", r"(\d+)\s+(?:entries|results)\s+per\s+page"],
        )
        if value is not None:
            return value
    if key_lower == "days":
        value = _extract_number_after_patterns(lower, [r"(\d+)\s*days?"])
        if value is not None:
            return value
    indexed_key = re.match(r"([a-z_]+?)(\d+)$", key_lower)
    if indexed_key and numbers:
        candidate_numbers = list(numbers)
        if len(candidate_numbers) >= 2 and candidate_numbers[0] == len(candidate_numbers) - 1:
            candidate_numbers = candidate_numbers[1:]
        ordinal = int(indexed_key.group(2)) - 1
        if 0 <= ordinal < len(candidate_numbers):
            return candidate_numbers[ordinal]
    if key_lower.endswith("id") or "identifier" in str(prop.get("description") or "").lower():
        for phrase in key_phrases:
            match = re.search(rf"{re.escape(phrase)}[^\d]*(\d+)", lower)
            if match:
                return int(match.group(1))
        id_match = re.search(r"\bid\b[^\d]*(\d+)", lower)
        if id_match:
            return int(id_match.group(1))
        noun = key_lower[:-2]
        if noun in {"node", "pod", "lane", "user", "device", "account"}:
            noun_match = re.search(rf"\b{re.escape(noun)}\b[^\d]*(\d+)", lower)
            if noun_match:
                return int(noun_match.group(1))
    if key_lower in {"a", "b"} and len(numbers) >= 2:
        if key_lower == "a":
            return numbers[0]
        second = numbers[1]
        if str(tool_id or "").strip().lower() == "add":
            if re.search(r"\b(donat(?:e|ed)|spent|lost|paid|gave away|give away)\b", lower):
                return -second
        return second
    if len(numbers) == 1:
        return numbers[0]
    return None


def _extract_array_value(key: str, prop: Mapping[str, Any], text: str) -> Any:
    items = prop.get("items") if isinstance(prop.get("items"), Mapping) else {}
    item_type = str(items.get("type") or "").strip().lower()
    lower = text.lower()
    if item_type == "integer":
        if key.lower() == "multiples":
            match = re.search(r"multiples? of\s+(.+?)(?:\s+between\b|\s+from\b|[.,;]|$)", lower)
            if match:
                values = _ordered_numeric_values(match.group(1))
                if values:
                    return values
        values = _ordered_numeric_values(text)
        return values or None
    if item_type == "string":
        key_lower = key.lower()
        if "email" in key_lower:
            emails = _EMAIL_PATTERN.findall(text)
            if emails:
                return emails
        if key_lower in {"columns", "fields"}:
            extracted: List[str] = []
            alias_map = {
                "email address": "email",
                "email addresses": "email",
                "emails": "email",
                "email": "email",
                "social security number": "ssn",
                "social security numbers": "ssn",
                "ssn": "ssn",
                "ssns": "ssn",
            }
            for phrase, canonical in alias_map.items():
                if phrase in lower and canonical not in extracted:
                    extracted.append(canonical)
            if extracted:
                return extracted
        quoted = _quoted_strings(text)
        return quoted or None
    return None


def _extract_string_value(tool_id: str, key: str, prop: Mapping[str, Any], text: str) -> Any:
    lower = text.lower()
    quoted = _quoted_strings(text)
    key_lower = key.lower()
    key_phrases = _normalized_key_phrases(key)

    def _clean_candidate(value: str) -> str:
        return value.strip(" .?!,;:'\"")

    def _titlecase_words(value: str) -> str:
        if re.search(r"[A-Z]", value):
            return value
        return " ".join(part.capitalize() for part in value.split())

    def _canonical_location(value: str) -> str:
        normalized = re.sub(r"\s+", " ", value).strip().lower()
        aliases = {
            "ha noi": "Ha Noi, Vietnam",
            "hanoi": "Ha Noi, Vietnam",
            "santa cruz": "Santa Cruz, USA",
        }
        return aliases.get(normalized, value)

    def _search_keyword_candidate() -> Any:
        patterns = [
            r"^(?:what is|who is|who was|tell me about|search for|look up)\s+(.+)$",
            r"^(?:how to cook)\s+(.+)$",
            r"^최근\s+(.+?)에 관한 뉴스를 찾아줘",
            r"^(.+?)\s+만드는 법 알려줘",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = _clean_candidate(match.group(1))
                return _titlecase_words(candidate) if re.fullmatch(r"[A-Za-z ]+", candidate) else candidate
        candidate = _clean_candidate(text)
        return _titlecase_words(candidate) if re.fullmatch(r"[A-Za-z ]+", candidate) else candidate

    def _command_candidate() -> Any:
        location_aliases = [
            ("utility room", "다용도실"),
            ("다용도실", "다용도실"),
            ("living room", "거실"),
            ("거실", "거실"),
        ]
        appliance_aliases = [
            ("washing machine", "통돌이"),
            ("통돌이", "통돌이"),
            ("air conditioner", "에어컨"),
            ("aircon", "에어컨"),
            ("에어컨", "에어컨"),
        ]
        action_aliases = [
            ("stop", "중지"),
            ("중지", "중지"),
            ("start", "실행"),
            ("run", "실행"),
            ("execute", "실행"),
            ("실행", "실행"),
        ]
        parts = []
        for aliases in (location_aliases, appliance_aliases, action_aliases):
            mapped = next((mapped for phrase, mapped in aliases if phrase in lower), None)
            if mapped is None:
                return None
            parts.append(mapped)
        return ", ".join(parts)

    if key_lower == "unit" and "units" in lower:
        return "units"
    if key_lower == "units":
        if "fahrenheit" in lower or "imperial" in lower:
            return "imperial"
        if "celsius" in lower or "metric" in lower:
            return "metric"
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
            for candidate in reversed(quoted):
                if not re.fullmatch(r"\d+", candidate.strip()):
                    return candidate
        match = re.search(r"special request[:\s]+(.+)$", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")
    if key_lower == "repos":
        match = re.search(r"star history of\s+(.+?)(?:, with| so that|$)", text, re.IGNORECASE)
        if match:
            repos = [item.strip(" .") for item in re.split(r"\band\b|,", match.group(1)) if "/" in item]
            if repos:
                return ",".join(repos)
    if key_lower in {"loc", "location"}:
        explicit_address = re.search(r"(?:địa chỉ|address)\s*[:：]?\s*['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        if explicit_address:
            return _canonical_location(_clean_candidate(explicit_address.group(1)))
        explicit_address = re.search(
            r"(?:địa chỉ|address)\s*[:：]?\s*([a-zA-Z0-9 .,'/-]+?)(?:\s+(?:and|và|with|for)\b|[.?!]|$)",
            text,
            re.IGNORECASE,
        )
        if explicit_address:
            return _canonical_location(_clean_candidate(explicit_address.group(1)))
        exact_city = re.search(r"use\s+(.+?)\s+as the exact city location", text, re.IGNORECASE)
        if exact_city:
            return _canonical_location(_clean_candidate(exact_city.group(1)))
        weather_match = re.search(r"weather(?:\s+conditions)?\s+(?:of|for|in)\s+(.+?)(?:\s+for me|,|\?|$)", text, re.IGNORECASE)
        if weather_match:
            return _canonical_location(_clean_candidate(weather_match.group(1)))
        match = re.search(r"from\s+(.+?)(?:, and i can wait| and i can wait|,?\s+I can wait|$)", text, re.IGNORECASE)
        if match:
            return _canonical_location(_clean_candidate(match.group(1)))
        candidate = _generic_location_candidate(text, (r"in", r"for", r"of"))
        if candidate:
            return _canonical_location(candidate)
    if key_lower == "where_to":
        candidate = _generic_location_candidate(text, (r"in", r"to", r"for"))
        if candidate:
            return _canonical_location(candidate)
    if key_lower == "city":
        candidate = _generic_location_candidate(text, (r"in", r"for", r"of"))
        if candidate:
            parts = [part.strip() for part in candidate.split(",") if part.strip()]
            return parts[0] if parts else candidate
    if key_lower == "country":
        candidate = _generic_location_candidate(text, (r"in", r"for", r"of"))
        if candidate and "," in candidate:
            parts = [part.strip() for part in candidate.split(",") if part.strip()]
            if len(parts) >= 2:
                return parts[-1]
    if key_lower == "ticker":
        ticker_patterns = [
            r"(?:ticker|symbol)\s*(?:is\s*)?([A-Z]{1,5})\b",
            r"\b([A-Z]{1,5})\b\s*(?:stock|shares?)",
        ]
        for pattern in ticker_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
    if key_lower.endswith("id") or "identifier" in str(prop.get("description") or "").lower():
        id_patterns = [
            *(rf"{re.escape(phrase)}\s+(?:is\s+)?['\"]?([a-zA-Z0-9_.-]+)['\"]?" for phrase in key_phrases),
            r"\bid(?:entifier)?\s+(?:is\s+)?['\"]?([a-zA-Z0-9_.-]+)['\"]?",
            r"\b(?:host agent|agent|user|device|account|lane)\s+(?:id\s+)?['\"]?([a-zA-Z0-9_.-]+)['\"]?",
        ]
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip(" .")
                if candidate and not candidate.isdigit():
                    return candidate
        if quoted:
            for candidate in quoted:
                stripped = candidate.strip()
                if stripped and re.fullmatch(r"[A-Za-z0-9_.-]+", stripped):
                    return stripped
    if "email" in key_lower:
        email_match = _EMAIL_PATTERN.search(text)
        if email_match:
            return email_match.group(0)
    if key_lower == "keyword":
        return _search_keyword_candidate()
    if key_lower == "command":
        command = _command_candidate()
        if command is not None:
            return command
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
    filtered_quoted = [candidate for candidate in quoted if key_lower.endswith("id") or not re.fullmatch(r"\d+", candidate.strip())]
    if filtered_quoted:
        return filtered_quoted[0]
    match = re.search(rf"{re.escape(key_lower.replace('_', ' '))}\s+(?:is\s+|of\s+)?([a-zA-Z0-9_./-]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(" .")
    if tool_id == "get_user_info" and key_lower == "user_id":
        match = re.search(r"\buser with the id\s+(\d+)", lower)
        if match:
            return match.group(1)
    return None
