from __future__ import annotations

from dataclasses import dataclass

from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.execution.executor import ExecutionOutcome, SequentialExecutor
from toolclaw.interaction.repair_updater import RepairUpdater, UserReply
from toolclaw.planner.htgp import HTGPPlanner, PlanningRequest
from toolclaw.registry import AssetRegistry
from toolclaw.schemas.repair import Repair
from toolclaw.schemas.workflow import Workflow


@dataclass
class ToolClawRuntime:
    planner: HTGPPlanner
    executor: SequentialExecutor
    repair_updater: RepairUpdater
    compiler: SWPCCompiler
    asset_registry: AssetRegistry

    def run_task(
        self,
        request: PlanningRequest,
        run_id: str,
        output_path: str,
    ) -> ExecutionOutcome:
        plan_result = self.planner.plan(request)
        return self.executor.run_until_blocked(
            workflow=plan_result.workflow,
            run_id=run_id,
            output_path=output_path,
        )

    def resume_task(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        run_id: str,
        output_path: str,
    ) -> ExecutionOutcome:
        resume_patch = self.repair_updater.ingest_reply(
            workflow=workflow,
            repair=repair,
            reply=reply,
            state_values={},
        )
        return self.executor.resume_from_patch(
            workflow=workflow,
            run_id=run_id,
            output_path=output_path,
            resume_patch=resume_patch,
        )
