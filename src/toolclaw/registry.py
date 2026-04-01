"""In-memory and file-backed registries for reusable ToolClaw artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
        asset_path = self.root / f"{asset_id}.json"
        asset_path.write_text(
            json.dumps(
                {
                    "asset_id": asset_id,
                    "asset_type": type(artifact).__name__,
                    "task_signature": task_signature,
                    "payload": asset_payload,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        index["assets"][asset_id] = {"path": asset_path.name, "task_signature": task_signature}
        if task_signature:
            index["task_index"].setdefault(task_signature, [])
            if asset_id not in index["task_index"][task_signature]:
                index["task_index"][task_signature].append(asset_id)
        self._save_index(index)
        return asset_id

    def query(self, task_signature: str, top_k: int = 5) -> List[AssetMatch]:
        index = self._load_index()
        ids = index["task_index"].get(task_signature, [])[:top_k]
        matches: List[AssetMatch] = []
        for rank, asset_id in enumerate(ids):
            asset_meta = index["assets"][asset_id]
            matches.append(
                AssetMatch(
                    asset_id=asset_id,
                    asset_type=asset_meta["path"].replace(".json", ""),
                    score=max(0.0, 1.0 - rank * 0.1),
                    metadata={"task_signature": task_signature},
                )
            )
        return matches

    def get(self, asset_id: str) -> Optional[Any]:
        index = self._load_index()
        meta = index["assets"].get(asset_id)
        if meta is None:
            return None
        payload = json.loads((self.root / meta["path"]).read_text(encoding="utf-8"))
        return SimpleNamespace(**payload["payload"])
