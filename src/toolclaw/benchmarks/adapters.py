"""Adapters that normalize external benchmark formats into ToolClaw requests and scores."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol

from toolclaw.benchmarks.task_annotations import annotate_task_payload
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
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"bfcl source not found: {path}")

        payload_rows = list(_load_jsonlike_rows(path))
        samples: List[BenchmarkSample] = []
        for idx, raw in enumerate(payload_rows, start=1):
            sample_id = str(
                raw.get("sample_id")
                or raw.get("task_id")
                or raw.get("id")
                or f"bfcl_sample_{idx:05d}"
            )
            metadata = dict(raw.get("metadata", {})) if isinstance(raw.get("metadata"), dict) else {}
            scenario = str(raw.get("scenario") or metadata.get("bfcl_group") or "bfcl")
            samples.append(BenchmarkSample(sample_id=sample_id, raw_payload=raw, scenario=scenario, metadata=metadata))
        return samples

    def load_samples_from_tasks(self, tasks: Iterable[Dict[str, Any]]) -> List[BenchmarkSample]:
        samples: List[BenchmarkSample] = []
        for idx, task in enumerate(tasks, start=1):
            metadata = dict(task.get("metadata", {})) if isinstance(task.get("metadata"), dict) else {}
            sample_id = str(task.get("task_id") or task.get("sample_id") or f"bfcl_task_{idx:05d}")
            samples.append(
                BenchmarkSample(
                    sample_id=sample_id,
                    raw_payload={
                        "sample_id": sample_id,
                        "query": task.get("query"),
                        "candidate_tools": list(task.get("candidate_tools", [])) if isinstance(task.get("candidate_tools"), list) else [],
                        "constraints": dict(task.get("constraints", {})) if isinstance(task.get("constraints"), dict) else {},
                        "expected_call_structure": metadata.get("expected_call_structure", task.get("expected_call_structure", {})),
                        "metadata": metadata,
                    },
                    scenario=str(task.get("scenario") or metadata.get("bfcl_group") or "bfcl"),
                    metadata=metadata,
                )
            )
        return samples

    def build_request(self, sample: BenchmarkSample) -> PlanningRequest:
        eval_task = self.to_eval_task(sample)
        demo = Workflow.demo()
        task = TaskSpec(
            task_id=str(eval_task["task_id"]),
            user_goal=str(eval_task["query"]),
            success_criteria=list(
                sample.raw_payload.get(
                    "success_criteria",
                    [
                        "select the correct tool or function",
                        "produce the expected call structure",
                        "fill arguments that satisfy the benchmark schema",
                    ],
                )
            ),
            constraints=self._build_constraints(sample),
        )
        context = WorkflowContext(
            environment=demo.context.environment,
            candidate_tools=self._build_candidate_tools(sample),
        )
        return PlanningRequest(task=task, context=context, policy=demo.policy)

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        metadata = dict(sample.metadata)
        task: Dict[str, Any] = {
            "task_id": sample.sample_id,
            "scenario": str(sample.raw_payload.get("scenario") or metadata.get("bfcl_group") or "bfcl"),
            "query": self._extract_query(sample.raw_payload),
            "candidate_tools": self._normalized_candidate_tools(sample.raw_payload),
            "constraints": dict(sample.raw_payload.get("constraints", {})) if isinstance(sample.raw_payload.get("constraints"), dict) else {},
            "metadata": {
                "benchmark": self.benchmark_name,
                "bfcl_track": metadata.get("bfcl_track", sample.raw_payload.get("bfcl_track", "")),
                "bfcl_group": metadata.get("bfcl_group", sample.raw_payload.get("bfcl_group", "")),
                "bfcl_call_pattern": metadata.get("bfcl_call_pattern", sample.raw_payload.get("bfcl_call_pattern", "serial")),
                "bfcl_language": metadata.get("bfcl_language", sample.raw_payload.get("bfcl_language", "en")),
                "expected_call_structure": sample.raw_payload.get("expected_call_structure", {}),
                "official_evaluator_supported": bool(
                    metadata.get(
                        "official_evaluator_supported",
                        sample.raw_payload.get("official_evaluator_supported", False),
                    )
                ),
                **metadata,
            },
        }
        if sample.raw_payload.get("ideal_tool_calls") is not None:
            task["ideal_tool_calls"] = sample.raw_payload.get("ideal_tool_calls")
        elif sample.raw_payload.get("expected_call_structure"):
            task["ideal_tool_calls"] = len(self._flatten_expected_calls(sample.raw_payload.get("expected_call_structure", {})))
        return annotate_task_payload(task)

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        expected_calls = self._flatten_expected_calls(sample.raw_payload.get("expected_call_structure", {}))
        expected_tools = [str(call.get("tool_name") or call.get("tool_id") or "").strip() for call in expected_calls]
        actual_calls = self._extract_actual_calls(trace_payload)
        actual_tools = [str(call.get("tool_id") or "").strip() for call in actual_calls]
        expected_counter = Counter(tool for tool in expected_tools if tool)
        actual_counter = Counter(tool for tool in actual_tools if tool)
        tool_sequence_match = 1.0 if expected_tools and actual_tools == expected_tools else 0.0
        tool_selection_overlap = 1.0
        if expected_counter:
            matched = sum(min(expected_counter[tool], actual_counter.get(tool, 0)) for tool in expected_counter)
            tool_selection_overlap = matched / max(sum(expected_counter.values()), 1)
        parameter_fill_ratio = self._parameter_fill_ratio(expected_calls, actual_calls)
        candidate_tool_ids = {
            str(tool.get("tool_id") or tool.get("name") or "").strip()
            for tool in self._normalized_candidate_tools(sample.raw_payload)
        }
        policy_format_compliance = 1.0 if all(tool in candidate_tool_ids for tool in actual_tools if tool) else 0.0
        repairs = int(trace_payload.get("metrics", {}).get("repair_actions", 0) or 0)
        tool_calls = int(trace_payload.get("metrics", {}).get("tool_calls", 0) or 0)
        user_queries = int(trace_payload.get("metrics", {}).get("user_queries", 0) or 0)
        repair_applied_count = sum(1 for event in trace_payload.get("events", []) if event.get("event_type") == "repair_applied")
        missing_required_input_events = self._missing_required_input_events(trace_payload)
        missing_required_input_count = sum(len(event.get("missing_required_inputs", [])) for event in missing_required_input_events)
        required_input_total = sum(
            len(event.get("required_input_keys") or event.get("missing_required_inputs") or [])
            for event in missing_required_input_events
        )
        missing_required_arg_rate = (
            float(missing_required_input_count) / float(required_input_total)
            if required_input_total > 0
            else 0.0
        )
        preflight_interception_rate = 1.0 if missing_required_input_events else 0.0
        benchmark_success = bool(trace_payload.get("metrics", {}).get("success")) and tool_selection_overlap >= 1.0 and parameter_fill_ratio >= 1.0
        exec_verified = 1.0 if bool(trace_payload.get("metrics", {}).get("success")) and not missing_required_input_events else 0.0
        repair_success_rate = 1.0 if repairs > 0 and benchmark_success else 0.0
        repair_success_count = 1.0 if repair_applied_count > 0 and benchmark_success else 0.0
        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=benchmark_success,
            metrics={
                "binder_selection_match": tool_selection_overlap,
                "tool_sequence_match": tool_sequence_match,
                "parameter_fill_ratio": parameter_fill_ratio,
                "policy_format_compliance": policy_format_compliance,
                "repair_overhead": float(repairs),
                "missing_required_arg_rate": missing_required_arg_rate,
                "preflight_interception_rate": preflight_interception_rate,
                "repair_success_rate": repair_success_rate,
                "repair_applied_count": float(repair_applied_count),
                "repair_success_count": repair_success_count,
                "exec_verified": exec_verified,
                "avg_tool_calls": float(tool_calls),
                "avg_user_queries": float(user_queries),
            },
            diagnostics={
                "expected_tools": expected_tools,
                "actual_tools": actual_tools,
                "expected_call_count": len(expected_calls),
                "actual_call_count": len(actual_calls),
                "repair_actions": repairs,
                "repair_applied_count": repair_applied_count,
                "missing_required_input_events": missing_required_input_events,
            },
        )

    @staticmethod
    def _extract_query(raw: Dict[str, Any]) -> str:
        return str(
            raw.get("query")
            or raw.get("user_goal")
            or raw.get("instruction")
            or raw.get("prompt")
            or "complete the benchmark task"
        )

    @staticmethod
    def _normalized_candidate_tools(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_tools = raw.get("candidate_tools") or raw.get("tools") or []
        if not isinstance(raw_tools, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for idx, raw_tool in enumerate(raw_tools, start=1):
            if isinstance(raw_tool, str):
                normalized.append({"tool_id": raw_tool, "description": raw_tool})
                continue
            if isinstance(raw_tool, dict):
                parameters = raw_tool.get("parameters") or raw_tool.get("schema") or {}
                normalized.append(
                    {
                        "tool_id": str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                        "description": str(
                            raw_tool.get("description")
                            or raw_tool.get("tool_id")
                            or raw_tool.get("name")
                            or "tool"
                        ),
                        "parameters": parameters if isinstance(parameters, dict) else {},
                    }
                )
        return normalized

    def _build_candidate_tools(self, sample: BenchmarkSample) -> List[ToolSpec]:
        normalized = self._normalized_candidate_tools(sample.raw_payload)
        if normalized:
            return [
                ToolSpec(
                    tool_id=str(tool["tool_id"]),
                    description=str(tool["description"]),
                    metadata={"parameters": dict(tool.get("parameters", {}))},
                )
                for tool in normalized
            ]
        return [
            ToolSpec(tool_id="search_tool", description="Search information from a source."),
            ToolSpec(tool_id="write_tool", description="Write output artifact."),
        ]

    @staticmethod
    def _build_constraints(sample: BenchmarkSample) -> TaskConstraints:
        raw_constraints = sample.raw_payload.get("constraints", {})
        task_constraints = TaskConstraints()
        if not isinstance(raw_constraints, dict):
            return task_constraints
        if raw_constraints.get("max_tool_calls") is not None:
            task_constraints.max_tool_calls = int(raw_constraints["max_tool_calls"])
        if raw_constraints.get("max_user_turns") is not None:
            task_constraints.max_user_turns = int(raw_constraints["max_user_turns"])
        if raw_constraints.get("max_repair_attempts") is not None:
            task_constraints.max_repair_attempts = int(raw_constraints["max_repair_attempts"])
        return task_constraints

    @staticmethod
    def _flatten_expected_calls(structure: Any) -> List[Dict[str, Any]]:
        if isinstance(structure, list):
            return [call for call in structure if isinstance(call, dict)]
        if isinstance(structure, dict):
            if isinstance(structure.get("calls"), list):
                return [call for call in structure["calls"] if isinstance(call, dict)]
            groups = structure.get("groups")
            flattened: List[Dict[str, Any]] = []
            if isinstance(groups, list):
                for group in groups:
                    if not isinstance(group, list):
                        continue
                    flattened.extend(call for call in group if isinstance(call, dict))
            return flattened
        return []

    @staticmethod
    def _extract_actual_calls(trace_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        actual: List[Dict[str, Any]] = []
        for event in trace_payload.get("events", []):
            if not isinstance(event, dict) or event.get("event_type") != "tool_call":
                continue
            tool_args = event.get("tool_args")
            actual.append(
                {
                    "tool_id": str(event.get("tool_id") or ""),
                    "arguments": dict(tool_args) if isinstance(tool_args, dict) else {},
                }
            )
        return actual

    @staticmethod
    def _missing_required_input_events(trace_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for event in trace_payload.get("events", []):
            if not isinstance(event, dict) or event.get("event_type") != "preflight_check":
                continue
            output = event.get("output", {})
            metadata = event.get("metadata", {})
            if not isinstance(output, dict) or str(output.get("reason") or "") != "missing_required_input":
                continue
            missing_required_inputs = output.get("missing_required_inputs", [])
            required_input_keys = metadata.get("required_input_keys", [])
            events.append(
                {
                    "step_id": str(event.get("step_id") or ""),
                    "tool_id": str(event.get("tool_id") or ""),
                    "missing_required_inputs": [str(item) for item in missing_required_inputs if str(item)]
                    if isinstance(missing_required_inputs, list)
                    else [],
                    "required_input_keys": [str(item) for item in required_input_keys if str(item)]
                    if isinstance(required_input_keys, list)
                    else [],
                }
            )
        return events

    @staticmethod
    def _parameter_fill_ratio(expected_calls: List[Dict[str, Any]], actual_calls: List[Dict[str, Any]]) -> float:
        expected_keys = 0
        matched_keys = 0
        for expected_call, actual_call in zip(expected_calls, actual_calls):
            expected_args = expected_call.get("arguments", {})
            actual_args = actual_call.get("arguments", {})
            if not isinstance(expected_args, dict):
                continue
            expected_keys += len(expected_args)
            for key, value in expected_args.items():
                if key in actual_args and actual_args.get(key) == value:
                    matched_keys += 1
        if expected_keys == 0:
            return 1.0
        return matched_keys / expected_keys


def _load_jsonlike_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if isinstance(raw, dict):
                yield raw
        return

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        for raw in payload:
            if isinstance(raw, dict):
                yield raw
        return
    if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
        for raw in payload["samples"]:
            if isinstance(raw, dict):
                yield raw
        return
    raise ValueError(f"Unsupported JSON payload for benchmark source: {path}")


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
        return annotate_task_payload(task)

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
        if raw_constraints.get("max_tool_calls") is not None:
            task_constraints.max_tool_calls = int(raw_constraints["max_tool_calls"])
        if raw_constraints.get("max_user_turns") is not None:
            task_constraints.max_user_turns = int(raw_constraints["max_user_turns"])
        if raw_constraints.get("max_repair_attempts") is not None:
            task_constraints.max_repair_attempts = int(raw_constraints["max_repair_attempts"])
        if raw_constraints.get("max_recovery_budget") is not None:
            task_constraints.max_recovery_budget = float(raw_constraints["max_recovery_budget"])
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
        raw_budget_profile = sample.raw_payload.get("budget_profile", sample.metadata.get("budget_profile", {}))
        budget_profile = dict(raw_budget_profile) if isinstance(raw_budget_profile, dict) else {}
        request.hints.user_style["benchmark"] = self.benchmark_name
        request.hints.user_style["scenario"] = sample.scenario
        request.hints.user_style["requires_interaction"] = self._expected_interaction(sample)
        request.hints.user_style["simulated_policy_mode"] = str(
            sample.raw_payload.get("simulated_policy", {}).get("mode", "cooperative")
        )
        request.hints.user_style["primary_failtax"] = str(sample.raw_payload.get("primary_failtax") or sample.metadata.get("primary_failtax") or "recovery")
        raw_failtaxes = sample.raw_payload.get("failtaxes", sample.metadata.get("failtaxes", []))
        request.hints.user_style["failtaxes"] = list(raw_failtaxes) if isinstance(raw_failtaxes, list) else []
        request.hints.user_style["task_family"] = str(sample.raw_payload.get("task_family") or sample.metadata.get("task_family") or "t0_general")
        raw_state_slots = sample.raw_payload.get("state_slots", sample.metadata.get("state_slots", []))
        request.hints.user_style["state_slots"] = list(raw_state_slots) if isinstance(raw_state_slots, list) else []
        request.hints.user_style["budget_profile"] = budget_profile
        request.hints.user_style["gold_recovery_class"] = str(
            sample.raw_payload.get("gold_recovery_class") or sample.metadata.get("gold_recovery_class") or ""
        )
        raw_override_inputs = sample.raw_payload.get("reuse_override_inputs", {})
        request.hints.user_style["reuse_override_inputs"] = dict(raw_override_inputs) if isinstance(raw_override_inputs, dict) else {}
        return request

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        raw_metadata = dict(sample.raw_payload.get("metadata", {})) if isinstance(sample.raw_payload.get("metadata"), dict) else {}
        raw_budget_profile = sample.raw_payload.get("budget_profile", raw_metadata.get("budget_profile", {}))
        budget_profile = dict(raw_budget_profile) if isinstance(raw_budget_profile, dict) else {}
        approval_required = bool(sample.raw_payload.get("constraints", {}).get("requires_user_approval")) or sample.scenario in {
            "approval_required",
            "policy_failure",
            "dual_control",
        }
        approval_target_step = str(
            sample.raw_payload.get("failure_step")
            or raw_metadata.get("approval_target_step")
            or "step_02"
        )
        task: Dict[str, Any] = {
            "task_id": sample.sample_id,
            "scenario": sample.scenario,
            "query": self._extract_query(sample.raw_payload),
            "target_path": sample.raw_payload.get("target_path") or f"{self.default_target_dir}/{sample.sample_id}.txt",
            "primary_failtax": sample.raw_payload.get("primary_failtax"),
            "failtaxes": list(sample.raw_payload.get("failtaxes", [])) if isinstance(sample.raw_payload.get("failtaxes"), list) else [],
            "task_family": sample.raw_payload.get("task_family"),
            "state_slots": list(sample.raw_payload.get("state_slots", [])) if isinstance(sample.raw_payload.get("state_slots"), list) else [],
            "dependency_edges": list(sample.raw_payload.get("dependency_edges", [])) if isinstance(sample.raw_payload.get("dependency_edges"), list) else [],
            "expected_recovery_path": sample.raw_payload.get("gold_recovery_class"),
            "budget_profile": budget_profile,
            "metadata": {
                "benchmark": self.benchmark_name,
                "requires_interaction": self._expected_interaction(sample),
                "expected_user_turns": sample.raw_payload.get("expected_user_turns"),
                "expected_repairs": sample.raw_payload.get("expected_repairs"),
                "budget_profile": budget_profile,
                "gold_recovery_class": sample.raw_payload.get("gold_recovery_class"),
                "approval_scope": "failure_step" if approval_required else raw_metadata.get("approval_scope"),
                "approval_target_step": approval_target_step if approval_required else raw_metadata.get("approval_target_step"),
                **raw_metadata,
            },
        }
        if sample.raw_payload.get("reuse_family_id") is not None:
            task["reuse_family_id"] = sample.raw_payload.get("reuse_family_id")
        if sample.raw_payload.get("reuse_pass_index") is not None:
            task["reuse_pass_index"] = sample.raw_payload.get("reuse_pass_index")
        if "simulated_policy" in sample.raw_payload:
            task["simulated_policy"] = dict(sample.raw_payload["simulated_policy"])
        if "backup_tool_map" in sample.raw_payload:
            task["backup_tool_map"] = dict(sample.raw_payload["backup_tool_map"])
        if "candidate_tools" in sample.raw_payload:
            task["candidate_tools"] = list(sample.raw_payload["candidate_tools"])
        if "constraints" in sample.raw_payload:
            task["constraints"] = dict(sample.raw_payload["constraints"])
        if "state_failure_mode" in sample.raw_payload:
            task["state_failure_mode"] = sample.raw_payload["state_failure_mode"]
        if "wrong_target_path" in sample.raw_payload:
            task["wrong_target_path"] = sample.raw_payload["wrong_target_path"]
        if "reuse_override_inputs" in sample.raw_payload:
            task["reuse_override_inputs"] = dict(sample.raw_payload["reuse_override_inputs"])
        return annotate_task_payload(task)

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        trace_metrics = trace_payload.get("metrics", {})
        events = trace_payload.get("events", [])
        raw_success = bool(trace_metrics.get("success"))
        repairs = int(trace_metrics.get("repair_actions", 0))
        tool_calls = int(trace_metrics.get("tool_calls", 0))
        stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
        stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"

        user_queries = sum(1 for event in events if event.get("event_type") == "user_query")
        user_replies = sum(1 for event in events if event.get("event_type") == "user_reply")
        approval_requests = sum(
            1
            for event in events
            if event.get("event_type") == "approval_request"
            or (
                event.get("event_type") == "user_query"
                and "approval" in str(event.get("output", {}).get("expected_answer_type") or "").lower()
            )
        )
        approval_responses = sum(
            1
            for event in events
            if event.get("event_type") == "approval_response"
            or (
                event.get("event_type") == "user_reply"
                and isinstance(event.get("output"), dict)
                and "approved" in event.get("output", {})
            )
        )
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
            elif raw_success:
                approval_following = 0.0
            else:
                approval_following = 0.5

        if expected_interaction:
            if user_queries == 0 and approval_requests == 0 and not raw_success:
                interaction_efficiency = 0.0
            else:
                interaction_efficiency = self._efficiency_score(
                    observed=max(user_queries + approval_requests, 1 if raw_success else 0),
                    expected=max(expected_user_turns, 1),
                    step_penalty=0.2,
                )
        else:
            interaction_efficiency = 1.0 if interaction_events == 0 else max(0.0, 0.8 - 0.2 * interaction_events)

        policy_stop = stop_reason in {"safe_abort_success", "policy_compliant_stop"}
        policy_relevant = sample.scenario in {"approval_required", "policy_failure", "dual_control"}
        state_relevant = str(sample.raw_payload.get("primary_failtax") or "").lower() == "state" or sample.scenario == "state_failure"
        benchmark_success = raw_success
        if approval_required:
            benchmark_success = (raw_success and approval_following == 1.0) or policy_stop

        repair_salvage = 1.0 if benchmark_success and repairs > 0 else (0.0 if repairs > 0 else 1.0)
        repair_efficiency = self._efficiency_score(observed=max(repairs, 1), expected=max(expected_repairs, 1), step_penalty=0.25)
        if repairs == 0 and expected_repairs == 0:
            repair_efficiency = 1.0

        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=benchmark_success,
            metrics={
                "interactive_correction": float(interaction_events),
                "interaction_efficiency": interaction_efficiency,
                "repair_salvage": repair_salvage,
                "repair_efficiency": repair_efficiency,
                "approval_following": approval_following,
                "tool_efficiency": max(0.0, 1.0 - 0.1 * max(tool_calls - 1, 0)),
                "safe_abort_rate": 1.0 if stop_reason == "safe_abort_success" else 0.0,
                "policy_compliance_success_rate": 1.0 if policy_relevant and benchmark_success else 0.0,
                "state_repair_success_rate": 1.0 if state_relevant and benchmark_success and repairs > 0 else 0.0,
            },
            diagnostics={
                "scenario": sample.scenario,
                "stop_reason": stop_reason,
                "raw_success": raw_success,
                "benchmark_success": benchmark_success,
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
        metadata["primary_failtax"] = raw.get("primary_failtax") or metadata.get("primary_failtax")
        metadata["failtaxes"] = list(raw.get("failtaxes", metadata.get("failtaxes", []))) if isinstance(raw.get("failtaxes", metadata.get("failtaxes", [])), list) else []
        metadata["task_family"] = raw.get("task_family") or metadata.get("task_family")
        metadata["state_slots"] = list(raw.get("state_slots", metadata.get("state_slots", []))) if isinstance(raw.get("state_slots", metadata.get("state_slots", [])), list) else []
        metadata["budget_profile"] = dict(raw.get("budget_profile", metadata.get("budget_profile", {}))) if isinstance(raw.get("budget_profile", metadata.get("budget_profile", {})), dict) else {}
        metadata["gold_recovery_class"] = raw.get("gold_recovery_class") or metadata.get("gold_recovery_class")
        raw_override_inputs = raw.get("reuse_override_inputs", metadata.get("reuse_override_inputs", {}))
        metadata["reuse_override_inputs"] = dict(raw_override_inputs) if isinstance(raw_override_inputs, dict) else {}
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
        if raw_constraints.get("max_tool_calls") is not None:
            task_constraints.max_tool_calls = int(raw_constraints["max_tool_calls"])
        if raw_constraints.get("max_user_turns") is not None:
            task_constraints.max_user_turns = int(raw_constraints["max_user_turns"])
        if raw_constraints.get("max_repair_attempts") is not None:
            task_constraints.max_repair_attempts = int(raw_constraints["max_repair_attempts"])
        if raw_constraints.get("max_recovery_budget") is not None:
            task_constraints.max_recovery_budget = float(raw_constraints["max_recovery_budget"])
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
            "state_failure",
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
        return 1 if scenario in {"binding_failure", "environment_failure", "interaction_failure", "policy_failure", "state_failure"} else 0

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
        "planner sensitive": "planner_sensitive",
    }

    PLANNER_SENSITIVE_PROTOCOL = "planner_sensitive_v1"
    PLANNER_SENSITIVE_GOLD_KEYS = {
        "expected_capability_order",
        "expected_dependency_edges",
        "expected_tool_sequence",
        "required_state_slots_by_step",
        "forbidden_shortcuts",
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
        visible_payload = self._planner_visible_payload(sample.raw_payload)
        categories = self._extract_categories(visible_payload)
        task = TaskSpec(
            task_id=sample.sample_id,
            user_goal=self._extract_query(visible_payload),
            success_criteria=list(
                visible_payload.get(
                    "success_criteria",
                    [
                        "critical ToolSandbox milestones are satisfied",
                        "final agent response matches the intended outcome",
                    ],
                )
            ),
            constraints=self._build_constraints(visible_payload),
        )
        context = WorkflowContext(
            environment=Workflow.demo().context.environment,
            candidate_tools=self._build_candidate_tools(visible_payload),
        )
        request = PlanningRequest(task=task, context=context, policy=Workflow.demo().policy)
        request.hints.user_style["benchmark"] = self.benchmark_name
        request.hints.user_style["categories"] = categories
        request.hints.user_style["requires_interaction"] = self._interaction_expected(categories)
        if self._is_planner_sensitive_protocol(sample.raw_payload):
            request.hints.user_style["planner_sensitive_protocol"] = self.PLANNER_SENSITIVE_PROTOCOL
            request.hints.user_style["milestone_count"] = 0
            request.hints.user_style["milestones"] = []
            request.hints.user_style["tool_allow_list"] = []
            request.hints.user_style["branch_options"] = []
            request.hints.user_style["ideal_tool_calls"] = None
            request.hints.user_style["ideal_turn_count"] = visible_payload.get("ideal_turn_count")
        else:
            request.hints.user_style["milestone_count"] = len(visible_payload.get("milestones", []))
            request.hints.user_style["milestones"] = list(visible_payload.get("milestones", []))
            request.hints.user_style["tool_allow_list"] = self._tool_allow_list(visible_payload)
            request.hints.user_style["branch_options"] = list(visible_payload.get("branch_options", []))
            request.hints.user_style["ideal_tool_calls"] = visible_payload.get("ideal_tool_calls")
            request.hints.user_style["ideal_turn_count"] = visible_payload.get("ideal_turn_count")
        request.hints.user_style["tool_execution_backend"] = "semantic_mock"
        return request

    def to_eval_task(self, sample: BenchmarkSample) -> Dict[str, Any]:
        visible_payload = self._planner_visible_payload(sample.raw_payload)
        planner_sensitive = self._is_planner_sensitive_protocol(sample.raw_payload)
        categories = self._extract_categories(visible_payload)
        query = self._extract_query(visible_payload)
        task_id = sample.sample_id
        target_path = visible_payload.get("target_path") or f"{self.default_target_dir}/{task_id}.txt"
        tool_allow_list = [] if planner_sensitive else self._tool_allow_list(visible_payload)
        raw_metadata = dict(visible_payload.get("metadata", {}))
        milestones = [] if planner_sensitive else list(visible_payload.get("milestones", []))
        reference_result_summary = self._extract_reference_result_summary(visible_payload)

        task: Dict[str, Any] = {
            "task_id": task_id,
            "scenario": str(visible_payload.get("execution_scenario") or (categories[0] if categories else "toolsandbox")),
            "query": query,
            "target_path": target_path,
            "messages": list(visible_payload.get("messages", [])),
            "milestones": milestones,
            "branch_options": [] if planner_sensitive else list(visible_payload.get("branch_options", [])),
            "tool_allow_list": tool_allow_list,
            "ideal_turn_count": visible_payload.get("ideal_turn_count"),
            "ideal_tool_calls": None if planner_sensitive else visible_payload.get("ideal_tool_calls"),
            "reference_result_summary": reference_result_summary,
            "metadata": {
                **raw_metadata,
                "benchmark": self.benchmark_name,
                "toolsandbox_categories": categories,
                "tool_allow_list": tool_allow_list,
                "milestone_count": len(milestones),
                "ideal_turn_count": visible_payload.get("ideal_turn_count"),
                "ideal_tool_calls": None if planner_sensitive else visible_payload.get("ideal_tool_calls"),
                "messages": list(visible_payload.get("messages", [])),
                "milestones": milestones,
                "branch_options": [] if planner_sensitive else list(visible_payload.get("branch_options", [])),
                "toolsandbox_reference_result": reference_result_summary,
                "reference_result_summary_present": bool(reference_result_summary),
                "tool_execution_backend": "semantic_mock",
            },
        }
        if planner_sensitive:
            task["metadata"]["planner_sensitive_protocol"] = self.PLANNER_SENSITIVE_PROTOCOL
            task["metadata"]["planner_visible_keys"] = sorted(visible_payload.keys())
        task["tool_execution_backend"] = "semantic_mock"
        if "candidate_tools" in visible_payload:
            task["candidate_tools"] = list(visible_payload.get("candidate_tools", []))
        elif tool_allow_list:
            task["candidate_tools"] = list(tool_allow_list)
        if "constraints" in visible_payload:
            task["constraints"] = dict(visible_payload["constraints"])
        if "simulated_policy" in visible_payload:
            task["simulated_policy"] = dict(visible_payload["simulated_policy"])
        for passthrough_key in (
            "oracle_user_replies",
            "negative_user_replies",
            "interaction_live",
            "gold_decoded_signal",
            "expected_query_type",
            "expected_patch_targets",
            "expected_effect_scope",
            "gold_effective_patch",
            "gold_post_query_progress",
            "manual_label_status",
            "slice_type",
            "source_task_id",
        ):
            if passthrough_key in visible_payload:
                value = visible_payload[passthrough_key]
                if isinstance(value, dict):
                    task[passthrough_key] = dict(value)
                elif isinstance(value, list):
                    task[passthrough_key] = list(value)
                else:
                    task[passthrough_key] = value
        if sample.raw_payload.get("reuse_family_id") is not None:
            task["reuse_family_id"] = sample.raw_payload.get("reuse_family_id")
        if sample.raw_payload.get("reuse_pass_index") is not None:
            task["reuse_pass_index"] = sample.raw_payload.get("reuse_pass_index")
        if "backup_tool_map" in sample.raw_payload:
            task["backup_tool_map"] = dict(sample.raw_payload["backup_tool_map"])
        if "state_failure_mode" in sample.raw_payload:
            task["state_failure_mode"] = sample.raw_payload["state_failure_mode"]
        if "wrong_target_path" in sample.raw_payload:
            task["wrong_target_path"] = sample.raw_payload["wrong_target_path"]
        if "reuse_override_inputs" in sample.raw_payload:
            task["reuse_override_inputs"] = dict(sample.raw_payload["reuse_override_inputs"])
        return annotate_task_payload(task)

    def score_trace(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> BenchmarkTraceScore:
        trace_metrics = trace_payload.get("metrics", {})
        trace_events = trace_payload.get("events", [])
        current_result_summary = self._extract_current_result_summary(trace_payload)
        reference_result_summary = self._extract_reference_result_summary(sample.raw_payload)
        result_summary = current_result_summary or self.build_proxy_result_summary(sample, trace_payload)
        categories = self._extract_categories(sample.raw_payload)
        similarity = self._extract_similarity(result_summary)
        raw_trace_success = bool(trace_metrics.get("success"))
        milestone_mapping = self._extract_milestone_mapping(result_summary)
        total_milestones = self._expected_milestone_count(sample.raw_payload, milestone_mapping)
        matched_milestones = self._matched_milestones(milestone_mapping, result_summary)
        has_explicit_milestone_signal = bool(milestone_mapping) or result_summary.get("matched_milestones") is not None
        if total_milestones > 0 and has_explicit_milestone_signal:
            milestone_coverage = matched_milestones / total_milestones
        else:
            milestone_coverage = 0.0

        tool_calls = int(trace_metrics.get("tool_calls", 0))
        user_queries = sum(1 for event in trace_events if event.get("event_type") == "user_query")
        approval_requests = sum(
            1
            for event in trace_events
            if event.get("event_type") == "approval_request"
            or (
                event.get("event_type") == "user_query"
                and "approval" in str(event.get("output", {}).get("expected_answer_type") or "").lower()
            )
        )
        approval_responses = sum(
            1
            for event in trace_events
            if event.get("event_type") == "approval_response"
            or (
                event.get("event_type") == "user_reply"
                and isinstance(event.get("output"), dict)
                and "approved" in event.get("output", {})
            )
        )
        probe_user_queries = 0
        repair_user_queries = 0
        probe_user_replies = 0
        repair_user_replies = 0
        interaction_rounds = 0
        reply_usable_count = 0
        target_aligned_patch_count = 0
        effective_patch_count = 0
        post_query_progress_count = 0
        useful_interaction_round_count = 0
        for event in trace_events:
            event_type = str(event.get("event_type") or "")
            metadata = event.get("metadata", {}) or {}
            if event_type == "user_query":
                query_metadata = metadata.get("query_metadata", {}) or {}
                if bool(query_metadata.get("interaction_probe")):
                    probe_user_queries += 1
                else:
                    repair_user_queries += 1
            elif event_type == "user_reply":
                reply_metadata = metadata.get("reply_metadata", {}) or {}
                if bool(reply_metadata.get("interaction_probe")) or str(reply_metadata.get("decoded_intent_type") or "") == "interaction_probe":
                    probe_user_replies += 1
                else:
                    repair_user_replies += 1
            elif event_type == "interaction_round_outcome":
                output = event.get("output", {}) or {}
                interaction_rounds += 1
                reply_usable_count += 1 if bool(output.get("decoded_is_usable")) else 0
                target_aligned_patch_count += 1 if float(output.get("target_alignment", 0.0) or 0.0) >= 0.5 else 0
                effective_patch_count += 1 if bool(output.get("effective_patch")) else 0
                post_query_progress_count += 1 if bool(output.get("post_query_progress")) else 0
                useful_interaction_round_count += 1 if bool(output.get("interaction_round_useful")) else 0
        reply_usable_rate = (reply_usable_count / interaction_rounds) if interaction_rounds else 0.0
        target_aligned_patch_rate = (target_aligned_patch_count / interaction_rounds) if interaction_rounds else 0.0
        effective_patch_rate = (effective_patch_count / interaction_rounds) if interaction_rounds else 0.0
        post_query_progress_rate = (post_query_progress_count / interaction_rounds) if interaction_rounds else 0.0
        useful_interaction_round_rate = (useful_interaction_round_count / interaction_rounds) if interaction_rounds else 0.0
        turn_count = self._extract_turn_count(result_summary, trace_events)
        expected_turns = self._expected_turn_count(sample.raw_payload, categories)
        expected_tool_calls = self._expected_tool_calls(sample.raw_payload, categories)
        hallucination_free = self._hallucination_avoidance(sample.raw_payload, trace_events)
        result_summary_source = self._result_summary_source(result_summary)
        if result_summary_source == "toolclaw_proxy" and total_milestones == 0:
            similarity = None
        proxy_summary_success = self._proxy_summary_success(
            similarity=similarity,
            result_summary_source=result_summary_source,
            total_milestones=total_milestones,
        )
        reference_summary_success = None
        if result_summary_source != "toolclaw_proxy":
            reference_summary_success = self._reference_summary_success(result_summary)
        write_target_verified = self._write_target_verified(
            raw=sample.raw_payload,
            task_id=sample.sample_id,
            trace_events=trace_events,
        )
        execution_verified_success = self._execution_verified_success(
            raw_trace_success=raw_trace_success,
            result_summary_source=result_summary_source,
            proxy_summary_success=proxy_summary_success,
            reference_summary_success=reference_summary_success,
            matched_milestones=matched_milestones,
            total_milestones=total_milestones,
            write_target_verified=write_target_verified,
        )
        must_interact_expected = self._must_interact_expected(sample.raw_payload, categories)
        interaction_contract_satisfied = (user_queries > 0 or approval_requests > 0) if must_interact_expected else True
        repair_interaction_satisfied = (
            repair_user_queries > 0
            or repair_user_replies > 0
            or approval_requests > 0
            or approval_responses > 0
        )
        interaction_gate_blocked = must_interact_expected and not interaction_contract_satisfied
        strict_scored_success = execution_verified_success and interaction_contract_satisfied
        repair_scored_success = strict_scored_success and repair_interaction_satisfied
        milestone_similarity = float(similarity) if similarity is not None else 0.0
        expected_target_path = self._expected_write_target_path(sample.raw_payload, sample.sample_id)
        observed_target_path = self._observed_write_target_path(sample.raw_payload, trace_events)

        return BenchmarkTraceScore(
            benchmark=self.benchmark_name,
            sample_id=sample.sample_id,
            success=strict_scored_success,
            metrics={
                "milestone_similarity": milestone_similarity,
                "milestone_coverage": milestone_coverage,
                "tool_efficiency": self._efficiency_score(tool_calls, expected_tool_calls, step_penalty=0.15),
                "turn_efficiency": self._efficiency_score(turn_count, expected_turns, step_penalty=0.2),
                "interaction_efficiency": self._interaction_efficiency(
                    success=strict_scored_success,
                    categories=categories,
                    user_queries=user_queries,
                    turn_count=turn_count,
                    expected_turns=expected_turns,
                ),
                "hallucination_avoidance": hallucination_free,
                "execution_verified_success": 1.0 if execution_verified_success else 0.0,
                "strict_scored_success": 1.0 if strict_scored_success else 0.0,
                "repair_scored_success": 1.0 if repair_scored_success else 0.0,
                "raw_execution_success": 1.0 if raw_trace_success else 0.0,
                "interaction_contract_satisfied": 1.0 if interaction_contract_satisfied else 0.0,
                "mean_user_queries": float(user_queries),
                "reply_usable_rate": reply_usable_rate,
                "target_aligned_patch_rate": target_aligned_patch_rate,
                "effective_patch_rate": effective_patch_rate,
                "post_query_progress_rate": post_query_progress_rate,
                "useful_interaction_round_rate": useful_interaction_round_rate,
                "repair_interaction_satisfied": 1.0 if repair_interaction_satisfied else 0.0,
                "must_interact_query_rate": 1.0 if interaction_contract_satisfied else 0.0 if must_interact_expected else 1.0,
                "success_given_query": 1.0 if (user_queries > 0 and strict_scored_success) else 0.0,
                "success_given_repair_query": 1.0 if (repair_interaction_satisfied and repair_scored_success) else 0.0,
                "zero_query_success_count": 1.0 if (must_interact_expected and user_queries == 0 and raw_trace_success) else 0.0,
                "proxy_summary_success": 1.0 if proxy_summary_success else 0.0,
                "state_dependency_score": milestone_similarity if "state_dependency" in categories else 1.0,
                "write_target_verified": 1.0 if write_target_verified else 0.0,
            },
            diagnostics={
                "categories": categories,
                "primary_category": categories[0] if categories else "toolsandbox",
                "similarity": similarity,
                "raw_trace_success": raw_trace_success,
                "raw_execution_success": raw_trace_success,
                "execution_verified_success": execution_verified_success,
                "strict_scored_success": strict_scored_success,
                "repair_scored_success": repair_scored_success,
                "interaction_contract_satisfied": interaction_contract_satisfied,
                "repair_interaction_satisfied": repair_interaction_satisfied,
                "interaction_gate_blocked": interaction_gate_blocked,
                "must_interact_expected": must_interact_expected,
                "proxy_summary_success": proxy_summary_success,
                "matched_milestones": matched_milestones,
                "total_milestones": total_milestones,
                "turn_count": turn_count,
                "expected_turn_count": expected_turns,
                "expected_tool_calls": expected_tool_calls,
                "tool_calls": tool_calls,
                "user_queries": user_queries,
                "approval_requests": approval_requests,
                "approval_responses": approval_responses,
                "probe_user_queries": probe_user_queries,
                "repair_user_queries": repair_user_queries,
                "probe_user_replies": probe_user_replies,
                "repair_user_replies": repair_user_replies,
                "interaction_rounds": interaction_rounds,
                "reply_usable_count": reply_usable_count,
                "target_aligned_patch_count": target_aligned_patch_count,
                "effective_patch_count": effective_patch_count,
                "post_query_progress_count": post_query_progress_count,
                "useful_interaction_round_count": useful_interaction_round_count,
                "reply_usable_rate": reply_usable_rate,
                "target_aligned_patch_rate": target_aligned_patch_rate,
                "effective_patch_rate": effective_patch_rate,
                "post_query_progress_rate": post_query_progress_rate,
                "useful_interaction_round_rate": useful_interaction_round_rate,
                "milestone_signal_available": total_milestones > 0 and has_explicit_milestone_signal,
                "used_result_summary": bool(result_summary),
                "result_summary_source": result_summary_source,
                "reference_result_summary_available": bool(reference_result_summary),
                "expected_target_path": expected_target_path,
                "observed_target_path": observed_target_path,
            },
        )

    def build_proxy_result_summary(self, sample: BenchmarkSample, trace_payload: Dict[str, Any]) -> Dict[str, Any]:
        trace_metrics = trace_payload.get("metrics", {})
        trace_events = trace_payload.get("events", [])
        milestones = list(sample.raw_payload.get("milestones", []))
        success = bool(trace_metrics.get("success"))
        user_queries = sum(1 for event in trace_events if event.get("event_type") == "user_query")
        turn_count = self._extract_turn_count({}, trace_events)
        matched_milestones = 0
        if milestones:
            progress_signals = self._proxy_progress_signals(sample.raw_payload, trace_payload)
            matched_milestones = min(len(milestones), progress_signals)
        similarity = (matched_milestones / len(milestones)) if milestones else None
        milestone_mapping: List[Any] = [idx for idx in range(matched_milestones)] + [None] * max(len(milestones) - matched_milestones, 0)
        return {
            "similarity": float(similarity) if similarity is not None else None,
            "milestone_mapping": milestone_mapping,
            "matched_milestones": matched_milestones,
            "turn_count": turn_count,
            "tool_calls": int(trace_metrics.get("tool_calls", 0)),
            "success": success,
            "source": "toolclaw_proxy",
            "proxy_evaluation": True,
        }

    def _proxy_progress_signals(self, raw: Dict[str, Any], trace_payload: Dict[str, Any]) -> int:
        trace_metrics = trace_payload.get("metrics", {})
        trace_events = trace_payload.get("events", [])
        tool_ids = [
            str(event.get("tool_id") or "").strip()
            for event in trace_events
            if event.get("event_type") in {"tool_call", "tool_result"} and str(event.get("tool_id") or "").strip()
        ]
        # Count progress depth: non-write capabilities collapse to one slot each, but distinct
        # write-capable tools get separate slots so planner-sensitive tasks (e.g. archive vs primary
        # writer) can match multi-milestone traces without relying on coarse "write" alone.
        progress_keys: set[tuple[str, ...]] = set()
        for tool_id in tool_ids:
            capability = self._infer_proxy_tool_capability(raw, tool_id)
            if not capability:
                continue
            if capability == "write":
                progress_keys.add(("write", tool_id))
            else:
                progress_keys.add((capability,))
        progress_base = len(progress_keys)
        interaction_bonus = 1 if self._interaction_expected(self._extract_categories(raw)) and any(event.get("event_type") == "user_query" for event in trace_events) else 0
        repair_bonus = 1 if any(event.get("event_type") in {"repair_triggered", "repair_applied"} for event in trace_events) else 0
        success_bonus = 0
        expected_tool_calls = self._expected_tool_calls(raw, self._extract_categories(raw))
        if bool(trace_metrics.get("success")) and progress_base >= min(max(expected_tool_calls, 1), 2):
            success_bonus = 1
        return progress_base + interaction_bonus + repair_bonus + success_bonus

    @staticmethod
    def _proxy_tool_spec(raw: Dict[str, Any], tool_id: str) -> Dict[str, Any]:
        for raw_tool in raw.get("candidate_tools", []) or []:
            if isinstance(raw_tool, dict):
                candidate_id = raw_tool.get("tool_id") or raw_tool.get("name")
                if str(candidate_id or "").strip() == tool_id:
                    return raw_tool
        return {}

    def _infer_proxy_tool_capability(self, raw: Dict[str, Any], tool_id: str) -> str:
        spec = self._proxy_tool_spec(raw, tool_id)
        text = " ".join(
            [
                tool_id,
                str(spec.get("description") or ""),
                " ".join(str(item) for item in spec.get("affordances", []) if str(item)),
                " ".join(str(item) for item in spec.get("semantic_tags", []) if str(item)),
            ]
        ).lower()
        retrieve_hints = {"retrieve", "search", "find", "lookup", "fetch", "query", "read", "collect"}
        write_hints = {"write", "writer", "save", "store", "persist", "create"}
        message_hints = {"message", "send", "reply", "email", "sms", "text", "notify"}
        state_hints = {"set", "toggle", "enable", "disable", "status", "state", "update"}
        if any(token in text for token in message_hints):
            return "message"
        if any(token in text for token in write_hints):
            return "write"
        if any(token in text for token in retrieve_hints):
            return "retrieve"
        if any(token in text for token in state_hints):
            return "state"
        return ""

    def _make_sample(self, raw: Dict[str, Any], idx: int) -> BenchmarkSample:
        sample_id = str(
            raw.get("sample_id")
            or raw.get("name")
            or raw.get("scenario_id")
            or raw.get("task_id")
            or raw.get("id")
            or f"toolsandbox_{idx:05d}"
        )
        visible_payload = self._planner_visible_payload(raw)
        categories = self._extract_categories(visible_payload)
        metadata = dict(visible_payload.get("metadata", {}))
        metadata["toolsandbox_categories"] = categories
        metadata["tool_allow_list"] = [] if self._is_planner_sensitive_protocol(raw) else self._tool_allow_list(visible_payload)
        metadata["milestone_count"] = 0 if self._is_planner_sensitive_protocol(raw) else len(visible_payload.get("milestones", []))
        if self._is_planner_sensitive_protocol(raw):
            metadata["planner_sensitive_protocol"] = self.PLANNER_SENSITIVE_PROTOCOL
        scenario = categories[0] if categories else "toolsandbox"
        return BenchmarkSample(sample_id=sample_id, raw_payload=raw, scenario=scenario, metadata=metadata)

    def _is_planner_sensitive_protocol(self, raw: Dict[str, Any]) -> bool:
        protocol = raw.get("planner_sensitive_protocol") or raw.get("protocol")
        return str(protocol or "").strip() == self.PLANNER_SENSITIVE_PROTOCOL

    def _planner_visible_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_planner_sensitive_protocol(raw):
            return raw
        visible = dict(raw.get("planner_visible", {}) or {})
        for key in (
            "sample_id",
            "task_id",
            "name",
            "scenario_id",
            "execution_scenario",
            "slice_type",
            "task_family",
        ):
            if key in raw and key not in visible:
                visible[key] = raw[key]
        visible.setdefault("categories", ["planner_sensitive", "multiple_tool", "state_dependency"])
        visible.setdefault(
            "success_criteria",
            [
                "execute a multi-step capability sequence in the required dependency order",
                "avoid forbidden shortcut tools",
                "produce the requested final state or artifact",
            ],
        )
        return visible

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
        if isinstance(raw_tools, list):
            tools: List[ToolSpec] = []
            for idx, raw_tool in enumerate(raw_tools, start=1):
                if isinstance(raw_tool, str):
                    tools.append(
                        ToolSpec(
                            tool_id=raw_tool,
                            description=f"ToolSandbox tool: {raw_tool}",
                            metadata={"execution_backend": "semantic_mock", "benchmark": self.benchmark_name},
                        )
                    )
                    continue
                if isinstance(raw_tool, dict):
                    raw_metadata = {k: v for k, v in raw_tool.items() if k not in {"tool_id", "name", "description"}}
                    tools.append(
                        ToolSpec(
                            tool_id=str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                            description=str(
                                raw_tool.get("description")
                                or raw_tool.get("tool_id")
                                or raw_tool.get("name")
                                or "ToolSandbox tool"
                            ),
                            metadata={
                                "execution_backend": "semantic_mock",
                                "benchmark": self.benchmark_name,
                                **raw_metadata,
                            },
                        )
                    )
            return tools

        allow_list = self._tool_allow_list(raw)
        if allow_list:
            return [
                ToolSpec(
                    tool_id=tool_id,
                    description=f"ToolSandbox tool: {tool_id}",
                    metadata={"execution_backend": "semantic_mock", "benchmark": self.benchmark_name},
                )
                for tool_id in allow_list
            ]

        return []

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
        if raw_constraints.get("max_tool_calls") is not None:
            task_constraints.max_tool_calls = int(raw_constraints["max_tool_calls"])
        if raw_constraints.get("max_user_turns") is not None:
            task_constraints.max_user_turns = int(raw_constraints["max_user_turns"])
        if raw_constraints.get("max_repair_attempts") is not None:
            task_constraints.max_repair_attempts = int(raw_constraints["max_repair_attempts"])
        if raw_constraints.get("max_recovery_budget") is not None:
            task_constraints.max_recovery_budget = float(raw_constraints["max_recovery_budget"])
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

    def _must_interact_expected(self, raw: Dict[str, Any], categories: List[str]) -> bool:
        if self._interaction_expected(categories):
            return True
        task_family = str(raw.get("task_family") or raw.get("reuse_family_id") or "")
        metadata = raw.get("metadata", {})
        if isinstance(metadata, dict):
            task_family = str(metadata.get("task_family") or task_family)
        return task_family == "t3_must_interact"

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

    @staticmethod
    def _result_summary_source(result_summary: Dict[str, Any]) -> str:
        return str(result_summary.get("source") or result_summary.get("summary_source") or "toolclaw_proxy")

    def _proxy_summary_success(self, similarity: Any, result_summary_source: str, total_milestones: int) -> bool:
        if result_summary_source == "toolclaw_proxy" and total_milestones <= 0:
            return False
        try:
            return float(similarity) >= float(self.default_success_threshold)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _reference_summary_success(result_summary: Dict[str, Any]) -> Optional[bool]:
        for key in ("success", "is_success", "completed", "solved"):
            value = result_summary.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"true", "1", "yes", "y"}:
                    return True
                if normalized in {"false", "0", "no", "n"}:
                    return False
        return None

    def _expected_write_target_path(self, raw: Dict[str, Any], task_id: str) -> Optional[str]:
        if raw.get("target_path") is not None:
            return str(raw.get("target_path"))
        if self._task_expects_write(raw):
            return f"{self.default_target_dir}/{task_id}.txt"
        return None

    def _observed_write_target_path(self, raw: Dict[str, Any], trace_events: List[Dict[str, Any]]) -> Optional[str]:
        observed_paths: List[str] = []
        for event in trace_events:
            if event.get("event_type") != "tool_call":
                continue
            tool_id = str(event.get("tool_id") or "").strip()
            if not tool_id:
                continue
            tool_args = event.get("tool_args")
            if not isinstance(tool_args, dict):
                continue
            target_path = tool_args.get("target_path")
            if target_path is None:
                continue
            if self._infer_proxy_tool_capability(raw, tool_id) == "write" or self._tool_call_is_write_like_for_benchmark(
                raw, tool_id
            ):
                observed_paths.append(str(target_path))
        if not observed_paths:
            return None
        return observed_paths[-1]

    def _tool_call_is_write_like_for_benchmark(self, raw: Dict[str, Any], tool_id: str) -> bool:
        """Fallback when descriptions omit write keywords but the tool is a benchmark write endpoint."""
        if self._infer_proxy_tool_capability(raw, tool_id) == "write":
            return True
        if tool_id not in self._tool_allow_list(raw):
            return False
        spec = self._proxy_tool_spec(raw, tool_id)
        blob = " ".join(
            [
                tool_id.lower(),
                str(spec.get("description") or "").lower(),
                " ".join(str(x) for x in spec.get("semantic_tags", []) if str(x)).lower(),
            ]
        )
        if any(token in blob for token in ("write", "writer", "save", "persist", "archive", "report", "artifact")):
            return True
        return any(fragment in tool_id.lower() for fragment in ("write", "archive", "persist", "backup"))

    @staticmethod
    def _normalize_benchmark_path(path: str) -> str:
        cleaned = path.strip().replace("\\", "/")
        return os.path.normpath(cleaned)

    def _paths_match_for_benchmark_write(self, expected: str, observed: str) -> bool:
        if not expected or not observed:
            return False
        e = self._normalize_benchmark_path(expected)
        o = self._normalize_benchmark_path(observed)
        if e == o:
            return True
        try:
            return Path(e).expanduser().resolve() == Path(o).expanduser().resolve()
        except (OSError, RuntimeError):
            return False

    def _write_target_verified(self, *, raw: Dict[str, Any], task_id: str, trace_events: List[Dict[str, Any]]) -> bool:
        expected_target_path = self._expected_write_target_path(raw, task_id)
        if expected_target_path is None:
            return True
        observed_target_path = self._observed_write_target_path(raw, trace_events)
        if observed_target_path is None:
            return False
        return self._paths_match_for_benchmark_write(expected_target_path, observed_target_path)

    def _task_expects_write(self, raw: Dict[str, Any]) -> bool:
        if raw.get("target_path") is not None:
            return True
        tool_ids = self._tool_allow_list(raw)
        if not tool_ids:
            tool_ids = [
                str(raw_tool.get("tool_id") or raw_tool.get("name") or "").strip()
                for raw_tool in raw.get("candidate_tools", []) or []
                if isinstance(raw_tool, dict)
            ]
        return any(self._infer_proxy_tool_capability(raw, tool_id) == "write" for tool_id in tool_ids if tool_id)

    @staticmethod
    def _execution_verified_success(
        *,
        raw_trace_success: bool,
        result_summary_source: str,
        proxy_summary_success: bool,
        reference_summary_success: Optional[bool],
        matched_milestones: int,
        total_milestones: int,
        write_target_verified: bool,
    ) -> bool:
        if not raw_trace_success or not write_target_verified:
            return False
        if result_summary_source != "toolclaw_proxy":
            if reference_summary_success is not None:
                return reference_summary_success
            return proxy_summary_success
        if not proxy_summary_success:
            return False
        return total_milestones > 0 and matched_milestones == total_milestones


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
