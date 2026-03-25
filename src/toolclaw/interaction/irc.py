from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from toolclaw.execution.executor import ExecutionOutcome
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest


@dataclass
class InteractionLoopConfig:
    max_turns: int = 3
    simulator_policy: SimulatedPolicy = field(default_factory=SimulatedPolicy)


class InteractionShell:
    """Drive blocked execution until completion/abort for phase-1 evaluation."""

    def __init__(
        self,
        runtime: ToolClawRuntime,
        repair_updater: Optional[RepairUpdater] = None,
        config: Optional[InteractionLoopConfig] = None,
    ) -> None:
        self.runtime = runtime
        self.repair_updater = repair_updater or runtime.repair_updater
        self.config = config or InteractionLoopConfig()
        self.simulator = UserSimulator(self.config.simulator_policy)

    def run(
        self,
        request: PlanningRequest,
        run_id: str,
        output_path: str,
    ) -> ExecutionOutcome:
        outcome = self.runtime.run_task(request=request, run_id=run_id, output_path=output_path)
        turns = 0

        while outcome.blocked and outcome.pending_interaction and turns < self.config.max_turns:
            turns += 1
            repair = outcome.pending_interaction.repair
            query = self.repair_updater.build_query(
                workflow=outcome.workflow,
                repair=repair,
                state_values=outcome.final_state,
            )
            reply = self.simulator.reply(query)
            if not self.repair_updater.validate_reply(query, reply):
                return ExecutionOutcome(
                    run_id=outcome.run_id,
                    workflow=outcome.workflow,
                    success=False,
                    blocked=False,
                    pending_interaction=None,
                    final_state=outcome.final_state,
                    trace_path=outcome.trace_path,
                    last_error_id=outcome.last_error_id,
                    metadata={"stopped_reason": "invalid_user_reply"},
                )

            outcome = self.runtime.resume_task(
                workflow=outcome.workflow,
                repair=repair,
                reply=reply,
                run_id=run_id,
                output_path=output_path,
            )

        if outcome.blocked:
            return ExecutionOutcome(
                run_id=outcome.run_id,
                workflow=outcome.workflow,
                success=False,
                blocked=False,
                pending_interaction=None,
                final_state=outcome.final_state,
                trace_path=outcome.trace_path,
                last_error_id=outcome.last_error_id,
                metadata={"stopped_reason": "interaction_turn_limit"},
            )

        return outcome
