# Raw vs Benchmark Success Gap Summary

raw_execution_success is executor-side completion; execution_verified_success and strict_scored_success are benchmark-facing checks. Positive gaps identify where execution completed but benchmark contract or strict interaction scoring did not pass.

## By System

| system | rows | raw_execution_success | execution_verified_success | strict_scored_success | raw_minus_verified | raw_minus_strict | verified_minus_strict |
|---|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | 264 | 0.989 | 0.989 | 0.682 | +0.000 | +0.307 | +0.307 |
| a2_planner | 264 | 1.000 | 1.000 | 0.693 | +0.000 | +0.307 | +0.307 |
| a3_full_interaction | 264 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | 264 | 1.000 | 1.000 | 0.693 | +0.000 | +0.307 | +0.307 |
| a3_noisy_user | 264 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |

## By System, Failure Type, And Category

| system | failure_type | category | rows | raw_execution_success | execution_verified_success | strict_scored_success | raw_minus_verified | raw_minus_strict | verified_minus_strict |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| a1_recovery | canonicalization | canonicalization | 87 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a1_recovery | insufficient_information | insufficient_information | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a1_recovery | multiple_user_turn | canonicalization | 45 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a1_recovery | multiple_user_turn | multiple_tool | 24 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a1_recovery | multiple_user_turn | state_dependency | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a1_recovery | single_user_turn | multiple_tool | 18 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a1_recovery | single_user_turn | single_tool | 42 | 0.929 | 0.929 | 0.929 | +0.000 | +0.000 | +0.000 |
| a1_recovery | state_dependency | canonicalization | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a1_recovery | state_dependency | state_dependency | 30 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a2_planner | canonicalization | canonicalization | 87 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a2_planner | insufficient_information | insufficient_information | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a2_planner | multiple_user_turn | canonicalization | 45 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a2_planner | multiple_user_turn | multiple_tool | 24 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a2_planner | multiple_user_turn | state_dependency | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a2_planner | single_user_turn | multiple_tool | 18 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a2_planner | single_user_turn | single_tool | 42 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a2_planner | state_dependency | canonicalization | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a2_planner | state_dependency | state_dependency | 30 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | canonicalization | canonicalization | 87 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | insufficient_information | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | multiple_user_turn | canonicalization | 45 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | multiple_user_turn | multiple_tool | 24 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | multiple_user_turn | state_dependency | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | single_user_turn | multiple_tool | 18 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | single_user_turn | single_tool | 42 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | state_dependency | canonicalization | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_full_interaction | state_dependency | state_dependency | 30 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | canonicalization | canonicalization | 87 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | insufficient_information | insufficient_information | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a3_no_query | multiple_user_turn | canonicalization | 45 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a3_no_query | multiple_user_turn | multiple_tool | 24 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a3_no_query | multiple_user_turn | state_dependency | 6 | 1.000 | 1.000 | 0.000 | +0.000 | +1.000 | +1.000 |
| a3_no_query | single_user_turn | multiple_tool | 18 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | single_user_turn | single_tool | 42 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | state_dependency | canonicalization | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_no_query | state_dependency | state_dependency | 30 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | canonicalization | canonicalization | 87 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | insufficient_information | insufficient_information | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | multiple_user_turn | canonicalization | 45 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | multiple_user_turn | multiple_tool | 24 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | multiple_user_turn | state_dependency | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | single_user_turn | multiple_tool | 18 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | single_user_turn | single_tool | 42 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | state_dependency | canonicalization | 6 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |
| a3_noisy_user | state_dependency | state_dependency | 30 | 1.000 | 1.000 | 1.000 | +0.000 | +0.000 | +0.000 |