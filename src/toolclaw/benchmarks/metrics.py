"""CSV/report helpers for comparing systems on normalized evaluation outputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Tuple


@dataclass
class EvalRow:
    task_id: str
    system: str
    scenario: str
    task_family: str
    failure_type: str
    success: bool
    tool_calls: int
    repair_actions: int
    repair_triggered: int
    user_turns: int
    total_steps: int
    token_cost: float
    wall_clock_ms: int
    observed_error_type: str
    first_failure_recovered: bool
    repair_extra_tool_calls: int
    repair_extra_user_turns: int
    repair_user_clarification: bool
    reuse_pass_index: int
    reused_artifact: bool
    second_run_improvement: float
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
                "task_family",
                "failure_type",
                "success",
                "tool_calls",
                "repair_actions",
                "repair_triggered",
                "user_turns",
                "total_steps",
                "token_cost",
                "wall_clock_ms",
                "observed_error_type",
                "first_failure_recovered",
                "repair_extra_tool_calls",
                "repair_extra_user_turns",
                "repair_user_clarification",
                "reuse_pass_index",
                "reused_artifact",
                "second_run_improvement",
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
        summary[system] = _aggregate_rows(sys_rows)
    return summary


def summarize_by_scenario(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, float]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.scenario), []).append(row)
    return {key: _aggregate_rows(group_rows) for key, group_rows in grouped.items()}


def summarize_by_failure_type(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, float]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.failure_type), []).append(row)
    return {key: _aggregate_rows(group_rows) for key, group_rows in grouped.items()}


def summarize_by_observed_error_type(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, float]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.observed_error_type), []).append(row)
    return {key: _aggregate_rows(group_rows) for key, group_rows in grouped.items()}


def summarize_by_task_family(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, float]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        grouped.setdefault((row.system, row.task_family), []).append(row)
    return {key: _aggregate_rows(group_rows) for key, group_rows in grouped.items()}


def summarize_repeated_families(rows: List[EvalRow]) -> Dict[Tuple[str, str], Dict[str, object]]:
    grouped: Dict[Tuple[str, str], List[EvalRow]] = {}
    for row in rows:
        if row.reuse_pass_index <= 0:
            continue
        grouped.setdefault((row.system, _repeat_family_key(row.task_id)), []).append(row)

    summary: Dict[Tuple[str, str], Dict[str, object]] = {}
    for key, family_rows in grouped.items():
        pass_map = {row.reuse_pass_index: row for row in family_rows}
        if 1 not in pass_map or 2 not in pass_map:
            continue
        pass_1 = pass_map[1]
        pass_2 = pass_map[2]
        summary[key] = {
            "pass_1_success": 1.0 if pass_1.success else 0.0,
            "pass_2_success": 1.0 if pass_2.success else 0.0,
            "pass_1_tool_calls": float(pass_1.tool_calls),
            "pass_2_tool_calls": float(pass_2.tool_calls),
            "pass_1_user_turns": float(pass_1.user_turns),
            "pass_2_user_turns": float(pass_2.user_turns),
            "pass_1_fail_stop": 0.0 if pass_1.success else 1.0,
            "pass_2_fail_stop": 0.0 if pass_2.success else 1.0,
            "pass_2_reused_artifact": 1.0 if pass_2.reused_artifact else 0.0,
            "second_run_improvement": float(pass_2.second_run_improvement),
        }
    return summary


def write_report_md(
    *,
    rows: List[EvalRow],
    summary: Dict[str, Dict[str, float]],
    scenario_summary: Dict[Tuple[str, str], Dict[str, float]],
    report_path: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    failure_summary = summarize_by_failure_type(rows)
    observed_error_summary = summarize_by_observed_error_type(rows)
    family_summary = summarize_by_task_family(rows)
    repeated_family_summary = summarize_repeated_families(rows)

    lines = [
        "# ToolClaw Phase-1 Evaluation Report",
        "",
        "## Aggregate Comparison",
        "",
        "| system | tasks | success_rate | repair_success_rate | avg_tool_calls | avg_user_turns | avg_repair_actions | avg_total_steps | avg_token_cost | avg_wall_clock_ms | fail_stop_rate | reuse_usage_rate | mean_second_run_improvement |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for system, stats in summary.items():
        lines.append(
            f"| {system} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['repair_success_rate']:.3f} | {stats['avg_tool_calls']:.2f} | {stats['avg_user_turns']:.2f} | {stats['avg_repair_actions']:.2f} | {stats['avg_total_steps']:.2f} | {stats['avg_token_cost']:.3f} | {stats['avg_wall_clock_ms']:.1f} | {stats['fail_stop_rate']:.3f} | {stats['reuse_usage_rate']:.3f} | {stats['mean_second_run_improvement']:.3f} |"
        )

    a0 = summary.get("a0_baseline") or summary.get("baseline")
    a1 = summary.get("a1_recovery")
    a2 = summary.get("a2_planner")
    a3 = summary.get("a3_interaction") or summary.get("toolclaw_lite")
    a4 = summary.get("a4_reuse")
    if a0 and a4:
        lines.extend(
            [
                "",
                "## Delta (A4 Reuse vs A0 Baseline)",
                "",
                "| metric | delta |",
                "|---|---:|",
                f"| success_rate | {a4['success_rate'] - a0['success_rate']:+.3f} |",
                f"| avg_tool_calls | {a4['avg_tool_calls'] - a0['avg_tool_calls']:+.2f} |",
                f"| avg_user_turns | {a4['avg_user_turns'] - a0['avg_user_turns']:+.2f} |",
                f"| avg_token_cost | {a4['avg_token_cost'] - a0['avg_token_cost']:+.3f} |",
                f"| avg_wall_clock_ms | {a4['avg_wall_clock_ms'] - a0['avg_wall_clock_ms']:+.1f} |",
                f"| fail_stop_rate | {a4['fail_stop_rate'] - a0['fail_stop_rate']:+.3f} |",
                f"| reuse_usage_rate | {a4['reuse_usage_rate'] - a0['reuse_usage_rate']:+.3f} |",
                f"| mean_second_run_improvement | {a4['mean_second_run_improvement'] - a0['mean_second_run_improvement']:+.3f} |",
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
                f"| {label} | {right['success_rate'] - left['success_rate']:+.3f} | {right['repair_success_rate'] - left['repair_success_rate']:+.3f} | {right['avg_user_turns'] - left['avg_user_turns']:+.2f} | {right['fail_stop_rate'] - left['fail_stop_rate']:+.3f} | {right['mean_second_run_improvement'] - left['mean_second_run_improvement']:+.3f} |"
            )
    if pair_lines:
        lines.extend(
            [
                "",
                "## Ablation Deltas",
                "",
                "| pair | success_rate | repair_success_rate | avg_user_turns | fail_stop_rate | mean_second_run_improvement |",
                "|---|---:|---:|---:|---:|---:|",
                *pair_lines,
            ]
        )

    lines.extend(
        [
            "",
            "## Per-Task Results",
            "",
            "| task_id | task_family | system | success | tool_calls | repair_actions | user_turns | repair_extra_tool_calls | repair_extra_user_turns | stop_reason | failure_type | observed_error_type | reused_artifact | second_run_improvement |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.task_id} | {row.task_family} | {row.system} | {1.0 if row.success else 0.0:.0f} | {row.tool_calls} | {row.repair_actions} | {row.user_turns} | {row.repair_extra_tool_calls} | {row.repair_extra_user_turns} | {row.stop_reason} | {row.failure_type} | {row.observed_error_type} | {1.0 if row.reused_artifact else 0.0:.0f} | {row.second_run_improvement:.3f} |"
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

    lines.extend(
        [
            "",
            "## Failure-Type Breakdown",
            "",
            "| system | failure_type | tasks | success_rate | repair_success_rate | fail_stop_rate |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for (system, failure_type), stats in sorted(failure_summary.items()):
        lines.append(
            f"| {system} | {failure_type} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['repair_success_rate']:.3f} | {stats['fail_stop_rate']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Observed Error-Type Breakdown",
            "",
            "| system | observed_error_type | tasks | success_rate | repair_success_rate | first_failure_recovery_rate | clarification_rate |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for (system, observed_error_type), stats in sorted(observed_error_summary.items()):
        lines.append(
            f"| {system} | {observed_error_type} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['repair_success_rate']:.3f} | {stats['first_failure_recovery_rate']:.3f} | {stats['repair_user_clarification_rate']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Task-Family Breakdown",
            "",
            "| system | task_family | tasks | success_rate | reuse_usage_rate | mean_second_run_improvement |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for (system, task_family), stats in sorted(family_summary.items()):
        lines.append(
            f"| {system} | {task_family} | {int(stats['num_tasks'])} | {stats['success_rate']:.3f} | {stats['reuse_usage_rate']:.3f} | {stats['mean_second_run_improvement']:.3f} |"
        )

    if repeated_family_summary:
        lines.extend(
            [
                "",
                "## Repeated-Family Analysis",
                "",
                "| system | repeat_family | pass_1_success | pass_2_success | pass_1_tool_calls | pass_2_tool_calls | pass_1_user_turns | pass_2_user_turns | pass_2_reused_artifact | second_run_improvement |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for (system, repeat_family), stats in sorted(repeated_family_summary.items()):
            lines.append(
                f"| {system} | {repeat_family} | {stats['pass_1_success']:.3f} | {stats['pass_2_success']:.3f} | {stats['pass_1_tool_calls']:.2f} | {stats['pass_2_tool_calls']:.2f} | {stats['pass_1_user_turns']:.2f} | {stats['pass_2_user_turns']:.2f} | {stats['pass_2_reused_artifact']:.3f} | {stats['second_run_improvement']:.3f} |"
            )

    a3_t4 = family_summary.get(("a3_interaction", "t4_repeated_reusable")) or family_summary.get(("toolclaw_lite", "t4_repeated_reusable"))
    a4_t4 = family_summary.get(("a4_reuse", "t4_repeated_reusable"))
    if a3_t4 and a4_t4:
        lines.extend(
            [
                "",
                "## Repeated-Family A3 vs A4",
                "",
                "| metric | a3_interaction | a4_reuse | delta_a4_minus_a3 |",
                "|---|---:|---:|---:|",
                f"| success_rate | {a3_t4['success_rate']:.3f} | {a4_t4['success_rate']:.3f} | {a4_t4['success_rate'] - a3_t4['success_rate']:+.3f} |",
                f"| avg_repair_actions | {a3_t4['avg_repair_actions']:.2f} | {a4_t4['avg_repair_actions']:.2f} | {a4_t4['avg_repair_actions'] - a3_t4['avg_repair_actions']:+.2f} |",
                f"| avg_user_turns | {a3_t4['avg_user_turns']:.2f} | {a4_t4['avg_user_turns']:.2f} | {a4_t4['avg_user_turns'] - a3_t4['avg_user_turns']:+.2f} |",
                f"| reuse_usage_rate | {a3_t4['reuse_usage_rate']:.3f} | {a4_t4['reuse_usage_rate']:.3f} | {a4_t4['reuse_usage_rate'] - a3_t4['reuse_usage_rate']:+.3f} |",
                f"| mean_second_run_improvement | {a3_t4['mean_second_run_improvement']:.3f} | {a4_t4['mean_second_run_improvement']:.3f} | {a4_t4['mean_second_run_improvement'] - a3_t4['mean_second_run_improvement']:+.3f} |",
            ]
        )

    lines.extend(
        [
            "",
            "## Recovery And Cost",
            "",
            "| system | first_failure_recovery_rate | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | clarification_rate | avg_token_cost | avg_wall_clock_ms |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for system, stats in summary.items():
        lines.append(
            f"| {system} | {stats['first_failure_recovery_rate']:.3f} | {stats['avg_repair_extra_tool_calls']:.2f} | {stats['avg_repair_extra_user_turns']:.2f} | {stats['repair_user_clarification_rate']:.3f} | {stats['avg_token_cost']:.3f} | {stats['avg_wall_clock_ms']:.1f} |"
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
            "- reuse_usage_rate reports how often a system actually ran with a retrieved reusable artifact.",
            "- mean_second_run_improvement is only meaningful on repeated families with explicit first-vs-second-run pairs.",
            "- Interpret A4 reuse gains primarily through the repeated-family sections, not the full-task aggregate.",
            "- Use failure_type and task_family tables to keep benchmark slicing aligned with experimental claims.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def _aggregate_rows(rows: List[EvalRow]) -> Dict[str, float]:
    return {
        "num_tasks": float(len(rows)),
        "success_rate": mean(1.0 if r.success else 0.0 for r in rows),
        "repair_success_rate": _repair_success_rate(rows),
        "avg_tool_calls": mean(r.tool_calls for r in rows),
        "avg_user_turns": mean(r.user_turns for r in rows),
        "avg_repair_actions": mean(r.repair_actions for r in rows),
        "avg_total_steps": mean(r.total_steps for r in rows),
        "avg_token_cost": mean(r.token_cost for r in rows),
        "avg_wall_clock_ms": mean(r.wall_clock_ms for r in rows),
        "first_failure_recovery_rate": _first_failure_recovery_rate(rows),
        "avg_repair_extra_tool_calls": mean(r.repair_extra_tool_calls for r in rows),
        "avg_repair_extra_user_turns": mean(r.repair_extra_user_turns for r in rows),
        "repair_user_clarification_rate": mean(1.0 if r.repair_user_clarification else 0.0 for r in rows),
        "fail_stop_rate": mean(0.0 if r.success else 1.0 for r in rows),
        "reuse_usage_rate": mean(1.0 if r.reused_artifact else 0.0 for r in rows),
        "mean_second_run_improvement": mean(r.second_run_improvement for r in rows),
    }


def _repair_success_rate(rows: List[EvalRow]) -> float:
    repaired_rows = [row for row in rows if row.repair_triggered > 0]
    if not repaired_rows:
        return 0.0
    return mean(1.0 if row.success else 0.0 for row in repaired_rows)


def _first_failure_recovery_rate(rows: List[EvalRow]) -> float:
    failure_rows = [row for row in rows if row.observed_error_type != "none"]
    if not failure_rows:
        return 0.0
    return mean(1.0 if row.first_failure_recovered else 0.0 for row in failure_rows)


def _repeat_family_key(task_id: str) -> str:
    if "__pass" in task_id:
        return task_id.rsplit("__pass", 1)[0]
    return task_id
