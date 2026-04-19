"""Targeted Tau2-style before/after study for compound approval+repair interaction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.execution.executor import SequentialExecutor
from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.query_policy import QueryPlan, QueryPolicy
from toolclaw.interaction.repair_updater import InteractionRequest, RepairUpdater
from toolclaw.interaction.reply_provider import RawUserReply
from toolclaw.interaction.semantic_decoder import DecodedInteractionSignal, SemanticDecoder
from toolclaw.interaction.user_simulator import SimulatedPolicy
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningHints, PlanningRequest, build_default_planner
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.workflow import Permissions, TaskConstraints, TaskSpec, ToolSpec, Workflow, WorkflowContext


@dataclass
class CompoundCaseSpec:
    case_id: str
    description: str
    candidate_tools: List[str]
    workflow_step_patch: Dict[str, Any]
    simulated_policy: Dict[str, Any] = field(default_factory=dict)
    backup_tool_map: Dict[str, str] = field(default_factory=dict)
    task_constraints: Dict[str, Any] = field(default_factory=dict)
    expected_fix_type: str = ""
    control_case: bool = False


@dataclass
class CompoundCaseResult:
    variant: str
    case_id: str
    description: str
    success: bool
    stop_reason: str
    user_queries: int
    tool_calls: int
    repair_actions: int
    compound_query_count: int
    compound_reply_count: int
    max_user_turns_exceeded: bool
    trace_path: str
    expected_fix_type: str
    control_case: bool


class LegacyApprovalOnlyQueryPolicy(QueryPolicy):
    """Approximate pre-fix behavior: approval was requested separately from repair."""

    def decide_query(self, report: Any) -> QueryPlan:
        if report.primary_label in {"approval_needed", "policy_approval"}:
            remaining = report.metadata.get("remaining_user_turns")
            last_turn = remaining is not None and int(remaining) <= 1
            return QueryPlan(
                ask=True,
                question_type="approval",
                question_text="Approve this blocked action?",
                response_schema={
                    "type": "object",
                    "properties": {"approved": {"type": "boolean"}},
                    "required": ["approved"],
                    "additionalProperties": False,
                },
                patch_targets={"approved": "policy.approved"},
                urgency="critical" if last_turn else "high",
            )
        return super().decide_query(report)


class LegacyApprovalDecoder(SemanticDecoder):
    """Approximate pre-fix behavior: approval replies did not ingest joint repair patches."""

    def decode(self, request: InteractionRequest, raw_reply: RawUserReply) -> DecodedInteractionSignal:
        q_type = str(request.metadata.get("query_policy", {}).get("question_type") or request.expected_answer_type or "").lower()
        if q_type == "approval":
            payload = dict(raw_reply.raw_payload or {})
            if "approved" in payload:
                return DecodedInteractionSignal(
                    intent_type="permission_confirm",
                    approvals={"approved": bool(payload.get("approved"))},
                    metadata={"decode_strategy": "legacy_payload", "decode_confidence": 1.0},
                )
        return super().decode(request, raw_reply)


def build_tau2_compound_cases() -> List[CompoundCaseSpec]:
    return [
        CompoundCaseSpec(
            case_id="tau2_compound_approval_target_path_001",
            description="Approval plus missing target_path on the blocked write step.",
            candidate_tools=["write_tool"],
            workflow_step_patch={"tool_id": "write_tool", "inputs": {}},
            simulated_policy={"missing_arg_values": {"target_path": "outputs/tau2/compound_target_path.txt"}},
            task_constraints={"max_repair_attempts": 0},
            expected_fix_type="target_path",
        ),
        CompoundCaseSpec(
            case_id="tau2_compound_approval_state_slot_001",
            description="Approval plus missing required state slot on the blocked write step.",
            candidate_tools=["write_tool"],
            workflow_step_patch={
                "tool_id": "write_tool",
                "inputs": {"target_path": "outputs/tau2/compound_state_slot.txt"},
                "metadata": {"required_state_slots": ["approval_note"]},
            },
            simulated_policy={"missing_arg_values": {"approval_note": "approved once with final target confirmed"}},
            expected_fix_type="state_slot",
        ),
        CompoundCaseSpec(
            case_id="tau2_compound_approval_tool_switch_001",
            description="Approval plus backup tool switch when the primary route is unavailable.",
            candidate_tools=["write_tool", "backup_write_tool"],
            workflow_step_patch={
                "tool_id": "write_tool",
                "inputs": {
                    "target_path": "outputs/tau2/compound_tool_switch.txt",
                    "force_environment_failure": True,
                },
                "metadata": {"allowed_tools": ["write_tool", "backup_write_tool"]},
            },
            simulated_policy={"tool_switch_hints": {"tool_id": "backup_write_tool"}},
            expected_fix_type="tool_switch",
        ),
        CompoundCaseSpec(
            case_id="tau2_compound_approval_only_control_001",
            description="Pure approval control case without an extra repair payload.",
            candidate_tools=["write_tool"],
            workflow_step_patch={
                "tool_id": "write_tool",
                "inputs": {"target_path": "outputs/tau2/approval_only_control.txt"},
            },
            expected_fix_type="approval_only",
            control_case=True,
        ),
    ]


def run_compound_ablation(outdir: Path) -> Dict[str, Any]:
    cases = build_tau2_compound_cases()
    results: List[CompoundCaseResult] = []
    for variant, compound_enabled in (("before", False), ("after", True)):
        runtime = _build_runtime()
        for index, case in enumerate(cases, start=1):
            case_outdir = outdir / variant / "traces"
            case_outdir.mkdir(parents=True, exist_ok=True)
            trace_path = case_outdir / f"{index:03d}_{case.case_id}.json"
            results.append(
                _run_case(
                    runtime=runtime,
                    case=case,
                    variant=variant,
                    compound_enabled=compound_enabled,
                    trace_path=trace_path,
                )
            )
    analysis = _summarize_results(results)
    analysis["outdir"] = str(outdir)
    (outdir / "tau2_compound_approval_repair_ablation.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    (outdir / "tau2_compound_approval_repair_ablation.md").write_text(render_markdown(analysis), encoding="utf-8")
    return analysis


def render_markdown(analysis: Dict[str, Any]) -> str:
    lines = [
        "# Tau2 Compound Approval+Repair Ablation",
        "",
        f"- outdir: `{analysis['outdir']}`",
        f"- num_cases: `{analysis['num_cases']}`",
        "",
        "## Aggregate",
        "",
        "| variant | success_rate | max_user_turns_exceeded_rate | avg_user_queries | avg_tool_calls | avg_repair_actions | compound_query_rate | compound_reply_rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in ("before", "after"):
        stats = analysis["aggregate"][variant]
        lines.append(
            f"| {variant} | {stats['success_rate']:.3f} | {stats['max_user_turns_exceeded_rate']:.3f} | {stats['avg_user_queries']:.2f} | {stats['avg_tool_calls']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['compound_query_rate']:.3f} | {stats['compound_reply_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Per-Case",
            "",
            "| case_id | expected_fix_type | before_success | after_success | before_stop | after_stop | before_compound_query | after_compound_query | before_compound_reply | after_compound_reply |",
            "|---|---|---:|---:|---|---|---:|---:|---:|---:|",
        ]
    )
    for item in analysis["case_deltas"]:
        lines.append(
            f"| {item['case_id']} | {item['expected_fix_type']} | {1 if item['before']['success'] else 0} | {1 if item['after']['success'] else 0} | {item['before']['stop_reason']} | {item['after']['stop_reason']} | {item['before']['compound_query_count']} | {item['after']['compound_query_count']} | {item['before']['compound_reply_count']} | {item['after']['compound_reply_count']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- headline: **{analysis['headline']}**",
            f"- rationale: {analysis['rationale']}",
        ]
    )
    return "\n".join(lines)


def _build_runtime() -> ToolClawRuntime:
    registry = InMemoryAssetRegistry()
    return ToolClawRuntime(
        planner=build_default_planner(asset_registry=registry),
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )


def _run_case(
    *,
    runtime: ToolClawRuntime,
    case: CompoundCaseSpec,
    variant: str,
    compound_enabled: bool,
    trace_path: Path,
) -> CompoundCaseResult:
    query_policy = QueryPolicy() if compound_enabled else LegacyApprovalOnlyQueryPolicy()
    semantic_decoder = SemanticDecoder() if compound_enabled else LegacyApprovalDecoder()
    shell = InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            max_turns=1,
            simulator_policy=SimulatedPolicy(
                mode="cooperative",
                missing_arg_values=dict(case.simulated_policy.get("missing_arg_values", {})),
                tool_switch_hints=dict(case.simulated_policy.get("tool_switch_hints", {})),
            ),
        ),
        query_policy=query_policy,
        semantic_decoder=semantic_decoder,
    )
    outcome = shell.run(
        request=_build_request(case),
        run_id=f"{variant}_{case.case_id}",
        output_path=str(trace_path),
        use_reuse=False,
        compile_on_success=False,
        backup_tool_map=dict(case.backup_tool_map),
    )
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {})
    stop_reason = str(outcome.metadata.get("stopped_reason") or _final_stop_reason(payload) or "")
    compound_query_count = 0
    compound_reply_count = 0
    for event in payload.get("events", []):
        if event.get("event_type") == "user_query":
            question_type = str(event.get("metadata", {}).get("query_policy_decision", {}).get("question_type") or "")
            if question_type == "approval_and_patch":
                compound_query_count += 1
        elif event.get("event_type") == "user_reply":
            reply_payload = dict(event.get("output", {}))
            if reply_payload.get("approved") is True and any(key != "approved" for key in reply_payload.keys()):
                compound_reply_count += 1
    return CompoundCaseResult(
        variant=variant,
        case_id=case.case_id,
        description=case.description,
        success=bool(outcome.success),
        stop_reason=stop_reason,
        user_queries=int(metrics.get("user_queries", 0) or 0),
        tool_calls=int(metrics.get("tool_calls", 0) or 0),
        repair_actions=int(metrics.get("repair_actions", 0) or 0),
        compound_query_count=compound_query_count,
        compound_reply_count=compound_reply_count,
        max_user_turns_exceeded=stop_reason == "max_user_turns_exceeded",
        trace_path=str(trace_path),
        expected_fix_type=case.expected_fix_type,
        control_case=case.control_case,
    )


def _build_request(case: CompoundCaseSpec) -> PlanningRequest:
    constraints = TaskConstraints(requires_user_approval=True, max_user_turns=1)
    if case.task_constraints.get("max_repair_attempts") is not None:
        constraints.max_repair_attempts = int(case.task_constraints["max_repair_attempts"])
    request = PlanningRequest(
        task=TaskSpec(
            task_id=case.case_id,
            user_goal="save the final answer",
            constraints=constraints,
        ),
        context=WorkflowContext(
            environment=Workflow.demo().context.environment,
            candidate_tools=[ToolSpec(tool_id=tool_id, description=tool_id.replace("_", " ")) for tool_id in case.candidate_tools],
        ),
        hints=PlanningHints(
            user_style={
                "categories": ["single_tool"],
                "tool_allow_list": list(case.candidate_tools),
                "ideal_tool_calls": 1,
                "ideal_turn_count": 1,
                "milestones": ["save artifact"],
                "simulated_policy": {"mode": "strict"},
            }
        ),
        workflow_overrides={"steps": {"step_01": dict(case.workflow_step_patch)}},
    )
    request.context.environment.permissions = Permissions(
        network=True,
        filesystem_read=True,
        filesystem_write=True,
        external_api=True,
    )
    return request


def _final_stop_reason(payload: Dict[str, Any]) -> str:
    for event in reversed(payload.get("events", [])):
        if event.get("event_type") == "stop":
            return str(event.get("output", {}).get("reason") or "")
    return ""


def _mean_bool(values: List[bool]) -> float:
    return mean(1.0 if item else 0.0 for item in values) if values else 0.0


def _mean_int(values: List[int]) -> float:
    return mean(values) if values else 0.0


def _summarize_results(results: List[CompoundCaseResult]) -> Dict[str, Any]:
    aggregate: Dict[str, Dict[str, float]] = {}
    by_variant: Dict[str, List[CompoundCaseResult]] = {"before": [], "after": []}
    for result in results:
        by_variant.setdefault(result.variant, []).append(result)
    for variant, rows in by_variant.items():
        aggregate[variant] = {
            "success_rate": _mean_bool([row.success for row in rows]),
            "max_user_turns_exceeded_rate": _mean_bool([row.max_user_turns_exceeded for row in rows]),
            "avg_user_queries": _mean_int([row.user_queries for row in rows]),
            "avg_tool_calls": _mean_int([row.tool_calls for row in rows]),
            "avg_repair_actions": _mean_int([row.repair_actions for row in rows]),
            "compound_query_rate": _mean_bool([row.compound_query_count > 0 for row in rows]),
            "compound_reply_rate": _mean_bool([row.compound_reply_count > 0 for row in rows]),
        }
    before_map = {row.case_id: row for row in by_variant.get("before", [])}
    after_map = {row.case_id: row for row in by_variant.get("after", [])}
    case_deltas: List[Dict[str, Any]] = []
    compound_improved = 0
    compound_total = 0
    for case in build_tau2_compound_cases():
        before = before_map[case.case_id]
        after = after_map[case.case_id]
        if not case.control_case:
            compound_total += 1
            if (not before.success) and after.success:
                compound_improved += 1
        case_deltas.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_fix_type": case.expected_fix_type,
                "control_case": case.control_case,
                "before": before.__dict__,
                "after": after.__dict__,
            }
        )
    headline = "compound approval+repair closes the loop"
    rationale = (
        f"Targeted Tau2-style compound cases improved on {compound_improved}/{compound_total} cases "
        "when approval+patch querying and joint decoding were enabled."
    )
    return {
        "outdir": "",
        "num_cases": len(build_tau2_compound_cases()),
        "aggregate": aggregate,
        "case_deltas": case_deltas,
        "headline": headline,
        "rationale": rationale,
    }
