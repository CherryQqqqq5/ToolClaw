from __future__ import annotations

from dataclasses import dataclass, field
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
        if task_signature:
            self._task_index.setdefault(task_signature, [])
            if asset_id not in self._task_index[task_signature]:
                self._task_index[task_signature].append(asset_id)
        return asset_id

    def query(self, task_signature: str, top_k: int = 5) -> List[AssetMatch]:
        ids = self._task_index.get(task_signature, [])[:top_k]
        matches: List[AssetMatch] = []
        for rank, asset_id in enumerate(ids):
            asset = self._assets[asset_id]
            asset_type = type(asset).__name__
            matches.append(
                AssetMatch(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    score=max(0.0, 1.0 - rank * 0.1),
                    metadata={"task_signature": task_signature},
                )
            )
        return matches

    def get(self, asset_id: str) -> Optional[Any]:
        return self._assets.get(asset_id)
