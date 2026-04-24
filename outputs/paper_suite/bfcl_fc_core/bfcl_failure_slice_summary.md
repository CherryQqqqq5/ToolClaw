# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.3088 | 0.4846 | 0.3088 | 0.4703 | 0.5171 | 0.6603 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1341, "other_official_failure": 159, "value_error": 537, "wrong_count": 1371, "wrong_func_name": 83}` |
| system=a1_recovery | 4291 | 0.3088 | 0.4861 | 0.3088 | 0.4715 | 0.5186 | 0.6588 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1341, "other_official_failure": 159, "value_error": 542, "wrong_count": 1366, "wrong_func_name": 83}` |
| system=a2_planner | 4291 | 0.3032 | 0.4858 | 0.3032 | 0.4715 | 0.5183 | 0.6587 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1317, "other_official_failure": 188, "value_error": 542, "wrong_count": 1361, "wrong_func_name": 83}` |
| system=a3_interaction | 4291 | 0.3039 | 0.6989 | 0.3039 | 0.6612 | 0.7329 | 0.4152 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1320, "other_official_failure": 298, "value_error": 859, "wrong_count": 436, "wrong_func_name": 178}` |
| system=a4_reuse | 4291 | 0.3039 | 0.6989 | 0.3039 | 0.6612 | 0.7329 | 0.4152 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1320, "other_official_failure": 298, "value_error": 859, "wrong_count": 436, "wrong_func_name": 178}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.4602 | 0.7301 | 0.4602 | 0.7268 | 0.7372 | 0.7287 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 142, "value_error": 460, "wrong_count": 515, "wrong_func_name": 82}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2331 | 0.3516 | 0.2331 | 0.3081 | 0.3516 | 0.8407 | `{"official_success_or_safe_failure": 289, "other_official_failure": 17, "value_error": 77, "wrong_count": 856, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.4602 | 0.7310 | 0.4602 | 0.7277 | 0.7381 | 0.7278 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 142, "value_error": 462, "wrong_count": 513, "wrong_func_name": 82}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2331 | 0.3551 | 0.2331 | 0.3105 | 0.3551 | 0.8368 | `{"official_success_or_safe_failure": 289, "other_official_failure": 17, "value_error": 80, "wrong_count": 853, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.4496 | 0.7306 | 0.4496 | 0.7277 | 0.7377 | 0.7276 | `{"official_success_or_safe_failure": 1028, "other_official_failure": 164, "value_error": 462, "wrong_count": 515, "wrong_func_name": 82}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2331 | 0.3547 | 0.2331 | 0.3105 | 0.3547 | 0.8370 | `{"official_success_or_safe_failure": 289, "other_official_failure": 24, "value_error": 80, "wrong_count": 846, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.4509 | 0.8912 | 0.4509 | 0.8863 | 0.8984 | 0.5465 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 197, "value_error": 647, "wrong_count": 67, "wrong_func_name": 169}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2331 | 0.8008 | 0.2331 | 0.6790 | 0.8008 | 0.3455 | `{"missing_required": 260, "official_success_or_safe_failure": 289, "other_official_failure": 101, "value_error": 212, "wrong_count": 369, "wrong_func_name": 9}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.4509 | 0.8912 | 0.4509 | 0.8863 | 0.8984 | 0.5465 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 197, "value_error": 647, "wrong_count": 67, "wrong_func_name": 169}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2331 | 0.8008 | 0.2331 | 0.6790 | 0.8008 | 0.3455 | `{"missing_required": 260, "official_success_or_safe_failure": 289, "other_official_failure": 101, "value_error": 212, "wrong_count": 369, "wrong_func_name": 9}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0136 | 0.1760 | 0.0136 | 0.0364 | 0.1760 | 0.6791 | `{"official_success_or_safe_failure": 6, "other_official_failure": 13, "wrong_count": 421}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.3425 | 0.5199 | 0.3425 | 0.5199 | 0.5561 | 0.6582 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1335, "other_official_failure": 146, "value_error": 537, "wrong_count": 950, "wrong_func_name": 83}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0136 | 0.1791 | 0.0136 | 0.0364 | 0.1791 | 0.6738 | `{"official_success_or_safe_failure": 6, "other_official_failure": 13, "wrong_count": 421}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.3425 | 0.5212 | 0.3425 | 0.5212 | 0.5574 | 0.6570 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1335, "other_official_failure": 146, "value_error": 542, "wrong_count": 945, "wrong_func_name": 83}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0136 | 0.1762 | 0.0136 | 0.0364 | 0.1762 | 0.6736 | `{"official_success_or_safe_failure": 6, "other_official_failure": 18, "wrong_count": 416}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.3363 | 0.5212 | 0.3363 | 0.5212 | 0.5574 | 0.6570 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1311, "other_official_failure": 170, "value_error": 542, "wrong_count": 945, "wrong_func_name": 83}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0136 | 0.4640 | 0.0136 | 0.0955 | 0.4640 | 0.1344 | `{"official_success_or_safe_failure": 6, "other_official_failure": 60, "wrong_count": 374}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.3371 | 0.7258 | 0.3371 | 0.7258 | 0.7636 | 0.4473 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1314, "other_official_failure": 238, "value_error": 859, "wrong_count": 62, "wrong_func_name": 178}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0136 | 0.4640 | 0.0136 | 0.0955 | 0.4640 | 0.1344 | `{"official_success_or_safe_failure": 6, "other_official_failure": 60, "wrong_count": 374}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.3371 | 0.7258 | 0.3371 | 0.7258 | 0.7636 | 0.4473 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1314, "other_official_failure": 238, "value_error": 859, "wrong_count": 62, "wrong_func_name": 178}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0250 | 0.2875 | 0.0250 | 0.1000 | 0.2875 | 0.6175 | `{"official_success_or_safe_failure": 1, "other_official_failure": 5, "wrong_count": 34}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4681 | 0.7381 | 0.4681 | 0.7381 | 0.7454 | 0.7307 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 137, "value_error": 460, "wrong_count": 481, "wrong_func_name": 82}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1649 | 0.0125 | 0.0300 | 0.1649 | 0.6852 | `{"official_success_or_safe_failure": 5, "other_official_failure": 8, "wrong_count": 387}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4405 | 0.3381 | 0.4405 | 0.4405 | 0.9148 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 77, "wrong_count": 469, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0250 | 0.2875 | 0.0250 | 0.1000 | 0.2875 | 0.6175 | `{"official_success_or_safe_failure": 1, "other_official_failure": 5, "wrong_count": 34}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4681 | 0.7390 | 0.4681 | 0.7390 | 0.7463 | 0.7298 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 137, "value_error": 462, "wrong_count": 479, "wrong_func_name": 82}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1682 | 0.0125 | 0.0300 | 0.1682 | 0.6794 | `{"official_success_or_safe_failure": 5, "other_official_failure": 8, "wrong_count": 387}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4440 | 0.3381 | 0.4440 | 0.4440 | 0.9118 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 80, "wrong_count": 466, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0250 | 0.2667 | 0.0250 | 0.1000 | 0.2667 | 0.6083 | `{"official_success_or_safe_failure": 1, "other_official_failure": 3, "wrong_count": 36}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4573 | 0.7390 | 0.4573 | 0.7390 | 0.7463 | 0.7298 | `{"official_success_or_safe_failure": 1027, "other_official_failure": 161, "value_error": 462, "wrong_count": 479, "wrong_func_name": 82}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1672 | 0.0125 | 0.0300 | 0.1672 | 0.6801 | `{"official_success_or_safe_failure": 5, "other_official_failure": 15, "wrong_count": 380}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4440 | 0.3381 | 0.4440 | 0.4440 | 0.9118 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 80, "wrong_count": 466, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0250 | 0.5050 | 0.0250 | 0.2250 | 0.5050 | 0.2383 | `{"official_success_or_safe_failure": 1, "other_official_failure": 12, "wrong_count": 27}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4586 | 0.8982 | 0.4586 | 0.8982 | 0.9055 | 0.5521 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 185, "value_error": 647, "wrong_count": 40, "wrong_func_name": 169}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.4599 | 0.0125 | 0.0825 | 0.4599 | 0.1240 | `{"official_success_or_safe_failure": 5, "other_official_failure": 48, "wrong_count": 347}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.9631 | 0.3381 | 0.9631 | 0.9631 | 0.4511 | `{"missing_required": 260, "official_success_or_safe_failure": 284, "other_official_failure": 53, "value_error": 212, "wrong_count": 22, "wrong_func_name": 9}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0250 | 0.5050 | 0.0250 | 0.2250 | 0.5050 | 0.2383 | `{"official_success_or_safe_failure": 1, "other_official_failure": 12, "wrong_count": 27}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4586 | 0.8982 | 0.4586 | 0.8982 | 0.9055 | 0.5521 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 185, "value_error": 647, "wrong_count": 40, "wrong_func_name": 169}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.4599 | 0.0125 | 0.0825 | 0.4599 | 0.1240 | `{"official_success_or_safe_failure": 5, "other_official_failure": 48, "wrong_count": 347}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.9631 | 0.3381 | 0.9631 | 0.9631 | 0.4511 | `{"missing_required": 260, "official_success_or_safe_failure": 284, "other_official_failure": 53, "value_error": 212, "wrong_count": 22, "wrong_func_name": 9}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1341 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9541 | `{"official_success_or_safe_failure": 1341}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 159 | 0.0000 | 0.9906 | 0.0000 | 0.9811 | 0.9906 | 0.2914 | `{"other_official_failure": 159}` |
| system=a0_baseline / official_failure_bucket=value_error | 537 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2088 | `{"value_error": 537}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 1371 | 0.0000 | 0.0437 | 0.0000 | 0.0000 | 0.0437 | 0.9035 | `{"wrong_count": 1371}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1341 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9541 | `{"official_success_or_safe_failure": 1341}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 159 | 0.0000 | 0.9906 | 0.0000 | 0.9811 | 0.9906 | 0.2914 | `{"other_official_failure": 159}` |
| system=a1_recovery / official_failure_bucket=value_error | 542 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2078 | `{"value_error": 542}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 1366 | 0.0000 | 0.0449 | 0.0000 | 0.0000 | 0.0449 | 0.9015 | `{"wrong_count": 1366}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1317 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9532 | `{"official_success_or_safe_failure": 1317}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 188 | 0.0000 | 0.9752 | 0.0000 | 0.9574 | 0.9752 | 0.3720 | `{"other_official_failure": 188}` |
| system=a2_planner / official_failure_bucket=value_error | 542 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2078 | `{"value_error": 542}` |
| system=a2_planner / official_failure_bucket=wrong_count | 1361 | 0.0000 | 0.0428 | 0.0000 | 0.0000 | 0.0428 | 0.9050 | `{"wrong_count": 1361}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a3_interaction / official_failure_bucket=missing_required | 400 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0843 | `{"missing_required": 400}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1320 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9533 | `{"official_success_or_safe_failure": 1320}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 298 | 0.0000 | 0.9558 | 0.0000 | 0.9195 | 0.9558 | 0.2969 | `{"other_official_failure": 298}` |
| system=a3_interaction / official_failure_bucket=value_error | 859 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1868 | `{"value_error": 859}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 436 | 0.0000 | 0.3471 | 0.0000 | 0.0000 | 0.3471 | 0.2447 | `{"wrong_count": 436}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 178 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0618 | `{"wrong_func_name": 178}` |
| system=a4_reuse / official_failure_bucket=missing_required | 400 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0843 | `{"missing_required": 400}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1320 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9533 | `{"official_success_or_safe_failure": 1320}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 298 | 0.0000 | 0.9558 | 0.0000 | 0.9195 | 0.9558 | 0.2969 | `{"other_official_failure": 298}` |
| system=a4_reuse / official_failure_bucket=value_error | 859 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1868 | `{"value_error": 859}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 436 | 0.0000 | 0.3471 | 0.0000 | 0.0000 | 0.3471 | 0.2447 | `{"wrong_count": 436}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 178 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0618 | `{"wrong_func_name": 178}` |
