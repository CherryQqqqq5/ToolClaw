"""Placeholder MCP adapter that exposes a uniform ToolAdapter interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from toolclaw.schemas.workflow import ToolSpec
from toolclaw.tools.base import ToolCostProfile, ToolResult, ValidationResult


@dataclass
class MCPToolAdapter:
    tool_id: str
    description: str

    def describe(self) -> ToolSpec:
        return ToolSpec(tool_id=self.tool_id, description=self.description, metadata={"adapter": "mcp"})

    def validate_args(self, args: Dict[str, Any]) -> ValidationResult:
        return ValidationResult(valid=isinstance(args, dict))

    def execute(self, args: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        _ = context
        return ToolResult(status="not_implemented", payload={"tool_id": self.tool_id, "args": args})

    def estimate_cost(self, args: Dict[str, Any]) -> ToolCostProfile:
        _ = args
        return ToolCostProfile(dollar_cost=0.01, token_cost=10.0, latency_ms=150)
