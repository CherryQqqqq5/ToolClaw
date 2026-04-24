# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.3086 | 0.4837 | 0.3086 | 0.4689 | 0.5162 | 0.6599 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1340, "other_official_failure": 153, "value_error": 537, "wrong_count": 1378, "wrong_func_name": 83}` |
| system=a1_recovery | 4291 | 0.3086 | 0.4852 | 0.3086 | 0.4701 | 0.5177 | 0.6584 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1340, "other_official_failure": 153, "value_error": 542, "wrong_count": 1373, "wrong_func_name": 83}` |
| system=a2_planner | 4291 | 0.3030 | 0.4848 | 0.3030 | 0.4698 | 0.5173 | 0.6584 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1316, "other_official_failure": 182, "value_error": 542, "wrong_count": 1368, "wrong_func_name": 83}` |
| system=a3_interaction | 4291 | 0.3037 | 0.6949 | 0.3037 | 0.6556 | 0.7288 | 0.4148 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1319, "other_official_failure": 277, "value_error": 859, "wrong_count": 458, "wrong_func_name": 178}` |
| system=a4_reuse | 4291 | 0.3037 | 0.6949 | 0.3037 | 0.6556 | 0.7288 | 0.4148 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1319, "other_official_failure": 277, "value_error": 859, "wrong_count": 458, "wrong_func_name": 178}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.4598 | 0.7299 | 0.4598 | 0.7263 | 0.7370 | 0.7287 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 142, "value_error": 460, "wrong_count": 516, "wrong_func_name": 82}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2331 | 0.3488 | 0.2331 | 0.3040 | 0.3488 | 0.8393 | `{"official_success_or_safe_failure": 289, "other_official_failure": 11, "value_error": 77, "wrong_count": 862, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.4598 | 0.7308 | 0.4598 | 0.7272 | 0.7379 | 0.7278 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 142, "value_error": 462, "wrong_count": 514, "wrong_func_name": 82}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2331 | 0.3523 | 0.2331 | 0.3065 | 0.3523 | 0.8355 | `{"official_success_or_safe_failure": 289, "other_official_failure": 11, "value_error": 80, "wrong_count": 859, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.4491 | 0.7304 | 0.4491 | 0.7272 | 0.7375 | 0.7276 | `{"official_success_or_safe_failure": 1027, "other_official_failure": 164, "value_error": 462, "wrong_count": 516, "wrong_func_name": 82}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2331 | 0.3518 | 0.2331 | 0.3056 | 0.3518 | 0.8359 | `{"official_success_or_safe_failure": 289, "other_official_failure": 18, "value_error": 80, "wrong_count": 852, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.4505 | 0.8901 | 0.4505 | 0.8841 | 0.8972 | 0.5465 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 194, "value_error": 647, "wrong_count": 71, "wrong_func_name": 169}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2331 | 0.7887 | 0.2331 | 0.6637 | 0.7887 | 0.3442 | `{"missing_required": 260, "official_success_or_safe_failure": 289, "other_official_failure": 83, "value_error": 212, "wrong_count": 387, "wrong_func_name": 9}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.4505 | 0.8901 | 0.4505 | 0.8841 | 0.8972 | 0.5465 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 194, "value_error": 647, "wrong_count": 71, "wrong_func_name": 169}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2331 | 0.7887 | 0.2331 | 0.6637 | 0.7887 | 0.3442 | `{"missing_required": 260, "official_success_or_safe_failure": 289, "other_official_failure": 83, "value_error": 212, "wrong_count": 387, "wrong_func_name": 9}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0114 | 0.1671 | 0.0114 | 0.0227 | 0.1671 | 0.6752 | `{"official_success_or_safe_failure": 5, "other_official_failure": 7, "wrong_count": 428}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.3425 | 0.5199 | 0.3425 | 0.5199 | 0.5561 | 0.6582 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1335, "other_official_failure": 146, "value_error": 537, "wrong_count": 950, "wrong_func_name": 83}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0114 | 0.1702 | 0.0114 | 0.0227 | 0.1702 | 0.6699 | `{"official_success_or_safe_failure": 5, "other_official_failure": 7, "wrong_count": 428}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.3425 | 0.5212 | 0.3425 | 0.5212 | 0.5574 | 0.6570 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1335, "other_official_failure": 146, "value_error": 542, "wrong_count": 945, "wrong_func_name": 83}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0114 | 0.1669 | 0.0114 | 0.0205 | 0.1669 | 0.6704 | `{"official_success_or_safe_failure": 5, "other_official_failure": 12, "wrong_count": 423}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.3363 | 0.5212 | 0.3363 | 0.5212 | 0.5574 | 0.6570 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1311, "other_official_failure": 170, "value_error": 542, "wrong_count": 945, "wrong_func_name": 83}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0114 | 0.4244 | 0.0114 | 0.0409 | 0.4244 | 0.1305 | `{"official_success_or_safe_failure": 5, "other_official_failure": 39, "wrong_count": 396}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.3371 | 0.7258 | 0.3371 | 0.7258 | 0.7636 | 0.4473 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1314, "other_official_failure": 238, "value_error": 859, "wrong_count": 62, "wrong_func_name": 178}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0114 | 0.4244 | 0.0114 | 0.0409 | 0.4244 | 0.1305 | `{"official_success_or_safe_failure": 5, "other_official_failure": 39, "wrong_count": 396}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.3371 | 0.7258 | 0.3371 | 0.7258 | 0.7636 | 0.4473 | `{"missing_required": 400, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1314, "other_official_failure": 238, "value_error": 859, "wrong_count": 62, "wrong_func_name": 178}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.2750 | 0.0000 | 0.0750 | 0.2750 | 0.6175 | `{"other_official_failure": 5, "wrong_count": 35}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4681 | 0.7381 | 0.4681 | 0.7381 | 0.7454 | 0.7307 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 137, "value_error": 460, "wrong_count": 481, "wrong_func_name": 82}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1563 | 0.0125 | 0.0175 | 0.1563 | 0.6810 | `{"official_success_or_safe_failure": 5, "other_official_failure": 2, "wrong_count": 393}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4405 | 0.3381 | 0.4405 | 0.4405 | 0.9148 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 77, "wrong_count": 469, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.2750 | 0.0000 | 0.0750 | 0.2750 | 0.6175 | `{"other_official_failure": 5, "wrong_count": 35}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4681 | 0.7390 | 0.4681 | 0.7390 | 0.7463 | 0.7298 | `{"official_success_or_safe_failure": 1051, "other_official_failure": 137, "value_error": 462, "wrong_count": 479, "wrong_func_name": 82}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1597 | 0.0125 | 0.0175 | 0.1597 | 0.6751 | `{"official_success_or_safe_failure": 5, "other_official_failure": 2, "wrong_count": 393}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4440 | 0.3381 | 0.4440 | 0.4440 | 0.9118 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 80, "wrong_count": 466, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.2542 | 0.0000 | 0.0750 | 0.2542 | 0.6083 | `{"other_official_failure": 3, "wrong_count": 37}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4573 | 0.7390 | 0.4573 | 0.7390 | 0.7463 | 0.7298 | `{"official_success_or_safe_failure": 1027, "other_official_failure": 161, "value_error": 462, "wrong_count": 479, "wrong_func_name": 82}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1582 | 0.0125 | 0.0150 | 0.1582 | 0.6766 | `{"official_success_or_safe_failure": 5, "other_official_failure": 9, "wrong_count": 386}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.4440 | 0.3381 | 0.4440 | 0.4440 | 0.9118 | `{"official_success_or_safe_failure": 284, "other_official_failure": 9, "value_error": 80, "wrong_count": 466, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4425 | 0.0000 | 0.1000 | 0.4425 | 0.2383 | `{"other_official_failure": 9, "wrong_count": 31}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4586 | 0.8982 | 0.4586 | 0.8982 | 0.9055 | 0.5521 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 185, "value_error": 647, "wrong_count": 40, "wrong_func_name": 169}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.4226 | 0.0125 | 0.0350 | 0.4226 | 0.1197 | `{"official_success_or_safe_failure": 5, "other_official_failure": 30, "wrong_count": 365}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.9631 | 0.3381 | 0.9631 | 0.9631 | 0.4511 | `{"missing_required": 260, "official_success_or_safe_failure": 284, "other_official_failure": 53, "value_error": 212, "wrong_count": 22, "wrong_func_name": 9}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4425 | 0.0000 | 0.1000 | 0.4425 | 0.2383 | `{"other_official_failure": 9, "wrong_count": 31}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4586 | 0.8982 | 0.4586 | 0.8982 | 0.9055 | 0.5521 | `{"missing_required": 140, "official_success_or_safe_failure": 1030, "other_official_failure": 185, "value_error": 647, "wrong_count": 40, "wrong_func_name": 169}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.4226 | 0.0125 | 0.0350 | 0.4226 | 0.1197 | `{"official_success_or_safe_failure": 5, "other_official_failure": 30, "wrong_count": 365}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3381 | 0.9631 | 0.3381 | 0.9631 | 0.9631 | 0.4511 | `{"missing_required": 260, "official_success_or_safe_failure": 284, "other_official_failure": 53, "value_error": 212, "wrong_count": 22, "wrong_func_name": 9}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1340 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9540 | `{"official_success_or_safe_failure": 1340}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 153 | 0.0000 | 0.9935 | 0.0000 | 0.9869 | 0.9935 | 0.2879 | `{"other_official_failure": 153}` |
| system=a0_baseline / official_failure_bucket=value_error | 537 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2088 | `{"value_error": 537}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 1378 | 0.0000 | 0.0454 | 0.0000 | 0.0000 | 0.0454 | 0.9001 | `{"wrong_count": 1378}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1340 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9540 | `{"official_success_or_safe_failure": 1340}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 153 | 0.0000 | 0.9935 | 0.0000 | 0.9869 | 0.9935 | 0.2879 | `{"other_official_failure": 153}` |
| system=a1_recovery / official_failure_bucket=value_error | 542 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2078 | `{"value_error": 542}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 1373 | 0.0000 | 0.0465 | 0.0000 | 0.0000 | 0.0465 | 0.8980 | `{"wrong_count": 1373}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1316 | 0.9878 | 0.9878 | 0.9878 | 0.9878 | 1.0000 | 0.9532 | `{"official_success_or_safe_failure": 1316}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 182 | 0.0000 | 0.9744 | 0.0000 | 0.9560 | 0.9744 | 0.3733 | `{"other_official_failure": 182}` |
| system=a2_planner / official_failure_bucket=value_error | 542 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2078 | `{"value_error": 542}` |
| system=a2_planner / official_failure_bucket=wrong_count | 1368 | 0.0000 | 0.0447 | 0.0000 | 0.0000 | 0.0447 | 0.9015 | `{"wrong_count": 1368}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0743 | `{"wrong_func_name": 83}` |
| system=a3_interaction / official_failure_bucket=missing_required | 400 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0843 | `{"missing_required": 400}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1319 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9533 | `{"official_success_or_safe_failure": 1319}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 277 | 0.0000 | 0.9489 | 0.0000 | 0.9061 | 0.9489 | 0.3045 | `{"other_official_failure": 277}` |
| system=a3_interaction / official_failure_bucket=value_error | 859 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1868 | `{"value_error": 859}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 458 | 0.0000 | 0.3426 | 0.0000 | 0.0000 | 0.3426 | 0.2404 | `{"wrong_count": 458}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 178 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0618 | `{"wrong_func_name": 178}` |
| system=a4_reuse / official_failure_bucket=missing_required | 400 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0843 | `{"missing_required": 400}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1319 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9533 | `{"official_success_or_safe_failure": 1319}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 277 | 0.0000 | 0.9489 | 0.0000 | 0.9061 | 0.9489 | 0.3045 | `{"other_official_failure": 277}` |
| system=a4_reuse / official_failure_bucket=value_error | 859 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1868 | `{"value_error": 859}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 458 | 0.0000 | 0.3426 | 0.0000 | 0.0000 | 0.3426 | 0.2404 | `{"wrong_count": 458}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 178 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0618 | `{"wrong_func_name": 178}` |
