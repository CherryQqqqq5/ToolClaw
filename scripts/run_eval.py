from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from toolclaw.benchmarks.baseline_runner import run_baseline
from toolclaw.benchmarks.metrics import (
    EvalRow,
    summarize,
    summarize_by_scenario,
    write_report_md,
    write_rows_csv,
)
from toolclaw.benchmarks.tau_runner import run_toolclaw_lite
from toolclaw.planner.htgp import PlanningRequest, build_default_planner
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline vs ToolClaw-lite evaluation")
    parser.add_argument("--taskset", required=True, help="Path to taskset JSON")
    parser.add_argument("--outdir", default="outputs/eval", help="Output directory")
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner", help="Workflow source mode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    taskset_path = Path(args.taskset)
    outdir = Path(args.outdir)
    traces_dir = outdir / "traces"
    rows: List[EvalRow] = []

    tasks = json.loads(taskset_path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("taskset JSON must be a list of task objects")

    for idx, task in enumerate(tasks, start=1):
        workflow = build_workflow_from_task(task, mode=args.mode)
        task_id = str(task["task_id"])
        scenario = str(task.get("scenario", "success"))
        backup_map = task.get("backup_tool_map", {"write_tool": "backup_write_tool"})

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
        toolclaw_trace, toolclaw_stop = run_toolclaw_lite(
            workflow=workflow,
            run_id=f"toolclaw_{task_id}",
            output_path=toolclaw_trace_path,
            backup_tool_map=backup_map,
        )
        rows.append(
            EvalRow(
                task_id=task_id,
                system="toolclaw_lite",
                scenario=scenario,
                success=bool(toolclaw_trace.metrics.success),
                tool_calls=toolclaw_trace.metrics.tool_calls,
                repair_actions=toolclaw_trace.metrics.repair_actions,
                total_steps=toolclaw_trace.metrics.total_steps,
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
