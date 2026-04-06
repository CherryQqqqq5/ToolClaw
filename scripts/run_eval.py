"""Entry point for Phase-1 A0-A4 evaluation over normalized tasksets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow `python3 scripts/run_eval.py ...` from repo root without manual PYTHONPATH.
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toolclaw.benchmarks.baseline_runner import run_baseline
from toolclaw.benchmarks.metrics import (
    EvalRow,
    summarize,
    summarize_by_scenario,
    write_report_md,
    write_rows_csv,
)
from toolclaw.compiler.swpc import SWPCCompiler, build_task_signature_candidates
from toolclaw.execution.executor import ExecutorConfig, SequentialExecutor
from toolclaw.execution.recovery import RecoveryConfig, RecoveryEngine
from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.user_simulator import SimulatedPolicy
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
from toolclaw.registry import AssetRegistry, FileAssetRegistry, InMemoryAssetRegistry
from toolclaw.schemas.workflow import RiskLevel, TaskConstraints, ToolSpec, Workflow


@dataclass(frozen=True)
class SystemSpec:
    system_id: str
    workflow_mode: str
    execution_mode: str
    compile_on_success: bool = False
    use_reuse: bool = False
    allow_repair: bool = True
    allow_fallback: bool = True


SYSTEM_SPECS: Dict[str, SystemSpec] = {
    "a0_baseline": SystemSpec(system_id="a0_baseline", workflow_mode="demo", execution_mode="baseline"),
    "a1_recovery": SystemSpec(system_id="a1_recovery", workflow_mode="demo", execution_mode="executor"),
    "a2_planner": SystemSpec(system_id="a2_planner", workflow_mode="planner", execution_mode="executor"),
    "a3_interaction": SystemSpec(
        system_id="a3_interaction",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
    ),
    "a4_reuse": SystemSpec(
        system_id="a4_reuse",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=True,
        use_reuse=True,
    ),
    "tc_full": SystemSpec(
        system_id="tc_full",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=True,
        use_reuse=True,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_no_repair": SystemSpec(
        system_id="tc_no_repair",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=False,
        allow_fallback=False,
    ),
    "tc_no_fallback": SystemSpec(
        system_id="tc_no_fallback",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=False,
    ),
    "tc_no_reuse": SystemSpec(
        system_id="tc_no_reuse",
        workflow_mode="planner",
        execution_mode="interaction",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
    "tc_planner_only": SystemSpec(
        system_id="tc_planner_only",
        workflow_mode="planner",
        execution_mode="executor",
        compile_on_success=False,
        use_reuse=False,
        allow_repair=True,
        allow_fallback=True,
    ),
}

SYSTEM_ALIASES: Dict[str, str] = {
    "baseline": "a0_baseline",
    "planning": "a2_planner",
    "interactive": "a3_interaction",
    "toolclaw_lite": "a3_interaction",
}


def build_workflow_from_task(task: Dict[str, Any], mode: str = "demo") -> Workflow:
    if mode == "planner":
        planner = build_default_planner()
        demo = Workflow.demo()
        request = PlanningRequest(
            task=demo.task,
            context=demo.context,
            policy=demo.policy,
        )
        request.task.task_id = canonical_task_id(task)
        request.task.user_goal = str(task.get("query") or request.task.user_goal)
        workflow = planner.plan(request).workflow
    else:
        workflow = Workflow.demo()

    workflow.task.task_id = canonical_task_id(task)

    raw_metadata = task.get("metadata")
    toolsandbox_metadata = raw_metadata if isinstance(raw_metadata, dict) and raw_metadata.get("benchmark") == "toolsandbox" else {}
    retrieve_query = task.get("query")
    if not retrieve_query and isinstance(task.get("messages"), list):
        for message in task["messages"]:
            if not isinstance(message, dict):
                continue
            sender = str(message.get("sender") or message.get("role") or "").lower()
            if sender == "user" and message.get("content"):
                retrieve_query = str(message["content"])
                break
    if retrieve_query:
        workflow.execution_plan[0].inputs["query"] = retrieve_query

    if task.get("target_path") is not None and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs["target_path"] = task["target_path"]

    raw_constraints = task.get("constraints")
    if isinstance(raw_constraints, dict):
        constraints = TaskConstraints(
            budget_limit=float(raw_constraints["budget_limit"]) if raw_constraints.get("budget_limit") is not None else None,
            time_limit=float(raw_constraints["time_limit"]) if raw_constraints.get("time_limit") is not None else None,
            requires_user_approval=bool(raw_constraints.get("requires_user_approval", False)),
            forbidden_actions=list(raw_constraints.get("forbidden_actions", [])) if raw_constraints.get("forbidden_actions") else [],
        )
        risk_level = raw_constraints.get("risk_level")
        if risk_level in {"low", "medium", "high"}:
            constraints.risk_level = RiskLevel(risk_level)
        workflow.task.constraints = constraints

    raw_tools = task.get("candidate_tools")
    if isinstance(raw_tools, list) and raw_tools:
        candidate_tools: List[ToolSpec] = []
        for idx, raw_tool in enumerate(raw_tools, start=1):
            if isinstance(raw_tool, str):
                candidate_tools.append(ToolSpec(tool_id=raw_tool, description=raw_tool))
                continue
            if isinstance(raw_tool, dict):
                candidate_tools.append(
                    ToolSpec(
                        tool_id=str(raw_tool.get("tool_id") or raw_tool.get("name") or f"tool_{idx:02d}"),
                        description=str(raw_tool.get("description") or raw_tool.get("tool_id") or raw_tool.get("name") or "tool"),
                        metadata={k: v for k, v in raw_tool.items() if k not in {"tool_id", "name", "description"}},
                    )
                )
        if candidate_tools:
            workflow.context.candidate_tools = candidate_tools

    if isinstance(raw_metadata, dict):
        workflow.metadata.update(raw_metadata)
    workflow.metadata["task_family"] = derive_task_family(task, scenario=str(task.get("scenario", "success")), task_id=workflow.task.task_id)
    workflow.metadata["failure_type"] = derive_failure_type(task, scenario=str(task.get("scenario", "success")))
    workflow.metadata["scenario"] = str(task.get("scenario", "success"))
    if task.get("messages") is not None:
        workflow.metadata["messages"] = list(task.get("messages", []))
    if task.get("milestones") is not None:
        workflow.metadata["milestones"] = list(task.get("milestones", []))
    if task.get("tool_allow_list") is not None:
        workflow.metadata["tool_allow_list"] = list(task.get("tool_allow_list", []))
    if task.get("branch_options") is not None:
        workflow.metadata["branch_options"] = list(task.get("branch_options", []))
    if task.get("reference_result_summary") is not None:
        workflow.metadata["toolsandbox_reference_result"] = dict(task.get("reference_result_summary", {}))
    if task.get("ideal_turn_count") is not None:
        workflow.metadata["ideal_turn_count"] = task.get("ideal_turn_count")
    if task.get("ideal_tool_calls") is not None:
        workflow.metadata["ideal_tool_calls"] = task.get("ideal_tool_calls")

    if toolsandbox_metadata:
        allow_list = workflow.metadata.get("tool_allow_list") or []
        scenario = str(task.get("scenario", "toolsandbox"))
        ideal_tool_calls = task.get("ideal_tool_calls")
        low_branching = (
            len(allow_list) == 1
            or scenario in {"single_tool", "single_user_turn"}
            or ideal_tool_calls == 1
            or bool(toolsandbox_metadata.get("low_branching"))
        )
        if low_branching:
            workflow.execution_plan = workflow.execution_plan[:1]
            workflow.tool_bindings = workflow.tool_bindings[:1]
            workflow.workflow_graph.nodes = workflow.workflow_graph.nodes[:1]
            workflow.workflow_graph.edges = []
            workflow.workflow_graph.entry_nodes = ["step_01"]
            workflow.workflow_graph.exit_nodes = ["step_01"]
            workflow.metadata["low_branching_fast_path"] = True
            if allow_list and workflow.execution_plan:
                selected_tool = str(allow_list[0])
                workflow.execution_plan[0].tool_id = selected_tool
                if workflow.tool_bindings:
                    workflow.tool_bindings[0].primary_tool = selected_tool
                if workflow.workflow_graph.nodes:
                    workflow.workflow_graph.nodes[0].selected_tool = selected_tool
                    workflow.workflow_graph.nodes[0].tool_candidates = [selected_tool]

    scenario = task.get("scenario", "success")
    if scenario == "binding_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs.pop("target_path", None)
    elif scenario == "environment_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs["force_environment_failure"] = True

    return workflow


def existing_json_path(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(
            f"taskset file not found: {path}. Provide a real JSON file path (for example: data/eval_tasks.sample.json)."
        )
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"taskset path is not a file: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase-1 A0-A4 evaluation")
    parser.add_argument("--taskset", type=existing_json_path, required=True, help="Path to taskset JSON")
    parser.add_argument("--outdir", default="outputs/eval", help="Output directory")
    parser.add_argument(
        "--mode",
        choices=["demo", "planner"],
        default="planner",
        help="Legacy workflow source mode for alias compatibility; A0-A4 use fixed modes.",
    )
    parser.add_argument(
        "--systems",
        default="a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse",
        help=(
            "Comma-separated systems to run: "
            "a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse. "
            "Supported legacy aliases: baseline,planning,interactive,toolclaw_lite."
        ),
    )
    parser.add_argument(
        "--asset-registry-root",
        default=None,
        help=(
            "Optional directory for file-backed reusable assets. "
            "When set, each non-baseline system persists artifacts under <root>/<system_id> so reuse can survive across CLI invocations."
        ),
    )
    return parser.parse_args()


def build_runtime(asset_registry: Optional[AssetRegistry] = None) -> ToolClawRuntime:
    return build_runtime_for_spec(
        asset_registry=asset_registry,
        spec=SYSTEM_SPECS["a4_reuse"],
    )


def build_runtime_for_spec(
    *,
    spec: SystemSpec,
    asset_registry: Optional[AssetRegistry] = None,
) -> ToolClawRuntime:
    registry = asset_registry or InMemoryAssetRegistry()
    planner = build_default_planner(asset_registry=registry)
    return ToolClawRuntime(
        planner=planner,
        executor=SequentialExecutor(
            recovery_engine=RecoveryEngine(
                RecoveryConfig(enable_tool_fallback=spec.allow_fallback)
            ),
            config=ExecutorConfig(allow_repair=spec.allow_repair),
        ),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=registry,
    )


def parse_systems(raw_systems: str) -> List[SystemSpec]:
    system_specs: List[SystemSpec] = []
    seen: set[str] = set()
    for raw_system in raw_systems.split(","):
        candidate = raw_system.strip()
        if not candidate:
            continue
        canonical = SYSTEM_ALIASES.get(candidate, candidate)
        if canonical not in SYSTEM_SPECS:
            raise ValueError(f"unsupported system '{candidate}'. Valid systems: {', '.join(sorted(SYSTEM_SPECS))}")
        if canonical in seen:
            continue
        seen.add(canonical)
        system_specs.append(SYSTEM_SPECS[canonical])
    return system_specs


def build_planning_request(workflow: Workflow, *, allow_reuse: bool) -> PlanningRequest:
    request = PlanningRequest(
        task=workflow.task,
        context=workflow.context,
        policy=workflow.policy,
        workflow_overrides={
            "steps": {
                step.step_id: {
                    "inputs": dict(step.inputs),
                    "tool_id": step.tool_id,
                }
                for step in workflow.execution_plan
            }
        },
    )
    request.hints.user_style["task_family"] = str(workflow.metadata.get("task_family", "t0_general"))
    request.hints.user_style["failure_type"] = str(workflow.metadata.get("failure_type", "none"))
    request.hints.user_style["scenario"] = str(workflow.metadata.get("scenario", "success"))
    request.hints.user_style["categories"] = list(
        workflow.metadata.get("toolsandbox_categories")
        or workflow.metadata.get("categories")
        or []
    )
    request.hints.user_style["tool_allow_list"] = list(workflow.metadata.get("tool_allow_list", []))
    request.hints.user_style["branch_options"] = list(workflow.metadata.get("branch_options", []))
    request.hints.user_style["ideal_tool_calls"] = workflow.metadata.get("ideal_tool_calls")
    request.hints.user_style["ideal_turn_count"] = workflow.metadata.get("ideal_turn_count")
    request.hints.user_style["milestones"] = list(workflow.metadata.get("milestones", []))
    if not allow_reuse:
        request.hints.reusable_asset_ids = []
    return request


def build_shell(runtime: ToolClawRuntime, task: Dict[str, Any]) -> InteractionShell:
    policy_cfg = task.get("simulated_policy", {})
    return InteractionShell(
        runtime=runtime,
        config=InteractionLoopConfig(
            simulator_policy=SimulatedPolicy(
                mode=policy_cfg.get("mode", "cooperative"),
                missing_arg_values=policy_cfg.get("missing_arg_values", {}),
                backup_tool_preferences=policy_cfg.get("backup_tool_preferences", {}),
            )
        ),
    )


def canonical_task_id(task: Dict[str, Any]) -> str:
    for key in ("task_id", "sample_id", "name", "scenario_id", "id"):
        value = task.get(key)
        if value:
            return str(value)
    raise KeyError("task object must include one of: task_id, sample_id, name, scenario_id, id")


def task_signature_candidates(
    *,
    query: str,
    task_family: str | None = None,
    failure_type: str | None = None,
    capability_skeleton: Optional[List[str]] = None,
) -> List[str]:
    return build_task_signature_candidates(
        user_goal=query,
        task_family=task_family,
        capability_skeleton=capability_skeleton,
        failure_context=failure_type,
    )


def parse_reuse_pass_index(task_id: str, task: Dict[str, Any]) -> int:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_pass_index") is not None:
        return int(metadata["reuse_pass_index"])
    if task.get("reuse_pass_index") is not None:
        return int(task["reuse_pass_index"])
    match = re.search(r"__pass(\d+)$", task_id)
    return int(match.group(1)) if match else 0


def repeat_family_key(task_id: str, task: Dict[str, Any]) -> str:
    metadata = task.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("reuse_family_id"):
        return str(metadata["reuse_family_id"])
    if task.get("reuse_family_id"):
        return str(task["reuse_family_id"])
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id


def repeat_family_key_from_task_id(task_id: str) -> str:
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id


def derive_task_family(task: Dict[str, Any], scenario: str, task_id: str) -> str:
    metadata = task.get("metadata", {})
    raw_family = task.get("task_family")
    if raw_family is None and isinstance(metadata, dict):
        raw_family = metadata.get("task_family")
    if raw_family:
        return str(raw_family)

    categories = []
    raw_categories = task.get("categories")
    if isinstance(raw_categories, list):
        categories.extend(str(item).strip().lower().replace(" ", "_") for item in raw_categories)
    if isinstance(metadata, dict):
        meta_categories = metadata.get("toolsandbox_categories")
        if isinstance(meta_categories, list):
            categories.extend(str(item).strip().lower() for item in meta_categories)

    pass_index = parse_reuse_pass_index(task_id, task)
    if pass_index > 0 or (isinstance(metadata, dict) and metadata.get("reuse_family_id")):
        return "t4_repeated_reusable"
    if scenario in {"binding_failure", "environment_failure", "permission_failure", "missing_asset", "policy_failure"}:
        return "t1_static_recovery"
    if scenario in {"multiple_user_turn", "approval_required", "insufficient_information"}:
        return "t3_must_interact"
    if any(category in {"multiple_user_turn", "insufficient_information"} for category in categories):
        return "t3_must_interact"
    if any(category in {"state_dependency", "canonicalization", "multiple_tool", "dynamic_branching"} for category in categories):
        return "t2_dynamic_branching"
    if scenario in {"state_dependency", "canonicalization", "multiple_tool", "dynamic_branching"}:
        return "t2_dynamic_branching"
    return "t0_general"


def derive_failure_type(task: Dict[str, Any], scenario: str) -> str:
    metadata = task.get("metadata", {})
    raw_failure_type = task.get("failure_type")
    if raw_failure_type is None and isinstance(metadata, dict):
        raw_failure_type = metadata.get("failure_type")
    if raw_failure_type:
        return str(raw_failure_type)
    return "none" if scenario == "success" else scenario


def row_from_trace(
    *,
    task: Dict[str, Any],
    system: str,
    scenario: str,
    trace_path: Path,
    reused_artifact: bool,
) -> EvalRow:
    task_id = canonical_task_id(task)
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    events = trace_payload.get("events", [])
    metrics = trace_payload.get("metrics", {})
    stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
    stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"
    repair_triggered = sum(1 for event in events if event.get("event_type") == "repair_triggered")
    first_repair_index = next((idx for idx, event in enumerate(events) if event.get("event_type") == "repair_triggered"), None)
    observed_error_type = derive_failure_type(task, scenario)
    if first_repair_index is not None:
        observed_error_type = str(events[first_repair_index].get("metadata", {}).get("failtax_label") or observed_error_type)
    elif stop_reason == "repair_disabled":
        observed_error_type = str(trace_payload.get("metadata", {}).get("scenario") or observed_error_type)
    repair_extra_tool_calls = 0
    repair_extra_user_turns = 0
    if first_repair_index is not None:
        trailing_events = events[first_repair_index + 1 :]
        repair_extra_tool_calls = sum(1 for event in trailing_events if event.get("event_type") == "tool_call")
        repair_extra_user_turns = sum(1 for event in trailing_events if event.get("event_type") == "user_query")
    return EvalRow(
        task_id=task_id,
        system=system,
        scenario=scenario,
        task_family=derive_task_family(task, scenario, task_id),
        failure_type=derive_failure_type(task, scenario),
        success=bool(metrics.get("success")),
        tool_calls=int(metrics.get("tool_calls", 0)),
        repair_actions=int(metrics.get("repair_actions", 0)),
        repair_triggered=repair_triggered,
        user_turns=int(metrics.get("user_queries", 0)),
        total_steps=int(metrics.get("total_steps", 0)),
        token_cost=float(metrics.get("token_cost", 0.0) or 0.0),
        wall_clock_ms=int(metrics.get("latency_ms", 0) or 0),
        observed_error_type=observed_error_type,
        first_failure_recovered=bool(repair_triggered > 0 and metrics.get("success")),
        repair_extra_tool_calls=repair_extra_tool_calls,
        repair_extra_user_turns=repair_extra_user_turns,
        repair_user_clarification=bool(repair_extra_user_turns > 0),
        reuse_pass_index=parse_reuse_pass_index(task_id, task),
        reused_artifact=reused_artifact,
        second_run_improvement=0.0,
        stop_reason=str(stop_reason),
        trace_path=str(trace_path),
    )


def second_run_quality(row: EvalRow) -> float:
    fail_stop = 0.0 if row.success else 1.0
    return (100.0 if row.success else 0.0) - (20.0 * fail_stop) - float(row.tool_calls) - float(row.user_turns) - (0.5 * row.repair_actions)


def annotate_second_run_improvement(rows: List[EvalRow]) -> None:
    grouped: Dict[tuple[str, str], Dict[int, EvalRow]] = {}
    for row in rows:
        if row.reuse_pass_index <= 0:
            continue
        grouped.setdefault((row.system, repeat_family_key_from_task_id(row.task_id)), {})
        grouped[(row.system, repeat_family_key_from_task_id(row.task_id))][row.reuse_pass_index] = row

    for pass_map in grouped.values():
        if 1 not in pass_map or 2 not in pass_map:
            continue
        pass_1 = pass_map[1]
        pass_2 = pass_map[2]
        pass_2.second_run_improvement = second_run_quality(pass_2) - second_run_quality(pass_1)


def execute_system(
    *,
    spec: SystemSpec,
    task: Dict[str, Any],
    task_index: int,
    traces_dir: Path,
    runtime: Optional[ToolClawRuntime],
) -> EvalRow:
    task_id = canonical_task_id(task)
    scenario = str(task.get("scenario", "success"))
    trace_path = traces_dir / f"{task_index:03d}_{task_id}_{spec.system_id}.json"
    backup_tool_map = task.get("backup_tool_map", {})
    task_family = derive_task_family(task, scenario, task_id)
    failure_type = derive_failure_type(task, scenario)
    reused_artifact = False
    if spec.use_reuse and runtime is not None:
        query = str(task.get("query") or "")
        if query:
            signature_candidates = task_signature_candidates(
                query=query,
                task_family=task_family,
                failure_type=failure_type,
            )
            reused_artifact = any(runtime.asset_registry.query(signature) for signature in signature_candidates)

    if spec.execution_mode == "baseline":
        workflow = build_workflow_from_task(task, mode="demo")
        baseline_trace, baseline_stop = run_baseline(
            workflow=workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=trace_path,
        )
        return EvalRow(
            task_id=task_id,
            system=spec.system_id,
            scenario=scenario,
            task_family=task_family,
            failure_type=failure_type,
            success=bool(baseline_trace.metrics.success),
            tool_calls=baseline_trace.metrics.tool_calls,
            repair_actions=baseline_trace.metrics.repair_actions,
            repair_triggered=0,
            user_turns=0,
            total_steps=baseline_trace.metrics.total_steps,
            token_cost=float(baseline_trace.metrics.token_cost or 0.0),
            wall_clock_ms=int(baseline_trace.metrics.latency_ms or 0),
            observed_error_type="none" if baseline_trace.metrics.success else failure_type,
            first_failure_recovered=False,
            repair_extra_tool_calls=0,
            repair_extra_user_turns=0,
            repair_user_clarification=False,
            reuse_pass_index=parse_reuse_pass_index(task_id, task),
            reused_artifact=False,
            second_run_improvement=0.0,
            stop_reason=baseline_stop,
            trace_path=str(trace_path),
        )

    if runtime is None:
        raise RuntimeError(f"runtime missing for system {spec.system_id}")

    if spec.execution_mode == "executor":
        if spec.workflow_mode == "planner":
            seed_workflow = build_workflow_from_task(task, mode="planner")
            workflow = runtime.planner.plan(build_planning_request(seed_workflow, allow_reuse=False)).workflow
        else:
            workflow = build_workflow_from_task(task, mode="demo")
        runtime.executor.run_until_blocked(
            workflow=workflow,
            run_id=f"{spec.system_id}_{task_id}",
            output_path=str(trace_path),
            backup_tool_map=backup_tool_map,
        )
        return row_from_trace(
            task=task,
            system=spec.system_id,
            scenario=scenario,
            trace_path=trace_path,
            reused_artifact=False,
        )

    seed_workflow = build_workflow_from_task(task, mode="planner")
    if spec.use_reuse and runtime is not None and not reused_artifact:
        signature_candidates = task_signature_candidates(
            query=seed_workflow.task.user_goal,
            task_family=str(seed_workflow.metadata.get("task_family", task_family)),
            failure_type=str(seed_workflow.metadata.get("failure_type", failure_type)),
            capability_skeleton=[step.capability_id for step in seed_workflow.execution_plan],
        )
        reused_artifact = any(runtime.asset_registry.query(signature) for signature in signature_candidates)
    request = build_planning_request(seed_workflow, allow_reuse=spec.use_reuse)
    build_shell(runtime, task).run(
        request=request,
        run_id=f"{spec.system_id}_{task_id}",
        output_path=str(trace_path),
        backup_tool_map=backup_tool_map,
        use_reuse=spec.use_reuse,
        compile_on_success=spec.compile_on_success,
    )
    if spec.use_reuse:
        reused_artifact = reused_artifact or bool(request.hints.reusable_asset_ids)
    return row_from_trace(
        task=task,
        system=spec.system_id,
        scenario=scenario,
        trace_path=trace_path,
        reused_artifact=reused_artifact,
    )


def main() -> None:
    args = parse_args()
    taskset_path: Path = args.taskset
    outdir = Path(args.outdir)
    traces_dir = outdir / "traces"
    rows: List[EvalRow] = []
    system_specs = parse_systems(args.systems)
    asset_registry_root = Path(args.asset_registry_root) if args.asset_registry_root else None
    runtimes: Dict[str, ToolClawRuntime] = {}
    for spec in system_specs:
        if spec.execution_mode == "baseline":
            continue
        asset_registry: Optional[AssetRegistry] = None
        if asset_registry_root is not None:
            asset_registry = FileAssetRegistry(str(asset_registry_root / spec.system_id))
        runtimes[spec.system_id] = build_runtime_for_spec(spec=spec, asset_registry=asset_registry)

    tasks = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("taskset JSON must be a list of task objects")

    for idx, task in enumerate(tasks, start=1):
        for spec in system_specs:
            rows.append(
                execute_system(
                    spec=spec,
                    task=task,
                    task_index=idx,
                    traces_dir=traces_dir,
                    runtime=runtimes.get(spec.system_id),
                )
            )

    csv_path = outdir / "comparison.csv"
    report_path = outdir / "report.md"
    annotate_second_run_improvement(rows)
    write_rows_csv(rows, csv_path)
    write_report_md(
        rows=rows,
        summary=summarize(rows),
        scenario_summary=summarize_by_scenario(rows),
        report_path=report_path,
    )

    print(f"wrote: {csv_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()
