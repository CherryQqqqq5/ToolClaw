"""Base tool adapter protocol and shared execution/result containers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from toolclaw.schemas.workflow import ToolSpec


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCostProfile:
    dollar_cost: float = 0.0
    token_cost: float = 0.0
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    status: str
    payload: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolAdapter(Protocol):
    def describe(self) -> ToolSpec:
        ...

    def validate_args(self, args: Dict[str, Any]) -> ValidationResult:
        ...

    def execute(self, args: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        ...

    def estimate_cost(self, args: Dict[str, Any]) -> ToolCostProfile:
        ...
