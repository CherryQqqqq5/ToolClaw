"""Entry point for Phase-1 A0-A4 evaluation over normalized tasksets."""

from __future__ import annotations

import argparse
import json
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
from toolclaw.compiler.swpc import SWPCCompiler
from toolclaw.execution.executor import SequentialExecutor
from toolclaw.interaction.irc import InteractionLoopConfig, InteractionShell
from toolclaw.interaction.repair_updater import RepairUpdater
from toolclaw.interaction.user_simulator import SimulatedPolicy
from toolclaw.main import ToolClawRuntime
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
from toolclaw.registry import InMemoryAssetRegistry
from toolclaw.schemas.workflow import RiskLevel, TaskConstraints, ToolSpec, Workflow


@dataclass(frozen=True)
class SystemSpec:
    system_id: str
    workflow_mode: str
    execution_mode: str
    compile_on_success: bool = False
    use_reuse: bool = False


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
        request.task.task_id = str(task["task_id"])
        request.task.user_goal = str(task.get("query") or request.task.user_goal)
        workflow = planner.plan(request).workflow
    else:
        workflow = Workflow.demo()

    workflow.task.task_id = str(task["task_id"])

    retrieve_query = task.get("query")
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

    raw_metadata = task.get("metadata")
    if isinstance(raw_metadata, dict):
        workflow.metadata.update(raw_metadata)

    scenario = task.get("scenario", "success")
    if scenario == "binding_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs.pop("target_path", None)
    elif scenario == "environment_failure" and len(workflow.execution_plan) > 1:
        workflow.execution_plan[1].inputs["force_environment_failure"] = True

    return workflow


def existing_json_path(value: str) -> Path:
    path = Path(value)
    placeholder_path = Path("path/to/taskset.json")
    sample_path = ROOT_DIR / "data" / "eval_tasks.sample.json"
    if path.as_posix() == placeholder_path.as_posix() and sample_path.exists():
        print(
            f"[run_eval] --taskset uses README placeholder path ({path}); using sample taskset at {sample_path}.",
            file=sys.stderr,
        )
        return sample_path
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
    return parser.parse_args()


def build_runtime(asset_registry: Optional[InMemoryAssetRegistry] = None) -> ToolClawRuntime:
    registry = asset_registry or InMemoryAssetRegistry()
    planner = build_default_planner(asset_registry=registry)
    return ToolClawRuntime(
        planner=planner,
        executor=SequentialExecutor(),
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


def row_from_trace(task_id: str, system: str, scenario: str, trace_path: Path) -> EvalRow:
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    events = trace_payload.get("events", [])
    metrics = trace_payload.get("metrics", {})
    stop_event = next((event for event in reversed(events) if event.get("event_type") == "stop"), None)
    stop_reason = stop_event.get("output", {}).get("reason", "unknown") if isinstance(stop_event, dict) else "unknown"
    repair_triggered = sum(1 for event in events if event.get("event_type") == "repair_triggered")
    return EvalRow(
        task_id=task_id,
        system=system,
        scenario=scenario,
        success=bool(metrics.get("success")),
        tool_calls=int(metrics.get("tool_calls", 0)),
        repair_actions=int(metrics.get("repair_actions", 0)),
        repair_triggered=repair_triggered,
        user_turns=int(metrics.get("user_queries", 0)),
        total_steps=int(metrics.get("total_steps", 0)),
        stop_reason=str(stop_reason),
        trace_path=str(trace_path),
    )


def execute_system(
    *,
    spec: SystemSpec,
    task: Dict[str, Any],
    task_index: int,
    traces_dir: Path,
    runtime: Optional[ToolClawRuntime],
) -> EvalRow:
    task_id = str(task["task_id"])
    scenario = str(task.get("scenario", "success"))
    trace_path = traces_dir / f"{task_index:03d}_{task_id}_{spec.system_id}.json"
    backup_tool_map = task.get("backup_tool_map", {})

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
            success=bool(baseline_trace.metrics.success),
            tool_calls=baseline_trace.metrics.tool_calls,
            repair_actions=baseline_trace.metrics.repair_actions,
            repair_triggered=0,
            user_turns=0,
            total_steps=baseline_trace.metrics.total_steps,
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
        return row_from_trace(task_id, spec.system_id, scenario, trace_path)

    seed_workflow = build_workflow_from_task(task, mode="planner")
    request = build_planning_request(seed_workflow, allow_reuse=spec.use_reuse)
    build_shell(runtime, task).run(
        request=request,
        run_id=f"{spec.system_id}_{task_id}",
        output_path=str(trace_path),
        backup_tool_map=backup_tool_map,
        use_reuse=spec.use_reuse,
        compile_on_success=spec.compile_on_success,
    )
    return row_from_trace(task_id, spec.system_id, scenario, trace_path)


def main() -> None:
    args = parse_args()
    taskset_path: Path = args.taskset
    outdir = Path(args.outdir)
    traces_dir = outdir / "traces"
    rows: List[EvalRow] = []
    system_specs = parse_systems(args.systems)
    runtimes: Dict[str, ToolClawRuntime] = {
        spec.system_id: build_runtime()
        for spec in system_specs
        if spec.execution_mode != "baseline"
    }

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
    write_rows_csv(rows, csv_path)
    write_report_md(
        summary=summarize(rows),
        scenario_summary=summarize_by_scenario(rows),
        report_path=report_path,
    )

    print(f"wrote: {csv_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()
