from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import sys

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
from toolclaw.schemas.workflow import Workflow


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

    if task.get("target_path") is not None:
        workflow.execution_plan[1].inputs["target_path"] = task["target_path"]

    scenario = task.get("scenario", "success")
    if scenario == "binding_failure":
        workflow.execution_plan[1].inputs.pop("target_path", None)
    elif scenario == "environment_failure":
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
    parser = argparse.ArgumentParser(description="Run baseline vs ToolClaw-lite evaluation")
    parser.add_argument("--taskset", type=existing_json_path, required=True, help="Path to taskset JSON")
    parser.add_argument("--outdir", default="outputs/eval", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taskset_path: Path = args.taskset
    outdir = Path(args.outdir)
    traces_dir = outdir / "traces"
    rows: List[EvalRow] = []
    planner = build_default_planner(asset_registry=InMemoryAssetRegistry())
    runtime = ToolClawRuntime(
        planner=planner,
        executor=SequentialExecutor(),
        repair_updater=RepairUpdater(),
        compiler=SWPCCompiler(),
        asset_registry=InMemoryAssetRegistry(),
    )

    tasks = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("taskset JSON must be a list of task objects")

    for idx, task in enumerate(tasks, start=1):
        workflow = build_workflow_from_task(task, mode=args.mode)
        task_id = str(task["task_id"])
        scenario = str(task.get("scenario", "success"))

        baseline_trace_path = traces_dir / f"{idx:03d}_{task_id}_baseline.json"
        baseline_trace, baseline_stop = run_baseline(
            workflow=build_workflow_from_task(task, mode=args.mode),
            run_id=f"baseline_{task_id}",
            output_path=baseline_trace_path,
        )
        rows.append(
            EvalRow(
                task_id=task_id,
                system="baseline",
                scenario=scenario,
                success=bool(baseline_trace.metrics.success),
                tool_calls=baseline_trace.metrics.tool_calls,
                repair_actions=baseline_trace.metrics.repair_actions,
                total_steps=baseline_trace.metrics.total_steps,
                stop_reason=baseline_stop,
                trace_path=str(baseline_trace_path),
            )
        )

        toolclaw_trace_path = traces_dir / f"{idx:03d}_{task_id}_toolclaw_lite.json"
        policy_cfg = task.get("simulated_policy", {})
        shell = InteractionShell(
            runtime=runtime,
            config=InteractionLoopConfig(
                simulator_policy=SimulatedPolicy(
                    mode=policy_cfg.get("mode", "cooperative"),
                    missing_arg_values=policy_cfg.get("missing_arg_values", {}),
                    backup_tool_preferences=policy_cfg.get("backup_tool_preferences", {}),
                )
            ),
        )
        planning_request = PlanningRequest(
            task=workflow.task,
            context=workflow.context,
            policy=workflow.policy,
        )
        shell.run(
            request=planning_request,
            run_id=f"toolclaw_{task_id}",
            output_path=str(toolclaw_trace_path),
        )
        trace_payload = json.loads(toolclaw_trace_path.read_text(encoding="utf-8"))
        stop_event = next((e for e in reversed(trace_payload["events"]) if e["event_type"] == "stop"), None)
        toolclaw_stop = stop_event["output"].get("reason", "unknown") if stop_event and isinstance(stop_event.get("output"), dict) else "unknown"
        rows.append(
            EvalRow(
                task_id=task_id,
                system="toolclaw_lite",
                scenario=scenario,
                success=bool(trace_payload["metrics"]["success"]),
                tool_calls=int(trace_payload["metrics"]["tool_calls"]),
                repair_actions=int(trace_payload["metrics"]["repair_actions"]),
                total_steps=int(trace_payload["metrics"]["total_steps"]),
                stop_reason=toolclaw_stop,
                trace_path=str(toolclaw_trace_path),
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
