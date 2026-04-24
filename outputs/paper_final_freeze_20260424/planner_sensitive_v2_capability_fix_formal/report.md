# Non-Canonical Planner-Sensitive Claim Report

This generic ToolSandbox report is retained for runner diagnostics only. Use `planner_sensitive_summary.md` as the canonical report for planner-sensitive structural claims.

# ToolSandbox Benchmark Report

- source: `data/toolsandbox_planner_sensitive_v2.jsonl`
- normalized_taskset: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/prepared/toolsandbox.normalized.json` (`local_debug_only` unless committed by the suite allowlist)
- samples: `42`
- runs: `3`
- systems: `a1_recovery, a2_planner, a3_interaction, a4_reuse`
- scored_comparison: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/comparison.scored.csv`
- focused_slice_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/focused_slice_summary.md`
- causal_claim_summary: `not_generated`
- causal_claim_report: `not_generated`
- raw_vs_benchmark_gap_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/raw_vs_benchmark_gap_summary.md`
- per_failure_type_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/per_failure_type_summary.md`
- repair_loop_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/repair_loop_summary.md`
- statistical_robustness_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/statistical_robustness_summary.json`
- failtax_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/per_failtax_summary.json`

## Local Debug Artifacts

- raw_execution_report: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/latest_run_raw_report.md` (`local_debug_only`)
- raw_comparison: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/comparison.raw.csv` (`local_debug_only`)
- archive: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/archive` (`local_debug_only`)
- prepared_taskset: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/prepared/toolsandbox.normalized.json` (`local_debug_only` unless committed by the suite allowlist)
- reuse_focused_summary: `outputs/paper_final_freeze_20260424/planner_sensitive_v2_capability_fix_formal/reuse_focused_summary.md` (`local_debug_only`)

## Readiness

- reuse_scope: `within_invocation`
- asset_registry_root: `none`

- primary_result_ready: `false`
- caution_flags:
  - `no_reference_result_summaries`
  - `proxy_only_result_summaries`
  - `no_milestone_verification_signal`
  - `raw_vs_benchmark_success_gap`
- resolved_caution_flags:
  - `raw_vs_benchmark_success_gap`
- unresolved_caution_flags:
  - `no_reference_result_summaries`
  - `proxy_only_result_summaries`
  - `no_milestone_verification_signal`

## Aggregate

| system | mean_success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | consistency | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a1_recovery | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.850 | 0.600 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.738 | 0.738 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.739 | 0.357 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | 0.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.621 | 0.095 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | 0.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.621 | 0.095 | 0.000 | 1.000 | 0.000 | toolclaw_proxy |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a1_recovery | recovery | 42 | 0.000 | 0.000 | 1.000 |
| a2_planner | recovery | 42 | 0.000 | 0.000 | 1.000 |
| a3_interaction | recovery | 42 | 0.000 | 0.000 | 1.000 |
| a4_reuse | recovery | 42 | 0.000 | 0.000 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a1_recovery | planner_sensitive | 252 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.850 | 0.600 | 1.000 | 0.000 | toolclaw_proxy |
| a2_planner | planner_sensitive | 252 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.738 | 0.738 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.739 | 0.357 | 1.000 | 0.000 | toolclaw_proxy |
| a3_interaction | planner_sensitive | 252 | 0.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.621 | 0.095 | 1.000 | 0.000 | toolclaw_proxy |
| a4_reuse | planner_sensitive | 252 | 0.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.262 | 0.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.621 | 0.095 | 1.000 | 0.000 | toolclaw_proxy |

## Result Summary Sources

| system | result_summary_source | rows |
|---|---|---:|
| a1_recovery | toolclaw_proxy | 126 |
| a2_planner | toolclaw_proxy | 126 |
| a3_interaction | toolclaw_proxy | 126 |
| a4_reuse | toolclaw_proxy | 126 |

## Failure Type Summary

| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | planner_sensitive | 126 | 1.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 4.000 |
| a2_planner | planner_sensitive | 126 | 0.738 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.738 | 5.476 |
| a3_interaction | planner_sensitive | 126 | 1.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.000 | 0.262 | 0.262 | 3.524 | 7.571 |
| a4_reuse | planner_sensitive | 126 | 1.000 | 0.000 | 0.000 | 1.000 | 0.262 | 0.000 | 0.262 | 0.262 | 3.524 | 7.571 |

## Repair Loop Summary

| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | 126 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 126 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 126 | 33 | 0.000 | 0.262 | 0.000 | 0.262 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 126 | 33 | 0.000 | 0.262 | 0.000 | 0.262 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Reuse Focused

| system | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|

## Statistical Robustness

- consistency=1.0 here mainly indicates deterministic replication stability across repeats.
- paired comparison is reported at task level (wins/losses/ties) with bootstrap 95% CI on mean success delta.

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 42 | 0 | 0 | 42 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 42 | 0 | 0 | 42 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: approval

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: planner_distractor_hard

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: repeated_reusable

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

### Focused Slice: state_repair

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a3_interaction | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 0 | 0 | 0 | 0 | +0.000 | [+0.000, +0.000] |

## Interpretation

- `mean_success_rate` is computed from strict scored success, not from proxy summaries alone.
- `strict_scored_success` is the benchmark-facing success after the must-interact gate is applied.
- `repair_scored_success` is stricter: it only counts runs that both score successfully and include at least one non-probe repair interaction.
- `interaction_contract_satisfied` can be lifted by an interaction probe; `repair_interaction_satisfied` cannot.
- `raw_trace_success_rate` / `raw_execution_success_rate` are reported separately because executor success and benchmark-verified success can diverge.
- `proxy_summary_success` tracks runs that looked successful under the attached ToolClaw proxy summary path.
- `milestone_signal_coverage` shows whether the trace carried an explicit milestone verification signal; low coverage weakens benchmark claims even if proxy summaries exist.
- `result_summary_source` is reported explicitly so proxy-derived runs are visible in the main report.
- All aggregate and category tables in this report are computed from `comparison.scored.csv`, not from raw `run_eval.py` rows.
- FailTax is the default slicing axis for phase-2 style failure studies; category tables remain useful but secondary.
- `comparison.raw.csv` is a local_debug_only artifact that preserves original execution outputs from `run_eval.py` for audit and debugging.
- `latest_run_raw_report.md` is a local_debug_only artifact that preserves the raw `run_eval.py` report so it is not confused with this scored benchmark report.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.
- `budget_violation_rate` and `recovery_budget_used` are the budget-side controls for phase-2 evaluation.