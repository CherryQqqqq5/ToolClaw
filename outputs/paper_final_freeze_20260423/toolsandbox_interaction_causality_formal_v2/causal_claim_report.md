# ToolSandbox Causal Ablation Report

## Verdicts

| verdict | value |
|---|---:|
| htgp_structural_reduction_supported | false |
| interaction_not_cheating_supported | false |
| interaction_success_metric_caveat | true |
| no_query_repair_mechanism_supported | false |
| overall_interaction_query_contribution_supported | true |
| probe_only_success_caveat_present | true |
| protocol_complete | true |
| repair_semantic_usefulness_supported | false |

## Protocol

- protocol_complete: `true`
- systems_expected: `a1_recovery, a2_planner, a3_full_interaction, a3_no_query, a3_noisy_user`
- systems_observed: `a1_recovery, a2_planner, a3_full_interaction, a3_no_query, a3_noisy_user`
- missing_expected_systems: `none`
- unexpected_systems: `none`

## Slice Policy

- version: `toolsandbox_causality_v1`
- `overall`: `all`
- `repair_semantic`: `['state_dependency']`
- `probe_only`: `['insufficient_information', 'multiple_user_turn']`

## Overall System Summary

| system | strict_scored_success | execution_verified_success | raw_execution_success | repair_scored_success | interaction_contract_satisfied | mean_user_queries | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | 0.682 | 0.989 | 0.989 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 0.693 | 1.000 | 1.000 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 1.000 | 1.000 | 1.000 | 0.307 | 1.000 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | 0.693 | 1.000 | 1.000 | 0.000 | 0.693 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 1.000 | 1.000 | 1.000 | 0.307 | 1.000 | 0.307 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Repair Semantic Slice

| system | strict_scored_success | execution_verified_success | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | probe_user_queries | repair_user_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_no_query | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Probe Only Slice

| system | strict_scored_success | execution_verified_success | reply_usable_rate | target_aligned_patch_rate | effective_patch_rate | post_query_progress_rate | useful_interaction_round_rate | probe_user_queries | repair_user_queries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a2_planner | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| a3_no_query | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_noisy_user | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

## Risk Flags

- `noisy_user_above_planner`
- `success_metric_probe_only_caveat`
- `repair_semantic_usefulness_not_supported`
- `htgp_structural_claim_not_supported`