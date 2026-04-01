"""CSV/report helpers for comparing systems on normalized evaluation outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Tuple
import csv


@dataclass
class EvalRow:
    task_id: str
    system: str
    scenario: str
    success: bool
    tool_calls: int
    repair_actions: int
    total_steps: int
    stop_reason: str
    trace_path: str


def write_rows_csv(rows: Iterable[EvalRow], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "task_id",
                "system",
                "scenario",
                "success",
                "tool_calls",
                "repair_actions",
                "total_steps",
                "stop_reason",
                "trace_path",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def summarize(rows: List[EvalRow]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault(row.system, []).append(row)

    summary: Dict[str, Dict[str, float]] = {}
    for system, sys_rows in grouped.items():
        summary[system] = {
            "num_tasks": float(len(sys_rows)),
            "success_rate": mean(1.0 if r.success else 0.0 for r in sys_rows),
            "avg_tool_calls": mean(r.tool_calls for r in sys_rows),
            "avg_repair_actions": mean(r.repair_actions for r in sys_rows),
            "avg_total_steps": mean(r.total_steps for r in sys_rows),
        }
    return summary


def summarize_by_scenario(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, float]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.scenario), []).append(row)

    summary: Dict[Tuple[str, str], Dict[str, float]] = {}
    for key, key_rows in grouped.items():
        summary[key] = {
            "num_tasks": float(len(key_rows)),
            "success_rate": mean(1.0 if r.success else 0.0 for r in key_rows),
            "avg_tool_calls": mean(r.tool_calls for r in key_rows),
            "avg_repair_actions": mean(r.repair_actions for r in key_rows),
        }
    return summary


def write_report_md(
    summary: Dict[str, Dict[str, float]],
    scenario_summary: Dict[Tuple[str, str], Dict[str, float]],
    report_path: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ToolClaw Phase-1 Evaluation Report",
        "",
        "## Aggregate Comparison",
        "",
        "| system | tasks | success_rate | avg_tool_calls | avg_repair_actions | avg_total_steps |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for system, stats in summary.items():
        lines.append(
            f"| {system} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['avg_total_steps']:.2f} |"
        )

    baseline = summary.get("baseline")
    toolclaw = summary.get("toolclaw_lite")
    if baseline and toolclaw:
        success_uplift = toolclaw["success_rate"] - baseline["success_rate"]
        call_delta = toolclaw["avg_tool_calls"] - baseline["avg_tool_calls"]
        repair_delta = toolclaw["avg_repair_actions"] - baseline["avg_repair_actions"]
        lines.extend(
            [
                "",
                "## Delta (ToolClaw-lite vs Baseline)",
                "",
                "| metric | delta |",
                "|---|---:|",
                f"| success_rate | {success_uplift:+.3f} |",
                f"| avg_tool_calls | {call_delta:+.2f} |",
                f"| avg_repair_actions | {repair_delta:+.2f} |",
            ]
        )

    lines.extend(
        [
            "",
            "## Scenario Breakdown",
            "",
            "| system | scenario | tasks | success_rate | avg_tool_calls | avg_repair_actions |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for (system, scenario), stats in sorted(scenario_summary.items()):
        lines.append(
            f"| {system} | {scenario} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_repair_actions']:.2f} |"
        )

    verdict = "inconclusive"
    if baseline and toolclaw:
        if toolclaw["success_rate"] > baseline["success_rate"]:
            verdict = "toolclaw_lite_advantage"
        elif toolclaw["success_rate"] < baseline["success_rate"]:
            verdict = "baseline_advantage"
        else:
            verdict = "tie"

    lines.extend(
        [
            "",
            "## Interpretation (auto-generated)",
            "",
            f"- Verdict: **{verdict}**.",
            "- Compare success_rate first; this is the primary reliability indicator.",
            "- If ToolClaw-lite has higher success_rate with moderate call overhead, workflow intelligence is helping.",
            "- Use per-task CSV to inspect failure clusters by scenario and stop_reason.",
            "- If total task count is small (<30), treat this as a pilot rather than a final conclusion.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
