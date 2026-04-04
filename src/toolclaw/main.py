"""Top-level runtime facade that wires planning, execution, interaction, and reuse."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

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

    def __post_init__(self) -> None:
        self.executor.planner = self.planner

    def run_task(
        self,
        request: PlanningRequest,
        run_id: str,
        output_path: str,
        backup_tool_map: Optional[Dict[str, str]] = None,
        compile_on_success: bool = True,
    ) -> ExecutionOutcome:
        plan_result = self.planner.plan(request)
        outcome = self.executor.run_until_blocked(
            workflow=plan_result.workflow,
            run_id=run_id,
            output_path=output_path,
            backup_tool_map=backup_tool_map,
        )
        self._compile_and_store_if_success(outcome, enabled=compile_on_success)
        return outcome

    def run_task_with_reuse(
        self,
        request: PlanningRequest,
        run_id: str,
        output_path: str,
        backup_tool_map: Optional[Dict[str, str]] = None,
        compile_on_success: bool = True,
    ) -> ExecutionOutcome:
        if not request.hints.reusable_asset_ids and self.asset_registry:
            signature = f"phase1::{request.task.user_goal.lower().strip().replace(' ', '_')}"
            request.hints.reusable_asset_ids = [match.asset_id for match in self.asset_registry.query(signature)]
        return self.run_task(
            request=request,
            run_id=run_id,
            output_path=output_path,
            backup_tool_map=backup_tool_map,
            compile_on_success=compile_on_success,
        )

    def resume_task(
        self,
        workflow: Workflow,
        repair: Repair,
        reply: UserReply,
        run_id: str,
        output_path: str,
        backup_tool_map: Optional[Dict[str, str]] = None,
        state_values: Optional[Dict[str, object]] = None,
        compile_on_success: bool = True,
    ) -> ExecutionOutcome:
        resume_patch = self.repair_updater.ingest_reply(
            workflow=workflow,
            repair=repair,
            reply=reply,
            state_values=dict(state_values or {}),
        )
        outcome = self.executor.resume_from_patch(
            workflow=workflow,
            run_id=run_id,
            output_path=output_path,
            resume_patch=resume_patch,
            backup_tool_map=backup_tool_map,
        )
        self._compile_and_store_if_success(outcome, enabled=compile_on_success)
        return outcome

    def _compile_and_store_if_success(self, outcome: ExecutionOutcome, enabled: bool = True) -> None:
        if not enabled or not outcome.success:
            return

        from toolclaw.schemas.trace import Trace

        trace = Trace(
            run_id=outcome.run_id,
            workflow_id=outcome.workflow.workflow_id,
            task_id=outcome.workflow.task.task_id,
        )
        trace.metrics.success = True
        artifacts = self.compiler.compile_from_trace(
            workflow=outcome.workflow,
            trace=trace,
            final_state=outcome.final_state,
        )
        for artifact in artifacts.workflow_snippets + artifacts.skill_hints + artifacts.policy_snippets:
            self.asset_registry.upsert(artifact)
