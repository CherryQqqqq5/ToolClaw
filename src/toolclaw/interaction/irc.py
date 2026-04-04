"""Interactive repair loop that turns blocked execution into a correction dialogue."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Optional

from toolclaw.execution.executor import ExecutionOutcome
from toolclaw.interaction.query_policy import QueryPolicy
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.uncertainty_detector import UncertaintyDetector
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest
from toolclaw.schemas.trace import EventType, utc_now_iso


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
        uncertainty_detector: Optional[UncertaintyDetector] = None,
        query_policy: Optional[QueryPolicy] = None,
    ) -> None:
        self.runtime = runtime
        self.repair_updater = repair_updater or runtime.repair_updater
        self.config = config or InteractionLoopConfig()
        self.simulator = UserSimulator(self.config.simulator_policy)
        self.uncertainty_detector = uncertainty_detector or UncertaintyDetector()
        self.query_policy = query_policy or QueryPolicy()

    def run(
        self,
        request: PlanningRequest,
        run_id: str,
        output_path: str,
        backup_tool_map: Optional[Dict[str, str]] = None,
        use_reuse: bool = False,
        compile_on_success: bool = True,
    ) -> ExecutionOutcome:
        if use_reuse:
            outcome = self.runtime.run_task_with_reuse(
                request=request,
                run_id=run_id,
                output_path=output_path,
                backup_tool_map=backup_tool_map,
                compile_on_success=compile_on_success,
            )
        else:
            outcome = self.runtime.run_task(
                request=request,
                run_id=run_id,
                output_path=output_path,
                backup_tool_map=backup_tool_map,
                compile_on_success=compile_on_success,
            )
        combined_trace = self._load_trace(output_path)
        turns = 0

        while outcome.blocked and outcome.pending_interaction and turns < self.config.max_turns:
            turns += 1
            repair = outcome.pending_interaction.repair
            report = self.uncertainty_detector.analyze_failure(
                workflow=outcome.workflow,
                repair=repair,
                state_values=outcome.final_state,
            )
            query_plan = self.query_policy.decide_query(report)
            query = self.repair_updater.build_query(
                workflow=outcome.workflow,
                repair=repair,
                state_values=outcome.final_state,
            )
            if query_plan.ask and query_plan.question_text:
                query.question = query_plan.question_text
                query.expected_answer_type = query_plan.question_type
                query.allowed_response_schema = query_plan.response_schema
                query.metadata["uncertainty"] = report.primary_label
            reply = self.simulator.reply(query)
            self._append_interaction_events(combined_trace, query=query, reply=reply, turn_index=turns)
            if not self.repair_updater.validate_reply(query, reply):
                self._finalize_combined_trace(
                    combined_trace,
                    output_path=output_path,
                    success=False,
                    stop_reason="invalid_user_reply",
                )
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
                backup_tool_map=backup_tool_map,
                state_values=outcome.final_state,
                compile_on_success=compile_on_success,
            )
            combined_trace = self._merge_trace_payloads(combined_trace, self._load_trace(output_path))
            self._write_trace(output_path, combined_trace)

        if outcome.blocked:
            self._finalize_combined_trace(
                combined_trace,
                output_path=output_path,
                success=False,
                stop_reason="interaction_turn_limit",
            )
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

        self._write_trace(output_path, combined_trace)
        return outcome

    @staticmethod
    def _load_trace(output_path: str) -> Dict[str, Any]:
        path = Path(output_path)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_trace(output_path: str, trace_payload: Dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")

    @staticmethod
    def _append_interaction_events(
        trace_payload: Dict[str, Any],
        *,
        query: Any,
        reply: Any,
        turn_index: int,
    ) -> None:
        events = trace_payload.setdefault("events", [])
        metrics = trace_payload.setdefault("metrics", {})
        events.append(
            {
                "event_id": f"evt_user_query_{turn_index:02d}",
                "timestamp": utc_now_iso(),
                "step_id": query.context_summary.get("step_id"),
                "event_type": EventType.USER_QUERY.value,
                "actor": "interaction_shell",
                "tool_id": None,
                "input_ref": None,
                "tool_args": None,
                "output": {
                    "question": query.question,
                    "expected_answer_type": query.expected_answer_type,
                },
                "message": query.question,
                "metadata": {
                    "interaction_id": query.interaction_id,
                    "context_summary": dict(query.context_summary),
                    "allowed_response_schema": dict(query.allowed_response_schema),
                    "query_metadata": dict(query.metadata),
                },
            }
        )
        events.append(
            {
                "event_id": f"evt_user_reply_{turn_index:02d}",
                "timestamp": utc_now_iso(),
                "step_id": query.context_summary.get("step_id"),
                "event_type": EventType.USER_REPLY.value,
                "actor": "user_simulator",
                "tool_id": None,
                "input_ref": None,
                "tool_args": None,
                "output": dict(reply.payload),
                "message": reply.raw_text,
                "metadata": {
                    "interaction_id": reply.interaction_id,
                    "accepted": bool(reply.accepted),
                    "reply_metadata": dict(reply.metadata),
                },
            }
        )
        metrics["user_queries"] = int(metrics.get("user_queries", 0)) + 1

    @staticmethod
    def _merge_trace_payloads(base_trace: Dict[str, Any], new_trace: Dict[str, Any]) -> Dict[str, Any]:
        if not base_trace:
            return new_trace
        if not new_trace:
            return base_trace

        merged = dict(base_trace)
        merged["metadata"] = dict(new_trace.get("metadata", base_trace.get("metadata", {})))
        merged["state_snapshots"] = list(base_trace.get("state_snapshots", [])) + list(new_trace.get("state_snapshots", []))
        merged["events"] = list(base_trace.get("events", [])) + list(new_trace.get("events", []))
        merged_metrics = dict(base_trace.get("metrics", {}))
        new_metrics = dict(new_trace.get("metrics", {}))
        for key in ("tool_calls", "repair_actions", "user_queries"):
            merged_metrics[key] = int(base_trace.get("metrics", {}).get(key, 0)) + int(new_metrics.get(key, 0))
        for key in ("total_steps", "success", "token_cost", "latency_ms"):
            if key in new_metrics:
                merged_metrics[key] = new_metrics[key]
        merged["metrics"] = merged_metrics
        return merged

    def _finalize_combined_trace(
        self,
        trace_payload: Dict[str, Any],
        *,
        output_path: str,
        success: bool,
        stop_reason: str,
    ) -> None:
        events = trace_payload.setdefault("events", [])
        events.append(
            {
                "event_id": f"evt_stop_{len(events) + 1:03d}",
                "timestamp": utc_now_iso(),
                "step_id": None,
                "event_type": EventType.STOP.value,
                "actor": "interaction_shell",
                "tool_id": None,
                "input_ref": None,
                "tool_args": None,
                "output": {
                    "status": "success" if success else "failed",
                    "reason": stop_reason,
                },
                "message": None,
                "metadata": {},
            }
        )
        metrics = trace_payload.setdefault("metrics", {})
        metrics["success"] = success
        self._write_trace(output_path, trace_payload)
