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
    default_target_dir: str = "outputs/tau2_bench/reports"

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"tau2-bench source not found: {path}")

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

        raise ValueError("tau2-bench source must be JSON list, JSON object with 'samples', or JSONL")

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        demo = Workflow.demo()
        task = TaskSpec(
            task_id=sample.sample_id,
            user_goal=self._extract_query(sample.raw_payload),
            success_criteria=list(
                sample.raw_payload.get(
                    "success_criteria",
                    [
                        "interaction repair path resolves missing information or approval",
                        "final task completes after closed-loop correction",
                    ],
                )
            ),
            constraints=self._build_constraints(sample.raw_payload),
        )
        context = WorkflowContext(
            environment=demo.context.environment,
            candidate_tools=self._build_candidate_tools(sample.raw_payload),
        )
        request = PlanningRequest(task=task, context=context, policy=demo.policy)
        request.hints.user_style["benchmark"] = self.benchmark_name
        request.hints.user_style["scenario"] = sample.scenario
        request.hints.user_style["requires_interaction"] = self._expected_interaction(sample)
        request.hints.user_style["simulated_policy_mode"] = str(
            sample.raw_payload.get("simulated_policy", {}).get("mode", "cooperative")
        )
        return request

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        task: Dict[str, Any] = {
            "task_id": sample.sample_id,
            "scenario": sample.scenario,
            "query": self._extract_query(sample.raw_payload),
            "target_path": sample.raw_payload.get("target_path") or f"{self.default_target_dir}/{sample.sample_id}.txt",
            "metadata": {
                "benchmark": self.benchmark_name,
                "requires_interaction": self._expected_interaction(sample),
                "expected_user_turns": sample.raw_payload.get("expected_user_turns"),
                "expected_repairs": sample.raw_payload.get("expected_repairs"),
            },
        }
        if "simulated_policy" in sample.raw_payload:
            task["simulated_policy"] = dict(sample.raw_payload["simulated_policy"])
        if "backup_tool_map" in sample.raw_payload:
            task["backup_tool_map"] = dict(sample.raw_payload["backup_tool_map"])
        if "candidate_tools" in sample.raw_payload:
            task["candidate_tools"] = list(sample.raw_payload["candidate_tools"])
        if "constraints" in sample.raw_payload:
            task["constraints"] = dict(sample.raw_payload["constraints"])
        return task

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        trace_metrics = trace_payload.get("metrics", {})
        events = trace_payload.get("events", [])
        success = bool(trace_metrics.get("success"))
        repairs = int(trace_metrics.get("repair_actions", 0))
        tool_calls = int(trace_metrics.get("tool_calls", 0))
        stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
        stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"

        user_queries = sum(1 for event in events if event.get("event_type") == "user_query")
        user_replies = sum(1 for event in events if event.get("event_type") == "user_reply")
        approval_requests = sum(1 for event in events if event.get("event_type") == "approval_request")
        approval_responses = sum(1 for event in events if event.get("event_type") == "approval_response")
        interaction_events = user_queries + user_replies + approval_requests + approval_responses

        expected_interaction = self._expected_interaction(sample)
        expected_user_turns = self._expected_user_turns(sample)
        expected_repairs = self._expected_repairs(sample)
        approval_required = bool(sample.raw_payload.get("constraints", {}).get("requires_user_approval")) or sample.scenario in {
            "approval_required",
            "policy_failure",
            "dual_control",
        }
        approval_following = 1.0
        if approval_required:
            if approval_requests > 0 and approval_responses > 0:
                approval_following = 1.0
            elif success:
                approval_following = 0.0
            else:
                approval_following = 0.5

        if expected_interaction:
            if user_queries == 0 and approval_requests == 0 and not success:
                interaction_efficiency = 0.0
            else:
                interaction_efficiency = self._efficiency_score(
                    observed=max(user_queries + approval_requests, 1 if success else 0),
                    expected=max(expected_user_turns, 1),
                    step_penalty=0.2,
                )
        else:
            interaction_efficiency = 1.0 if interaction_events == 0 else max(0.0, 0.8 - 0.2 * interaction_events)

        repair_salvage = 1.0 if success and repairs > 0 else (0.0 if repairs > 0 else 1.0)
        repair_efficiency = self._efficiency_score(observed=max(repairs, 1), expected=max(expected_repairs, 1), step_penalty=0.25)
        if repairs == 0 and expected_repairs == 0:
            repair_efficiency = 1.0

        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=success,
            metrics={
                "interactive_correction": float(interaction_events),
                "interaction_efficiency": interaction_efficiency,
                "repair_salvage": repair_salvage,
                "repair_efficiency": repair_efficiency,
                "approval_following": approval_following,
                "tool_efficiency": max(0.0, 1.0 - 0.1 * max(tool_calls - 1, 0)),
            },
            diagnostics={
                "scenario": sample.scenario,
                "stop_reason": stop_reason,
                "tool_calls": tool_calls,
                "repair_actions": repairs,
                "user_queries": user_queries,
                "user_replies": user_replies,
                "approval_requests": approval_requests,
                "approval_responses": approval_responses,
                "expected_interaction": expected_interaction,
                "expected_user_turns": expected_user_turns,
                "expected_repairs": expected_repairs,
            },
        )

    def _make_sample(self, raw: Dict[str, Any], idx: int) -> BenchmarkSample:
        sample_id = str(
            raw.get("sample_id")
            or raw.get("task_id")
            or raw.get("name")
            or raw.get("id")
            or f"tau2_sample_{idx:05d}"
        )
        scenario = str(raw.get("scenario") or raw.get("label") or "interaction_failure")
        metadata = dict(raw.get("metadata", {}))
        metadata["expected_user_turns"] = raw.get("expected_user_turns")
        metadata["expected_repairs"] = raw.get("expected_repairs")
        return BenchmarkSample(sample_id=sample_id, raw_payload=raw, scenario=scenario, metadata=metadata)

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
    def _build_constraints(raw: Dict[str, Any]) -> TaskConstraints:
        raw_constraints = raw.get("constraints", {})
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
    def _build_candidate_tools(raw: Dict[str, Any]) -> List[ToolSpec]:
        raw_tools = raw.get("candidate_tools")
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

    @staticmethod
    def _expected_interaction(sample: BenchmarkSample) -> bool:
        scenario = str(sample.scenario).lower()
        return bool(sample.raw_payload.get("requires_interaction")) or scenario in {
            "interaction_failure",
            "environment_failure",
            "approval_required",
            "policy_failure",
            "dual_control",
            "binding_failure",
        } or "simulated_policy" in sample.raw_payload

    @staticmethod
    def _expected_user_turns(sample: BenchmarkSample) -> int:
        value = sample.raw_payload.get("expected_user_turns")
        if value is not None:
            try:
                return max(int(value), 1)
            except (TypeError, ValueError):
                pass
        return 1 if Tau2BenchAdapter._expected_interaction(sample) else 0

    @staticmethod
    def _expected_repairs(sample: BenchmarkSample) -> int:
        value = sample.raw_payload.get("expected_repairs")
        if value is not None:
            try:
                return max(int(value), 0)
            except (TypeError, ValueError):
                pass
        scenario = str(sample.scenario).lower()
        return 1 if scenario in {"binding_failure", "environment_failure", "interaction_failure", "policy_failure"} else 0

    @staticmethod
    def _efficiency_score(observed: int, expected: int, step_penalty: float) -> float:
        if observed <= max(expected, 0):
            return 1.0
        return max(0.0, 1.0 - step_penalty * (observed - max(expected, 0)))


@dataclass
class ToolSandboxAdapter:
    """Adapter for normalizing ToolSandbox scenarios into ToolClaw requests/scores."""

    benchmark_name: str = "toolsandbox"
    default_target_dir: str = "outputs/toolsandbox/reports"
    default_success_threshold: float = 0.95

    CATEGORY_ALIASES = {
        "single/multiple tool call": "multiple_tool",
        "single tool": "single_tool",
        "single tool call": "single_tool",
        "multiple tool": "multiple_tool",
        "multiple tool call": "multiple_tool",
        "multi tool": "multiple_tool",
        "single/multiple user turn": "multiple_user_turn",
        "single user turn": "single_user_turn",
        "multiple user turn": "multiple_user_turn",
        "multi user turn": "multiple_user_turn",
        "state dependency": "state_dependency",
        "canonicalization": "canonicalization",
        "insufficient information": "insufficient_information",
    }

    def load_samples(self, source: str) -> List[BenchmarkSample]:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"ToolSandbox source not found: {path}")

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

        raise ValueError("ToolSandbox source must be JSON list, JSON object with 'samples', or JSONL")

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        categories = self._extract_categories(sample.raw_payload)
        task = TaskSpec(
            task_id=sample.sample_id,
            user_goal=self._extract_query(sample.raw_payload),
            success_criteria=list(
                sample.raw_payload.get(
                    "success_criteria",
                    [
                        "critical ToolSandbox milestones are satisfied",
                        "final agent response matches the intended outcome",
                    ],
                )
            ),
            constraints=self._build_constraints(sample.raw_payload),
        )
        context = WorkflowContext(
            environment=Workflow.demo().context.environment,
            candidate_tools=self._build_candidate_tools(sample.raw_payload),
        )
        request = PlanningRequest(task=task, context=context, policy=Workflow.demo().policy)
        request.hints.user_style["benchmark"] = self.benchmark_name
        request.hints.user_style["categories"] = categories
        request.hints.user_style["requires_interaction"] = self._interaction_expected(categories)
        request.hints.user_style["milestone_count"] = len(sample.raw_payload.get("milestones", []))
        request.hints.user_style["milestones"] = list(sample.raw_payload.get("milestones", []))
        request.hints.user_style["tool_allow_list"] = self._tool_allow_list(sample.raw_payload)
        request.hints.user_style["ideal_tool_calls"] = sample.raw_payload.get("ideal_tool_calls")
        request.hints.user_style["ideal_turn_count"] = sample.raw_payload.get("ideal_turn_count")
        return request

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        categories = self._extract_categories(sample.raw_payload)
        query = self._extract_query(sample.raw_payload)
        task_id = sample.sample_id
        target_path = sample.raw_payload.get("target_path") or f"{self.default_target_dir}/{task_id}.txt"
        tool_allow_list = self._tool_allow_list(sample.raw_payload)
        milestones = list(sample.raw_payload.get("milestones", []))
        reference_result_summary = self._extract_reference_result_summary(sample.raw_payload)

        task: Dict[str, Any] = {
            "task_id": task_id,
            "scenario": str(sample.raw_payload.get("execution_scenario") or (categories[0] if categories else "toolsandbox")),
            "query": query,
            "target_path": target_path,
            "messages": list(sample.raw_payload.get("messages", [])),
            "milestones": milestones,
            "tool_allow_list": tool_allow_list,
            "ideal_turn_count": sample.raw_payload.get("ideal_turn_count"),
            "ideal_tool_calls": sample.raw_payload.get("ideal_tool_calls"),
            "reference_result_summary": reference_result_summary,
            "metadata": {
                "benchmark": self.benchmark_name,
                "toolsandbox_categories": categories,
                "tool_allow_list": tool_allow_list,
                "milestone_count": len(milestones),
                "ideal_turn_count": sample.raw_payload.get("ideal_turn_count"),
                "ideal_tool_calls": sample.raw_payload.get("ideal_tool_calls"),
                "messages": list(sample.raw_payload.get("messages", [])),
                "milestones": milestones,
                "toolsandbox_reference_result": reference_result_summary,
                "reference_result_summary_present": bool(reference_result_summary),
            },
        }
        if tool_allow_list:
            task["candidate_tools"] = tool_allow_list
        if "constraints" in sample.raw_payload:
            task["constraints"] = dict(sample.raw_payload["constraints"])
        if "simulated_policy" in sample.raw_payload:
            task["simulated_policy"] = dict(sample.raw_payload["simulated_policy"])
        return task

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        trace_metrics = trace_payload.get("metrics", {})
        trace_events = trace_payload.get("events", [])
        result_summary = self._extract_current_result_summary(trace_payload)
        if not result_summary:
            result_summary = self.build_proxy_result_summary(sample, trace_payload)
        categories = self._extract_categories(sample.raw_payload)
        similarity = self._extract_similarity(result_summary)
        success = bool(trace_metrics.get("success"))
        milestone_mapping = self._extract_milestone_mapping(result_summary)
        total_milestones = self._expected_milestone_count(sample.raw_payload, milestone_mapping)
        matched_milestones = self._matched_milestones(milestone_mapping, result_summary)
        has_explicit_milestone_signal = bool(milestone_mapping) or result_summary.get("matched_milestones") is not None
        if total_milestones > 0 and has_explicit_milestone_signal:
            milestone_coverage = matched_milestones / total_milestones
        else:
            milestone_coverage = 1.0 if success else 0.0

        tool_calls = int(trace_metrics.get("tool_calls", 0))
        user_queries = sum(1 for event in trace_events if event.get("event_type") == "user_query")
        turn_count = self._extract_turn_count(result_summary, trace_events)
        expected_turns = self._expected_turn_count(sample.raw_payload, categories)
        expected_tool_calls = self._expected_tool_calls(sample.raw_payload, categories)
        hallucination_free = self._hallucination_avoidance(sample.raw_payload, trace_events)
        reference_result_summary = self._extract_reference_result_summary(sample.raw_payload)

        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=success,
            metrics={
                "milestone_similarity": similarity if similarity is not None else (1.0 if success else 0.0),
                "milestone_coverage": milestone_coverage,
                "tool_efficiency": self._efficiency_score(tool_calls, expected_tool_calls, step_penalty=0.15),
                "turn_efficiency": self._efficiency_score(turn_count, expected_turns, step_penalty=0.2),
                "interaction_efficiency": self._interaction_efficiency(
                    success=success,
                    categories=categories,
                    user_queries=user_queries,
                    turn_count=turn_count,
                    expected_turns=expected_turns,
                ),
                "hallucination_avoidance": hallucination_free,
                "state_dependency_score": (
                    similarity if similarity is not None else (1.0 if success else 0.0)
                )
                if "state_dependency" in categories
                else 1.0,
            },
            diagnostics={
                "categories": categories,
                "primary_category": categories[0] if categories else "toolsandbox",
                "similarity": similarity,
                "matched_milestones": matched_milestones,
                "total_milestones": total_milestones,
                "turn_count": turn_count,
                "expected_turn_count": expected_turns,
                "expected_tool_calls": expected_tool_calls,
                "tool_calls": tool_calls,
                "user_queries": user_queries,
                "used_result_summary": bool(result_summary),
                "result_summary_source": str(result_summary.get("source") or result_summary.get("summary_source") or "toolclaw_proxy"),
                "reference_result_summary_available": bool(reference_result_summary),
            },
        )

    def build_proxy_result_summary(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> Dict[str, Any]:
        trace_metrics = trace_payload.get("metrics", {})
        trace_events = trace_payload.get("events", [])
        milestones = list(sample.raw_payload.get("milestones", []))
        success = bool(trace_metrics.get("success"))
        tool_results = sum(1 for event in trace_events if event.get("event_type") == "tool_result")
        user_queries = sum(1 for event in trace_events if event.get("event_type") == "user_query")
        turn_count = self._extract_turn_count({}, trace_events)
        matched_milestones = 0
        if milestones:
            progress_signals = max(tool_results, 0)
            if self._interaction_expected(self._extract_categories(sample.raw_payload)) and user_queries > 0:
                progress_signals += 1
            if success:
                matched_milestones = len(milestones)
            else:
                matched_milestones = min(len(milestones), progress_signals)
        similarity = (matched_milestones / len(milestones)) if milestones else (1.0 if success else 0.0)
        milestone_mapping: List[Any] = [idx for idx in range(matched_milestones)] + [None] * max(len(milestones) - matched_milestones, 0)
        return {
            "similarity": float(similarity),
            "milestone_mapping": milestone_mapping,
            "matched_milestones": matched_milestones,
            "turn_count": turn_count,
            "tool_calls": int(trace_metrics.get("tool_calls", 0)),
            "success": success,
            "source": "toolclaw_proxy",
            "proxy_evaluation": True,
        }

    def _make_sample(self, raw: Dict[str, Any], idx: int) -> BenchmarkSample:
        sample_id = str(
            raw.get("sample_id")
            or raw.get("name")
            or raw.get("scenario_id")
            or raw.get("task_id")
            or raw.get("id")
            or f"toolsandbox_{idx:05d}"
        )
        categories = self._extract_categories(raw)
        metadata = dict(raw.get("metadata", {}))
        metadata["toolsandbox_categories"] = categories
        metadata["tool_allow_list"] = self._tool_allow_list(raw)
        metadata["milestone_count"] = len(raw.get("milestones", []))
        scenario = categories[0] if categories else "toolsandbox"
        return BenchmarkSample(sample_id=sample_id, raw_payload=raw, scenario=scenario, metadata=metadata)

    def _extract_query(self, raw: Dict[str, Any]) -> str:
        query = raw.get("query") or raw.get("user_goal") or raw.get("instruction") or raw.get("prompt")
        if query:
            return str(query)

        messages = raw.get("messages")
        if isinstance(messages, list):
            for message in messages:
                if not isinstance(message, dict):
                    continue
                sender = str(message.get("sender") or message.get("role") or "").lower()
                recipient = str(message.get("recipient") or "").lower()
                if sender == "user" and (not recipient or recipient == "agent"):
                    content = message.get("content")
                    if content:
                        return str(content)
        return "complete ToolSandbox scenario"

    def _extract_categories(self, raw: Dict[str, Any]) -> List[str]:
        categories: List[str] = []
        raw_categories = raw.get("categories") or raw.get("category")
        if isinstance(raw_categories, list):
            for value in raw_categories:
                normalized = self._normalize_category(value)
                if normalized and normalized not in categories:
                    categories.append(normalized)
        elif isinstance(raw_categories, dict):
            for key, enabled in raw_categories.items():
                if enabled:
                    normalized = self._normalize_category(key)
                    if normalized and normalized not in categories:
                        categories.append(normalized)
        elif isinstance(raw_categories, str):
            normalized = self._normalize_category(raw_categories)
            if normalized:
                categories.append(normalized)

        if not categories:
            if bool(raw.get("requires_state_dependency")):
                categories.append("state_dependency")
            if bool(raw.get("requires_canonicalization")):
                categories.append("canonicalization")
            if bool(raw.get("insufficient_information")):
                categories.append("insufficient_information")
        return categories

    def _normalize_category(self, value: Any) -> str:
        if value is None:
            return ""
        normalized = str(value).strip().lower().replace("-", " ").replace("_", " ")
        normalized = " ".join(normalized.split())
        return self.CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))

    def _tool_allow_list(self, raw: Dict[str, Any]) -> List[str]:
        raw_tools = raw.get("tool_allow_list") or raw.get("candidate_tools") or []
        tools: List[str] = []
        if isinstance(raw_tools, list):
            for item in raw_tools:
                if isinstance(item, str):
                    tools.append(item)
                elif isinstance(item, dict):
                    tool_id = item.get("tool_id") or item.get("name")
                    if tool_id is not None:
                        tools.append(str(tool_id))
        return tools

    def _build_candidate_tools(self, raw: Dict[str, Any]) -> List[ToolSpec]:
        raw_tools = raw.get("candidate_tools")
        if isinstance(raw_tools, list) and raw_tools:
            tools: List[ToolSpec] = []
            for idx, raw_tool in enumerate(raw_tools, start=1):
                if isinstance(raw_tool, str):
                    tools.append(ToolSpec(tool_id=raw_tool, description=f"ToolSandbox tool: {raw_tool}"))
                    continue
                if isinstance(raw_tool, dict):
                    tools.append(
                        ToolSpec(
                            tool_id=str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                            description=str(
                                raw_tool.get("description")
                                or raw_tool.get("tool_id")
                                or raw_tool.get("name")
                                or "ToolSandbox tool"
                            ),
                            metadata={k: v for k, v in raw_tool.items() if k not in {"tool_id", "name", "description"}},
                        )
                    )
            if tools:
                return tools

        allow_list = self._tool_allow_list(raw)
        if allow_list:
            return [ToolSpec(tool_id=tool_id, description=f"ToolSandbox tool: {tool_id}") for tool_id in allow_list]

        return Workflow.demo().context.candidate_tools

    @staticmethod
    def _build_constraints(raw: Dict[str, Any]) -> TaskConstraints:
        raw_constraints = raw.get("constraints", {})
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
    def _extract_current_result_summary(trace_payload: Dict[str, Any]) -> Dict[str, Any]:
        for container in (
            trace_payload,
            trace_payload.get("metadata", {}),
        ):
            if isinstance(container, dict):
                summary = container.get("toolsandbox_result") or container.get("result_summary")
                if isinstance(summary, dict):
                    return summary
        return {}

    @staticmethod
    def _extract_reference_result_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        for container in (
            raw,
            raw.get("metadata", {}),
        ):
            if isinstance(container, dict):
                summary = (
                    container.get("reference_result_summary")
                    or container.get("toolsandbox_reference_result")
                    or container.get("result_summary")
                    or container.get("toolsandbox_result")
                )
                if isinstance(summary, dict):
                    return summary
        return {}

    @staticmethod
    def _extract_similarity(result_summary: Dict[str, Any]) -> Any:
        for key in ("similarity", "overall_similarity", "milestone_similarity", "score"):
            value = result_summary.get(key)
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _extract_milestone_mapping(result_summary: Dict[str, Any]) -> List[Any]:
        mapping = result_summary.get("milestone_mapping") or result_summary.get("milestone_matches") or []
        if isinstance(mapping, list):
            return mapping
        if isinstance(mapping, dict):
            ordered: List[Any] = []
            for _, value in sorted(mapping.items()):
                ordered.append(value)
            return ordered
        return []

    @staticmethod
    def _matched_milestones(mapping: List[Any], result_summary: Dict[str, Any]) -> int:
        if mapping:
            return sum(1 for item in mapping if item is not None and item != -1)
        matched = result_summary.get("matched_milestones")
        if matched is not None:
            try:
                return int(matched)
            except (TypeError, ValueError):
                return 0
        return 0

    @staticmethod
    def _expected_milestone_count(raw: Dict[str, Any], mapping: List[Any]) -> int:
        milestones = raw.get("milestones")
        if isinstance(milestones, list) and milestones:
            return len(milestones)
        if mapping:
            return len(mapping)
        metadata = raw.get("metadata", {})
        if isinstance(metadata, dict):
            total = metadata.get("milestone_count")
            if total is not None:
                try:
                    return int(total)
                except (TypeError, ValueError):
                    return 0
        return 0

    @staticmethod
    def _extract_turn_count(result_summary: Dict[str, Any], trace_events: List[Dict[str, Any]]) -> int:
        for key in ("turn_count", "conversation_turns", "num_turns"):
            value = result_summary.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    break
        agent_visible_events = {"user_query", "user_reply", "tool_call", "tool_result"}
        return sum(1 for event in trace_events if event.get("event_type") in agent_visible_events)

    def _expected_turn_count(self, raw: Dict[str, Any], categories: List[str]) -> int:
        for key in ("ideal_turn_count", "expected_turn_count"):
            value = raw.get(key)
            if value is not None:
                try:
                    return max(int(value), 1)
                except (TypeError, ValueError):
                    continue
        if "multiple_user_turn" in categories:
            return 4
        return 2

    def _expected_tool_calls(self, raw: Dict[str, Any], categories: List[str]) -> int:
        for key in ("ideal_tool_calls", "expected_tool_calls"):
            value = raw.get(key)
            if value is not None:
                try:
                    return max(int(value), 1)
                except (TypeError, ValueError):
                    continue
        if "multiple_tool" in categories or "state_dependency" in categories:
            return 2
        return 1

    @staticmethod
    def _efficiency_score(observed: int, expected: int, step_penalty: float) -> float:
        if observed <= max(expected, 1):
            return 1.0
        return max(0.0, 1.0 - step_penalty * (observed - max(expected, 1)))

    @staticmethod
    def _interaction_expected(categories: List[str]) -> bool:
        return "multiple_user_turn" in categories or "insufficient_information" in categories

    def _interaction_efficiency(
        self,
        success: bool,
        categories: List[str],
        user_queries: int,
        turn_count: int,
        expected_turns: int,
    ) -> float:
        if self._interaction_expected(categories):
            if user_queries == 0 and not success:
                return 0.0
            return self._efficiency_score(turn_count, expected_turns, step_penalty=0.15)
        if user_queries == 0:
            return 1.0
        return max(0.0, 0.8 - 0.2 * max(user_queries - 1, 0))

    def _hallucination_avoidance(self, raw: Dict[str, Any], trace_events: List[Dict[str, Any]]) -> float:
        allowed_tools = set(self._tool_allow_list(raw))
        if not allowed_tools:
            return 1.0
        for event in trace_events:
            if event.get("event_type") != "tool_call":
                continue
            tool_id = event.get("tool_id")
            if tool_id and str(tool_id) not in allowed_tools:
                return 0.0
        return 1.0


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
