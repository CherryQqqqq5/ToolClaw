"""In-memory and file-backed registries for reusable ToolClaw artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import re
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

    def query(self, task_signature: str, top_k: int = 5) -> List[AssetMatch]:
        ...

    def get(self, asset_id: str) -> Optional[Any]:
        ...


_SIGNATURE_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


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
            parsed["caps"] = [item for item in value.split("+") if item]
        elif key in {"family", "fail", "goal"}:
            parsed[key] = value
    parsed["goal_tokens"] = _signature_tokens(parsed["goal"])
    return parsed


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left.union(right)
    if not union:
        return 0.0
    return len(left.intersection(right)) / len(union)


def _score_signature_match(query_signature: str, candidate_signature: str) -> tuple[float, str]:
    query = _parse_task_signature(query_signature)
    candidate = _parse_task_signature(candidate_signature)
    if query["raw"] == candidate["raw"]:
        return 1.0, "exact"

    score = 0.0
    match_type = "lexical_similarity"
    if query["family"] and candidate["family"] and query["family"] == candidate["family"]:
        score += 0.28
        match_type = "structural_similarity"
    if query["fail"] and candidate["fail"] and query["fail"] == candidate["fail"]:
        score += 0.14
        match_type = "structural_similarity"

    query_caps = set(query["caps"])
    candidate_caps = set(candidate["caps"])
    if query_caps and candidate_caps:
        score += 0.38 * _jaccard(query_caps, candidate_caps)
        match_type = "structural_similarity"

    goal_overlap = _jaccard(query["goal_tokens"], candidate["goal_tokens"])
    if goal_overlap:
        score += 0.14 * goal_overlap

    token_overlap = _jaccard(query["tokens"], candidate["tokens"])
    if token_overlap:
        score += 0.06 * token_overlap

    return round(score, 4), match_type


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

    def query(self, task_signature: str, top_k: int = 5) -> List[AssetMatch]:
        ranked_matches: Dict[str, AssetMatch] = {}
        for rank, asset_id in enumerate(self._task_index.get(task_signature, [])):
            asset = self._assets[asset_id]
            ranked_matches[asset_id] = AssetMatch(
                asset_id=asset_id,
                asset_type=type(asset).__name__,
                score=max(0.0, 1.0 - rank * 0.02),
                metadata={"task_signature": task_signature, "matched_signature": task_signature, "match_type": "exact"},
            )

        for asset_id, asset in self._assets.items():
            primary_signature = getattr(asset, "task_signature", "")
            signatures = self._artifact_signatures(asset, primary_signature=primary_signature)
            best_score = -1.0
            best_signature = ""
            best_match_type = "lexical_similarity"
            for candidate_signature in signatures:
                score, match_type = _score_signature_match(task_signature, candidate_signature)
                if score > best_score:
                    best_score = score
                    best_signature = candidate_signature
                    best_match_type = match_type
            if best_score < 0.34:
                continue
            current = ranked_matches.get(asset_id)
            if current is None or best_score > current.score:
                ranked_matches[asset_id] = AssetMatch(
                    asset_id=asset_id,
                    asset_type=type(asset).__name__,
                    score=best_score,
                    metadata={
                        "task_signature": task_signature,
                        "matched_signature": best_signature,
                        "match_type": best_match_type,
                    },
                )

        matches = sorted(ranked_matches.values(), key=lambda match: (-match.score, match.asset_id))
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
        index["assets"][asset_id] = {"path": asset_path.name, "task_signature": task_signature}
        index["assets"][asset_id]["signatures"] = signatures
        for signature in signatures:
            index["task_index"].setdefault(signature, [])
            if asset_id not in index["task_index"][signature]:
                index["task_index"][signature].append(asset_id)
        self._save_index(index)
        return asset_id

    def query(self, task_signature: str, top_k: int = 5) -> List[AssetMatch]:
        index = self._load_index()
        ranked_matches: Dict[str, AssetMatch] = {}
        for rank, asset_id in enumerate(index["task_index"].get(task_signature, [])):
            asset_meta = index["assets"][asset_id]
            ranked_matches[asset_id] = AssetMatch(
                asset_id=asset_id,
                asset_type=asset_meta["path"].replace(".json", ""),
                score=max(0.0, 1.0 - rank * 0.02),
                metadata={"task_signature": task_signature, "matched_signature": task_signature, "match_type": "exact"},
            )

        for asset_id, asset_meta in index["assets"].items():
            signatures = [
                str(item)
                for item in asset_meta.get("signatures", [asset_meta.get("task_signature", "")])
                if str(item)
            ]
            best_score = -1.0
            best_signature = ""
            best_match_type = "lexical_similarity"
            for candidate_signature in signatures:
                score, match_type = _score_signature_match(task_signature, candidate_signature)
                if score > best_score:
                    best_score = score
                    best_signature = candidate_signature
                    best_match_type = match_type
            if best_score < 0.34:
                continue
            current = ranked_matches.get(asset_id)
            if current is None or best_score > current.score:
                ranked_matches[asset_id] = AssetMatch(
                    asset_id=asset_id,
                    asset_type=asset_meta["path"].replace(".json", ""),
                    score=best_score,
                    metadata={
                        "task_signature": task_signature,
                        "matched_signature": best_signature,
                        "match_type": best_match_type,
                    },
                )

        matches = sorted(ranked_matches.values(), key=lambda match: (-match.score, match.asset_id))
        return matches[:top_k]

    def get(self, asset_id: str) -> Optional[Any]:
        index = self._load_index()
        meta = index["assets"].get(asset_id)
        if meta is None:
            return None
        payload = json.loads((self.root / meta["path"]).read_text(encoding="utf-8"))
        return SimpleNamespace(**payload["payload"])
