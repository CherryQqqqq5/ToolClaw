# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.2804 | 0.4811 | 0.2804 | 0.4673 | 0.5432 | 0.6434 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1346, "other_official_failure": 179, "value_error": 629, "wrong_count": 1256, "wrong_func_name": 81}` |
| system=a1_recovery | 4291 | 0.2804 | 0.4826 | 0.2804 | 0.4687 | 0.5447 | 0.6419 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1346, "other_official_failure": 181, "value_error": 634, "wrong_count": 1249, "wrong_func_name": 81}` |
| system=a2_planner | 4291 | 0.2748 | 0.4824 | 0.2748 | 0.4687 | 0.5445 | 0.6419 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1322, "other_official_failure": 209, "value_error": 634, "wrong_count": 1245, "wrong_func_name": 81}` |
| system=a3_interaction | 4291 | 0.2396 | 0.6519 | 0.2396 | 0.6129 | 0.7513 | 0.4119 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1325, "other_official_failure": 343, "value_error": 913, "wrong_count": 380, "wrong_func_name": 154}` |
| system=a4_reuse | 4291 | 0.2396 | 0.6519 | 0.2396 | 0.6129 | 0.7513 | 0.4119 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1325, "other_official_failure": 343, "value_error": 913, "wrong_count": 380, "wrong_func_name": 154}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.4069 | 0.7139 | 0.4069 | 0.7112 | 0.7752 | 0.6989 | `{"official_success_or_safe_failure": 1054, "other_official_failure": 151, "value_error": 537, "wrong_count": 429, "wrong_func_name": 80}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2315 | 0.3689 | 0.2315 | 0.3258 | 0.3729 | 0.8360 | `{"official_success_or_safe_failure": 292, "other_official_failure": 28, "value_error": 92, "wrong_count": 827, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.4069 | 0.7148 | 0.4069 | 0.7121 | 0.7761 | 0.6980 | `{"official_success_or_safe_failure": 1054, "other_official_failure": 151, "value_error": 539, "wrong_count": 427, "wrong_func_name": 80}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2315 | 0.3725 | 0.2315 | 0.3290 | 0.3765 | 0.8326 | `{"official_success_or_safe_failure": 292, "other_official_failure": 30, "value_error": 95, "wrong_count": 822, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.3963 | 0.7144 | 0.3963 | 0.7121 | 0.7757 | 0.6979 | `{"official_success_or_safe_failure": 1030, "other_official_failure": 172, "value_error": 539, "wrong_count": 430, "wrong_func_name": 80}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2315 | 0.3724 | 0.2315 | 0.3290 | 0.3764 | 0.8329 | `{"official_success_or_safe_failure": 292, "other_official_failure": 37, "value_error": 95, "wrong_count": 815, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.3403 | 0.7996 | 0.3403 | 0.7952 | 0.9182 | 0.5409 | `{"missing_required": 140, "official_success_or_safe_failure": 1033, "other_official_failure": 209, "value_error": 680, "wrong_count": 45, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2113 | 0.8044 | 0.2113 | 0.6774 | 0.8286 | 0.3444 | `{"missing_required": 236, "official_success_or_safe_failure": 292, "other_official_failure": 134, "value_error": 233, "wrong_count": 335, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.3403 | 0.7996 | 0.3403 | 0.7952 | 0.9182 | 0.5409 | `{"missing_required": 140, "official_success_or_safe_failure": 1033, "other_official_failure": 209, "value_error": 680, "wrong_count": 45, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2113 | 0.8044 | 0.2113 | 0.6774 | 0.8286 | 0.3444 | `{"missing_required": 236, "official_success_or_safe_failure": 292, "other_official_failure": 134, "value_error": 233, "wrong_count": 335, "wrong_func_name": 10}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1918 | 0.0159 | 0.0568 | 0.1918 | 0.6841 | `{"official_success_or_safe_failure": 7, "other_official_failure": 24, "wrong_count": 409}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.3106 | 0.5142 | 0.3106 | 0.5142 | 0.5833 | 0.6387 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1339, "other_official_failure": 155, "value_error": 629, "wrong_count": 847, "wrong_func_name": 81}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1952 | 0.0159 | 0.0591 | 0.1952 | 0.6803 | `{"official_success_or_safe_failure": 7, "other_official_failure": 26, "wrong_count": 407}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.3106 | 0.5155 | 0.3106 | 0.5155 | 0.5846 | 0.6375 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1339, "other_official_failure": 155, "value_error": 634, "wrong_count": 842, "wrong_func_name": 81}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1931 | 0.0159 | 0.0591 | 0.1931 | 0.6805 | `{"official_success_or_safe_failure": 7, "other_official_failure": 30, "wrong_count": 403}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.3043 | 0.5155 | 0.3043 | 0.5155 | 0.5846 | 0.6375 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1315, "other_official_failure": 179, "value_error": 634, "wrong_count": 842, "wrong_func_name": 81}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5124 | 0.0159 | 0.1318 | 0.5124 | 0.1232 | `{"official_success_or_safe_failure": 7, "other_official_failure": 81, "wrong_count": 352}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.2651 | 0.6679 | 0.2651 | 0.6679 | 0.7786 | 0.4449 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1318, "other_official_failure": 262, "value_error": 913, "wrong_count": 28, "wrong_func_name": 154}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5124 | 0.0159 | 0.1318 | 0.5124 | 0.1232 | `{"official_success_or_safe_failure": 7, "other_official_failure": 81, "wrong_count": 352}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.2651 | 0.6679 | 0.2651 | 0.6679 | 0.7786 | 0.4449 | `{"missing_required": 376, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1318, "other_official_failure": 262, "value_error": 913, "wrong_count": 28, "wrong_func_name": 154}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4750 | 0.0500 | 0.3250 | 0.4750 | 0.4938 | `{"official_success_or_safe_failure": 2, "other_official_failure": 14, "wrong_count": 24}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4134 | 0.7182 | 0.4134 | 0.7182 | 0.7806 | 0.7026 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 137, "value_error": 537, "wrong_count": 405, "wrong_func_name": 80}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1634 | 0.0125 | 0.0300 | 0.1634 | 0.7031 | `{"official_success_or_safe_failure": 5, "other_official_failure": 10, "wrong_count": 385}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3357 | 0.4667 | 0.3357 | 0.4667 | 0.4726 | 0.8993 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 92, "wrong_count": 442, "wrong_func_name": 1}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4750 | 0.0500 | 0.3250 | 0.4750 | 0.4938 | `{"official_success_or_safe_failure": 2, "other_official_failure": 14, "wrong_count": 24}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4134 | 0.7191 | 0.4134 | 0.7191 | 0.7815 | 0.7017 | `{"official_success_or_safe_failure": 1052, "other_official_failure": 137, "value_error": 539, "wrong_count": 403, "wrong_func_name": 80}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1672 | 0.0125 | 0.0325 | 0.1672 | 0.6989 | `{"official_success_or_safe_failure": 5, "other_official_failure": 12, "wrong_count": 383}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3357 | 0.4702 | 0.3357 | 0.4702 | 0.4762 | 0.8963 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 95, "wrong_count": 439, "wrong_func_name": 1}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4542 | 0.0500 | 0.3250 | 0.4542 | 0.4896 | `{"official_success_or_safe_failure": 2, "other_official_failure": 11, "wrong_count": 27}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.4025 | 0.7191 | 0.4025 | 0.7191 | 0.7815 | 0.7017 | `{"official_success_or_safe_failure": 1028, "other_official_failure": 161, "value_error": 539, "wrong_count": 403, "wrong_func_name": 80}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1670 | 0.0125 | 0.0325 | 0.1670 | 0.6996 | `{"official_success_or_safe_failure": 5, "other_official_failure": 19, "wrong_count": 376}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3357 | 0.4702 | 0.3357 | 0.4702 | 0.4762 | 0.8963 | `{"official_success_or_safe_failure": 287, "other_official_failure": 18, "value_error": 95, "wrong_count": 439, "wrong_func_name": 1}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5988 | 0.0500 | 0.3500 | 0.5988 | 0.2125 | `{"official_success_or_safe_failure": 2, "other_official_failure": 17, "wrong_count": 21}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3455 | 0.8033 | 0.3455 | 0.8033 | 0.9240 | 0.5468 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 192, "value_error": 680, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5037 | 0.0125 | 0.1100 | 0.5037 | 0.1143 | `{"official_success_or_safe_failure": 5, "other_official_failure": 64, "wrong_count": 331}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3060 | 0.9476 | 0.3060 | 0.9476 | 0.9833 | 0.4540 | `{"missing_required": 236, "official_success_or_safe_failure": 287, "other_official_failure": 70, "value_error": 233, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5988 | 0.0500 | 0.3500 | 0.5988 | 0.2125 | `{"official_success_or_safe_failure": 2, "other_official_failure": 17, "wrong_count": 21}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3455 | 0.8033 | 0.3455 | 0.8033 | 0.9240 | 0.5468 | `{"missing_required": 140, "official_success_or_safe_failure": 1031, "other_official_failure": 192, "value_error": 680, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5037 | 0.0125 | 0.1100 | 0.5037 | 0.1143 | `{"official_success_or_safe_failure": 5, "other_official_failure": 64, "wrong_count": 331}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3060 | 0.9476 | 0.3060 | 0.9476 | 0.9833 | 0.4540 | `{"missing_required": 236, "official_success_or_safe_failure": 287, "other_official_failure": 70, "value_error": 233, "wrong_count": 4, "wrong_func_name": 10}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1346 | 0.8938 | 0.8938 | 0.8938 | 0.8938 | 1.0000 | 0.9526 | `{"official_success_or_safe_failure": 1346}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 179 | 0.0000 | 0.9842 | 0.0000 | 0.9665 | 0.9842 | 0.2899 | `{"other_official_failure": 179}` |
| system=a0_baseline / official_failure_bucket=value_error | 629 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2104 | `{"value_error": 629}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 1256 | 0.0000 | 0.0448 | 0.0000 | 0.0000 | 0.0448 | 0.9055 | `{"wrong_count": 1256}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1346 | 0.8938 | 0.8938 | 0.8938 | 0.8938 | 1.0000 | 0.9526 | `{"official_success_or_safe_failure": 1346}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 181 | 0.0000 | 0.9816 | 0.0000 | 0.9613 | 0.9816 | 0.2885 | `{"other_official_failure": 181}` |
| system=a1_recovery / official_failure_bucket=value_error | 634 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2096 | `{"value_error": 634}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 1249 | 0.0000 | 0.0450 | 0.0000 | 0.0000 | 0.0450 | 0.9050 | `{"wrong_count": 1249}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1322 | 0.8918 | 0.8918 | 0.8918 | 0.8918 | 1.0000 | 0.9517 | `{"official_success_or_safe_failure": 1322}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 209 | 0.0000 | 0.9713 | 0.0000 | 0.9474 | 0.9713 | 0.3637 | `{"other_official_failure": 209}` |
| system=a2_planner / official_failure_bucket=value_error | 634 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2096 | `{"value_error": 634}` |
| system=a2_planner / official_failure_bucket=wrong_count | 1245 | 0.0000 | 0.0433 | 0.0000 | 0.0000 | 0.0433 | 0.9081 | `{"wrong_count": 1245}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 81 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0761 | `{"wrong_func_name": 81}` |
| system=a3_interaction / official_failure_bucket=missing_required | 376 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0893 | `{"missing_required": 376}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1325 | 0.7758 | 0.7758 | 0.7758 | 0.7758 | 1.0000 | 0.9518 | `{"official_success_or_safe_failure": 1325}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 343 | 0.0000 | 0.9531 | 0.0000 | 0.9125 | 0.9531 | 0.2908 | `{"other_official_failure": 343}` |
| system=a3_interaction / official_failure_bucket=value_error | 913 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1924 | `{"value_error": 913}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 380 | 0.0000 | 0.4040 | 0.0000 | 0.0000 | 0.4040 | 0.1695 | `{"wrong_count": 380}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0650 | `{"wrong_func_name": 154}` |
| system=a4_reuse / official_failure_bucket=missing_required | 376 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0893 | `{"missing_required": 376}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1325 | 0.7758 | 0.7758 | 0.7758 | 0.7758 | 1.0000 | 0.9518 | `{"official_success_or_safe_failure": 1325}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 343 | 0.0000 | 0.9531 | 0.0000 | 0.9125 | 0.9531 | 0.2908 | `{"other_official_failure": 343}` |
| system=a4_reuse / official_failure_bucket=value_error | 913 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1924 | `{"value_error": 913}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 380 | 0.0000 | 0.4040 | 0.0000 | 0.0000 | 0.4040 | 0.1695 | `{"wrong_count": 380}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0650 | `{"wrong_func_name": 154}` |
