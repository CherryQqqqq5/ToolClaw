"""Shared lexical-semantic intent profiles for coarse capability inference."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class CapabilityIntentProfile:
    capability_id: str
    description: str
    goal_terms: tuple[str, ...]
    tool_terms: tuple[str, ...]
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

CAPABILITY_INTENT_PROFILES: tuple[CapabilityIntentProfile, ...] = (
    CapabilityIntentProfile(
        capability_id="cap_check",
        description="Check or inspect current state before changing it",
        goal_terms=(
            "audit",
            "check",
            "inspect",
            "scan",
            "status",
        ),
        tool_terms=(
            "audit",
            "check",
            "checker",
            "inspect",
            "inspector",
            "scan",
            "state",
            "status",
        ),
        postconditions=("state_checked",),
    ),
    CapabilityIntentProfile(
        capability_id="cap_retrieve",
        description="Retrieve relevant information",
        goal_terms=(
            "collect",
            "discover",
            "evidence",
            "fetch",
            "find",
            "get",
            "list",
            "load",
            "locate",
            "lookup",
            "notes",
            "query",
            "read",
            "retrieve",
            "search",
            "show",
            "source",
            "view",
        ),
        tool_terms=(
            "details",
            "evidence",
            "fetch",
            "find",
            "get",
            "list",
            "lookup",
            "query",
            "read",
            "retrieve",
            "search",
            "source",
        ),
        postconditions=("information_obtained", "context_retrieved", "sources_retrieved"),
    ),
    CapabilityIntentProfile(
        capability_id="cap_select",
        description="Select a branch or route based on retrieved context",
        goal_terms=(
            "branch",
            "choose",
            "classify",
            "route",
            "select",
        ),
        tool_terms=(
            "branch",
            "chooser",
            "classifier",
            "route",
            "router",
            "select",
            "selector",
        ),
        preconditions=("context_retrieved",),
        postconditions=("branch_selected", "selected_branch_ready"),
    ),
    CapabilityIntentProfile(
        capability_id="cap_modify",
        description="Modify, patch, update, or execute the selected change",
        goal_terms=(
            "change",
            "execute",
            "modify",
            "patch",
            "toggle",
            "update",
        ),
        tool_terms=(
            "change",
            "execute",
            "executor",
            "modify",
            "modifier",
            "patch",
            "state",
            "toggle",
            "update",
        ),
        postconditions=("state_modified", "branch_executed"),
    ),
    CapabilityIntentProfile(
        capability_id="cap_verify",
        description="Verify or validate that the final state is correct",
        goal_terms=(
            "assert",
            "confirm",
            "test",
            "validate",
            "verify",
        ),
        tool_terms=(
            "assert",
            "confirm",
            "test",
            "validate",
            "verifier",
            "verify",
        ),
        postconditions=("verification_passed",),
    ),
    CapabilityIntentProfile(
        capability_id="cap_merge",
        description="Merge multiple retrieved sources into one intermediate state",
        goal_terms=(
            "aggregate",
            "combine",
            "merge",
            "synthesize",
        ),
        tool_terms=(
            "aggregate",
            "combine",
            "join",
            "merge",
            "merger",
            "synthesize",
        ),
        preconditions=("sources_retrieved",),
        postconditions=("merged_state_ready",),
    ),
    CapabilityIntentProfile(
        capability_id="cap_summarize",
        description="Summarize retrieved information",
        goal_terms=(
            "analyze",
            "analysis",
            "brief",
            "compare",
            "condense",
            "digest",
            "explain",
            "review",
            "summarize",
            "summary",
        ),
        tool_terms=(
            "analyze",
            "brief",
            "compare",
            "digest",
            "explain",
            "summarize",
            "summary",
        ),
        preconditions=("information_obtained",),
        postconditions=("summary_ready",),
    ),
    CapabilityIntentProfile(
        capability_id="cap_write",
        description="Write or commit the final artifact",
        goal_terms=(
            "answer",
            "approve",
            "apply",
            "book",
            "cancel",
            "compose",
            "configure",
            "create",
            "disable",
            "draft",
            "email",
            "enable",
            "output",
            "post",
            "publish",
            "record",
            "reply",
            "report",
            "save",
            "send",
            "set",
            "submit",
            "turn",
            "write",
        ),
        tool_terms=(
            "apply",
            "book",
            "cancel",
            "compose",
            "create",
            "disable",
            "enable",
            "post",
            "publish",
            "reply",
            "report",
            "save",
            "send",
            "set",
            "writer",
            "write",
        ),
        postconditions=("artifact_ready",),
    ),
)

CAPABILITY_PROFILES_BY_ID = {
    profile.capability_id: profile for profile in CAPABILITY_INTENT_PROFILES
}


def tokenize_values(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            tokens.update(tokenize_values(*value.keys()))
            tokens.update(tokenize_values(*value.values()))
            continue
        if isinstance(value, (list, tuple, set, frozenset)):
            tokens.update(tokenize_values(*value))
            continue
        for token in _TOKEN_PATTERN.findall(str(value).lower()):
            if token:
                tokens.add(token)
    return tokens


def tool_semantic_tokens(candidate_tools: Sequence[Any], *, allowed_tool_ids: Optional[Sequence[str]] = None) -> set[str]:
    allowed = {str(item) for item in allowed_tool_ids or [] if str(item)}
    tokens: set[str] = set()
    for tool in candidate_tools:
        tool_id = str(getattr(tool, "tool_id", "") or "")
        if allowed and tool_id not in allowed:
            continue
        metadata = getattr(tool, "metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        tokens.update(
            tokenize_values(
                tool_id,
                getattr(tool, "description", ""),
                metadata.get("affordances", []),
                metadata.get("semantic_tags", []),
                metadata.get("preferred_capabilities", []),
                metadata.get("strengths", []),
                metadata.get("usage_notes"),
            )
        )
    return tokens


def rank_capability_profiles(
    *,
    goal_text: str,
    tool_tokens: Optional[Iterable[str]] = None,
    hint_texts: Optional[Sequence[Any]] = None,
) -> List[Dict[str, Any]]:
    goal_tokens = tokenize_values(goal_text)
    normalized_tool_tokens = {str(token) for token in (tool_tokens or set()) if str(token)}
    hint_tokens = tokenize_values(*(hint_texts or []))
    ranked: List[Dict[str, Any]] = []
    for profile in CAPABILITY_INTENT_PROFILES:
        goal_overlap = goal_tokens.intersection(profile.goal_terms)
        tool_overlap = normalized_tool_tokens.intersection(profile.tool_terms)
        hint_overlap = hint_tokens.intersection(profile.goal_terms + profile.tool_terms)
        score = min(0.66, 0.22 * len(goal_overlap))
        score += min(0.27, 0.09 * len(tool_overlap))
        score += min(0.12, 0.06 * len(hint_overlap))
        ranked.append(
            {
                "profile": profile,
                "score": round(score, 4),
                "goal_overlap": sorted(goal_overlap),
                "tool_overlap": sorted(tool_overlap),
                "hint_overlap": sorted(hint_overlap),
            }
        )
    ranked.sort(key=lambda item: (-float(item["score"]), item["profile"].capability_id))
    return ranked


def infer_capability_from_text(raw_value: Any) -> Optional[str]:
    ranked = rank_capability_profiles(goal_text=str(raw_value or ""))
    if not ranked or ranked[0]["score"] <= 0.0:
        return None
    return str(ranked[0]["profile"].capability_id)
