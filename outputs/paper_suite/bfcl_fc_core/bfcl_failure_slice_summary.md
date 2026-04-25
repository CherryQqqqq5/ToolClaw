# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.2529 | 0.6525 | 0.2529 | 0.6129 | 0.7503 | 0.4358 | `{"missing_required": 408, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1381, "other_official_failure": 288, "value_error": 860, "wrong_count": 401, "wrong_func_name": 153}` |
| system=a1_recovery | 4291 | 0.2529 | 0.6525 | 0.2529 | 0.6129 | 0.7503 | 0.4358 | `{"missing_required": 408, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1381, "other_official_failure": 288, "value_error": 860, "wrong_count": 401, "wrong_func_name": 153}` |
| system=a2_planner | 4291 | 0.2475 | 0.6376 | 0.2475 | 0.6103 | 0.7353 | 0.4664 | `{"missing_required": 408, "multi_turn_mismatch": 752, "multi_turn_other": 48, "official_success_or_safe_failure": 1358, "other_official_failure": 303, "value_error": 860, "wrong_count": 409, "wrong_func_name": 153}` |
| system=a3_interaction | 4291 | 0.2480 | 0.6535 | 0.2480 | 0.6120 | 0.7529 | 0.4265 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1361, "other_official_failure": 322, "value_error": 860, "wrong_count": 384, "wrong_func_name": 154}` |
| system=a4_reuse | 4291 | 0.2480 | 0.6535 | 0.2480 | 0.6120 | 0.7529 | 0.4265 | `{"missing_required": 410, "multi_turn_mismatch": 784, "multi_turn_other": 16, "official_success_or_safe_failure": 1361, "other_official_failure": 322, "value_error": 860, "wrong_count": 384, "wrong_func_name": 154}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.3523 | 0.7946 | 0.3523 | 0.7903 | 0.9128 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 167, "value_error": 659, "wrong_count": 61, "wrong_func_name": 143}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 730, "multi_turn_other": 70}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.2355 | 0.8156 | 0.2355 | 0.6863 | 0.8398 | 0.3774 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 121, "value_error": 201, "wrong_count": 340, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.3523 | 0.7946 | 0.3523 | 0.7903 | 0.9128 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 167, "value_error": 659, "wrong_count": 61, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.2355 | 0.8156 | 0.2355 | 0.6863 | 0.8398 | 0.3774 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 121, "value_error": 201, "wrong_count": 340, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.3421 | 0.7944 | 0.3421 | 0.7908 | 0.9126 | 0.5559 | `{"missing_required": 162, "official_success_or_safe_failure": 1036, "other_official_failure": 189, "value_error": 659, "wrong_count": 62, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.2355 | 0.7643 | 0.2355 | 0.6766 | 0.7885 | 0.4832 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 114, "value_error": 201, "wrong_count": 347, "wrong_func_name": 10}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.3430 | 0.7995 | 0.3430 | 0.7934 | 0.9182 | 0.5496 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 195, "value_error": 659, "wrong_count": 50, "wrong_func_name": 144}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.2355 | 0.8099 | 0.2355 | 0.6774 | 0.8341 | 0.3793 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 127, "value_error": 201, "wrong_count": 334, "wrong_func_name": 10}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.3430 | 0.7995 | 0.3430 | 0.7934 | 0.9182 | 0.5496 | `{"missing_required": 164, "official_success_or_safe_failure": 1039, "other_official_failure": 195, "value_error": 659, "wrong_count": 50, "wrong_func_name": 144}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1620 | 0.1535 | `{"multi_turn_mismatch": 784, "multi_turn_other": 16}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.2355 | 0.8099 | 0.2355 | 0.6774 | 0.8341 | 0.3793 | `{"missing_required": 246, "official_success_or_safe_failure": 322, "other_official_failure": 127, "value_error": 201, "wrong_count": 334, "wrong_func_name": 10}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.5272 | 0.0091 | 0.1409 | 0.5272 | 0.1392 | `{"official_success_or_safe_failure": 4, "other_official_failure": 69, "wrong_count": 367}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.2807 | 0.6668 | 0.2807 | 0.6668 | 0.7758 | 0.4697 | `{"missing_required": 408, "multi_turn_mismatch": 730, "multi_turn_other": 70, "official_success_or_safe_failure": 1377, "other_official_failure": 219, "value_error": 860, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.5272 | 0.0091 | 0.1409 | 0.5272 | 0.1392 | `{"official_success_or_safe_failure": 4, "other_official_failure": 69, "wrong_count": 367}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.2807 | 0.6668 | 0.2807 | 0.6668 | 0.7758 | 0.4697 | `{"missing_required": 408, "multi_turn_mismatch": 746, "multi_turn_other": 54, "official_success_or_safe_failure": 1377, "other_official_failure": 219, "value_error": 860, "wrong_count": 34, "wrong_func_name": 153}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0091 | 0.3815 | 0.0091 | 0.1159 | 0.3815 | 0.4367 | `{"official_success_or_safe_failure": 4, "other_official_failure": 61, "wrong_count": 375}` |
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
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.5383 | 0.0100 | 0.1375 | 0.5383 | 0.1060 | `{"official_success_or_safe_failure": 4, "other_official_failure": 60, "wrong_count": 336}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4167 | 0.0000 | 0.1750 | 0.4167 | 0.4708 | `{"other_official_failure": 9, "wrong_count": 31}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3587 | 0.8014 | 0.3587 | 0.8014 | 0.9218 | 0.5574 | `{"missing_required": 162, "official_success_or_safe_failure": 1059, "other_official_failure": 158, "value_error": 659, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 746, "multi_turn_other": 54}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.5383 | 0.0100 | 0.1375 | 0.5383 | 0.1060 | `{"official_success_or_safe_failure": 4, "other_official_failure": 60, "wrong_count": 336}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.3429 | 0.9476 | 0.3429 | 0.9476 | 0.9833 | 0.5067 | `{"missing_required": 246, "official_success_or_safe_failure": 318, "other_official_failure": 61, "value_error": 201, "wrong_count": 4, "wrong_func_name": 10}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4042 | 0.0000 | 0.2000 | 0.4042 | 0.4646 | `{"other_official_failure": 8, "wrong_count": 32}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.3483 | 0.8014 | 0.3483 | 0.8014 | 0.9218 | 0.5576 | `{"missing_required": 162, "official_success_or_safe_failure": 1036, "other_official_failure": 181, "value_error": 659, "wrong_count": 30, "wrong_func_name": 143}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1543 | 0.1885 | `{"multi_turn_mismatch": 752, "multi_turn_other": 48}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0100 | 0.3792 | 0.0100 | 0.1075 | 0.3792 | 0.4340 | `{"official_success_or_safe_failure": 4, "other_official_failure": 53, "wrong_count": 343}` |
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
| system=a0_baseline / official_failure_bucket=other_official_failure | 288 | 0.0000 | 0.9780 | 0.0000 | 0.9618 | 0.9780 | 0.2693 | `{"other_official_failure": 288}` |
| system=a0_baseline / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 401 | 0.0000 | 0.4123 | 0.0000 | 0.0000 | 0.4123 | 0.1978 | `{"wrong_count": 401}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0687 | `{"wrong_func_name": 153}` |
| system=a1_recovery / official_failure_bucket=missing_required | 408 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1379 | `{"missing_required": 408}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 746 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1565 | 0.1378 | `{"multi_turn_mismatch": 746}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 54 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1242 | 0.8889 | `{"multi_turn_other": 54}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1381 | 0.7857 | 0.7857 | 0.7857 | 0.7857 | 1.0000 | 0.9470 | `{"official_success_or_safe_failure": 1381}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 288 | 0.0000 | 0.9780 | 0.0000 | 0.9618 | 0.9780 | 0.2693 | `{"other_official_failure": 288}` |
| system=a1_recovery / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 401 | 0.0000 | 0.4123 | 0.0000 | 0.0000 | 0.4123 | 0.1978 | `{"wrong_count": 401}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 153 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0687 | `{"wrong_func_name": 153}` |
| system=a2_planner / official_failure_bucket=missing_required | 408 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1379 | `{"missing_required": 408}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 752 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1573 | 0.1420 | `{"multi_turn_mismatch": 752}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 48 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1069 | 0.9167 | `{"multi_turn_other": 48}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1358 | 0.7820 | 0.7820 | 0.7820 | 0.7820 | 1.0000 | 0.9461 | `{"official_success_or_safe_failure": 1358}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 303 | 0.0000 | 0.9728 | 0.0000 | 0.9538 | 0.9728 | 0.3296 | `{"other_official_failure": 303}` |
| system=a2_planner / official_failure_bucket=value_error | 860 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2184 | `{"value_error": 860}` |
| system=a2_planner / official_failure_bucket=wrong_count | 409 | 0.0000 | 0.2717 | 0.0000 | 0.0000 | 0.2717 | 0.5165 | `{"wrong_count": 409}` |
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
