# Interaction Live Benchmark Report

## Claim Summary

| verdict | value |
|---|---:|
| interaction_as_control_signal_supported | true |
| semantic_usefulness_supported_on_repair_semantic | true |
| probe_only_success_caveat_present | true |
| noisy_user_not_counted_as_useful_repair | true |
| irrelevant_user_not_counted_as_useful_repair | true |
| wrong_parameter_not_counted_as_effective_patch | true |
| extraction_f1_gate_passed | true |

## Repair Semantic Success

- `a2_planner`: 0.375
- `a3_no_query`: 0.375
- `a3_full_interaction_oracle`: 1.000
- `a3_full_interaction_noisy`: 0.625

## Interaction Effectiveness By System And Slice

| group | useful_round | reply_usable | effective_patch | post_query_progress | strict_success |
|---|---:|---:|---:|---:|---:|
| a3_full_interaction_irrelevant|repair_semantic_primary | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction_noisy|repair_semantic_primary | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| a3_full_interaction_oracle|repair_semantic_primary | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_full_interaction_partial|repair_semantic_primary | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| a3_full_interaction_wrong_parameter|repair_semantic_primary | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Extraction PRF By User Mode

| user_mode | target_f1 | value_f1 | action_f1 | target_false_positive_rate |
|---|---:|---:|---:|---:|
| irrelevant_user | 0.000 | 0.000 | 0.000 | 0.000 |
| noisy_user | 0.000 | 0.000 | 0.000 | 0.000 |
| oracle_user | 1.000 | 1.000 | 0.000 | 0.000 |
| partial_user | 1.000 | 0.000 | 0.000 | 0.000 |
| wrong_parameter_user | 0.000 | 0.000 | 0.000 | 0.000 |