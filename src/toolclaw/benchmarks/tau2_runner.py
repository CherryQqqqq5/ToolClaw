"""Minimal tau²-style runner focused on interaction-driven recovery loops."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.user_simulator import SimulatedPolicy
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest


@dataclass
class Tau2RunResult:
    success: bool
    stop_reason: str
    interaction_turns: int
    trace_path: str


def run_tau2_interactive(
    runtime: ToolClawRuntime,
    request: PlanningRequest,
    run_id: str,
    output_path: Path,
    simulated_policy: Optional[Dict[str, object]] = None,
) -> Tau2RunResult:
    simulated_policy = simulated_policy or {}
    shell = InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            simulator_policy=SimulatedPolicy(
                mode=str(simulated_policy.get("mode", "cooperative")),
                missing_arg_values=dict(simulated_policy.get("missing_arg_values", {})),
                backup_tool_preferences=dict(simulated_policy.get("backup_tool_preferences", {})),
            )
        ),
    )
    outcome = shell.run(request=request, run_id=run_id, output_path=str(output_path))
    stop_reason = outcome.metadata.get("stopped_reason", "success" if outcome.success else "unknown")
    return Tau2RunResult(
        success=outcome.success,
        stop_reason=str(stop_reason),
        interaction_turns=shell.config.max_turns if outcome.blocked else 0,
        trace_path=str(output_path),
    )
