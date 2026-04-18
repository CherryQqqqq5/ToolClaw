"""Top-level runtime facade that wires planning, execution, interaction, and reuse."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from toolclaw.compiler.swpc import SWPCCompiler, build_task_signature_candidates
from toolclaw.execution.executor import ExecutionOutcome, SequentialExecutor
from toolclaw.interaction.repair_updater import RepairUpdater, UserReply
from toolclaw.planner.htgp import HTGPPlanner, PlanningRequest
from toolclaw.registry import AssetRegistry
from toolclaw.schemas.repair import Repair
from toolclaw.schemas.trace import EventType, Trace
from toolclaw.schemas.workflow import Workflow


@dataclass
class ToolClawRuntime:
    planner: HTGPPlanner
    executor: SequentialExecutor
    repair_updater: RepairUpdater
    compiler: SWPCCompiler
    asset_registry: AssetRegistry
    wire_executor_planner: bool = True

    def __post_init__(self) -> None:
        if self.wire_executor_planner:
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
            signatures = build_task_signature_candidates(
                user_goal=request.task.user_goal,
                task_family=request.hints.user_style.get("task_family"),
                failure_context=request.hints.user_style.get("failure_type"),
            )
            reusable_ids = []
            for signature in signatures:
                reusable_ids.extend(match.asset_id for match in self.asset_registry.query(signature))
            request.hints.reusable_asset_ids = list(dict.fromkeys(reusable_ids))
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

        trace = self._load_trace_for_compilation(outcome)
        artifacts = self.compiler.compile_from_trace(
            workflow=outcome.workflow,
            trace=trace,
            final_state=outcome.final_state,
        )
        for artifact in artifacts.workflow_snippets + artifacts.skill_hints + artifacts.policy_snippets:
            self.asset_registry.upsert(artifact)

    @staticmethod
    def _load_trace_for_compilation(outcome: ExecutionOutcome) -> Trace:
        trace = Trace(
            run_id=outcome.run_id,
            workflow_id=outcome.workflow.workflow_id,
            task_id=outcome.workflow.task.task_id,
        )
        if not outcome.trace_path:
            trace.metrics.success = bool(outcome.success)
            return trace

        trace_path = Path(outcome.trace_path)
        if not trace_path.exists():
            trace.metrics.success = bool(outcome.success)
            return trace

        payload = json.loads(trace_path.read_text(encoding="utf-8"))
        metrics = dict(payload.get("metrics", {}))
        trace.metrics.success = bool(metrics.get("success"))
        trace.metrics.tool_calls = int(metrics.get("tool_calls", 0) or 0)
        trace.metrics.user_queries = int(metrics.get("user_queries", 0) or 0)
        trace.metrics.repair_actions = int(metrics.get("repair_actions", 0) or 0)
        trace.metrics.total_steps = int(metrics.get("total_steps", 0) or 0)
        for event in payload.get("events", []):
            event_type = event.get("event_type")
            if not event_type:
                continue
            trace.add_event(
                event_id=str(event.get("event_id", "")),
                event_type=EventType(event_type),
                actor=str(event.get("actor", "executor")),
                step_id=event.get("step_id"),
                tool_id=event.get("tool_id"),
                tool_args=event.get("tool_args"),
                output=event.get("output"),
                message=event.get("message"),
                metadata=event.get("metadata"),
            )
        trace.metrics.success = bool(metrics.get("success"))
        trace.metrics.tool_calls = int(metrics.get("tool_calls", 0) or 0)
        trace.metrics.user_queries = int(metrics.get("user_queries", 0) or 0)
        trace.metrics.repair_actions = int(metrics.get("repair_actions", 0) or 0)
        trace.metrics.total_steps = int(metrics.get("total_steps", 0) or 0)
        return trace
