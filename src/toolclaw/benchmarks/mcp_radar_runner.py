"""Utility scoring helpers that approximate MCP-RADAR-style dimensions from traces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import json


@dataclass
class McpRadarMetrics:
    correctness: float
    tool_efficiency: float
    parameter_accuracy: float
    execution_quality: float
    speed_score: float


def score_trace_for_mcp_radar(trace_path: Path) -> McpRadarMetrics:
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    tool_calls = max(int(metrics.get("tool_calls", 0)), 1)
    repair_actions = int(metrics.get("repair_actions", 0))
    success = 1.0 if metrics.get("success") else 0.0
    tool_efficiency = max(0.0, 1.0 - 0.1 * (tool_calls - 1))
    parameter_accuracy = max(0.0, 1.0 - 0.2 * repair_actions)
    execution_quality = 0.8 if success else 0.2
    speed_score = max(0.0, 1.0 - 0.05 * tool_calls)
    return McpRadarMetrics(
        correctness=success,
        tool_efficiency=tool_efficiency,
        parameter_accuracy=parameter_accuracy,
        execution_quality=execution_quality,
        speed_score=speed_score,
    )
