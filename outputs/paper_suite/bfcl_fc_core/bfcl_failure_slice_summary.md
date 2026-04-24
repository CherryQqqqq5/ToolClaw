# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.3100 | 0.5114 | 0.3100 | 0.4966 | 0.5439 | 0.6413 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1346, "other_official_failure": 175, "value_error": 629, "wrong_count": 1260, "wrong_func_name": 81}` |
| system=a1_recovery | 4291 | 0.3100 | 0.5129 | 0.3100 | 0.4980 | 0.5454 | 0.6398 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1346, "other_official_failure": 176, "value_error": 634, "wrong_count": 1254, "wrong_func_name": 81}` |
| system=a2_planner | 4291 | 0.3044 | 0.5125 | 0.3044 | 0.4978 | 0.5450 | 0.6398 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1322, "other_official_failure": 204, "value_error": 634, "wrong_count": 1250, "wrong_func_name": 81}` |
| system=a3_interaction | 4291 | 0.3051 | 0.7170 | 0.3051 | 0.6786 | 0.7509 | 0.4124 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1325, "other_official_failure": 338, "value_error": 913, "wrong_count": 385, "wrong_func_name": 154}` |
| system=a4_reuse | 4291 | 0.3051 | 0.7170 | 0.3051 | 0.6786 | 0.7509 | 0.4124 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1325, "other_official_failure": 338, "value_error": 913, "wrong_count": 385, "wrong_func_name": 154}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.4611 | 0.7679 | 0.4611 | 0.7650 | 0.7750 | 0.6991 | `{"official_success_or_safe_failure": 1054, "other_official_failure": 149, "value_error": 537, "wrong_count": 431, "wrong_func_name": 80}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2355 | 0.3757 | 0.2355 | 0.3298 | 0.3757 | 0.8284 | `{"official_success_or_safe_failure": 292, "other_official_failure": 26, "value_error": 92, "wrong_count": 829, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.4611 | 0.7688 | 0.4611 | 0.7659 | 0.7759 | 0.6982 | `{"official_success_or_safe_failure": 1054, "other_official_failure": 149, "value_error": 539, "wrong_count": 429, "wrong_func_name": 80}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2355 | 0.3794 | 0.2355 | 0.3331 | 0.3794 | 0.8250 | `{"official_success_or_safe_failure": 292, "other_official_failure": 27, "value_error": 95, "wrong_count": 825, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.4505 | 0.7682 | 0.4505 | 0.7654 | 0.7753 | 0.6980 | `{"official_success_or_safe_failure": 1030, "other_official_failure": 170, "value_error": 539, "wrong_count": 432, "wrong_func_name": 80}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2355 | 0.3790 | 0.2355 | 0.3331 | 0.3790 | 0.8253 | `{"official_success_or_safe_failure": 292, "other_official_failure": 34, "value_error": 95, "wrong_count": 818, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.4518 | 0.9109 | 0.4518 | 0.9063 | 0.9180 | 0.5411 | `{"missing_required": 140, "official_success_or_safe_failure": 1033, "other_official_failure": 207, "value_error": 680, "wrong_count": 47, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2355 | 0.8275 | 0.2355 | 0.7032 | 0.8275 | 0.3458 | `{"missing_required": 236, "official_success_or_safe_failure": 292, "other_official_failure": 131, "value_error": 233, "wrong_count": 338, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.4518 | 0.9109 | 0.4518 | 0.9063 | 0.9180 | 0.5411 | `{"missing_required": 140, "official_success_or_safe_failure": 1033, "other_official_failure": 207, "value_error": 680, "wrong_count": 47, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2355 | 0.8275 | 0.2355 | 0.7032 | 0.8275 | 0.3458 | `{"missing_required": 236, "official_success_or_safe_failure": 292, "other_official_failure": 131, "value_error": 233, "wrong_count": 338, "wrong_func_name": 10}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1987 | 0.0159 | 0.0545 | 0.1987 | 0.6637 | `{"official_success_or_safe_failure": 7, "other_official_failure": 20, "wrong_count": 413}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.3435 | 0.5471 | 0.3435 | 0.5471 | 0.5833 | 0.6387 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1339, "other_official_failure": 155, "value_error": 629, "wrong_count": 847, "wrong_func_name": 81}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.2021 | 0.0159 | 0.0568 | 0.2021 | 0.6599 | `{"official_success_or_safe_failure": 7, "other_official_failure": 21, "wrong_count": 412}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.3435 | 0.5484 | 0.3435 | 0.5484 | 0.5846 | 0.6375 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1339, "other_official_failure": 155, "value_error": 634, "wrong_count": 842, "wrong_func_name": 81}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1981 | 0.0159 | 0.0545 | 0.1981 | 0.6593 | `{"official_success_or_safe_failure": 7, "other_official_failure": 25, "wrong_count": 408}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.3373 | 0.5484 | 0.3373 | 0.5484 | 0.5846 | 0.6375 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1315, "other_official_failure": 179, "value_error": 634, "wrong_count": 842, "wrong_func_name": 81}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5082 | 0.0159 | 0.1341 | 0.5082 | 0.1280 | `{"official_success_or_safe_failure": 7, "other_official_failure": 76, "wrong_count": 357}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.3381 | 0.7408 | 0.3381 | 0.7408 | 0.7786 | 0.4449 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1318, "other_official_failure": 262, "value_error": 913, "wrong_count": 28, "wrong_func_name": 154}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5082 | 0.0159 | 0.1341 | 0.5082 | 0.1280 | `{"official_success_or_safe_failure": 7, "other_official_failure": 76, "wrong_count": 357}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.3381 | 0.7408 | 0.3381 | 0.7408 | 0.7786 | 0.4449 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1318, "other_official_failure": 262, "value_error": 913, "wrong_count": 28, "wrong_func_name": 154}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4625 | 0.0500 | 0.3000 | 0.4625 | 0.5050 | `{"official_success_or_safe_failure": 2, "other_official_failure": 12, "wrong_count": 26}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4686 | 0.7734 | 0.4686 | 0.7734 | 0.7806 | 0.7026 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 137, "value_error": 537, "wrong_count": 405, "wrong_func_name": 80}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1723 | 0.0125 | 0.0300 | 0.1723 | 0.6796 | `{"official_success_or_safe_failure": 5, "other_official_failure": 8, "wrong_count": 387}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3417 | 0.4726 | 0.3417 | 0.4726 | 0.4726 | 0.8993 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 92, "wrong_count": 442, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4625 | 0.0500 | 0.3000 | 0.4625 | 0.5050 | `{"official_success_or_safe_failure": 2, "other_official_failure": 12, "wrong_count": 26}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4686 | 0.7743 | 0.4686 | 0.7743 | 0.7815 | 0.7017 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 137, "value_error": 539, "wrong_count": 403, "wrong_func_name": 80}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1760 | 0.0125 | 0.0325 | 0.1760 | 0.6754 | `{"official_success_or_safe_failure": 5, "other_official_failure": 9, "wrong_count": 386}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3417 | 0.4762 | 0.3417 | 0.4762 | 0.4762 | 0.8963 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 95, "wrong_count": 439, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4292 | 0.0500 | 0.2750 | 0.4292 | 0.4917 | `{"official_success_or_safe_failure": 2, "other_official_failure": 9, "wrong_count": 29}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4577 | 0.7743 | 0.4577 | 0.7743 | 0.7815 | 0.7017 | `{"official_success_or_safe_failure": 1028, "other_official_failure": 161, "value_error": 539, "wrong_count": 403, "wrong_func_name": 80}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1750 | 0.0125 | 0.0325 | 0.1750 | 0.6761 | `{"official_success_or_safe_failure": 5, "other_official_failure": 16, "wrong_count": 379}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3417 | 0.4762 | 0.3417 | 0.4762 | 0.4762 | 0.8963 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 95, "wrong_count": 439, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5863 | 0.0500 | 0.3250 | 0.5863 | 0.2238 | `{"official_success_or_safe_failure": 2, "other_official_failure": 15, "wrong_count": 23}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4591 | 0.9168 | 0.4591 | 0.9168 | 0.9240 | 0.5468 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 192, "value_error": 680, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5004 | 0.0125 | 0.1150 | 0.5004 | 0.1184 | `{"official_success_or_safe_failure": 5, "other_official_failure": 61, "wrong_count": 334}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3417 | 0.9833 | 0.3417 | 0.9833 | 0.9833 | 0.4540 | `{"missing_required": 236, "official_success_or_safe_failure": 287, "other_official_failure": 70, "value_error": 233, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5863 | 0.0500 | 0.3250 | 0.5863 | 0.2238 | `{"official_success_or_safe_failure": 2, "other_official_failure": 15, "wrong_count": 23}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4591 | 0.9168 | 0.4591 | 0.9168 | 0.9240 | 0.5468 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 192, "value_error": 680, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5004 | 0.0125 | 0.1150 | 0.5004 | 0.1184 | `{"official_success_or_safe_failure": 5, "other_official_failure": 61, "wrong_count": 334}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3417 | 0.9833 | 0.3417 | 0.9833 | 0.9833 | 0.4540 | `{"missing_required": 236, "official_success_or_safe_failure": 287, "other_official_failure": 70, "value_error": 233, "wrong_count": 4, "wrong_func_name": 10}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1346 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9526 | `{"official_success_or_safe_failure": 1346}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 175 | 0.0000 | 0.9914 | 0.0000 | 0.9829 | 0.9914 | 0.2976 | `{"other_official_failure": 175}` |
| system=a0_baseline / official_failure_bucket=value_error | 629 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2104 | `{"value_error": 629}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 1260 | 0.0000 | 0.0491 | 0.0000 | 0.0000 | 0.0491 | 0.8953 | `{"wrong_count": 1260}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1346 | 0.9881 | 0.9881 | 0.9881 | 0.9881 | 1.0000 | 0.9526 | `{"official_success_or_safe_failure": 1346}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 176 | 0.0000 | 0.9915 | 0.0000 | 0.9830 | 0.9915 | 0.2959 | `{"other_official_failure": 176}` |
| system=a1_recovery / official_failure_bucket=value_error | 634 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2096 | `{"value_error": 634}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 1254 | 0.0000 | 0.0498 | 0.0000 | 0.0000 | 0.0498 | 0.8943 | `{"wrong_count": 1254}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1322 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9517 | `{"official_success_or_safe_failure": 1322}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 204 | 0.0000 | 0.9771 | 0.0000 | 0.9608 | 0.9771 | 0.3685 | `{"other_official_failure": 204}` |
| system=a2_planner / official_failure_bucket=value_error | 634 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2096 | `{"value_error": 634}` |
| system=a2_planner / official_failure_bucket=wrong_count | 1250 | 0.0000 | 0.0479 | 0.0000 | 0.0000 | 0.0479 | 0.8977 | `{"wrong_count": 1250}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a3_interaction / official_failure_bucket=missing_required | 376 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0893 | `{"missing_required": 376}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1325 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9518 | `{"official_success_or_safe_failure": 1325}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 338 | 0.0000 | 0.9610 | 0.0000 | 0.9290 | 0.9610 | 0.2965 | `{"other_official_failure": 338}` |
| system=a3_interaction / official_failure_bucket=value_error | 913 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1924 | `{"value_error": 913}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 385 | 0.0000 | 0.3994 | 0.0000 | 0.0000 | 0.3994 | 0.1716 | `{"wrong_count": 385}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0650 | `{"wrong_func_name": 154}` |
| system=a4_reuse / official_failure_bucket=missing_required | 376 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0893 | `{"missing_required": 376}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1325 | 0.9879 | 0.9879 | 0.9879 | 0.9879 | 1.0000 | 0.9518 | `{"official_success_or_safe_failure": 1325}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 338 | 0.0000 | 0.9610 | 0.0000 | 0.9290 | 0.9610 | 0.2965 | `{"other_official_failure": 338}` |
| system=a4_reuse / official_failure_bucket=value_error | 913 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1924 | `{"value_error": 913}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 385 | 0.0000 | 0.3994 | 0.0000 | 0.0000 | 0.3994 | 0.1716 | `{"wrong_count": 385}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0650 | `{"wrong_func_name": 154}` |
