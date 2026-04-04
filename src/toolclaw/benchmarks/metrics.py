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
    repair_triggered: int
    user_turns: int
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
                "repair_triggered",
                "user_turns",
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
            "repair_success_rate": _repair_success_rate(sys_rows),
            "avg_tool_calls": mean(r.tool_calls for r in sys_rows),
            "avg_user_turns": mean(r.user_turns for r in sys_rows),
            "avg_repair_actions": mean(r.repair_actions for r in sys_rows),
            "avg_total_steps": mean(r.total_steps for r in sys_rows),
            "fail_stop_rate": mean(0.0 if r.success else 1.0 for r in sys_rows),
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
            "repair_success_rate": _repair_success_rate(key_rows),
            "avg_tool_calls": mean(r.tool_calls for r in key_rows),
            "avg_user_turns": mean(r.user_turns for r in key_rows),
            "avg_repair_actions": mean(r.repair_actions for r in key_rows),
            "fail_stop_rate": mean(0.0 if r.success else 1.0 for r in key_rows),
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
        "| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | fail_stop_rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for system, stats in summary.items():
        lines.append(
            f"| {system} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['repair_success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['avg_total_steps']:.2f} | {stats['fail_stop_rate']:.3f} |"
        )

    a0 = summary.get("a0_baseline") or summary.get("baseline")
    a1 = summary.get("a1_recovery")
    a2 = summary.get("a2_planner")
    a3 = summary.get("a3_interaction") or summary.get("toolclaw_lite")
    a4 = summary.get("a4_reuse")
    if a0 and a4:
        success_uplift = a4["success_rate"] - a0["success_rate"]
        call_delta = a4["avg_tool_calls"] - a0["avg_tool_calls"]
        user_turn_delta = a4["avg_user_turns"] - a0["avg_user_turns"]
        fail_stop_delta = a4["fail_stop_rate"] - a0["fail_stop_rate"]
        lines.extend(
            [
                "",
                "## Delta (A4 Reuse vs A0 Baseline)",
                "",
                "| metric | delta |",
                "|---|---:|",
                f"| success_rate | {success_uplift:+.3f} |",
                f"| avg_tool_calls | {call_delta:+.2f} |",
                f"| avg_user_turns | {user_turn_delta:+.2f} |",
                f"| fail_stop_rate | {fail_stop_delta:+.3f} |",
            ]
        )

    ablation_pairs = [
        ("A0 vs A1", a0, a1),
        ("A1 vs A2", a1, a2),
        ("A2 vs A3", a2, a3),
        ("A3 vs A4", a3, a4),
    ]
    pair_lines = []
    for label, left, right in ablation_pairs:
        if left and right:
            pair_lines.append(
                f"| {label} | {right['success_rate'] - left['success_rate']:+.3f} | {right['repair_success_rate'] - left['repair_success_rate']:+.3f} | {right['avg_user_turns'] - left['avg_user_turns']:+.2f} | {right['fail_stop_rate'] - left['fail_stop_rate']:+.3f} |"
            )
    if pair_lines:
        lines.extend(
            [
                "",
                "## Ablation Deltas",
                "",
                "| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate |",
                "|---|---:|---:|---:|---:|",
                *pair_lines,
            ]
        )

    lines.extend(
        [
            "",
            "## Scenario Breakdown",
            "",
            "| system | scenario | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | fail_stop_rate |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for (system, scenario), stats in sorted(scenario_summary.items()):
        lines.append(
            f"| {system} | {scenario} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['repair_success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['fail_stop_rate']:.3f} |"
        )

    verdict = "inconclusive"
    if a0 and a4:
        if a4["success_rate"] > a0["success_rate"]:
            verdict = "a4_reuse_advantage"
        elif a4["success_rate"] < a0["success_rate"]:
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
            "- repair_success_rate isolates whether triggered recovery paths actually salvage runs.",
            "- avg_user_turns controls interaction burden; A3/A4 should not buy gains with excessive turns.",
            "- fail_stop_rate should fall as recovery and interaction layers are added.",
            "- Use per-task CSV to inspect failure clusters by scenario and stop_reason.",
            "- If total task count is small (<30), treat this as a pilot rather than a final conclusion.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _repair_success_rate(rows: List[EvalRow]) -> float:
    repaired_rows = [row for row in rows if row.repair_triggered > 0]
    if not repaired_rows:
        return 0.0
    return mean(1.0 if row.success else 0.0 for row in repaired_rows)
