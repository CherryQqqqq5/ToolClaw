"""Adapters that normalize external benchmark formats into ToolClaw requests and scores."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Protocol

from toolclaw.planner.htgp import PlanningRequest
from toolclaw.schemas.workflow import TaskConstraints, TaskSpec, ToolSpec, Workflow, WorkflowContext


@dataclass
class BenchmarkSample:
    sample_id: str
    raw_payload: Dict[str, Any]
    scenario: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkTraceScore:
    benchmark: str
    sample_id: str
    success: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class BenchmarkAdapter(Protocol):
    benchmark_name: str

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        ...

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        ...

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        ...

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        ...


@dataclass
class BFCLAdapter:
    benchmark_name: str = "bfcl"

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        _ = source
        return []

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        raise NotImplementedError("Implement BFCL dataset mapping here.")

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        _ = trace_payload
        return BenchmarkTraceScore(benchmark=self.benchmark_name, sample_id=sample.sample_id, success=False)


@dataclass
class TauBenchAdapter:
    benchmark_name: str = "tau_bench"
    default_target_dir: str = "outputs/tau_bench/reports"

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"tau-bench source not found: {path}")

        samples: List[BenchmarkSample] = []
        if path.suffix == ".jsonl":
            lines = path.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                samples.append(self._make_sample(raw, idx))
            return samples

        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for idx, raw in enumerate(payload, start=1):
                samples.append(self._make_sample(raw, idx))
            return samples
        if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
            for idx, raw in enumerate(payload["samples"], start=1):
                samples.append(self._make_sample(raw, idx))
            return samples

        raise ValueError("tau-bench source must be JSON list, JSON object with 'samples', or JSONL")

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        eval_task = self.to_eval_task(sample)
        demo = Workflow.demo()
        task = TaskSpec(
            task_id=str(eval_task["task_id"]),
            user_goal=str(eval_task["query"]),
            success_criteria=list(sample.raw_payload.get("success_criteria", demo.task.success_criteria)),
            constraints=self._build_constraints(sample),
        )
        context = WorkflowContext(
            environment=demo.context.environment,
            candidate_tools=self._build_candidate_tools(sample),
        )
        return PlanningRequest(task=task, context=context, policy=demo.policy)

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        query = self._extract_query(sample.raw_payload)
        task_id = sample.sample_id
        target_path = sample.raw_payload.get("target_path") or f"{self.default_target_dir}/{task_id}.txt"
        task: Dict[str, Any] = {
            "task_id": task_id,
            "scenario": sample.scenario,
            "query": query,
            "target_path": target_path,
        }
        if "simulated_policy" in sample.raw_payload:
            task["simulated_policy"] = dict(sample.raw_payload["simulated_policy"])
        if "backup_tool_map" in sample.raw_payload:
            task["backup_tool_map"] = dict(sample.raw_payload["backup_tool_map"])
        if "candidate_tools" in sample.raw_payload:
            task["candidate_tools"] = list(sample.raw_payload["candidate_tools"])
        if "constraints" in sample.raw_payload:
            task["constraints"] = dict(sample.raw_payload["constraints"])
        if "metadata" in sample.raw_payload:
            task["metadata"] = dict(sample.raw_payload["metadata"])
        return task

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        success = bool(trace_payload.get("metrics", {}).get("success"))
        events = trace_payload.get("events", [])
        repairs = int(trace_payload.get("metrics", {}).get("repair_actions", 0))
        tool_calls = int(trace_payload.get("metrics", {}).get("tool_calls", 0))
        stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
        stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"
        approval_events = sum(1 for event in events if event.get("event_type") in {"approval_request", "approval_response"})
        interactive_events = sum(1 for event in events if event.get("event_type") in {"user_query", "user_reply"})
        repair_prompt_events = sum(
            1
            for event in events
            if event.get("event_type") == "repair_triggered"
            and isinstance(event.get("output"), dict)
            and event["output"].get("repair_type") in {"ask_user", "request_approval"}
        )
        interaction_events = approval_events + interactive_events + repair_prompt_events

        raw_constraints = sample.raw_payload.get("constraints", {})
        required_approval = bool(raw_constraints.get("requires_user_approval")) or bool(
            sample.raw_payload.get("metadata", {}).get("requires_approval", False)
        )
        approval_score = 1.0
        if required_approval:
            if approval_events > 0 or "approval" in str(stop_reason):
                approval_score = 1.0
            elif success:
                approval_score = 0.0
            else:
                approval_score = 0.5

        forbidden_actions = raw_constraints.get("forbidden_actions", [])
        forbidden_violation = False
        if isinstance(forbidden_actions, list):
            for event in events:
                if event.get("event_type") != "tool_call":
                    continue
                tool_id = str(event.get("tool_id") or "")
                if any(str(forbidden).lower() in tool_id.lower() for forbidden in forbidden_actions):
                    forbidden_violation = True
                    break
        forbidden_score = 0.0 if forbidden_violation else 1.0

        scenario = str(sample.scenario).lower()
        expected_interaction = required_approval or scenario in {
            "environment_failure",
            "interaction_failure",
            "policy_failure",
            "dual_control",
        } or "simulated_policy" in sample.raw_payload

        if expected_interaction:
            if interaction_events == 0 and not success:
                interaction_quality = 0.0
            elif success:
                interaction_quality = max(0.0, 1.0 - 0.1 * max(interaction_events - 2, 0))
            else:
                interaction_quality = max(0.0, 0.5 - 0.1 * max(interaction_events - 2, 0))
        else:
            interaction_quality = 1.0 if interaction_events == 0 else max(0.0, 0.7 - 0.1 * max(interaction_events - 1, 0))

        repair_efficiency = 1.0 if repairs == 0 else max(0.0, 1.0 - 0.2 * repairs)
        rule_following = (approval_score + forbidden_score) / 2.0
        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=success,
            metrics={
                "rule_following": rule_following,
                "tool_efficiency": max(0.0, 1.0 - 0.1 * max(tool_calls - 1, 0)),
                "repair_overhead": float(repairs),
                "interaction_events": float(interaction_events),
                "interaction_quality": interaction_quality,
                "approval_following": approval_score,
                "forbidden_action_following": forbidden_score,
                "repair_efficiency": repair_efficiency,
            },
            diagnostics={
                "scenario": sample.scenario,
                "stop_reason": stop_reason,
                "tool_calls": tool_calls,
                "repair_actions": repairs,
                "required_approval": required_approval,
                "expected_interaction": expected_interaction,
                "interaction_events": interaction_events,
                "forbidden_violation": forbidden_violation,
            },
        )

    def _make_sample(self, raw: Dict[str, Any], idx: int) -> BenchmarkSample:
        sample_id = str(
            raw.get("sample_id")
            or raw.get("task_id")
            or raw.get("id")
            or f"tau_sample_{idx:05d}"
        )
        scenario = str(raw.get("scenario") or raw.get("label") or "success")
        return BenchmarkSample(sample_id=sample_id, raw_payload=raw, scenario=scenario, metadata=dict(raw.get("metadata", {})))

    @staticmethod
    def _extract_query(raw: Dict[str, Any]) -> str:
        return str(
            raw.get("query")
            or raw.get("user_goal")
            or raw.get("instruction")
            or raw.get("prompt")
            or "retrieve and write report"
        )

    @staticmethod
    def _build_constraints(sample: BenchmarkSample) -> TaskConstraints:
        raw_constraints = sample.raw_payload.get("constraints", {})
        if not isinstance(raw_constraints, dict):
            return TaskConstraints()
        task_constraints = TaskConstraints()
        if raw_constraints.get("budget_limit") is not None:
            task_constraints.budget_limit = float(raw_constraints["budget_limit"])
        if raw_constraints.get("time_limit") is not None:
            task_constraints.time_limit = float(raw_constraints["time_limit"])
        if raw_constraints.get("requires_user_approval") is not None:
            task_constraints.requires_user_approval = bool(raw_constraints["requires_user_approval"])
        if raw_constraints.get("forbidden_actions"):
            task_constraints.forbidden_actions = list(raw_constraints["forbidden_actions"])
        risk_level = raw_constraints.get("risk_level")
        if risk_level in {"low", "medium", "high"}:
            task_constraints.risk_level = task_constraints.risk_level.__class__(risk_level)
        return task_constraints

    @staticmethod
    def _build_candidate_tools(sample: BenchmarkSample) -> List[ToolSpec]:
        raw_tools = sample.raw_payload.get("candidate_tools")
        if isinstance(raw_tools, list) and raw_tools:
            tools = []
            for idx, raw_tool in enumerate(raw_tools, start=1):
                if isinstance(raw_tool, str):
                    tools.append(ToolSpec(tool_id=raw_tool, description=raw_tool))
                    continue
                if isinstance(raw_tool, dict):
                    tools.append(
                        ToolSpec(
                            tool_id=str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                            description=str(raw_tool.get("description") or raw_tool.get("tool_id") or raw_tool.get("name") or "tool"),
                            metadata={k: v for k, v in raw_tool.items() if k not in {"tool_id", "name", "description"}},
                        )
                    )
            if tools:
                return tools
        return [
            ToolSpec(tool_id="search_tool", description="Search information from a source."),
            ToolSpec(tool_id="write_tool", description="Write output artifact."),
            ToolSpec(tool_id="backup_write_tool", description="Fallback write output artifact."),
        ]


@dataclass
class Tau2BenchAdapter:
    benchmark_name: str = "tau2_bench"

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        _ = source
        return []

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        raise NotImplementedError("Implement tau2-bench request mapping here.")

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        success = bool(trace_payload.get("metrics", {}).get("success"))
        interaction_events = sum(1 for event in trace_payload.get("events", []) if event.get("event_type") in {"user_query", "approval_request"})
        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=success,
            metrics={"interactive_correction": float(interaction_events)},
        )


@dataclass
class MCPRadarAdapter:
    benchmark_name: str = "mcp_radar"

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        _ = source
        return []

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        raise NotImplementedError("Implement MCP-RADAR request mapping here.")

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        metrics = trace_payload.get("metrics", {})
        tool_calls = max(int(metrics.get("tool_calls", 0)), 1)
        repairs = int(metrics.get("repair_actions", 0))
        success = bool(metrics.get("success"))
        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=success,
            metrics={
                "correctness": 1.0 if success else 0.0,
                "tool_efficiency": max(0.0, 1.0 - 0.1 * (tool_calls - 1)),
                "parameter_accuracy": max(0.0, 1.0 - 0.2 * repairs),
            },
        )
