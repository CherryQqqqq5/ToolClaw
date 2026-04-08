"""Shared task annotation helpers for FailTax, dependency slices, and benchmark manifests."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


FAILTAX_BUCKETS = ("selection", "ordering", "state", "recovery")

_SELECTION_LABELS = {
    "selection_failure",
    "binding_failure",
    "canonicalization",
    "single_tool",
    "single_user_turn",
}
_ORDERING_LABELS = {
    "ordering_failure",
    "multiple_tool",
    "multiple_user_turn",
    "dynamic_branching",
    "dual_control",
}
_STATE_LABELS = {
    "state_failure",
    "state_dependency",
    "insufficient_information",
    "missing_asset",
}
_RECOVERY_LABELS = {
    "recovery_failure",
    "environment_failure",
    "interaction_failure",
    "policy_failure",
    "permission_failure",
    "approval_required",
}


def _string_list(values: Iterable[Any]) -> List[str]:
    seen: set[str] = set()
    items: List[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        items.append(normalized)
    return items


def _task_metadata(task: Dict[str, Any]) -> Dict[str, Any]:
    metadata = task.get("metadata")
    return dict(metadata) if isinstance(metadata, dict) else {}


def _candidate_tool_ids(task: Dict[str, Any]) -> List[str]:
    tool_ids: List[str] = []
    for source in (task.get("tool_allow_list"), task.get("candidate_tools")):
        if not isinstance(source, list):
            continue
        for item in source:
            if isinstance(item, str):
                tool_ids.append(item)
            elif isinstance(item, dict):
                tool_id = item.get("tool_id") or item.get("name")
                if tool_id:
                    tool_ids.append(str(tool_id))
    return _string_list(tool_ids)


def _raw_annotation_labels(task: Dict[str, Any]) -> List[str]:
    metadata = _task_metadata(task)
    labels: List[str] = []
    for source in (
        task.get("failtaxes"),
        metadata.get("failtaxes"),
        [task.get("primary_failtax")] if task.get("primary_failtax") else [],
        [metadata.get("primary_failtax")] if metadata.get("primary_failtax") else [],
        task.get("categories"),
        metadata.get("toolsandbox_categories"),
        [task.get("failure_type")] if task.get("failure_type") else [],
        [task.get("scenario")] if task.get("scenario") else [],
        [metadata.get("failure_type")] if metadata.get("failure_type") else [],
        [metadata.get("scenario")] if metadata.get("scenario") else [],
    ):
        if isinstance(source, list):
            labels.extend(str(item).strip().lower() for item in source if str(item).strip())
        elif source:
            labels.append(str(source).strip().lower())
    return _string_list(label.replace(" ", "_") for label in labels)


def map_failtax_bucket(label: str) -> str:
    normalized = str(label).strip().lower().replace(" ", "_")
    if normalized in FAILTAX_BUCKETS:
        return normalized
    if normalized in _SELECTION_LABELS:
        return "selection"
    if normalized in _ORDERING_LABELS:
        return "ordering"
    if normalized in _STATE_LABELS:
        return "state"
    if normalized in _RECOVERY_LABELS:
        return "recovery"
    return "recovery"


def derive_failtaxes(task: Dict[str, Any]) -> List[str]:
    metadata = _task_metadata(task)
    explicit = _string_list(
        value
        for value in (
            task.get("failtaxes") if isinstance(task.get("failtaxes"), list) else [],
            metadata.get("failtaxes") if isinstance(metadata.get("failtaxes"), list) else [],
        )
        for value in value
    )
    if explicit:
        return [map_failtax_bucket(label) for label in explicit]
    labels = _raw_annotation_labels(task)
    mapped = [map_failtax_bucket(label) for label in labels]
    if mapped:
        return _string_list(mapped)
    return ["recovery"]


def derive_primary_failtax(task: Dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    explicit = task.get("primary_failtax") or metadata.get("primary_failtax")
    if explicit:
        return map_failtax_bucket(str(explicit))
    failtaxes = derive_failtaxes(task)
    return failtaxes[0] if failtaxes else "recovery"


def derive_failure_step(task: Dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    explicit = task.get("failure_step") or metadata.get("failure_step")
    if explicit:
        return str(explicit)
    tool_ids = _candidate_tool_ids(task)
    categories = set(_raw_annotation_labels(task))
    if len(tool_ids) <= 1 and "single_tool" in categories:
        return "step_01"
    return "step_02"


def derive_expected_recovery_path(task: Dict[str, Any]) -> str:
    metadata = _task_metadata(task)
    explicit = task.get("expected_recovery_path") or metadata.get("expected_recovery_path")
    if explicit:
        return str(explicit)
    primary = derive_primary_failtax(task)
    scenario = str(task.get("scenario") or metadata.get("scenario") or "").strip().lower().replace(" ", "_")
    if scenario in {"approval_required", "dual_control", "policy_failure"}:
        return "ask_approval_then_retry"
    if scenario in {"binding_failure", "insufficient_information", "missing_asset"}:
        return "clarify_then_patch_then_retry"
    if scenario in {"environment_failure", "interaction_failure"}:
        return "clarify_or_switch_then_retry"
    if primary == "selection":
        return "rebind_or_switch_then_retry"
    if primary == "ordering":
        return "replan_or_reroute_then_retry"
    if primary == "state":
        return "patch_state_then_retry"
    return "repair_then_retry"


def derive_gold_tool(task: Dict[str, Any]) -> Optional[str]:
    metadata = _task_metadata(task)
    explicit = task.get("gold_tool") or metadata.get("gold_tool")
    if explicit:
        return str(explicit)
    tool_ids = _candidate_tool_ids(task)
    if len(tool_ids) == 1:
        return tool_ids[0]
    scenario = str(task.get("scenario") or "").lower()
    if "write" in str(task.get("query") or "").lower() and "write_tool" in tool_ids:
        return "write_tool"
    if scenario in {"canonicalization", "single_tool"} and tool_ids:
        return tool_ids[0]
    return None


def derive_state_slots(task: Dict[str, Any]) -> List[str]:
    metadata = _task_metadata(task)
    explicit = task.get("state_slots") or metadata.get("state_slots")
    if isinstance(explicit, list):
        return _string_list(explicit)
    slots: List[str] = []
    if task.get("query"):
        slots.append("query")
    if task.get("target_path") is not None:
        slots.append("target_path")
    if task.get("messages"):
        slots.append("messages")
    categories = set(_raw_annotation_labels(task))
    if "state_dependency" in categories:
        slots.extend(["retrieved_info", "artifact_ready"])
    if "insufficient_information" in categories:
        slots.append("user_clarification")
    if "approval_required" in categories or "policy_failure" in categories:
        slots.append("approved")
    return _string_list(slots)


def derive_dependency_edges(task: Dict[str, Any]) -> List[Dict[str, str]]:
    metadata = _task_metadata(task)
    explicit = task.get("dependency_edges") or metadata.get("dependency_edges")
    if isinstance(explicit, list):
        normalized_edges: List[Dict[str, str]] = []
        for item in explicit:
            if isinstance(item, dict):
                source = str(item.get("source") or "").strip()
                target = str(item.get("target") or "").strip()
                edge_type = str(item.get("type") or item.get("edge_type") or "default").strip()
                if source and target:
                    normalized_edges.append({"source": source, "target": target, "type": edge_type})
        if normalized_edges:
            return normalized_edges
    if task.get("target_path") is not None or len(_candidate_tool_ids(task)) > 1:
        return [{"source": "step_01", "target": "step_02", "type": "state"}]
    return []


def annotate_task(task: Dict[str, Any]) -> Dict[str, Any]:
    failtaxes = derive_failtaxes(task)
    primary_failtax = derive_primary_failtax(task)
    return {
        "primary_failtax": primary_failtax,
        "failtaxes": failtaxes,
        "failure_step": derive_failure_step(task),
        "expected_recovery_path": derive_expected_recovery_path(task),
        "gold_tool": derive_gold_tool(task),
        "state_slots": derive_state_slots(task),
        "dependency_edges": derive_dependency_edges(task),
    }


def annotate_task_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    annotated = dict(task)
    annotations = annotate_task(task)
    annotated.update({key: value for key, value in annotations.items() if key not in annotated or annotated.get(key) in (None, [], "")})
    metadata = _task_metadata(task)
    metadata.update({key: value for key, value in annotations.items() if key not in metadata or metadata.get(key) in (None, [], "")})
    annotated["metadata"] = metadata
    return annotated


def sample_id_checksum(sample_ids: Sequence[str]) -> str:
    payload = "\n".join(sorted(str(sample_id) for sample_id in sample_ids))
    return sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> Optional[str]:
    try:
        if not path.exists() or not path.is_file():
            return None
        return sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()
