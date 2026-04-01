"""Registry for discovered tool adapters and simple capability-oriented filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from toolclaw.tools.base import ToolAdapter


@dataclass
class ToolRegistry:
    adapters: Dict[str, ToolAdapter] = field(default_factory=dict)

    def register_adapter(self, tool_id: str, adapter: ToolAdapter) -> None:
        self.adapters[tool_id] = adapter

    def discover_tools(self) -> List[str]:
        return sorted(self.adapters.keys())

    def get(self, tool_id: str) -> Optional[ToolAdapter]:
        return self.adapters.get(tool_id)

    def filter_by_capability(self, capability_keyword: str) -> List[str]:
        capability_keyword = capability_keyword.lower()
        matches = []
        for tool_id, adapter in self.adapters.items():
            spec = adapter.describe()
            haystack = f"{tool_id} {spec.description}".lower()
            if capability_keyword in haystack:
                matches.append(tool_id)
        return sorted(matches)
