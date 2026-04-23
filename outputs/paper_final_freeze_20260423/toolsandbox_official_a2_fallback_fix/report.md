# ToolSandbox Benchmark Report

- source: `/cephfs/qiuyn/ToolClaw/data/toolsandbox.formal.official.json`
- normalized_taskset: `/cephfs/qiuyn/ToolClaw/outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/prepared/toolsandbox.normalized.json`
- samples: `88`
- runs: `3`
- systems: `a0_baseline, a1_recovery, a2_planner, a3_interaction, a4_reuse`
- raw_execution_report: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/latest_run_raw_report.md`
- raw_comparison: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/comparison.raw.csv`
- scored_comparison: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/comparison.scored.csv`
- focused_slice_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/focused_slice_summary.md`
- reuse_focused_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/reuse_focused_summary.md`
- per_failure_type_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/per_failure_type_summary.md`
- repair_loop_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/repair_loop_summary.md`
- statistical_robustness_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/statistical_robustness_summary.json`
- failtax_summary: `outputs/paper_final_freeze_20260423/toolsandbox_official_a2_fallback_fix/per_failtax_summary.json`

## Readiness

- reuse_scope: `within_invocation`
- asset_registry_root: `none`

- primary_result_ready: `False`
- caution_flags:
  - `raw_vs_benchmark_success_gap`

## Aggregate

| system | mean_success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | consistency | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | budget_violation_rate | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | 0.636 | 0.636 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.943 | 0.943 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.261 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | 0.682 | 0.682 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.989 | 0.989 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.261 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | 0.693 | 0.693 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 1.000 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | 1.000 | 1.000 | 0.307 | 1.000 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.307 | 0.239 | 1.000 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | 1.000 | 1.000 | 0.375 | 1.000 | 0.375 | 0.068 | 0.068 | 0.068 | 0.068 | 0.068 | 0.375 | 0.239 | 1.000 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 0.000 | 1.000 | 1.000 | reference_result_summary |

## FailTax Breakdown

| system | primary_failtax | rows | success_rate | pass@k | consistency |
|---|---|---:|---:|---:|---:|
| a0_baseline | ordering | 14 | 0.429 | 0.429 | 1.000 |
| a0_baseline | selection | 60 | 0.667 | 0.667 | 1.000 |
| a0_baseline | state | 14 | 0.714 | 0.714 | 1.000 |
| a1_recovery | ordering | 14 | 0.429 | 0.429 | 1.000 |
| a1_recovery | selection | 60 | 0.733 | 0.733 | 1.000 |
| a1_recovery | state | 14 | 0.714 | 0.714 | 1.000 |
| a2_planner | ordering | 14 | 0.429 | 0.429 | 1.000 |
| a2_planner | selection | 60 | 0.750 | 0.750 | 1.000 |
| a2_planner | state | 14 | 0.714 | 0.714 | 1.000 |
| a3_interaction | ordering | 14 | 1.000 | 1.000 | 1.000 |
| a3_interaction | selection | 60 | 1.000 | 1.000 | 1.000 |
| a3_interaction | state | 14 | 1.000 | 1.000 | 1.000 |
| a4_reuse | ordering | 14 | 1.000 | 1.000 | 1.000 |
| a4_reuse | selection | 60 | 1.000 | 1.000 | 1.000 |
| a4_reuse | state | 14 | 1.000 | 1.000 | 1.000 |

## Category Breakdown

| system | category | rows | success_rate | strict_scored_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | repair_interaction_satisfied | proxy_summary_success | raw_trace_success_rate | raw_execution_success_rate | milestone_similarity | milestone_coverage | milestone_signal_coverage | state_dependency_score | hallucination_avoidance | tool_efficiency | turn_efficiency | result_summary_coverage | reference_summary_coverage | dominant_result_summary_source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| a0_baseline | canonicalization | 138 | 1.000 | 0.674 | 0.000 | 0.674 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 0.022 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | multiple_tool | 213 | 1.000 | 0.648 | 0.000 | 0.648 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 0.085 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | no_distraction_tools | 264 | 0.943 | 0.636 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.943 | 0.943 | 0.790 | 1.000 | 1.000 | 0.977 | 0.261 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | single_tool | 45 | 0.667 | 0.667 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 0.667 | 0.667 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | single_user_turn | 183 | 0.918 | 0.918 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 0.918 | 0.918 | 0.820 | 1.000 | 1.000 | 0.978 | 0.344 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a0_baseline | state_dependency | 48 | 1.000 | 0.750 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | canonicalization | 138 | 1.000 | 0.674 | 0.000 | 0.674 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 0.022 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | multiple_tool | 213 | 1.000 | 0.648 | 0.000 | 0.648 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 0.085 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | no_distraction_tools | 264 | 0.989 | 0.682 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 0.989 | 0.989 | 0.790 | 1.000 | 1.000 | 0.977 | 0.261 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | single_tool | 45 | 0.933 | 0.933 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 0.933 | 0.933 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.960 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | single_user_turn | 183 | 0.984 | 0.984 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 0.984 | 0.984 | 0.820 | 1.000 | 1.000 | 0.978 | 0.344 | 0.990 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a1_recovery | state_dependency | 48 | 1.000 | 0.750 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 0.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | canonicalization | 138 | 1.000 | 0.674 | 0.000 | 0.674 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 0.913 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | multiple_tool | 213 | 1.000 | 0.648 | 0.000 | 0.648 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 0.859 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 0.880 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | no_distraction_tools | 264 | 1.000 | 0.693 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | single_tool | 45 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | single_user_turn | 183 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 1.000 | 1.000 | 0.820 | 1.000 | 1.000 | 0.978 | 0.885 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a2_planner | state_dependency | 48 | 1.000 | 0.750 | 0.000 | 0.750 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 0.562 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | canonicalization | 138 | 1.000 | 1.000 | 0.326 | 1.000 | 0.326 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.326 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 0.913 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | multiple_tool | 213 | 1.000 | 1.000 | 0.352 | 1.000 | 0.352 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.352 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 0.859 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | multiple_user_turn | 75 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 0.880 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | no_distraction_tools | 264 | 1.000 | 1.000 | 0.307 | 1.000 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.307 | 0.239 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | single_tool | 45 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | single_user_turn | 183 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.262 | 1.000 | 1.000 | 0.820 | 1.000 | 1.000 | 0.978 | 0.885 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a3_interaction | state_dependency | 48 | 1.000 | 1.000 | 0.250 | 1.000 | 0.250 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.250 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 0.562 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | canonicalization | 138 | 1.000 | 1.000 | 0.326 | 1.000 | 0.326 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.326 | 0.304 | 1.000 | 1.000 | 0.755 | 1.000 | 1.000 | 0.979 | 0.913 | 0.997 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.635 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | multiple_tool | 213 | 1.000 | 1.000 | 0.437 | 1.000 | 0.437 | 0.085 | 0.085 | 0.085 | 0.085 | 0.085 | 0.437 | 0.239 | 1.000 | 1.000 | 0.774 | 1.000 | 1.000 | 0.971 | 0.859 | 0.998 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | multiple_user_turn | 75 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.200 | 1.000 | 1.000 | 0.732 | 1.000 | 1.000 | 0.972 | 0.880 | 0.994 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | no_distraction_tools | 264 | 1.000 | 1.000 | 0.375 | 1.000 | 0.375 | 0.068 | 0.068 | 0.068 | 0.068 | 0.068 | 0.375 | 0.239 | 1.000 | 1.000 | 0.790 | 1.000 | 1.000 | 0.977 | 0.886 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | single_tool | 45 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.267 | 1.000 | 1.000 | 0.890 | 1.000 | 1.000 | 1.000 | 1.000 | 0.970 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | single_user_turn | 183 | 1.000 | 1.000 | 0.098 | 1.000 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.098 | 0.262 | 1.000 | 1.000 | 0.820 | 1.000 | 1.000 | 0.978 | 0.885 | 0.993 | 1.000 | 1.000 | 1.000 | reference_result_summary |
| a4_reuse | state_dependency | 48 | 1.000 | 1.000 | 0.625 | 1.000 | 0.625 | 0.375 | 0.375 | 0.375 | 0.375 | 0.375 | 0.625 | 0.188 | 1.000 | 1.000 | 0.873 | 1.000 | 1.000 | 0.873 | 0.562 | 0.991 | 1.000 | 1.000 | 1.000 | reference_result_summary |

## Result Summary Sources

| system | result_summary_source | rows |
|---|---|---:|
| a0_baseline | reference_result_summary | 264 |
| a1_recovery | reference_result_summary | 264 |
| a2_planner | reference_result_summary | 264 |
| a3_interaction | reference_result_summary | 264 |
| a4_reuse | reference_result_summary | 264 |

## Failure Type Summary

| system | failure_type | rows | raw_execution_success | strict_scored_success | repair_scored_success | interaction_contract_satisfied | repair_interaction_satisfied | probe_user_queries | repair_user_queries | patch_success_rate | tool_calls | turn_count |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | canonicalization | 87 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.966 | 10.276 |
| a0_baseline | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a0_baseline | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 11.160 |
| a0_baseline | single_user_turn | 60 | 0.750 | 0.750 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 4.200 |
| a0_baseline | state_dependency | 36 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 11.333 |
| a1_recovery | canonicalization | 87 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.966 | 10.276 |
| a1_recovery | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a1_recovery | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 11.160 |
| a1_recovery | single_user_turn | 60 | 0.950 | 0.950 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.200 | 4.200 |
| a1_recovery | state_dependency | 36 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 2.000 | 11.333 |
| a2_planner | canonicalization | 87 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a2_planner | insufficient_information | 6 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a2_planner | multiple_user_turn | 75 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.280 | 11.160 |
| a2_planner | single_user_turn | 60 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a2_planner | state_dependency | 36 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.500 | 11.333 |
| a3_interaction | canonicalization | 87 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a3_interaction | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a3_interaction | multiple_user_turn | 75 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.280 | 11.160 |
| a3_interaction | single_user_turn | 60 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a3_interaction | state_dependency | 36 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.500 | 11.333 |
| a4_reuse | canonicalization | 87 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.069 | 10.276 |
| a4_reuse | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 13.000 |
| a4_reuse | multiple_user_turn | 75 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.280 | 11.160 |
| a4_reuse | single_user_turn | 60 | 1.000 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.150 | 4.200 |
| a4_reuse | state_dependency | 36 | 1.000 | 1.000 | 0.500 | 1.000 | 0.500 | 0.000 | 0.500 | 0.500 | 1.500 | 11.333 |

## Repair Loop Summary

| system | rows | repair_rows | repair_scored_success | repair_user_queries | probe_user_queries | patch_success_rate | has_patch_compiled | has_resume_requested | patch_compiled_count | resume_requested_count | state_patch_count | policy_patch_count | binding_patch_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a0_baseline | 264 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a1_recovery | 264 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 264 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_interaction | 264 | 81 | 0.307 | 0.000 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a4_reuse | 264 | 99 | 0.375 | 0.068 | 0.307 | 0.068 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Reuse Focused

| system | avg_tool_calls | repair_trigger_rate | avg_repair_actions | avg_repair_extra_tool_calls | avg_repair_extra_user_turns | reused_artifact_rate | mean_second_run_improvement | first_failure_recovered_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|

## Statistical Robustness

- consistency=1.0 here mainly indicates deterministic replication stability across repeats.
- paired comparison is reported at task level (wins/losses/ties) with bootstrap 95% CI on mean success delta.

| pair | tasks | wins | losses | ties | mean_success_delta | bootstrap_95%_ci |
|---|---:|---:|---:|---:|---:|---|
| a2_planner vs a3_interaction | 88 | 0 | 27 | 61 | -0.307 | [-0.409, -0.216] |
| a4_reuse vs a3_interaction | 88 | 0 | 0 | 88 | +0.000 | [+0.000, +0.000] |
| a4_reuse vs a0_baseline | 88 | 32 | 0 | 56 | +0.364 | [+0.261, +0.477] |

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
- `comparison.raw.csv` preserves the original execution outputs from `run_eval.py` for audit and debugging.
- `latest_run_raw_report.md` preserves the raw `run_eval.py` report so it is not confused with this scored benchmark report.
- `result_summary_coverage` shows how much of the benchmark has a current ToolClaw-run ToolSandbox summary attached to the trace. This should be 1.0 for normal runs.
- `reference_summary_coverage` shows how much of the benchmark also carries imported external ToolSandbox summaries for offline comparison or dataset freezing.
- These scores come from ToolClaw proxy evaluation over ToolSandbox-style tasks unless you are reading outputs from the official ToolSandbox CLI directly.
- `state_dependency_score` is only meaningful on `state_dependency` slices; interpret it through the category table rather than overall averages.
- `turn_efficiency` and `tool_efficiency` are control metrics, not success substitutes.
- `budget_violation_rate` and `recovery_budget_used` are the budget-side controls for phase-2 evaluation.