"""Interactive repair loop that turns blocked execution into a correction dialogue."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional

from toolclaw.execution.executor import ExecutionOutcome
from toolclaw.interaction.query_policy import QueryPolicy
from toolclaw.interaction.repair_updater import AnswerPatchCompiler, RepairUpdater, UserReply
from toolclaw.interaction.reply_provider import ReplyProvider
from toolclaw.interaction.uncertainty_detector import UncertaintyDetector
from toolclaw.interaction.user_simulator import SimulatedPolicy, UserSimulator
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest
from toolclaw.schemas.trace import EventType, utc_now_iso


@dataclass
class InteractionLoopConfig:
    max_turns: int = 3
    reply_timeout_s: float = 45.0
    simulator_policy: SimulatedPolicy = field(default_factory=SimulatedPolicy)


class InteractionShell:
    """Drive blocked execution until completion or policy-compliant termination."""

    def __init__(
        self,
        runtime: ToolClawRuntime,
        repair_updater: Optional[RepairUpdater] = None,
        config: Optional[InteractionLoopConfig] = None,
        uncertainty_detector: Optional[UncertaintyDetector] = None,
        query_policy: Optional[QueryPolicy] = None,
        reply_provider: Optional[ReplyProvider] = None,
    ) -> None:
        self.runtime = runtime
        self.repair_updater = repair_updater or runtime.repair_updater
        self.answer_patch_compiler = (
            self.repair_updater
            if isinstance(self.repair_updater, AnswerPatchCompiler)
            else AnswerPatchCompiler()
        )
        self.config = config or InteractionLoopConfig()
        self.reply_provider = reply_provider or UserSimulator(self.config.simulator_policy)
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
        combined_trace.setdefault("metadata", {})
        combined_trace["metadata"].setdefault(
            "interaction_modules",
            ["uncertainty_detector", "query_policy", "answer_patch_compiler"],
        )
        interaction_stats = {
            "asked": 0,
            "necessary": 0,
            "asked_and_necessary": 0,
            "unnecessary": 0,
            "patch_attempts": 0,
            "patch_successes": 0,
            "post_answer_retry_count": 0,
        }
        turns = 0
        failure_counts: Dict[str, int] = {}
        max_turns = self._max_turns(outcome)

        while outcome.blocked and outcome.pending_interaction and turns < max_turns:
            turns += 1
            repair = outcome.pending_interaction.repair
            failure_signature = self._failure_signature(outcome)
            # region agent log
            self._debug_log(
                "H5",
                "src/toolclaw/interaction/irc.py:run:loop",
                "interaction turn start",
                {
                    "run_id": run_id,
                    "turn": turns,
                    "failure_signature": failure_signature,
                    "repair_type": repair.repair_type.value,
                },
            )
            # endregion
            repeat_count = failure_counts.get(failure_signature, 0)
            failure_counts[failure_signature] = repeat_count + 1
            report = self.uncertainty_detector.analyze_failure(
                workflow=outcome.workflow,
                repair=repair,
                state_values=outcome.final_state,
            )
            query_plan = self.query_policy.decide_query(report)
            necessary_question = self._question_is_necessary(report)
            interaction_stats["necessary"] += 1 if necessary_question else 0
            if query_plan.ask:
                interaction_stats["asked"] += 1
                interaction_stats["asked_and_necessary"] += 1 if necessary_question else 0
                interaction_stats["unnecessary"] += 0 if necessary_question else 1
            query = self.answer_patch_compiler.build_query(
                workflow=outcome.workflow,
                repair=repair,
                state_values=outcome.final_state,
            )
            if query_plan.ask and query_plan.question_text:
                query.question = query_plan.question_text
                query.expected_answer_type = query_plan.question_type
                query.allowed_response_schema = query_plan.response_schema
                query.metadata["uncertainty"] = report.primary_label
                query.metadata["patch_targets"] = dict(query_plan.patch_targets)
                query.metadata["query_policy"] = {
                    "question_type": query_plan.question_type,
                    "target_scope": query_plan.target_scope,
                    "urgency": query_plan.urgency,
                }
            self._escalate_query(
                query=query,
                outcome=outcome,
                repeat_count=repeat_count,
                backup_tool_map=backup_tool_map or {},
            )
            auto_reply = self._repeat_failure_reply(
                query=query,
                outcome=outcome,
                repeat_count=repeat_count,
                backup_tool_map=backup_tool_map or {},
            )
            if auto_reply is not None:
                reply = auto_reply
            elif repeat_count > 0 and query.metadata.get("repeat_failure_action") == "abort":
                self._finalize_combined_trace(
                    combined_trace,
                    output_path=output_path,
                    success=False,
                    stop_reason="repeat_failure_abort",
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
                    metadata={"stopped_reason": "repeat_failure_abort"},
                )
            else:
                reply = self._reply_with_timeout(query)
            self._append_interaction_events(combined_trace, query=query, reply=reply, turn_index=turns)
            self._increment_recovery_budget(combined_trace, outcome, turns)
            handled_stop = self._handled_non_accept_reply(combined_trace, output_path, outcome, reply)
            if handled_stop is not None:
                self._finalize_interaction_metrics(combined_trace, interaction_stats)
                return handled_stop
            if not self.answer_patch_compiler.validate_reply(query, reply):
                self._finalize_interaction_metrics(combined_trace, interaction_stats)
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

            interaction_stats["patch_attempts"] += 1
            resumed_state = dict(outcome.final_state)
            resumed_state["__user_turns__"] = turns
            budget_violation = self._interaction_budget_violation(outcome, resumed_state, turns)
            if budget_violation is not None:
                combined_trace.setdefault("metrics", {})["budget_violation"] = True
                combined_trace["metrics"]["budget_violation_reason"] = budget_violation
                self._finalize_interaction_metrics(combined_trace, interaction_stats)
                self._finalize_combined_trace(
                    combined_trace,
                    output_path=output_path,
                    success=False,
                    stop_reason=budget_violation,
                )
                return ExecutionOutcome(
                    run_id=outcome.run_id,
                    workflow=outcome.workflow,
                    success=False,
                    blocked=False,
                    pending_interaction=None,
                    final_state=resumed_state,
                    trace_path=outcome.trace_path,
                    last_error_id=outcome.last_error_id,
                    metadata={"stopped_reason": budget_violation},
                )

            outcome = self.runtime.resume_task(
                workflow=outcome.workflow,
                repair=repair,
                reply=reply,
                run_id=run_id,
                output_path=output_path,
                backup_tool_map=backup_tool_map,
                state_values=resumed_state,
                compile_on_success=compile_on_success,
            )
            next_signature = self._failure_signature(outcome)
            if outcome.success or not outcome.blocked or next_signature != failure_signature:
                interaction_stats["patch_successes"] += 1
            else:
                interaction_stats["post_answer_retry_count"] += 1
            combined_trace = self._merge_trace_payloads(combined_trace, self._load_trace(output_path))
            self._finalize_interaction_metrics(combined_trace, interaction_stats)
            self._write_trace(output_path, combined_trace)

        if outcome.blocked:
            stop_reason = "interaction_turn_limit"
            if outcome.workflow.task.constraints.max_user_turns is not None and turns >= int(outcome.workflow.task.constraints.max_user_turns):
                stop_reason = "max_user_turns_exceeded"
                combined_trace.setdefault("metrics", {})["budget_violation"] = True
                combined_trace["metrics"]["budget_violation_reason"] = stop_reason
            self._finalize_interaction_metrics(combined_trace, interaction_stats)
            self._finalize_combined_trace(
                combined_trace,
                output_path=output_path,
                success=False,
                stop_reason=stop_reason,
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
                metadata={"stopped_reason": stop_reason},
            )

        self._finalize_interaction_metrics(combined_trace, interaction_stats)
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
                    "uncertainty_cause": query.metadata.get("uncertainty"),
                    "query_policy_decision": dict(query.metadata.get("query_policy", {})),
                    "patch_targets": dict(query.metadata.get("patch_targets", {})),
                    "primary_failtax": query.metadata.get("primary_failtax"),
                    "budget_profile": dict(query.metadata.get("budget_profile", {}))
                    if isinstance(query.metadata.get("budget_profile"), dict)
                    else query.metadata.get("budget_profile"),
                },
            }
        )
        reply_status = str(getattr(reply, "status", "accept"))
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
                    "status": reply_status,
                    "reply_class": reply_status,
                    "policy_outcome": (
                        "safe_abort_success"
                        if reply_status == "deny"
                        else "policy_compliant_stop"
                        if reply_status == "abstain"
                        else "invalid_user_reply"
                        if reply_status == "malformed"
                        else "continue"
                    ),
                    "patch_targets": dict(reply.metadata.get("patch_targets", {})),
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

    @staticmethod
    def _failure_signature(outcome: ExecutionOutcome) -> str:
        if outcome.pending_interaction is None:
            return "completed"
        repair = outcome.pending_interaction.repair
        return "::".join(
            [
                outcome.pending_interaction.step_id or "unknown_step",
                repair.repair_type.value,
                str(repair.metadata.get("mapped_from_error_category") or "unknown_error"),
                str(repair.metadata.get("failed_tool_id") or "unknown_tool"),
            ]
        )

    @staticmethod
    def _escalate_query(
        *,
        query: Any,
        outcome: ExecutionOutcome,
        repeat_count: int,
        backup_tool_map: Dict[str, str],
    ) -> None:
        if outcome.pending_interaction is None:
            return
        repair = outcome.pending_interaction.repair
        step = outcome.workflow.get_step(outcome.pending_interaction.step_id)
        uncertainty = str(query.metadata.get("uncertainty") or "")
        query.metadata["repeat_failure_count"] = repeat_count
        query.metadata["escalation_level"] = repeat_count
        if repair.metadata.get("mapped_from_error_category") == "environment_failure":
            query.metadata["clear_failure_flag_recommended"] = True
        if repeat_count <= 0:
            return

        query.metadata["strategy_upgrade"] = "repeat_failure_escalation"
        query.expected_answer_type = "escalated_patch"
        query.question = (
            f"{query.question} This is a repeated failure. "
            "Prefer an alternate tool, a fallback execution path, or an explicit input patch instead of retrying unchanged."
        )
        if step is not None:
            backup_tool_id = backup_tool_map.get(step.tool_id or "")
            if backup_tool_id and uncertainty in {"environment_unavailable", "tool_mismatch"}:
                query.metadata["recommended_backup_tool"] = backup_tool_id
                query.metadata["backup_tool_id"] = backup_tool_id
                query.allowed_response_schema.setdefault("properties", {})
                query.allowed_response_schema["properties"]["use_backup_tool"] = {"type": "boolean"}
                query.metadata["repeat_failure_action"] = "force_backup_tool"
                return
        if uncertainty == "branch_disambiguation":
            query.metadata["repeat_failure_action"] = "abort"
            query.question = (
                f"{query.question} The branch choice is still unresolved. "
                "A deterministic abort is safer than retrying the same ambiguous branch."
            )
            return
        query.metadata["repeat_failure_action"] = "abort"

    @staticmethod
    def _repeat_failure_reply(
        *,
        query: Any,
        outcome: ExecutionOutcome,
        repeat_count: int,
        backup_tool_map: Dict[str, str],
    ) -> Any:
        if repeat_count <= 0 or outcome.pending_interaction is None:
            return None
        if query.metadata.get("repeat_failure_action") != "force_backup_tool":
            return None
        step = outcome.workflow.get_step(outcome.pending_interaction.step_id)
        backup_tool_id = str(query.metadata.get("backup_tool_id") or "")
        if not backup_tool_id and step is not None:
            backup_tool_id = str(backup_tool_map.get(step.tool_id or "") or "")
        if not backup_tool_id:
            return None
        from toolclaw.interaction.repair_updater import UserReply

        return UserReply(
            interaction_id=query.interaction_id,
            payload={"use_backup_tool": True, "clear_failure_flag": True},
            raw_text="auto-escalated backup tool switch",
            accepted=True,
            metadata={
                "patch_targets": dict(query.metadata.get("patch_targets", {})),
                "escalation_level": int(query.metadata.get("escalation_level", 0)),
                "auto_strategy": "repeat_failure_force_backup_tool",
            },
        )

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

    @staticmethod
    def _question_is_necessary(report: UncertaintyReport) -> bool:
        return report.primary_label in {
            "policy_approval",
            "missing_asset",
            "stale_state",
            "constraint_conflict",
            "branch_disambiguation",
            "execution_guidance",
            "tool_mismatch",
            "environment_unavailable",
        }

    def _max_turns(self, outcome: ExecutionOutcome) -> int:
        limit = self.config.max_turns
        workflow_limit = outcome.workflow.task.constraints.max_user_turns
        if workflow_limit is not None:
            limit = min(limit, int(workflow_limit))
        return max(limit, 0)

    @staticmethod
    def _increment_recovery_budget(trace_payload: Dict[str, Any], outcome: ExecutionOutcome, turns: int) -> None:
        metrics = trace_payload.setdefault("metrics", {})
        budget_used = float(metrics.get("recovery_budget_used", 0.0) or 0.0)
        metrics["recovery_budget_used"] = max(budget_used, float(outcome.final_state.get("__recovery_budget_spent__", 0.0)))
        metrics["user_queries"] = max(int(metrics.get("user_queries", 0)), turns)

    @staticmethod
    def _interaction_budget_violation(
        outcome: ExecutionOutcome,
        resumed_state: Dict[str, Any],
        turns: int,
    ) -> Optional[str]:
        constraints = outcome.workflow.task.constraints
        if constraints.max_user_turns is not None and turns > int(constraints.max_user_turns):
            return "max_user_turns_exceeded"
        if constraints.max_recovery_budget is not None and float(resumed_state.get("__recovery_budget_spent__", 0.0)) > float(constraints.max_recovery_budget):
            return "max_recovery_budget_exceeded"
        return None

    def _handled_non_accept_reply(
        self,
        trace_payload: Dict[str, Any],
        output_path: str,
        outcome: ExecutionOutcome,
        reply: Any,
    ) -> Optional[ExecutionOutcome]:
        status = str(getattr(reply, "status", "accept") or "accept")
        if status == "deny":
            trace_payload.setdefault("metrics", {})["safe_abort"] = True
            trace_payload["metrics"]["policy_compliance_success"] = True
            self._finalize_combined_trace(
                trace_payload,
                output_path=output_path,
                success=True,
                stop_reason="safe_abort_success",
            )
            return ExecutionOutcome(
                run_id=outcome.run_id,
                workflow=outcome.workflow,
                success=True,
                blocked=False,
                pending_interaction=None,
                final_state=outcome.final_state,
                trace_path=outcome.trace_path,
                last_error_id=outcome.last_error_id,
                metadata={"stopped_reason": "safe_abort_success"},
            )
        if status == "abstain":
            trace_payload.setdefault("metrics", {})["policy_compliance_success"] = True
            self._finalize_combined_trace(
                trace_payload,
                output_path=output_path,
                success=False,
                stop_reason="policy_compliant_stop",
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
                metadata={"stopped_reason": "policy_compliant_stop"},
            )
        return None

    @staticmethod
    def _finalize_interaction_metrics(trace_payload: Dict[str, Any], interaction_stats: Dict[str, int]) -> None:
        metrics = trace_payload.setdefault("metrics", {})
        asked = int(interaction_stats.get("asked", 0))
        necessary = int(interaction_stats.get("necessary", 0))
        asked_and_necessary = int(interaction_stats.get("asked_and_necessary", 0))
        unnecessary = int(interaction_stats.get("unnecessary", 0))
        patch_attempts = int(interaction_stats.get("patch_attempts", 0))
        patch_successes = int(interaction_stats.get("patch_successes", 0))
        metrics["clarification_precision"] = (asked_and_necessary / asked) if asked else 0.0
        metrics["clarification_recall"] = (asked_and_necessary / necessary) if necessary else 0.0
        metrics["unnecessary_question_rate"] = (unnecessary / asked) if asked else 0.0
        metrics["patch_success_rate"] = (patch_successes / patch_attempts) if patch_attempts else 0.0
        metrics["post_answer_retry_count"] = int(interaction_stats.get("post_answer_retry_count", 0))

    def _reply_with_timeout(self, request: Any) -> Any:
        timeout_s = max(float(self.config.reply_timeout_s or 0.0), 0.0)
        if timeout_s <= 0.0:
            return self.reply_provider.reply(request)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.reply_provider.reply, request)
            try:
                return future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                future.cancel()
                # region agent log
                self._debug_log(
                    "H1",
                    "src/toolclaw/interaction/irc.py:_reply_with_timeout:timeout",
                    "reply provider timeout",
                    {
                        "timeout_s": timeout_s,
                        "expected_answer_type": str(request.expected_answer_type or ""),
                    },
                )
                # endregion
                return self._timeout_reply(request, timeout_s)

    @staticmethod
    def _timeout_reply(request: Any, timeout_s: float) -> Any:
        # Timeout is treated as abstain so the loop exits safely
        # instead of blocking the whole benchmark run.
        return UserReply(
            interaction_id=request.interaction_id,
            payload={"abstain": True, "reason": "reply_timeout"},
            raw_text=f"interaction_reply_timeout:{timeout_s}s",
            accepted=False,
            status="abstain",
            metadata={
                "patch_targets": dict(request.metadata.get("patch_targets", {})),
                "reply_timeout_s": timeout_s,
            },
        )

    @staticmethod
    def _debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
        # region agent log
        try:
            payload = {
                "sessionId": "4b188d",
                "runId": os.environ.get("TOOLCLAW_DEBUG_RUN_ID", "interaction_shell"),
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }
            with open("/Users/cherry/Documents/ToolClaw/.cursor/debug-4b188d.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        except Exception:
            pass
        # endregion
