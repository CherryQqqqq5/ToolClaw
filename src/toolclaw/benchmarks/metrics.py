from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List
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


def write_report_md(summary: Dict[str, Dict[str, float]], report_path: Path) -> None:
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

    lines.extend(
        [
            "",
            "## Interpretation (auto-generated)",
            "",
            "- Compare success_rate first; this is the primary reliability indicator.",
            "- If ToolClaw-lite has higher success_rate with moderate call overhead, workflow intelligence is helping.",
            "- Use per-task CSV to inspect failure clusters by scenario and stop_reason.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
