# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.2529 | 0.6157 | 0.2529 | 0.6022 | 0.7134 | 0.4952 | `{"missing_required": 408, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1381, "other_official_failure": 237, "value_error": 860, "wrong_count": 452, "wrong_func_name": 153}` |
| system=a1_recovery | 4291 | 0.2529 | 0.6160 | 0.2529 | 0.6024 | 0.7138 | 0.4948 | `{"missing_required": 408, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1381, "other_official_failure": 239, "value_error": 860, "wrong_count": 450, "wrong_func_name": 153}` |
| system=a2_planner | 4291 | 0.2475 | 0.6158 | 0.2475 | 0.6027 | 0.7135 | 0.4949 | `{"missing_required": 408, "multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1358, "other_official_failure": 268, "value_error": 860, "wrong_count": 444, "wrong_func_name": 153}` |
| system=a3_interaction | 4291 | 0.2480 | 0.6535 | 0.2480 | 0.6120 | 0.7529 | 0.4265 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1361, "other_official_failure": 322, "value_error": 860, "wrong_count": 384, "wrong_func_name": 154}` |
| system=a4_reuse | 4291 | 0.2480 | 0.6535 | 0.2480 | 0.6120 | 0.7529 | 0.4265 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1361, "other_official_failure": 322, "value_error": 860, "wrong_count": 384, "wrong_func_name": 154}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.3523 | 0.7946 | 0.3523 | 0.7903 | 0.9128 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 167, "value_error": 659, "wrong_count": 61, "wrong_func_name": 143}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2355 | 0.6880 | 0.2355 | 0.6492 | 0.7122 | 0.5829 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 70, "value_error": 201, "wrong_count": 391, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.3523 | 0.7946 | 0.3523 | 0.7903 | 0.9128 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 167, "value_error": 659, "wrong_count": 61, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2355 | 0.6892 | 0.2355 | 0.6500 | 0.7134 | 0.5815 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 72, "value_error": 201, "wrong_count": 389, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.3421 | 0.7944 | 0.3421 | 0.7908 | 0.9126 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1036, "other_official_failure": 189, "value_error": 659, "wrong_count": 62, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2355 | 0.6888 | 0.2355 | 0.6500 | 0.7130 | 0.5817 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 79, "value_error": 201, "wrong_count": 382, "wrong_func_name": 10}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.3430 | 0.7995 | 0.3430 | 0.7934 | 0.9182 | 0.5496 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 195, "value_error": 659, "wrong_count": 50, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2355 | 0.8099 | 0.2355 | 0.6774 | 0.8341 | 0.3793 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 127, "value_error": 201, "wrong_count": 334, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.3430 | 0.7995 | 0.3430 | 0.7934 | 0.9182 | 0.5496 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 195, "value_error": 659, "wrong_count": 50, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2355 | 0.8099 | 0.2355 | 0.6774 | 0.8341 | 0.3793 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 127, "value_error": 201, "wrong_count": 334, "wrong_func_name": 10}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.1678 | 0.0091 | 0.0364 | 0.1678 | 0.7181 | `{"official_success_or_safe_failure": 4, "other_official_failure": 18, "wrong_count": 418}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.2807 | 0.6668 | 0.2807 | 0.6668 | 0.7758 | 0.4697 | `{"missing_required": 408, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1377, "other_official_failure": 219, "value_error": 860, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.1712 | 0.0091 | 0.0386 | 0.1712 | 0.7143 | `{"official_success_or_safe_failure": 4, "other_official_failure": 20, "wrong_count": 416}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.2807 | 0.6668 | 0.2807 | 0.6668 | 0.7758 | 0.4697 | `{"missing_required": 408, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1377, "other_official_failure": 219, "value_error": 860, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.1688 | 0.0091 | 0.0409 | 0.1688 | 0.7144 | `{"official_success_or_safe_failure": 4, "other_official_failure": 26, "wrong_count": 410}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.2747 | 0.6668 | 0.2747 | 0.6668 | 0.7758 | 0.4698 | `{"missing_required": 408, "multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1354, "other_official_failure": 242, "value_error": 860, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.5274 | 0.0091 | 0.1227 | 0.5274 | 0.1158 | `{"official_success_or_safe_failure": 4, "other_official_failure": 80, "wrong_count": 356}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.2753 | 0.6679 | 0.2753 | 0.6679 | 0.7786 | 0.4620 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1357, "other_official_failure": 242, "value_error": 860, "wrong_count": 28, "wrong_func_name": 154}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.5274 | 0.0091 | 0.1227 | 0.5274 | 0.1158 | `{"official_success_or_safe_failure": 4, "other_official_failure": 80, "wrong_count": 356}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.2753 | 0.6679 | 0.2753 | 0.6679 | 0.7786 | 0.4620 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1357, "other_official_failure": 242, "value_error": 860, "wrong_count": 28, "wrong_func_name": 154}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4167 | 0.0000 | 0.1750 | 0.4167 | 0.4708 | `{"other_official_failure": 9, "wrong_count": 31}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3587 | 0.8014 | 0.3587 | 0.8014 | 0.9218 | 0.5574 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 158, "value_error": 659, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.1429 | 0.0100 | 0.0225 | 0.1429 | 0.7428 | `{"official_success_or_safe_failure": 4, "other_official_failure": 9, "wrong_count": 387}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4167 | 0.0000 | 0.1750 | 0.4167 | 0.4708 | `{"other_official_failure": 9, "wrong_count": 31}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3587 | 0.8014 | 0.3587 | 0.8014 | 0.9218 | 0.5574 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 158, "value_error": 659, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.1467 | 0.0100 | 0.0250 | 0.1467 | 0.7387 | `{"official_success_or_safe_failure": 4, "other_official_failure": 11, "wrong_count": 385}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4042 | 0.0000 | 0.2000 | 0.4042 | 0.4646 | `{"other_official_failure": 8, "wrong_count": 32}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3483 | 0.8014 | 0.3483 | 0.8014 | 0.9218 | 0.5576 | `{"missing_required": 162, "official_success_or_safe_failure": 1036, "other_official_failure": 181, "value_error": 659, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.1452 | 0.0100 | 0.0250 | 0.1452 | 0.7394 | `{"official_success_or_safe_failure": 4, "other_official_failure": 18, "wrong_count": 378}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.5946 | 0.0000 | 0.2500 | 0.5946 | 0.1562 | `{"other_official_failure": 14, "wrong_count": 26}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3492 | 0.8033 | 0.3492 | 0.8033 | 0.9240 | 0.5567 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 181, "value_error": 659, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.5207 | 0.0100 | 0.1100 | 0.5207 | 0.1118 | `{"official_success_or_safe_failure": 4, "other_official_failure": 66, "wrong_count": 330}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.5946 | 0.0000 | 0.2500 | 0.5946 | 0.1562 | `{"other_official_failure": 14, "wrong_count": 26}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3492 | 0.8033 | 0.3492 | 0.8033 | 0.9240 | 0.5567 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 181, "value_error": 659, "wrong_count": 24, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.5207 | 0.0100 | 0.1100 | 0.5207 | 0.1118 | `{"official_success_or_safe_failure": 4, "other_official_failure": 66, "wrong_count": 330}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=missing_required | 408 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1379 | `{"missing_required": 408}` |
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1563 | 0.1189 | `{"multi_turn_mismatch": 730}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 70 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1334 | 0.9143 | `{"multi_turn_other": 70}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1381 | 0.7857 | 0.7857 | 0.7857 | 0.7857 | 1.0000 | 0.9470 | `{"official_success_or_safe_failure": 1381}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 237 | 0.0000 | 0.9859 | 0.0000 | 0.9747 | 0.9859 | 0.2911 | `{"other_official_failure": 237}` |
| system=a0_baseline / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 452 | 0.0000 | 0.1221 | 0.0000 | 0.0000 | 0.1221 | 0.7580 | `{"wrong_count": 452}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0687 | `{"wrong_func_name": 153}` |
| system=a1_recovery / official_failure_bucket=missing_required | 408 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1379 | `{"missing_required": 408}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1381 | 0.7857 | 0.7857 | 0.7857 | 0.7857 | 1.0000 | 0.9470 | `{"official_success_or_safe_failure": 1381}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 239 | 0.0000 | 0.9840 | 0.0000 | 0.9707 | 0.9840 | 0.2901 | `{"other_official_failure": 239}` |
| system=a1_recovery / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 450 | 0.0000 | 0.1226 | 0.0000 | 0.0000 | 0.1226 | 0.7569 | `{"wrong_count": 450}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0687 | `{"wrong_func_name": 153}` |
| system=a2_planner / official_failure_bucket=missing_required | 408 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1379 | `{"missing_required": 408}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1358 | 0.7820 | 0.7820 | 0.7820 | 0.7820 | 1.0000 | 0.9461 | `{"official_success_or_safe_failure": 1358}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 268 | 0.0000 | 0.9739 | 0.0000 | 0.9552 | 0.9739 | 0.3450 | `{"other_official_failure": 268}` |
| system=a2_planner / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a2_planner / official_failure_bucket=wrong_count | 444 | 0.0000 | 0.1154 | 0.0000 | 0.0000 | 0.1154 | 0.7676 | `{"wrong_count": 444}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0687 | `{"wrong_func_name": 153}` |
| system=a3_interaction / official_failure_bucket=missing_required | 410 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1373 | `{"missing_required": 410}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1361 | 0.7818 | 0.7818 | 0.7818 | 0.7818 | 1.0000 | 0.9462 | `{"official_success_or_safe_failure": 1361}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 322 | 0.0000 | 0.9480 | 0.0000 | 0.9068 | 0.9480 | 0.3166 | `{"other_official_failure": 322}` |
| system=a3_interaction / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 384 | 0.0000 | 0.4292 | 0.0000 | 0.0000 | 0.4292 | 0.1614 | `{"wrong_count": 384}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0747 | `{"wrong_func_name": 154}` |
| system=a4_reuse / official_failure_bucket=missing_required | 410 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1373 | `{"missing_required": 410}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 784 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1587 | 0.1413 | `{"multi_turn_mismatch": 784}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 16 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.3208 | 0.7500 | `{"multi_turn_other": 16}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1361 | 0.7818 | 0.7818 | 0.7818 | 0.7818 | 1.0000 | 0.9462 | `{"official_success_or_safe_failure": 1361}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 322 | 0.0000 | 0.9480 | 0.0000 | 0.9068 | 0.9480 | 0.3166 | `{"other_official_failure": 322}` |
| system=a4_reuse / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 384 | 0.0000 | 0.4292 | 0.0000 | 0.0000 | 0.4292 | 0.1614 | `{"wrong_count": 384}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 154 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0747 | `{"wrong_func_name": 154}` |
