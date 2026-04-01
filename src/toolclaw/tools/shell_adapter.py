"""Placeholder shell adapter that matches the shared ToolAdapter contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from toolclaw.schemas.workflow import ToolSpec
from toolclaw.tools.base import ToolCostProfile, ToolResult, ValidationResult


@dataclass
class ShellToolAdapter:
    tool_id: str
    description: str

    def describe(self) -> ToolSpec:
        return ToolSpec(tool_id=self.tool_id, description=self.description, metadata={"adapter": "shell"})

    def validate_args(self, args: Dict[str, Any]) -> ValidationResult:
        valid = isinstance(args, dict) and "command" in args
        return ValidationResult(valid=valid, errors=[] if valid else ["missing command"])

    def execute(self, args: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        _ = context
        return ToolResult(status="not_implemented", payload={"command": args.get("command")})

    def estimate_cost(self, args: Dict[str, Any]) -> ToolCostProfile:
        _ = args
        return ToolCostProfile(dollar_cost=0.005, token_cost=0.0, latency_ms=60)
