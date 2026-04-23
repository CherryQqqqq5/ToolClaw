# ToolSandbox Causal Ablation Report

## Verdicts

| verdict | value |
|---|---:|
| htgp_structural_reduction_supported | true |
| interaction_not_cheating_supported | true |
| interaction_query_contribution_supported | true |
| interaction_success_metric_caveat | false |
| no_query_repair_mechanism_supported | false |

## System Summary

| system | strict_scored_success | execution_verified_success | raw_execution_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a2_planner | 0.625 | 0.625 | 0.932 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 1.000 | 1.000 | 1.000 | 0.375 | 1.000 | 0.375 | 0.068 | 0.068 | 0.068 | 0.068 | 0.068 |
| a3_no_query | 0.625 | 0.625 | 0.932 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 0.932 | 0.932 | 0.932 | 0.307 | 1.000 | 0.375 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Risk Flags

- `noisy_user_above_planner`