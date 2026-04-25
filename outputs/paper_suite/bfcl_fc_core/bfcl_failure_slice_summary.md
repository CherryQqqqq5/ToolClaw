# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.2473 | 0.6181 | 0.2473 | 0.6043 | 0.7159 | 0.4869 | `{"missing_required": 572, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1357, "other_official_failure": 215, "value_error": 751, "wrong_count": 443, "wrong_func_name": 153}` |
| system=a1_recovery | 4291 | 0.2473 | 0.6185 | 0.2473 | 0.6045 | 0.7162 | 0.4865 | `{"missing_required": 572, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1357, "other_official_failure": 217, "value_error": 751, "wrong_count": 441, "wrong_func_name": 153}` |
| system=a2_planner | 4291 | 0.2419 | 0.6183 | 0.2419 | 0.6045 | 0.7160 | 0.4866 | `{"missing_required": 572, "multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1334, "other_official_failure": 244, "value_error": 751, "wrong_count": 437, "wrong_func_name": 153}` |
| system=a3_interaction | 4291 | 0.2424 | 0.6519 | 0.2424 | 0.6129 | 0.7513 | 0.4224 | `{"missing_required": 574, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1337, "other_official_failure": 295, "value_error": 751, "wrong_count": 380, "wrong_func_name": 154}` |
| system=a4_reuse | 4291 | 0.2424 | 0.6519 | 0.2424 | 0.6129 | 0.7513 | 0.4224 | `{"missing_required": 574, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1337, "other_official_failure": 295, "value_error": 751, "wrong_count": 380, "wrong_func_name": 154}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.3510 | 0.7956 | 0.3510 | 0.7930 | 0.9138 | 0.5524 | `{"missing_required": 257, "official_success_or_safe_failure": 1056, "other_official_failure": 158, "value_error": 583, "wrong_count": 54, "wrong_func_name": 143}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2185 | 0.6947 | 0.2185 | 0.6516 | 0.7189 | 0.5604 | `{"missing_required": 315, "official_success_or_safe_failure": 301, "other_official_failure": 57, "value_error": 168, "wrong_count": 389, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.3510 | 0.7956 | 0.3510 | 0.7930 | 0.9138 | 0.5524 | `{"missing_required": 257, "official_success_or_safe_failure": 1056, "other_official_failure": 158, "value_error": 583, "wrong_count": 54, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2185 | 0.6959 | 0.2185 | 0.6524 | 0.7201 | 0.5591 | `{"missing_required": 315, "official_success_or_safe_failure": 301, "other_official_failure": 59, "value_error": 168, "wrong_count": 387, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.3407 | 0.7953 | 0.3407 | 0.7930 | 0.9134 | 0.5525 | `{"missing_required": 257, "official_success_or_safe_failure": 1033, "other_official_failure": 178, "value_error": 583, "wrong_count": 57, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2185 | 0.6958 | 0.2185 | 0.6524 | 0.7200 | 0.5593 | `{"missing_required": 315, "official_success_or_safe_failure": 301, "other_official_failure": 66, "value_error": 168, "wrong_count": 380, "wrong_func_name": 10}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.3416 | 0.7996 | 0.3416 | 0.7952 | 0.9182 | 0.5467 | `{"missing_required": 259, "official_success_or_safe_failure": 1036, "other_official_failure": 184, "value_error": 583, "wrong_count": 45, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2185 | 0.8044 | 0.2185 | 0.6774 | 0.8286 | 0.3705 | `{"missing_required": 315, "official_success_or_safe_failure": 301, "other_official_failure": 111, "value_error": 168, "wrong_count": 335, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.3416 | 0.7996 | 0.3416 | 0.7952 | 0.9182 | 0.5467 | `{"missing_required": 259, "official_success_or_safe_failure": 1036, "other_official_failure": 184, "value_error": 583, "wrong_count": 45, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2185 | 0.8044 | 0.2185 | 0.6774 | 0.8286 | 0.3705 | `{"missing_required": 315, "official_success_or_safe_failure": 301, "other_official_failure": 111, "value_error": 168, "wrong_count": 335, "wrong_func_name": 10}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1918 | 0.0159 | 0.0568 | 0.1918 | 0.6841 | `{"official_success_or_safe_failure": 7, "other_official_failure": 24, "wrong_count": 409}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.2737 | 0.6668 | 0.2737 | 0.6668 | 0.7758 | 0.4643 | `{"missing_required": 572, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1350, "other_official_failure": 191, "value_error": 751, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1952 | 0.0159 | 0.0591 | 0.1952 | 0.6803 | `{"official_success_or_safe_failure": 7, "other_official_failure": 26, "wrong_count": 407}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.2737 | 0.6668 | 0.2737 | 0.6668 | 0.7758 | 0.4643 | `{"missing_required": 572, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1350, "other_official_failure": 191, "value_error": 751, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.1931 | 0.0159 | 0.0591 | 0.1931 | 0.6805 | `{"official_success_or_safe_failure": 7, "other_official_failure": 30, "wrong_count": 403}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.2677 | 0.6668 | 0.2677 | 0.6668 | 0.7758 | 0.4644 | `{"missing_required": 572, "multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1327, "other_official_failure": 214, "value_error": 751, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5124 | 0.0159 | 0.1318 | 0.5124 | 0.1232 | `{"official_success_or_safe_failure": 7, "other_official_failure": 81, "wrong_count": 352}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.2682 | 0.6679 | 0.2682 | 0.6679 | 0.7786 | 0.4566 | `{"missing_required": 574, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1330, "other_official_failure": 214, "value_error": 751, "wrong_count": 28, "wrong_func_name": 154}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0159 | 0.5124 | 0.0159 | 0.1318 | 0.5124 | 0.1232 | `{"official_success_or_safe_failure": 7, "other_official_failure": 81, "wrong_count": 352}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.2682 | 0.6679 | 0.2682 | 0.6679 | 0.7786 | 0.4566 | `{"missing_required": 574, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1330, "other_official_failure": 214, "value_error": 751, "wrong_count": 28, "wrong_func_name": 154}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4750 | 0.0500 | 0.3250 | 0.4750 | 0.4938 | `{"official_success_or_safe_failure": 2, "other_official_failure": 14, "wrong_count": 24}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3564 | 0.8014 | 0.3564 | 0.8014 | 0.9218 | 0.5535 | `{"missing_required": 257, "official_success_or_safe_failure": 1054, "other_official_failure": 144, "value_error": 583, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1634 | 0.0125 | 0.0300 | 0.1634 | 0.7031 | `{"official_success_or_safe_failure": 5, "other_official_failure": 10, "wrong_count": 385}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3167 | 0.9476 | 0.3167 | 0.9476 | 0.9833 | 0.4925 | `{"missing_required": 315, "official_success_or_safe_failure": 296, "other_official_failure": 47, "value_error": 168, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4750 | 0.0500 | 0.3250 | 0.4750 | 0.4938 | `{"official_success_or_safe_failure": 2, "other_official_failure": 14, "wrong_count": 24}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3564 | 0.8014 | 0.3564 | 0.8014 | 0.9218 | 0.5535 | `{"missing_required": 257, "official_success_or_safe_failure": 1054, "other_official_failure": 144, "value_error": 583, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1672 | 0.0125 | 0.0325 | 0.1672 | 0.6989 | `{"official_success_or_safe_failure": 5, "other_official_failure": 12, "wrong_count": 383}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3167 | 0.9476 | 0.3167 | 0.9476 | 0.9833 | 0.4925 | `{"missing_required": 315, "official_success_or_safe_failure": 296, "other_official_failure": 47, "value_error": 168, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.4542 | 0.0500 | 0.3250 | 0.4542 | 0.4896 | `{"official_success_or_safe_failure": 2, "other_official_failure": 11, "wrong_count": 27}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3460 | 0.8014 | 0.3460 | 0.8014 | 0.9218 | 0.5536 | `{"missing_required": 257, "official_success_or_safe_failure": 1031, "other_official_failure": 167, "value_error": 583, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.1670 | 0.0125 | 0.0325 | 0.1670 | 0.6996 | `{"official_success_or_safe_failure": 5, "other_official_failure": 19, "wrong_count": 376}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3167 | 0.9476 | 0.3167 | 0.9476 | 0.9833 | 0.4925 | `{"missing_required": 315, "official_success_or_safe_failure": 296, "other_official_failure": 47, "value_error": 168, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5988 | 0.0500 | 0.3500 | 0.5988 | 0.2125 | `{"official_success_or_safe_failure": 2, "other_official_failure": 17, "wrong_count": 21}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3469 | 0.8033 | 0.3469 | 0.8033 | 0.9240 | 0.5527 | `{"missing_required": 259, "official_success_or_safe_failure": 1034, "other_official_failure": 167, "value_error": 583, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5037 | 0.0125 | 0.1100 | 0.5037 | 0.1143 | `{"official_success_or_safe_failure": 5, "other_official_failure": 64, "wrong_count": 331}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3167 | 0.9476 | 0.3167 | 0.9476 | 0.9833 | 0.4925 | `{"missing_required": 315, "official_success_or_safe_failure": 296, "other_official_failure": 47, "value_error": 168, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0500 | 0.5988 | 0.0500 | 0.3500 | 0.5988 | 0.2125 | `{"official_success_or_safe_failure": 2, "other_official_failure": 17, "wrong_count": 21}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3469 | 0.8033 | 0.3469 | 0.8033 | 0.9240 | 0.5527 | `{"missing_required": 259, "official_success_or_safe_failure": 1034, "other_official_failure": 167, "value_error": 583, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0125 | 0.5037 | 0.0125 | 0.1100 | 0.5037 | 0.1143 | `{"official_success_or_safe_failure": 5, "other_official_failure": 64, "wrong_count": 331}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3167 | 0.9476 | 0.3167 | 0.9476 | 0.9833 | 0.4925 | `{"missing_required": 315, "official_success_or_safe_failure": 296, "other_official_failure": 47, "value_error": 168, "wrong_count": 4, "wrong_func_name": 10}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=missing_required | 572 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1484 | `{"missing_required": 572}` |
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1357 | 0.7819 | 0.7819 | 0.7819 | 0.7819 | 1.0000 | 0.9512 | `{"official_success_or_safe_failure": 1357}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 215 | 0.0000 | 0.9868 | 0.0000 | 0.9721 | 0.9868 | 0.2973 | `{"other_official_failure": 215}` |
| system=a0_baseline / official_failure_bucket=value_error | 751 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2197 | `{"value_error": 751}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 443 | 0.0000 | 0.1269 | 0.0000 | 0.0000 | 0.1269 | 0.7320 | `{"wrong_count": 443}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0621 | `{"wrong_func_name": 153}` |
| system=a1_recovery / official_failure_bucket=missing_required | 572 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1484 | `{"missing_required": 572}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1357 | 0.7819 | 0.7819 | 0.7819 | 0.7819 | 1.0000 | 0.9512 | `{"official_success_or_safe_failure": 1357}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 217 | 0.0000 | 0.9846 | 0.0000 | 0.9677 | 0.9846 | 0.2961 | `{"other_official_failure": 217}` |
| system=a1_recovery / official_failure_bucket=value_error | 751 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2197 | `{"value_error": 751}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 441 | 0.0000 | 0.1275 | 0.0000 | 0.0000 | 0.1275 | 0.7308 | `{"wrong_count": 441}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0621 | `{"wrong_func_name": 153}` |
| system=a2_planner / official_failure_bucket=missing_required | 572 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1484 | `{"missing_required": 572}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1334 | 0.7781 | 0.7781 | 0.7781 | 0.7781 | 1.0000 | 0.9504 | `{"official_success_or_safe_failure": 1334}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 244 | 0.0000 | 0.9754 | 0.0000 | 0.9549 | 0.9754 | 0.3581 | `{"other_official_failure": 244}` |
| system=a2_planner / official_failure_bucket=value_error | 751 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2197 | `{"value_error": 751}` |
| system=a2_planner / official_failure_bucket=wrong_count | 437 | 0.0000 | 0.1235 | 0.0000 | 0.0000 | 0.1235 | 0.7382 | `{"wrong_count": 437}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0621 | `{"wrong_func_name": 153}` |
| system=a3_interaction / official_failure_bucket=missing_required | 574 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1478 | `{"missing_required": 574}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1337 | 0.7779 | 0.7779 | 0.7779 | 0.7779 | 1.0000 | 0.9505 | `{"official_success_or_safe_failure": 1337}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 295 | 0.0000 | 0.9455 | 0.0000 | 0.8983 | 0.9455 | 0.3198 | `{"other_official_failure": 295}` |
| system=a3_interaction / official_failure_bucket=value_error | 751 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2197 | `{"value_error": 751}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 380 | 0.0000 | 0.4040 | 0.0000 | 0.0000 | 0.4040 | 0.1695 | `{"wrong_count": 380}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0682 | `{"wrong_func_name": 154}` |
| system=a4_reuse / official_failure_bucket=missing_required | 574 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1478 | `{"missing_required": 574}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1337 | 0.7779 | 0.7779 | 0.7779 | 0.7779 | 1.0000 | 0.9505 | `{"official_success_or_safe_failure": 1337}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 295 | 0.0000 | 0.9455 | 0.0000 | 0.8983 | 0.9455 | 0.3198 | `{"other_official_failure": 295}` |
| system=a4_reuse / official_failure_bucket=value_error | 751 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2197 | `{"value_error": 751}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 380 | 0.0000 | 0.4040 | 0.0000 | 0.0000 | 0.4040 | 0.1695 | `{"wrong_count": 380}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0682 | `{"wrong_func_name": 154}` |
