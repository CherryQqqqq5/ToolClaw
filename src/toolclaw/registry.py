"""In-memory and file-backed registries for reusable ToolClaw artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class AssetMatch:
    asset_id: str
    asset_type: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssetRegistry(Protocol):
    def upsert(self, artifact: Any) -> str:
        ...

    def query(
        self,
        task_signature: str,
        top_k: int = 5,
        *,
        required_capability_skeleton: Optional[List[str]] = None,
        failure_context: Optional[str] = None,
        required_state_slots: Optional[List[str]] = None,
    ) -> List[AssetMatch]:
        ...

    def get(self, asset_id: str) -> Optional[Any]:
        ...


_SIGNATURE_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
_ASSET_TYPE_PRIORITY = {
    "WorkflowSnippet": 0,
    "workflowsnippet": 0,
    "PolicySnippet": 1,
    "policysnippet": 1,
    "SkillHint": 2,
    "skillhint": 2,
}


def _normalize_field(value: Any, *, default: str = "") -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    normalized = _NON_ALNUM_PATTERN.sub("_", text).strip("_")
    return normalized or default


def _normalize_str_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    normalized: List[str] = []
    for value in values:
        token = _normalize_field(value)
        if token and token not in normalized:
            normalized.append(token)
    return normalized


def _signature_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    for token in _SIGNATURE_TOKEN_PATTERN.findall(str(value or "").lower()):
        if token:
            tokens.add(token)
    return tokens


def _parse_task_signature(signature: str) -> Dict[str, Any]:
    text = str(signature or "").strip().lower()
    parsed: Dict[str, Any] = {
        "raw": text,
        "family": "",
        "fail": "",
        "goal": "",
        "caps": [],
        "tokens": _signature_tokens(text),
    }
    for part in text.split("::"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "caps":
            parsed["caps"] = [_normalize_field(item) for item in value.split("+") if _normalize_field(item)]
        elif key in {"family", "fail", "goal"}:
            parsed[key] = _normalize_field(value)
    parsed["goal_tokens"] = _signature_tokens(parsed["goal"])
    return parsed


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left.union(right)
    if not union:
        return 0.0
    return len(left.intersection(right)) / len(union)


def _score_signature_match(query_signature: str, candidate_signature: str) -> Dict[str, Any]:
    query = _parse_task_signature(query_signature)
    candidate = _parse_task_signature(candidate_signature)
    family_match = bool(query["family"] and candidate["family"] and query["family"] == candidate["family"])
    fail_match = bool(query["fail"] and candidate["fail"] and query["fail"] == candidate["fail"])
    caps_match = bool(query["caps"] and candidate["caps"] and list(query["caps"]) == list(candidate["caps"]))
    goal_match = bool(query["goal"] and candidate["goal"] and query["goal"] == candidate["goal"])
    goal_overlap = _jaccard(query["goal_tokens"], candidate["goal_tokens"])
    token_overlap = _jaccard(query["tokens"], candidate["tokens"])

    exact_score = 1.0 if family_match and fail_match and caps_match and goal_match else 0.0
    transfer_score = 0.0
    reuse_mode = "none"
    if exact_score >= 1.0:
        reuse_mode = "exact_reuse"
        transfer_score = 0.98
    elif family_match and fail_match and caps_match:
        transfer_score = round(min(0.98, 0.58 + 0.28 * goal_overlap + 0.08 * token_overlap), 4)
        if transfer_score >= 0.62:
            reuse_mode = "transfer_reuse"

    best_score = exact_score if reuse_mode == "exact_reuse" else transfer_score
    return {
        "query_signature": query_signature,
        "candidate_signature": candidate_signature,
        "reuse_mode": reuse_mode,
        "match_type": reuse_mode,
        "exact_score": round(exact_score, 4),
        "transfer_score": round(transfer_score, 4),
        "score": round(best_score, 4),
        "goal_overlap": round(goal_overlap, 4),
        "token_overlap": round(token_overlap, 4),
        "family_match": family_match,
        "fail_match": fail_match,
        "caps_match": caps_match,
        "goal_match": goal_match,
    }


def _asset_metadata(asset: Any) -> Dict[str, Any]:
    metadata = getattr(asset, "metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _asset_capability_skeleton(asset: Any) -> List[str]:
    skeleton = getattr(asset, "capability_skeleton", None)
    if isinstance(skeleton, list):
        return _normalize_str_list(skeleton)
    metadata = _asset_metadata(asset)
    if isinstance(metadata.get("capability_skeleton"), list):
        return _normalize_str_list(metadata.get("capability_skeleton"))
    parsed = _parse_task_signature(str(getattr(asset, "task_signature", "")))
    return list(parsed["caps"])


def _asset_failure_context(asset: Any) -> str:
    metadata = _asset_metadata(asset)
    explicit = metadata.get("failure_context")
    if explicit not in (None, ""):
        return _normalize_field(explicit, default="none")
    parsed = _parse_task_signature(str(getattr(asset, "task_signature", "")))
    return _normalize_field(parsed.get("fail"), default="none")


def _asset_required_state_slots(asset: Any) -> List[str]:
    metadata = _asset_metadata(asset)
    return _normalize_str_list(metadata.get("required_state_slots"))


def _asset_source_task_id(asset: Any) -> str:
    metadata = _asset_metadata(asset)
    return str(metadata.get("source_task_id") or "").strip()


def _asset_source_reuse_family(asset: Any) -> str:
    metadata = _asset_metadata(asset)
    return str(metadata.get("reuse_family_id") or "").strip()


def _asset_source_semantic_reuse_family(asset: Any) -> str:
    metadata = _asset_metadata(asset)
    semantic_family = str(metadata.get("semantic_reuse_family") or "").strip()
    if semantic_family:
        return semantic_family
    reuse_family_id = _asset_source_reuse_family(asset)
    if not reuse_family_id:
        return ""
    family = re.sub(r"__pair\d+$", "", reuse_family_id)
    family = re.sub(r"_\d+$", "", family)
    return family


def _quality_score(asset: Any) -> float:
    try:
        return float(getattr(asset, "quality_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _asset_utility_profile(asset: Any) -> Dict[str, Any]:
    metadata = _asset_metadata(asset)
    raw_profile = metadata.get("utility_profile")
    profile = dict(raw_profile) if isinstance(raw_profile, dict) else {}
    recommended_inputs = getattr(asset, "recommended_inputs", None)
    continuation_hints = getattr(asset, "continuation_hints", None)
    gain = round(
        _coerce_float(
            profile.get("utility_gain_score", metadata.get("utility_gain_score", 0.0)),
            0.0,
        ),
        4,
    )
    application = str(
        profile.get("reuse_application_hint")
        or metadata.get("reuse_application_hint")
        or ""
    ).strip()
    if not application:
        if isinstance(continuation_hints, list) and continuation_hints and gain > 0.0:
            application = "continuation_prior"
        else:
            application = "execution_prior" if isinstance(recommended_inputs, dict) and recommended_inputs else "binding_prior"
    return {
        "reuse_application_hint": application,
        "utility_gain_score": gain,
        "observed_tool_calls": int(profile.get("observed_tool_calls", metadata.get("observed_tool_calls", 0)) or 0),
        "observed_user_queries": int(profile.get("observed_user_queries", metadata.get("observed_user_queries", 0)) or 0),
        "observed_repair_actions": int(profile.get("observed_repair_actions", metadata.get("observed_repair_actions", 0)) or 0),
        "expected_tool_calls": int(profile.get("expected_tool_calls", metadata.get("expected_tool_calls", 0)) or 0),
        "expected_turns": int(profile.get("expected_turns", metadata.get("expected_turns", 0)) or 0),
        "tool_efficiency": round(_coerce_float(profile.get("tool_efficiency", metadata.get("tool_efficiency", 0.0)), 0.0), 4),
        "turn_efficiency": round(_coerce_float(profile.get("turn_efficiency", metadata.get("turn_efficiency", 0.0)), 0.0), 4),
        "repair_score": round(_coerce_float(profile.get("repair_score", metadata.get("repair_score", 0.0)), 0.0), 4),
        "utility_gain_signature": str(
            profile.get("utility_gain_signature")
            or metadata.get("utility_gain_signature")
            or ""
        ).strip(),
    }


def _compatibility_rejections(
    *,
    asset: Any,
    required_capability_skeleton: Optional[List[str]],
    failure_context: Optional[str],
    required_state_slots: Optional[List[str]],
) -> List[str]:
    rejection_reasons: List[str] = []
    normalized_skeleton = _normalize_str_list(required_capability_skeleton)
    if normalized_skeleton and _asset_capability_skeleton(asset) != normalized_skeleton:
        rejection_reasons.append("capability_skeleton_mismatch")
    normalized_failure = _normalize_field(failure_context, default="none") if failure_context else ""
    if normalized_failure and _asset_failure_context(asset) != normalized_failure:
        rejection_reasons.append("failure_context_mismatch")
    normalized_state_slots = _normalize_str_list(required_state_slots)
    asset_state_slots = _asset_required_state_slots(asset)
    if normalized_state_slots and asset_state_slots != normalized_state_slots:
        rejection_reasons.append("required_state_slots_mismatch")
    return rejection_reasons


def _ranked_match_for_asset(
    *,
    asset_id: str,
    asset: Any,
    asset_type: str,
    task_signature: str,
    signatures: List[str],
    required_capability_skeleton: Optional[List[str]],
    failure_context: Optional[str],
    required_state_slots: Optional[List[str]],
) -> Optional[AssetMatch]:
    rejection_reasons = _compatibility_rejections(
        asset=asset,
        required_capability_skeleton=required_capability_skeleton,
        failure_context=failure_context,
        required_state_slots=required_state_slots,
    )
    if rejection_reasons:
        return None

    best_details: Optional[Dict[str, Any]] = None
    best_signature = ""
    for candidate_signature in signatures:
        details = _score_signature_match(task_signature, candidate_signature)
        if details["reuse_mode"] == "none":
            continue
        if best_details is None or details["score"] > best_details["score"]:
            best_details = details
            best_signature = candidate_signature
    if best_details is None:
        return None
    return AssetMatch(
        asset_id=asset_id,
        asset_type=asset_type,
        score=float(best_details["score"]),
        metadata={
            "task_signature": task_signature,
            "matched_signature": best_signature,
            "match_type": best_details["match_type"],
            "reuse_mode": best_details["reuse_mode"],
            "exact_score": best_details["exact_score"],
            "transfer_score": best_details["transfer_score"],
            "goal_overlap": best_details["goal_overlap"],
            "token_overlap": best_details["token_overlap"],
            "quality_score": round(_quality_score(asset), 4),
            "asset_capability_skeleton": _asset_capability_skeleton(asset),
            "asset_failure_context": _asset_failure_context(asset),
            "asset_required_state_slots": _asset_required_state_slots(asset),
            "source_task_id": _asset_source_task_id(asset),
            "source_reuse_family_id": _asset_source_reuse_family(asset),
            "source_semantic_reuse_family": _asset_source_semantic_reuse_family(asset),
            **_asset_utility_profile(asset),
            "query_required_capability_skeleton": _normalize_str_list(required_capability_skeleton),
            "query_failure_context": _normalize_field(failure_context, default="none") if failure_context else "",
            "query_required_state_slots": _normalize_str_list(required_state_slots),
            "rejection_reasons": [],
        },
    )


def _match_sort_key(match: AssetMatch) -> tuple[int, float, int, float, float, int, str]:
    reuse_mode = str(match.metadata.get("reuse_mode") or "")
    reuse_application = str(match.metadata.get("reuse_application_hint") or "binding_prior")
    if reuse_application == "continuation_prior":
        application_rank = 0
    elif reuse_application == "execution_prior":
        application_rank = 1
    elif reuse_application == "binding_prior":
        application_rank = 2
    else:
        application_rank = 3
    utility_gain_score = _coerce_float(match.metadata.get("utility_gain_score", 0.0), 0.0)
    mode_rank = 0 if reuse_mode == "exact_reuse" else 1
    quality_score = float(match.metadata.get("quality_score", 0.0) or 0.0)
    asset_type_rank = _ASSET_TYPE_PRIORITY.get(match.asset_type, _ASSET_TYPE_PRIORITY.get(match.asset_type.lower(), 9))
    return (application_rank, -utility_gain_score, mode_rank, -match.score, -quality_score, asset_type_rank, match.asset_id)


class InMemoryAssetRegistry:
    def __init__(self) -> None:
        self._assets: Dict[str, Any] = {}
        self._task_index: Dict[str, List[str]] = {}
        self._counter = 0

    def upsert(self, artifact: Any) -> str:
        self._counter += 1
        asset_id = getattr(artifact, "snippet_id", None) or getattr(artifact, "hint_id", None) or getattr(artifact, "policy_id", None)
        if not asset_id:
            asset_id = f"asset_{self._counter:05d}"

        task_signature = getattr(artifact, "task_signature", "")
        self._assets[asset_id] = artifact
        signatures = self._artifact_signatures(artifact, primary_signature=task_signature)
        for signature in signatures:
            self._task_index.setdefault(signature, [])
            if asset_id not in self._task_index[signature]:
                self._task_index[signature].append(asset_id)
        return asset_id

    def query(
        self,
        task_signature: str,
        top_k: int = 5,
        *,
        required_capability_skeleton: Optional[List[str]] = None,
        failure_context: Optional[str] = None,
        required_state_slots: Optional[List[str]] = None,
    ) -> List[AssetMatch]:
        matches: List[AssetMatch] = []
        for asset_id, asset in self._assets.items():
            primary_signature = getattr(asset, "task_signature", "")
            signatures = self._artifact_signatures(asset, primary_signature=primary_signature)
            ranked = _ranked_match_for_asset(
                asset_id=asset_id,
                asset=asset,
                asset_type=type(asset).__name__,
                task_signature=task_signature,
                signatures=signatures,
                required_capability_skeleton=required_capability_skeleton,
                failure_context=failure_context,
                required_state_slots=required_state_slots,
            )
            if ranked is not None:
                matches.append(ranked)

        matches = sorted(matches, key=_match_sort_key)
        return matches[:top_k]

    def get(self, asset_id: str) -> Optional[Any]:
        return self._assets.get(asset_id)

    @staticmethod
    def _artifact_signatures(artifact: Any, *, primary_signature: str) -> List[str]:
        signatures: List[str] = []
        if primary_signature:
            signatures.append(primary_signature)
        metadata = getattr(artifact, "metadata", {})
        if isinstance(metadata, dict):
            for alias in metadata.get("task_signature_aliases", []):
                alias_text = str(alias).strip()
                if alias_text and alias_text not in signatures:
                    signatures.append(alias_text)
        return signatures


class FileAssetRegistry:
    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"assets": {}, "task_index": {}}), encoding="utf-8")

    def _load_index(self) -> Dict[str, Any]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self, payload: Dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert(self, artifact: Any) -> str:
        index = self._load_index()
        asset_id = (
            getattr(artifact, "snippet_id", None)
            or getattr(artifact, "hint_id", None)
            or getattr(artifact, "policy_id", None)
            or getattr(artifact, "asset_id", None)
            or f"asset_{len(index['assets']) + 1:05d}"
        )
        task_signature = getattr(artifact, "task_signature", "")
        asset_payload = artifact.__dict__ if hasattr(artifact, "__dict__") else {"value": artifact}
        signatures = InMemoryAssetRegistry._artifact_signatures(artifact, primary_signature=task_signature)
        asset_path = self.root / f"{asset_id}.json"
        asset_path.write_text(
            json.dumps(
                {
                    "asset_id": asset_id,
                    "asset_type": type(artifact).__name__,
                    "task_signature": task_signature,
                    "task_signature_aliases": signatures[1:],
                    "payload": asset_payload,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        index["assets"][asset_id] = {
            "path": asset_path.name,
            "task_signature": task_signature,
            "asset_type": type(artifact).__name__,
        }
        index["assets"][asset_id]["signatures"] = signatures
        for signature in signatures:
            index["task_index"].setdefault(signature, [])
            if asset_id not in index["task_index"][signature]:
                index["task_index"][signature].append(asset_id)
        self._save_index(index)
        return asset_id

    def query(
        self,
        task_signature: str,
        top_k: int = 5,
        *,
        required_capability_skeleton: Optional[List[str]] = None,
        failure_context: Optional[str] = None,
        required_state_slots: Optional[List[str]] = None,
    ) -> List[AssetMatch]:
        index = self._load_index()
        matches: List[AssetMatch] = []
        for asset_id, asset_meta in index["assets"].items():
            signatures = [
                str(item)
                for item in asset_meta.get("signatures", [asset_meta.get("task_signature", "")])
                if str(item)
            ]
            asset = self.get(asset_id)
            if asset is None:
                continue
            ranked = _ranked_match_for_asset(
                asset_id=asset_id,
                asset=asset,
                asset_type=str(asset_meta.get("asset_type") or type(asset).__name__),
                task_signature=task_signature,
                signatures=signatures,
                required_capability_skeleton=required_capability_skeleton,
                failure_context=failure_context,
                required_state_slots=required_state_slots,
            )
            if ranked is not None:
                matches.append(ranked)

        matches = sorted(matches, key=_match_sort_key)
        return matches[:top_k]

    def get(self, asset_id: str) -> Optional[Any]:
        index = self._load_index()
        meta = index["assets"].get(asset_id)
        if meta is None:
            return None
        payload = json.loads((self.root / meta["path"]).read_text(encoding="utf-8"))
        return SimpleNamespace(**payload["payload"])
