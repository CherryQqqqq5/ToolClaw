"""tau³-bench bridge skeleton for mapping benchmark tasks into ToolClaw.

This bridge now provides a default turn-level framework:
- plan once into a ToolClaw workflow
- emit benchmark-native ToolCall messages one step at a time
- consume ToolMessage / MultiToolMessage results
- apply lightweight policy and recovery decisions between turns

The default handler is intentionally conservative. It is suitable for remote
smoke testing and interface alignment, not final leaderboard runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.execution.executor import ExecutionOutcome, SequentialExecutor
from toolclaw.execution.recovery import RecoveryEngine
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningHints, PlanningRequest, build_default_planner
from toolclaw.policy.policy_engine import PolicyEngine
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.error import (
    ErrorCategory,
    ErrorEvidence,
    ErrorSeverity,
    ErrorStage,
    Recoverability,
    StateContext,
    ToolClawError,
)
from toolclaw.schemas.workflow import (
    EnvironmentContext,
    Permissions,
    RiskLevel,
    TaskConstraints,
    TaskSpec,
    ToolSpec,
    Workflow,
    WorkflowContext,
    WorkflowStep,
)

try:
    from tau2.agent import HalfDuplexAgent
    from tau2.data_model.message import AssistantMessage, MultiToolMessage, ToolCall, ToolMessage

    TAU3_BENCH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised implicitly in local repo mode
    TAU3_BENCH_AVAILABLE = False

    class HalfDuplexAgent:  # type: ignore[override]
        """Fallback base so the bridge can be imported without tau2 installed."""

        def __class_getitem__(cls, item: object) -> type["HalfDuplexAgent"]:
            _ = item
            return cls

    AssistantMessage = None  # type: ignore[assignment]
    MultiToolMessage = None  # type: ignore[assignment]
    ToolCall = None  # type: ignore[assignment]
    ToolMessage = None  # type: ignore[assignment]


@dataclass
class FallbackToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]
    requestor: str = "assistant"


@dataclass
class FallbackToolMessage:
    id: str
    content: Optional[str] = None
    role: str = "tool"
    requestor: str = "assistant"
    error: bool = False


@dataclass
class FallbackMultiToolMessage:
    tool_messages: List[FallbackToolMessage]
    role: str = "tool"


@dataclass
class FallbackAssistantMessage:
    """Minimal assistant message stand-in when tau2/tau³ types are unavailable."""

    content: str
    role: str = "assistant"
    tool_calls: List[Any] = field(default_factory=list)


@dataclass
class Tau3TaskView:
    task_id: str
    user_goal: str
    success_criteria: List[str] = field(default_factory=list)
    target_path: Optional[str] = None
    scenario: str = "success"
    constraints: TaskConstraints = field(default_factory=TaskConstraints)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolClawTau3State:
    """Agent-side state aligned to benchmark turns while preserving ToolClaw context."""

    task_id: Optional[str] = None
    message_history: List[Any] = field(default_factory=list)
    latest_request: Optional[PlanningRequest] = None
    latest_outcome: Optional[ExecutionOutcome] = None
    latest_trace_path: Optional[str] = None
    final_state: Dict[str, Any] = field(default_factory=dict)
    workflow: Optional[Workflow] = None
    current_step_index: int = 0
    completed_step_ids: List[str] = field(default_factory=list)
    pending_tool_calls: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_user_question: Optional[str] = None
    pending_repair_type: Optional[str] = None
    pending_step_id: Optional[str] = None
    finished: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def waiting_step_id(self) -> Optional[str]:
        if self.pending_step_id:
            return self.pending_step_id
        if not self.pending_tool_calls:
            return None
        first_pending = sorted(
            self.pending_tool_calls.values(),
            key=lambda item: (int(item.get("step_index", 0)), str(item.get("step_id", ""))),
        )[0]
        return str(first_pending.get("step_id") or "")

    @property
    def waiting_tool_call_id(self) -> Optional[str]:
        if not self.pending_tool_calls:
            return None
        return sorted(
            self.pending_tool_calls.items(),
            key=lambda item: (int(item[1].get("step_index", 0)), item[0]),
        )[0][0]

    @property
    def waiting_tool_name(self) -> Optional[str]:
        if not self.pending_tool_calls:
            return None
        first_pending = sorted(
            self.pending_tool_calls.values(),
            key=lambda item: (int(item.get("step_index", 0)), str(item.get("tool_name", ""))),
        )[0]
        tool_name = first_pending.get("tool_name")
        return str(tool_name) if tool_name is not None else None


@dataclass
class ToolClawTau3TurnContext:
    incoming_message: Any
    state: ToolClawTau3State
    request: PlanningRequest
    runtime: ToolClawRuntime
    run_id: str
    output_path: str
    backup_tool_map: Dict[str, str] = field(default_factory=dict)
    task_view: Optional[Tau3TaskView] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedToolResult:
    tool_call_id: str
    content_raw: Any
    content_value: Any
    payload: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: bool = False
    parse_error: Optional[str] = None


@dataclass
class ToolArgMapping:
    tool_arg: str
    step_arg: str
    source_state_key: Optional[str] = None
    output_state_key: Optional[str] = None
    required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkToolBinding:
    tool_id: str
    benchmark_tool: Any
    description: str = ""
    arg_mappings: List[ToolArgMapping] = field(default_factory=list)
    output_payload_key: Optional[str] = None
    output_state_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tau3ToolRuntimeAdapter:
    """Normalize benchmark-native tool executor results into ToolMessage payloads."""

    _CONTENT_KEYS = ("content", "output", "result", "payload", "data", "value", "message")
    _ID_KEYS = ("id", "tool_call_id", "call_id")
    _BATCH_KEYS = ("tool_messages", "tool_results", "results", "outputs", "responses")
    _ERROR_KEYS = ("error", "is_error", "failed")
    _SUCCESS_KEYS = ("ok", "success")
    _STATUS_KEYS = ("status", "status_code", "code")

    def normalize_incoming_message(
        self,
        message: Any,
        pending_tool_calls: Dict[str, Dict[str, Any]],
    ) -> List[Any]:
        direct_messages = self._extract_direct_tool_messages(message)
        if direct_messages:
            return [self._normalize_tool_message_shape(item) for item in direct_messages]

        if message is None:
            return []

        if isinstance(message, list):
            return self._normalize_batch_results(message, pending_tool_calls)

        mapping = Tau3BenchAdapter._coerce_mapping(message)
        if mapping:
            for batch_key in self._BATCH_KEYS:
                batch_value = mapping.get(batch_key)
                if isinstance(batch_value, list):
                    return self._normalize_batch_results(batch_value, pending_tool_calls)
            if self._looks_like_runtime_result(mapping):
                return self._normalize_batch_results([mapping], pending_tool_calls)

        if isinstance(message, BaseException) and pending_tool_calls:
            return self._normalize_batch_results([message], pending_tool_calls)

        return []

    def _normalize_batch_results(
        self,
        results: Sequence[Any],
        pending_tool_calls: Dict[str, Dict[str, Any]],
    ) -> List[Any]:
        pending_items = sorted(
            pending_tool_calls.items(),
            key=lambda item: (int(item[1].get("step_index", 0)), item[0]),
        )
        pending_by_id = {call_id: pending for call_id, pending in pending_items}
        normalized: List[Any] = []
        next_pending_index = 0
        for result in results:
            runtime_mapping = Tau3BenchAdapter._coerce_mapping(result)
            tool_call_id = self._extract_first(runtime_mapping, self._ID_KEYS) if runtime_mapping else None
            pending = None
            if tool_call_id and tool_call_id in pending_by_id:
                pending = pending_by_id[tool_call_id]
            elif next_pending_index < len(pending_items):
                tool_call_id = pending_items[next_pending_index][0]
                pending = pending_items[next_pending_index][1]
                next_pending_index += 1
            normalized.append(
                self._normalize_runtime_result(
                    result=result,
                    tool_call_id=str(tool_call_id or ""),
                    tool_name=str(pending.get("tool_name") or "") if pending else None,
                )
            )
        return normalized

    def _normalize_tool_message_shape(self, message: Any) -> Any:
        if isinstance(message, dict):
            tool_call_id = str(message.get("id") or "")
            content = self._serialize_content(
                content=message.get("content"),
                metadata=self._extract_message_metadata(message, exclude={"id", "content", "error", "role"}),
            )
            return self._make_tool_message(
                tool_call_id=tool_call_id,
                content=content,
                error=bool(message.get("error", False)),
                requestor=str(message.get("requestor") or "assistant"),
            )
        return message

    def _normalize_runtime_result(
        self,
        result: Any,
        tool_call_id: str,
        tool_name: Optional[str] = None,
    ) -> Any:
        if isinstance(result, BaseException):
            content = json.dumps(
                {
                    "error_type": type(result).__name__,
                    "message": str(result),
                    "metadata": {"tool_name": tool_name} if tool_name else {},
                },
                sort_keys=True,
            )
            return self._make_tool_message(tool_call_id=tool_call_id, content=content, error=True)

        if isinstance(result, str):
            return self._make_tool_message(tool_call_id=tool_call_id, content=result, error=False)

        mapping = Tau3BenchAdapter._coerce_mapping(result)
        if not mapping:
            return self._make_tool_message(
                tool_call_id=tool_call_id,
                content=self._serialize_content(content=result, metadata={"tool_name": tool_name} if tool_name else {}),
                error=False,
            )

        error = any(bool(mapping.get(key)) for key in self._ERROR_KEYS)
        if any(key in mapping and mapping[key] is False for key in self._SUCCESS_KEYS):
            error = True

        status_value = self._extract_first(mapping, self._STATUS_KEYS)
        if isinstance(status_value, int) and status_value >= 400:
            error = True
        if isinstance(status_value, str) and status_value.lower() in {"error", "failed", "failure", "denied"}:
            error = True

        content = self._extract_first(mapping, self._CONTENT_KEYS)
        metadata = self._extract_message_metadata(
            mapping,
            exclude=set(self._CONTENT_KEYS) | set(self._ID_KEYS) | set(self._ERROR_KEYS) | set(self._SUCCESS_KEYS) | set(self._STATUS_KEYS),
        )
        if tool_name and "tool_name" not in metadata:
            metadata["tool_name"] = tool_name
        if "metadata" in mapping and isinstance(mapping["metadata"], dict):
            merged_metadata = dict(mapping["metadata"])
            merged_metadata.update(metadata)
            metadata = merged_metadata

        return self._make_tool_message(
            tool_call_id=str(self._extract_first(mapping, self._ID_KEYS) or tool_call_id or ""),
            content=self._serialize_content(content=content, metadata=metadata),
            error=error,
            requestor=str(mapping.get("requestor") or "assistant"),
        )

    @classmethod
    def _extract_direct_tool_messages(cls, message: Any) -> List[Any]:
        if message is None:
            return []
        if isinstance(message, list):
            if all(cls._is_tool_message_like(item) or cls._looks_like_runtime_result(Tau3BenchAdapter._coerce_mapping(item)) for item in message):
                return list(message)
            return []
        if hasattr(message, "tool_messages"):
            tool_messages = getattr(message, "tool_messages", None)
            if isinstance(tool_messages, list):
                return list(tool_messages)
        if cls._is_tool_message_like(message):
            return [message]
        if isinstance(message, dict):
            if isinstance(message.get("tool_messages"), list):
                return list(message["tool_messages"])
            if cls._is_tool_message_like(message):
                return [message]
        return []

    @staticmethod
    def _extract_first(mapping: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
        for key in keys:
            if key in mapping and mapping[key] is not None:
                return mapping[key]
        return None

    @staticmethod
    def _extract_message_metadata(mapping: Dict[str, Any], exclude: set[str]) -> Dict[str, Any]:
        return {key: value for key, value in mapping.items() if key not in exclude}

    @classmethod
    def _serialize_content(cls, content: Any, metadata: Dict[str, Any]) -> Optional[str]:
        if isinstance(content, str) and not metadata:
            return content
        if content is None and not metadata:
            return None
        if not metadata and isinstance(content, (int, float, bool)):
            return json.dumps(content)
        if not metadata and isinstance(content, str):
            return content
        envelope: Dict[str, Any] = {}
        if content is not None:
            envelope["payload"] = content
        if metadata:
            envelope["metadata"] = metadata
        return json.dumps(envelope, sort_keys=True)

    @staticmethod
    def _is_tool_message_like(message: Any) -> bool:
        if isinstance(message, dict):
            return message.get("role") == "tool" or ("id" in message and "content" in message)
        return bool(getattr(message, "role", None) == "tool" or (getattr(message, "id", None) and hasattr(message, "content")))

    @classmethod
    def _looks_like_runtime_result(cls, mapping: Dict[str, Any]) -> bool:
        if not mapping:
            return False
        signal_keys = set(cls._CONTENT_KEYS) | set(cls._ID_KEYS) | set(cls._ERROR_KEYS) | set(cls._SUCCESS_KEYS) | set(cls._STATUS_KEYS)
        return any(key in mapping for key in signal_keys)

    @staticmethod
    def _make_tool_message(
        tool_call_id: str,
        content: Optional[str],
        error: bool = False,
        requestor: str = "assistant",
    ) -> Any:
        if TAU3_BENCH_AVAILABLE and ToolMessage is not None:
            return ToolMessage(id=tool_call_id, content=content, error=error, requestor=requestor)
        return FallbackToolMessage(id=tool_call_id, content=content, error=error, requestor=requestor)


class Tau3ToolErrorMapper:
    """Map benchmark-native executor failures into ToolClaw recovery categories."""

    _BINDING_TOKENS = (
        "missing required",
        "required field",
        "required parameter",
        "invalid argument",
        "invalid params",
        "validation error",
        "schema validation",
        "bad argument",
    )
    _POLICY_TOKENS = (
        "approval required",
        "requires approval",
        "policy",
        "blocked by policy",
        "guardrail",
    )
    _PERMISSION_TOKENS = (
        "permission denied",
        "access denied",
        "unauthorized",
        "forbidden",
        "not allowed",
        "permission",
    )
    _ORDERING_TOKENS = (
        "dependency",
        "precondition",
        "must call",
        "before calling",
        "out of order",
        "already completed",
    )
    _STATE_TOKENS = (
        "invalid state",
        "state mismatch",
        "missing context",
        "stale state",
        "unknown session",
    )
    _ENVIRONMENT_TOKENS = (
        "timeout",
        "timed out",
        "network",
        "connection",
        "unavailable",
        "internal error",
        "rate limit",
        "service",
        "temporary",
        "unreachable",
    )

    def build_error(
        self,
        *,
        context: ToolClawTau3TurnContext,
        step: WorkflowStep,
        parsed_result: ParsedToolResult,
    ) -> ToolClawError:
        raw_message = ToolClawTau3Agent._stringify_tool_content(parsed_result.content_value) or "tool execution failed"
        metadata_text = ToolClawTau3Agent._stringify_tool_content(parsed_result.metadata)
        signal_text = f"{raw_message} {metadata_text}".lower()
        category = self._classify_category(signal_text=signal_text, parsed_result=parsed_result)
        missing_assets = self._extract_missing_assets(step=step, parsed_result=parsed_result, signal_text=signal_text)
        subtype = str(parsed_result.metadata.get("error_type") or parsed_result.metadata.get("code") or parsed_result.parse_error or "tau3_tool_error")
        stage = ErrorStage.RECOVERY if parsed_result.parse_error else ErrorStage.EXECUTION

        return ToolClawError(
            error_id=f"err_{context.run_id}_{step.step_id}",
            run_id=context.run_id,
            workflow_id=context.state.workflow.workflow_id if context.state.workflow else f"wf_{context.request.task.task_id}",
            step_id=step.step_id,
            category=category,
            subtype=subtype,
            severity=ErrorSeverity.MEDIUM,
            stage=stage,
            symptoms=[raw_message],
            evidence=ErrorEvidence(
                tool_id=step.tool_id,
                raw_message=raw_message,
                exception_type=parsed_result.parse_error,
                inputs=dict(step.inputs),
                outputs={"payload": parsed_result.payload},
                metadata=dict(parsed_result.metadata),
            ),
            root_cause_hypothesis=self._root_cause_hypothesis(category=category, parsed_result=parsed_result),
            state_context=StateContext(
                active_capability=step.capability_id,
                active_step_id=step.step_id,
                missing_assets=missing_assets,
                state_values=dict(context.state.final_state),
                policy_flags={"approval_pending": bool(context.state.pending_user_question)},
            ),
            recoverability=self._recoverability(category=category),
            failtax_label=category.value,
            metadata={"parse_error": parsed_result.parse_error} if parsed_result.parse_error else {},
        )

    def _classify_category(self, signal_text: str, parsed_result: ParsedToolResult) -> ErrorCategory:
        if parsed_result.parse_error:
            return ErrorCategory.RECOVERY_FAILURE
        if any(token in signal_text for token in self._BINDING_TOKENS):
            return ErrorCategory.BINDING_FAILURE
        if any(token in signal_text for token in self._POLICY_TOKENS):
            return ErrorCategory.POLICY_FAILURE
        if any(token in signal_text for token in self._PERMISSION_TOKENS):
            return ErrorCategory.PERMISSION_FAILURE
        if any(token in signal_text for token in self._ORDERING_TOKENS):
            return ErrorCategory.ORDERING_FAILURE
        if any(token in signal_text for token in self._STATE_TOKENS):
            return ErrorCategory.STATE_FAILURE
        if any(token in signal_text for token in self._ENVIRONMENT_TOKENS):
            return ErrorCategory.ENVIRONMENT_FAILURE
        return ErrorCategory.ENVIRONMENT_FAILURE

    @staticmethod
    def _extract_missing_assets(
        step: WorkflowStep,
        parsed_result: ParsedToolResult,
        signal_text: str,
    ) -> List[str]:
        missing_assets: List[str] = []
        for key in step.inputs:
            if key.lower() in signal_text and key not in missing_assets:
                missing_assets.append(key)
        for meta_key in ("missing_fields", "missing_assets", "required_fields"):
            value = parsed_result.metadata.get(meta_key)
            if isinstance(value, list):
                for item in value:
                    asset = str(item)
                    if asset and asset not in missing_assets:
                        missing_assets.append(asset)
        return missing_assets

    @staticmethod
    def _root_cause_hypothesis(category: ErrorCategory, parsed_result: ParsedToolResult) -> List[str]:
        if parsed_result.parse_error:
            return ["benchmark tool runtime returned a payload the bridge could not normalize"]
        return [f"tau3 benchmark runtime produced a {category.value} signal"]

    @staticmethod
    def _recoverability(category: ErrorCategory) -> Recoverability:
        return Recoverability(
            recoverable=True,
            requires_user_input=category == ErrorCategory.ENVIRONMENT_FAILURE,
            requires_tool_switch=category == ErrorCategory.ENVIRONMENT_FAILURE,
            requires_rollback=category in {ErrorCategory.ORDERING_FAILURE, ErrorCategory.STATE_FAILURE, ErrorCategory.RECOVERY_FAILURE, ErrorCategory.PERMISSION_FAILURE},
            requires_approval=category == ErrorCategory.POLICY_FAILURE,
        )


class Tau3BenchAdapter:
    """Map tau³-bench task/tool objects into ToolClaw's PlanningRequest model."""

    benchmark_name: str = "tau3_bench"

    def build_request(
        self,
        task: Any,
        tools: Sequence[Any],
        domain_policy: Any = None,
        message_history: Optional[Sequence[Any]] = None,
        output_dir: str = "outputs/tau3_bench",
        hints: Optional[PlanningHints] = None,
    ) -> PlanningRequest:
        task_view = self.normalize_task(task=task, message_history=message_history, output_dir=output_dir)
        context = WorkflowContext(
            environment=self._build_environment(task_view=task_view, domain_policy=domain_policy),
            candidate_tools=self._build_candidate_tools(tools),
        )
        request = PlanningRequest(
            task=TaskSpec(
                task_id=task_view.task_id,
                user_goal=task_view.user_goal,
                success_criteria=list(task_view.success_criteria),
                constraints=task_view.constraints,
            ),
            context=context,
            hints=hints or PlanningHints(),
            planner_mode="tau3_bridge",
            workflow_overrides={
                "steps": {
                    "step_02": {
                        "inputs": {"target_path": task_view.target_path},
                    }
                }
            },
        )
        request.hints.user_style["tau3_metadata"] = dict(task_view.metadata)
        request.hints.user_style["tau3_domain_policy"] = self._stringify_domain_policy(domain_policy)
        return request

    def normalize_task(
        self,
        task: Any,
        message_history: Optional[Sequence[Any]] = None,
        output_dir: str = "outputs/tau3_bench",
    ) -> Tau3TaskView:
        raw = self._coerce_mapping(task)
        task_id = str(
            raw.get("task_id")
            or raw.get("id")
            or raw.get("sample_id")
            or raw.get("name")
            or "tau3_task"
        )
        user_goal = self._extract_user_goal(raw=raw, message_history=message_history)
        constraints = self._extract_constraints(raw)
        target_path = str(raw.get("target_path") or Path(output_dir) / "reports" / f"{task_id}.txt")
        success_criteria = self._normalize_string_list(raw.get("success_criteria"))
        if not success_criteria:
            success_criteria = ["complete the benchmark task correctly"]
        metadata = dict(raw.get("metadata", {})) if isinstance(raw.get("metadata"), dict) else {}
        metadata.setdefault("raw_task_keys", sorted(raw.keys()))
        return Tau3TaskView(
            task_id=task_id,
            user_goal=user_goal,
            success_criteria=success_criteria,
            target_path=target_path,
            scenario=str(raw.get("scenario") or raw.get("label") or "success"),
            constraints=constraints,
            metadata=metadata,
        )

    def build_backup_tool_map(self, tools: Sequence[Any]) -> Dict[str, str]:
        tool_ids = [self._extract_tool_id(tool) for tool in tools]
        tool_set = set(tool_ids)
        backup_map: Dict[str, str] = {}
        if "write_tool" in tool_set and "backup_write_tool" in tool_set:
            backup_map["write_tool"] = "backup_write_tool"
        return backup_map

    @staticmethod
    def _build_environment(task_view: Tau3TaskView, domain_policy: Any) -> EnvironmentContext:
        permissions = Permissions(
            network=True,
            filesystem_read=True,
            filesystem_write=True,
            external_api=True,
        )
        domain_text = Tau3BenchAdapter._stringify_domain_policy(domain_policy).lower()
        if "no_network" in domain_text:
            permissions.network = False
        if "read_only" in domain_text:
            permissions.filesystem_write = False
        env = EnvironmentContext(permissions=permissions)
        env.available_assets = [task_view.target_path] if task_view.target_path else []
        return env

    @staticmethod
    def _build_candidate_tools(tools: Sequence[Any]) -> List[ToolSpec]:
        candidate_tools: List[ToolSpec] = []
        for index, tool in enumerate(tools, start=1):
            tool_id = Tau3BenchAdapter._extract_tool_id(tool) or f"tau3_tool_{index:02d}"
            description = Tau3BenchAdapter._extract_tool_description(tool) or tool_id
            candidate_tools.append(
                ToolSpec(
                    tool_id=tool_id,
                    description=description,
                    metadata={
                        "source": "tau3_bench",
                        "tool_type": type(tool).__name__,
                    },
                )
            )
        return candidate_tools

    @staticmethod
    def _extract_constraints(raw: Dict[str, Any]) -> TaskConstraints:
        constraints = TaskConstraints()
        constraint_candidates = []
        if isinstance(raw.get("constraints"), dict):
            constraint_candidates.append(raw["constraints"])
        if isinstance(raw.get("metadata"), dict):
            constraint_candidates.append(raw["metadata"])
        merged: Dict[str, Any] = {}
        for candidate in constraint_candidates:
            merged.update(candidate)

        if merged.get("budget_limit") is not None:
            constraints.budget_limit = float(merged["budget_limit"])
        if merged.get("time_limit") is not None:
            constraints.time_limit = float(merged["time_limit"])
        if merged.get("requires_user_approval") is not None:
            constraints.requires_user_approval = bool(merged["requires_user_approval"])
        if merged.get("forbidden_actions"):
            constraints.forbidden_actions = [str(item) for item in merged["forbidden_actions"]]

        risk_level = str(merged.get("risk_level") or "").lower()
        if risk_level in {"low", "medium", "high"}:
            constraints.risk_level = RiskLevel(risk_level)
        return constraints

    @staticmethod
    def _extract_user_goal(raw: Dict[str, Any], message_history: Optional[Sequence[Any]]) -> str:
        for key in ("query", "user_goal", "instruction", "prompt", "goal", "description"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if message_history:
            texts = []
            for message in message_history:
                content = Tau3BenchAdapter._coerce_message_text(message)
                if content:
                    texts.append(content)
            if texts:
                return texts[-1]
        return "complete the benchmark task"

    @staticmethod
    def _extract_tool_id(tool: Any) -> str:
        for attr in ("tool_id", "name", "id"):
            value = getattr(tool, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(tool, dict):
            for key in ("tool_id", "name", "id"):
                value = tool.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @staticmethod
    def _extract_tool_description(tool: Any) -> str:
        for attr in ("description", "docstring", "help"):
            value = getattr(tool, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(tool, dict):
            for key in ("description", "docstring", "help"):
                value = tool.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @staticmethod
    def _coerce_mapping(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            if isinstance(dumped, dict):
                return dumped
        if hasattr(value, "__dict__"):
            return {key: val for key, val in vars(value).items() if not key.startswith("_")}
        return {}

    @staticmethod
    def _normalize_string_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        return []

    @staticmethod
    def _coerce_message_text(message: Any) -> str:
        if message is None:
            return ""
        if isinstance(message, str):
            return message.strip()
        for attr in ("content", "text", "message"):
            value = getattr(message, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(message, dict):
            for key in ("content", "text", "message"):
                value = message.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @staticmethod
    def _stringify_domain_policy(domain_policy: Any) -> str:
        if domain_policy is None:
            return ""
        if isinstance(domain_policy, str):
            return domain_policy
        if hasattr(domain_policy, "model_dump_json"):
            return str(domain_policy.model_dump_json())
        if hasattr(domain_policy, "__dict__"):
            return str({key: value for key, value in vars(domain_policy).items() if not key.startswith("_")})
        return str(domain_policy)


class BenchmarkToolRegistryBridge:
    """Normalize benchmark-native tool objects into ToolClaw-facing mappings."""

    def __init__(self, tools: Sequence[Any]) -> None:
        self.bindings: Dict[str, BenchmarkToolBinding] = {}
        for tool in tools:
            binding = self._build_binding(tool)
            self.bindings[binding.tool_id] = binding

    def resolve(self, tool_id: str) -> Optional[BenchmarkToolBinding]:
        return self.bindings.get(tool_id)

    def map_step_args_to_tool_args(
        self,
        tool_id: str,
        step: WorkflowStep,
        state_values: Dict[str, Any],
    ) -> Dict[str, Any]:
        binding = self.resolve(tool_id)
        resolved_inputs = ToolClawTau3Agent._resolve_step_inputs(step, state_values)
        if binding is None or not binding.arg_mappings:
            return dict(resolved_inputs)

        tool_args: Dict[str, Any] = {}
        consumed_step_args = set()
        for mapping in binding.arg_mappings:
            source_key = mapping.step_arg
            if source_key not in resolved_inputs and mapping.source_state_key and mapping.source_state_key in state_values:
                tool_args[mapping.tool_arg] = state_values[mapping.source_state_key]
                continue
            if source_key in resolved_inputs:
                tool_args[mapping.tool_arg] = resolved_inputs[source_key]
                consumed_step_args.add(source_key)
            elif mapping.required:
                raise KeyError(f"missing required mapped argument: {mapping.step_arg}")

        for key, value in resolved_inputs.items():
            if key not in consumed_step_args:
                tool_args[key] = value
        return tool_args

    def map_tool_result_to_state_patch(
        self,
        tool_id: str,
        parsed_result: ParsedToolResult,
        step: WorkflowStep,
    ) -> Dict[str, Any]:
        binding = self.resolve(tool_id)
        state_key = step.expected_output or step.step_id
        payload = parsed_result.payload
        patch = {state_key: payload}
        if binding is None:
            return patch
        if binding.output_payload_key and isinstance(parsed_result.content_value, dict):
            payload = parsed_result.content_value.get(binding.output_payload_key, payload)
            patch[state_key] = payload
        if binding.output_state_key:
            patch[binding.output_state_key] = payload
        for mapping in binding.arg_mappings:
            if mapping.output_state_key:
                patch[mapping.output_state_key] = payload
        return patch

    @staticmethod
    def _build_binding(tool: Any) -> BenchmarkToolBinding:
        tool_id = Tau3BenchAdapter._extract_tool_id(tool)
        description = Tau3BenchAdapter._extract_tool_description(tool)
        raw_mapping = BenchmarkToolRegistryBridge._extract_mapping_dict(tool, keys=("arg_map", "argument_map", "parameter_map"))
        mappings = [
            ToolArgMapping(tool_arg=str(tool_arg), step_arg=str(step_arg))
            for tool_arg, step_arg in raw_mapping.items()
        ]
        output_payload_key = BenchmarkToolRegistryBridge._extract_scalar(tool, ("output_payload_key", "payload_key"))
        output_state_key = BenchmarkToolRegistryBridge._extract_scalar(tool, ("output_state_key", "state_key"))
        metadata = BenchmarkToolRegistryBridge._extract_mapping_dict(tool, keys=("metadata",), default={})
        return BenchmarkToolBinding(
            tool_id=tool_id,
            benchmark_tool=tool,
            description=description,
            arg_mappings=mappings,
            output_payload_key=str(output_payload_key) if output_payload_key else None,
            output_state_key=str(output_state_key) if output_state_key else None,
            metadata=metadata,
        )

    @staticmethod
    def _extract_scalar(tool: Any, keys: Sequence[str]) -> Optional[Any]:
        if isinstance(tool, dict):
            for key in keys:
                if key in tool:
                    return tool[key]
        for key in keys:
            value = getattr(tool, key, None)
            if value is not None:
                return value
        return None

    @staticmethod
    def _extract_mapping_dict(tool: Any, keys: Sequence[str], default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        default = default or {}
        if isinstance(tool, dict):
            for key in keys:
                value = tool.get(key)
                if isinstance(value, dict):
                    return dict(value)
        for key in keys:
            value = getattr(tool, key, None)
            if isinstance(value, dict):
                return dict(value)
        return dict(default)


class ToolClawTau3Agent(HalfDuplexAgent[ToolClawTau3State]):
    """HalfDuplexAgent-compatible ToolClaw bridge for tau³-bench testing."""

    def __init__(
        self,
        tools: Sequence[Any],
        domain_policy: Any,
        *,
        task: Any = None,
        runtime: Optional[ToolClawRuntime] = None,
        runtime_factory: Optional[Callable[[], ToolClawRuntime]] = None,
        adapter: Optional[Tau3BenchAdapter] = None,
        turn_handler: Optional[Callable[[ToolClawTau3TurnContext], Any]] = None,
        backup_tool_map: Optional[Dict[str, str]] = None,
        output_dir: str = "outputs/tau3_bench_agent",
        run_id_prefix: str = "tau3",
        reuse_enabled: bool = True,
        **kwargs: Any,
    ) -> None:
        _ = kwargs
        self.tools = list(tools)
        self.domain_policy = domain_policy
        self.task = task
        self.adapter = adapter or Tau3BenchAdapter()
        self.output_dir = output_dir
        self.run_id_prefix = run_id_prefix
        self.reuse_enabled = reuse_enabled
        self.runtime = runtime or (runtime_factory() if runtime_factory else self._build_default_runtime())
        self.tool_bridge = BenchmarkToolRegistryBridge(self.tools)
        self.tool_runtime_adapter = Tau3ToolRuntimeAdapter()
        self.tool_error_mapper = Tau3ToolErrorMapper()
        self.backup_tool_map = backup_tool_map or self.adapter.build_backup_tool_map(self.tools)
        self.policy_engine = PolicyEngine()
        self.recovery_engine = RecoveryEngine()
        self._turn_index = 0
        self.turn_handler = turn_handler or self._default_turn_handler

    def get_init_state(self, message_history: Optional[Sequence[Any]] = None) -> ToolClawTau3State:
        task_view = self.adapter.normalize_task(task=self.task, message_history=message_history, output_dir=self.output_dir)
        return ToolClawTau3State(
            task_id=task_view.task_id,
            message_history=list(message_history or []),
            metadata={"task_view": task_view},
        )

    def generate_next_message(self, message: Any, state: ToolClawTau3State) -> tuple[Any, ToolClawTau3State]:
        state.message_history.append(message)
        self._turn_index += 1
        request = self.adapter.build_request(
            task=self.task,
            tools=self.tools,
            domain_policy=self.domain_policy,
            message_history=state.message_history,
            output_dir=self.output_dir,
        )
        state.latest_request = request
        task_view = self.adapter.normalize_task(task=self.task, message_history=state.message_history, output_dir=self.output_dir)
        run_id = f"{self.run_id_prefix}_{task_view.task_id}_{self._turn_index:03d}"
        output_path = str(Path(self.output_dir) / "traces" / f"{run_id}.json")
        context = ToolClawTau3TurnContext(
            incoming_message=message,
            state=state,
            request=request,
            runtime=self.runtime,
            run_id=run_id,
            output_path=output_path,
            backup_tool_map=dict(self.backup_tool_map),
            task_view=task_view,
        )

        assistant_message = self.turn_handler(context)
        state.message_history.append(assistant_message)
        return assistant_message, state

    def _default_turn_handler(self, context: ToolClawTau3TurnContext) -> Any:
        state = context.state
        self._ensure_workflow(context)

        if state.finished:
            return self._make_assistant_message("ToolClaw has already completed this task.")

        tool_messages = self.tool_runtime_adapter.normalize_incoming_message(
            message=context.incoming_message,
            pending_tool_calls=state.pending_tool_calls,
        )
        if tool_messages:
            return self._handle_tool_messages(context, tool_messages)

        if state.pending_user_question:
            return self._handle_user_reply(context)

        if state.pending_tool_calls:
            pending_names = ", ".join(
                pending.get("tool_name", call_id)
                for call_id, pending in sorted(state.pending_tool_calls.items())
            )
            return self._make_assistant_message(f"Awaiting result for pending tool calls: {pending_names}.")

        return self._emit_next_action(context)

    def _ensure_workflow(self, context: ToolClawTau3TurnContext) -> None:
        state = context.state
        if state.workflow is not None:
            self._normalize_workflow_for_benchmark(state.workflow)
            return
        if self.reuse_enabled and not context.request.hints.reusable_asset_ids:
            signature = f"phase1::{context.request.task.user_goal.lower().strip().replace(' ', '_')}"
            context.request.hints.reusable_asset_ids = [
                match.asset_id for match in context.runtime.asset_registry.query(signature)
            ]
        state.workflow = context.runtime.planner.plan(context.request).workflow
        self._normalize_workflow_for_benchmark(state.workflow)
        state.current_step_index = 0

    def _emit_next_action(self, context: ToolClawTau3TurnContext) -> Any:
        state = context.state
        workflow = state.workflow
        if workflow is None:
            return self._make_assistant_message("No workflow is available for execution.")

        self._advance_cursor(state, workflow)
        if state.current_step_index >= len(workflow.execution_plan):
            state.finished = True
            state.latest_outcome = ExecutionOutcome(
                run_id=context.run_id,
                workflow=workflow,
                success=True,
                final_state=dict(state.final_state),
                trace_path=state.latest_trace_path,
            )
            return self._make_assistant_message(self._format_completion_text(state.final_state))

        ready_steps = self._collect_ready_steps(workflow=workflow, state=state)
        if not ready_steps:
            state.finished = True
            return self._make_assistant_message("No ready workflow steps remain, but the workflow is not marked complete.")

        tool_calls: List[Any] = []
        call_summaries: List[str] = []
        for step in ready_steps:
            decision = self.policy_engine.evaluate_before_step(step, workflow, state.final_state)
            if decision.abort:
                state.finished = True
                state.latest_outcome = ExecutionOutcome(
                    run_id=context.run_id,
                    workflow=workflow,
                    success=False,
                    final_state=dict(state.final_state),
                    trace_path=state.latest_trace_path,
                    metadata={"stop_reason": decision.reason},
                )
                return self._make_assistant_message(f"Execution stopped by policy: {decision.reason}")

            if decision.require_confirmation:
                state.pending_user_question = f"Step {step.step_id} requires approval. Reply 'approve' to continue."
                state.pending_repair_type = "request_approval"
                state.pending_step_id = step.step_id
                return self._make_assistant_message(state.pending_user_question)

            tool_args = self.tool_bridge.map_step_args_to_tool_args(
                tool_id=step.tool_id or step.capability_id,
                step=step,
                state_values=state.final_state,
            )
            tool_call_id = f"toolcall_{context.run_id}_{step.step_id}"
            state.pending_tool_calls[tool_call_id] = {
                "step_id": step.step_id,
                "tool_name": step.tool_id or step.capability_id,
                "step_index": workflow.execution_plan.index(step),
                "arguments": dict(tool_args),
            }
            state.metadata["last_step_args"] = dict(tool_args)
            call_summaries.append(f"`{step.tool_id}` for `{step.step_id}`")
            tool_calls.append(
                self._build_tool_call(
                    tool_call_id=tool_call_id,
                    tool_name=step.tool_id or step.capability_id,
                    arguments=tool_args,
                )
            )

        content = "Calling tools: " + ", ".join(call_summaries)
        return self._make_tool_call_message(content=content, tool_calls=tool_calls)

    def _handle_tool_messages(self, context: ToolClawTau3TurnContext, tool_messages: List[Any]) -> Any:
        state = context.state
        workflow = state.workflow
        if workflow is None or not state.pending_tool_calls:
            return self._make_assistant_message("Received tool output without a pending tool call.")

        parsed_results = {result.tool_call_id: result for result in self._parse_tool_results(tool_messages)}
        unresolved = [call_id for call_id in state.pending_tool_calls if call_id not in parsed_results]
        if unresolved:
            return self._make_assistant_message(
                f"Received partial tool output. Still waiting on: {', '.join(sorted(unresolved))}."
            )

        for call_id, pending in sorted(state.pending_tool_calls.items(), key=lambda item: item[1]["step_index"]):
            step_id = str(pending["step_id"])
            step = workflow.get_step(step_id)
            if step is None:
                return self._make_assistant_message(f"Unable to find workflow step `{step_id}`.")
            parsed = parsed_results[call_id]
            if parsed.error:
                error = self._build_tool_error(context=context, step=step, parsed_result=parsed)
                repair = self.recovery_engine.plan_repair(
                    error=error,
                    backup_tool_id=context.backup_tool_map.get(step.tool_id or ""),
                )
                state.pending_tool_calls = {}
                return self._apply_repair(context, step, repair)

            state.final_state.update(
                self.tool_bridge.map_tool_result_to_state_patch(
                    tool_id=step.tool_id or step.capability_id,
                    parsed_result=parsed,
                    step=step,
                )
            )
            after_decision = self.policy_engine.evaluate_after_step(step, workflow, state.final_state)
            state.final_state.update(after_decision.state_patch)
            if step.step_id not in state.completed_step_ids:
                state.completed_step_ids.append(step.step_id)

        state.pending_tool_calls = {}
        self._advance_cursor(state, workflow)
        return self._emit_next_action(context)

    def _apply_repair(self, context: ToolClawTau3TurnContext, step: WorkflowStep, repair: Any) -> Any:
        state = context.state
        workflow = state.workflow
        if workflow is None:
            return self._make_assistant_message("Repair requested, but no workflow is loaded.")

        if repair.repair_type.value == "switch_tool":
            for action in repair.actions:
                if action.action_type.value == "switch_tool" and isinstance(action.value, str):
                    step.tool_id = action.value
                    break
            return self._emit_next_action(context)

        if repair.repair_type.value == "rebind_args":
            for action in repair.actions:
                if action.action_type.value != "state_patch" or not action.target:
                    continue
                if ".inputs." in action.target:
                    key = action.target.split(".inputs.", 1)[1]
                    step.inputs[key] = action.value
            return self._emit_next_action(context)

        if repair.repair_type.value in {"ask_user", "request_approval"}:
            state.pending_user_question = repair.interaction.question or "Please provide the missing information."
            state.pending_repair_type = repair.repair_type.value
            state.pending_step_id = step.step_id
            return self._make_assistant_message(state.pending_user_question)

        state.finished = True
        return self._make_assistant_message(f"Recovery path `{repair.repair_type.value}` is not yet automated.")

    def _handle_user_reply(self, context: ToolClawTau3TurnContext) -> Any:
        state = context.state
        workflow = state.workflow
        if workflow is None or state.pending_step_id is None:
            state.pending_user_question = None
            state.pending_repair_type = None
            return self._make_assistant_message("No pending interaction is active.")

        text = self.adapter._coerce_message_text(context.incoming_message).lower()
        step = workflow.get_step(state.pending_step_id)
        if step is None:
            state.pending_user_question = None
            state.pending_repair_type = None
            return self._make_assistant_message(f"Unable to resolve pending step `{state.pending_step_id}`.")

        if state.pending_repair_type == "request_approval":
            if any(token in text for token in ("approve", "approved", "yes", "continue")):
                approved = set(state.final_state.get("__approved_steps__", []))
                approved.add(step.step_id)
                state.final_state["__approved_steps__"] = sorted(approved)
                state.pending_user_question = None
                state.pending_repair_type = None
                state.pending_step_id = None
                return self._emit_next_action(context)
            state.finished = True
            state.pending_user_question = None
            state.pending_repair_type = None
            return self._make_assistant_message("Approval was not granted. Stopping execution.")

        patch = self._extract_user_patch(context.incoming_message)
        if patch:
            step.inputs.update(patch)
            state.pending_user_question = None
            state.pending_repair_type = None
            state.pending_step_id = None
            return self._emit_next_action(context)

        return self._make_assistant_message(
            "I still need structured input for the pending step. "
            "Reply with JSON like {\"target_path\": \"...\"} or similar key/value pairs."
        )

    def _extract_user_patch(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            return {
                key: value
                for key, value in message.items()
                if key not in {"role", "content", "tool_calls"}
            }
        text = self.adapter._coerce_message_text(message)
        if not text:
            return {}
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
        if "=" in text:
            patch: Dict[str, Any] = {}
            for part in text.split(","):
                if "=" not in part:
                    continue
                key, value = part.split("=", 1)
                patch[key.strip()] = value.strip()
            return patch
        return {}

    @staticmethod
    def _extract_tool_messages(message: Any) -> List[Any]:
        if message is None:
            return []
        if isinstance(message, list):
            return list(message)
        if hasattr(message, "tool_messages"):
            tool_messages = getattr(message, "tool_messages", None)
            if isinstance(tool_messages, list):
                return list(tool_messages)
        if hasattr(message, "role") and getattr(message, "role", None) == "tool":
            return [message]
        if isinstance(message, dict):
            if isinstance(message.get("tool_messages"), list):
                return list(message["tool_messages"])
            if message.get("role") == "tool" or "error" in message:
                return [message]
        return []

    @staticmethod
    def _extract_tool_message_id(message: Any) -> str:
        if isinstance(message, dict):
            return str(message.get("id") or "")
        return str(getattr(message, "id", "") or "")

    def _build_tool_error(self, context: ToolClawTau3TurnContext, step: WorkflowStep, parsed_result: ParsedToolResult) -> ToolClawError:
        return self.tool_error_mapper.build_error(
            context=context,
            step=step,
            parsed_result=parsed_result,
        )

    def _parse_tool_results(self, tool_messages: List[Any]) -> List[ParsedToolResult]:
        return [self._parse_single_tool_result(message) for message in tool_messages]

    def _parse_single_tool_result(self, message: Any) -> ParsedToolResult:
        tool_call_id = self._extract_tool_message_id(message)
        content_raw = self._extract_tool_message_content_raw(message)
        envelope_error = self._tool_message_error(message)
        parsed_value, parse_error = self._coerce_structured_content(content_raw)
        payload = self._extract_payload(parsed_value)
        metadata = self._extract_metadata(parsed_value)
        metadata.update(self._extract_tool_message_envelope_metadata(message))
        error = envelope_error or bool(parse_error)
        if isinstance(parsed_value, dict):
            if parsed_value.get("error") is True:
                error = True
            if parsed_value.get("ok") is False or parsed_value.get("success") is False:
                error = True
        if not tool_call_id:
            error = True
            parse_error = parse_error or "missing_tool_call_id"
        return ParsedToolResult(
            tool_call_id=tool_call_id,
            content_raw=content_raw,
            content_value=parsed_value,
            payload=payload,
            metadata=metadata,
            error=error,
            parse_error=parse_error,
        )

    @staticmethod
    def _resolve_step_inputs(step: WorkflowStep, state_values: Dict[str, Any]) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}
        for key, value in step.inputs.items():
            if isinstance(value, str) and key.endswith("_key") and value in state_values:
                resolved[key] = state_values[value]
            else:
                resolved[key] = value
        return resolved

    @staticmethod
    def _advance_cursor(state: ToolClawTau3State, workflow: Workflow) -> None:
        while state.current_step_index < len(workflow.execution_plan):
            step = workflow.execution_plan[state.current_step_index]
            if step.step_id in state.completed_step_ids:
                state.current_step_index += 1
                continue
            break

    @staticmethod
    def _collect_ready_steps(workflow: Workflow, state: ToolClawTau3State) -> List[WorkflowStep]:
        if state.pending_tool_calls:
            return []
        ready: List[WorkflowStep] = []
        for step in workflow.execution_plan[state.current_step_index :]:
            if step.step_id in state.completed_step_ids:
                continue
            node = workflow.get_node(step.step_id)
            dependencies = list(node.dependencies) if node is not None else []
            if any(dep not in state.completed_step_ids for dep in dependencies):
                if ready:
                    break
                return []
            ready.append(step)
            if dependencies:
                break
        return ready[:4]

    @staticmethod
    def _extract_tool_message_content_raw(message: Any) -> Any:
        if isinstance(message, dict):
            return message.get("content")
        return getattr(message, "content", None)

    @staticmethod
    def _tool_message_error(message: Any) -> bool:
        if isinstance(message, dict):
            return bool(message.get("error", False))
        return bool(getattr(message, "error", False))

    @staticmethod
    def _coerce_structured_content(content: Any) -> tuple[Any, Optional[str]]:
        if content is None:
            return "", None
        if isinstance(content, (dict, list, int, float, bool)):
            return content, None
        if isinstance(content, str):
            stripped = content.strip()
            if not stripped:
                return "", None
            try:
                return json.loads(stripped), None
            except json.JSONDecodeError:
                return stripped, None
        return str(content), f"unsupported_content_type:{type(content).__name__}"

    @staticmethod
    def _extract_payload(parsed_value: Any) -> Any:
        if isinstance(parsed_value, dict):
            for key in ("payload", "result", "output", "data", "value", "content"):
                if key in parsed_value:
                    return parsed_value[key]
        return parsed_value

    @staticmethod
    def _extract_metadata(parsed_value: Any) -> Dict[str, Any]:
        if not isinstance(parsed_value, dict):
            return {}
        if isinstance(parsed_value.get("metadata"), dict):
            return dict(parsed_value["metadata"])
        metadata = {
            key: value
            for key, value in parsed_value.items()
            if key not in {"payload", "result", "output", "data", "value", "content"}
        }
        return metadata

    @staticmethod
    def _extract_tool_message_envelope_metadata(message: Any) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        for key in ("requestor", "turn_idx", "timestamp", "role"):
            value = message.get(key) if isinstance(message, dict) else getattr(message, key, None)
            if value is not None:
                metadata[key] = value
        return metadata

    def _normalize_workflow_for_benchmark(self, workflow: Workflow) -> None:
        permissions = workflow.context.environment.permissions
        if "tau3_permissions_normalized" in workflow.metadata:
            return

        inferred_requires_write = False
        inferred_requires_network = False
        inferred_requires_api = False
        for step in workflow.execution_plan:
            haystack = " ".join(
                [
                    step.capability_id.lower(),
                    (step.tool_id or "").lower(),
                    step.expected_output or "",
                ]
            ).lower()
            if any(keyword in haystack for keyword in {"write", "save", "output", "report"}):
                inferred_requires_write = True
            if any(keyword in haystack for keyword in {"search", "retrieve", "web", "download"}):
                inferred_requires_network = True
            if "api" in haystack:
                inferred_requires_api = True

        domain_text = self.adapter._stringify_domain_policy(self.domain_policy).lower()
        if inferred_requires_write and "read_only" not in domain_text:
            permissions.filesystem_write = True
        if inferred_requires_network and "no_network" not in domain_text:
            permissions.network = True
        if inferred_requires_api:
            permissions.external_api = True
        workflow.metadata["tau3_permissions_normalized"] = True

    @staticmethod
    def _stringify_tool_content(value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, sort_keys=True)
        except TypeError:
            return str(value)

    @staticmethod
    def _format_completion_text(final_state: Dict[str, Any]) -> str:
        visible_keys = sorted(key for key in final_state.keys() if not key.startswith("__"))
        if not visible_keys:
            return "ToolClaw completed the workflow."
        return f"ToolClaw completed the workflow. Final state keys: {', '.join(visible_keys)}"

    @staticmethod
    def _build_tool_call(tool_call_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if TAU3_BENCH_AVAILABLE and ToolCall is not None:
            return ToolCall(id=tool_call_id, name=tool_name, arguments=arguments, requestor="assistant")
        return FallbackToolCall(id=tool_call_id, name=tool_name, arguments=arguments, requestor="assistant")

    @staticmethod
    def _make_tool_call_message(content: str, tool_calls: List[Any]) -> Any:
        if TAU3_BENCH_AVAILABLE and AssistantMessage is not None:
            return AssistantMessage.text(content, tool_calls=tool_calls)
        return FallbackAssistantMessage(content=content, tool_calls=tool_calls)

    @staticmethod
    def _make_assistant_message(content: str) -> Any:
        if TAU3_BENCH_AVAILABLE and AssistantMessage is not None:
            return AssistantMessage.text(content)
        return FallbackAssistantMessage(content=content)

    @staticmethod
    def _build_default_runtime() -> ToolClawRuntime:
        registry = InMemoryAssetRegistry()
        return ToolClawRuntime(
            planner=build_default_planner(asset_registry=registry),
            executor=SequentialExecutor(),
            repair_updater=RepairUpdater(),
            compiler=SWPCCompiler(),
            asset_registry=registry,
        )


def create_toolclaw_tau3_agent(
    tools: Sequence[Any],
    domain_policy: Any,
    **kwargs: Any,
) -> ToolClawTau3Agent:
    """Factory matching the benchmark's expected agent constructor signature."""

    return ToolClawTau3Agent(tools=tools, domain_policy=domain_policy, **kwargs)
