# BFCL Failure Slice Diagnostic

This report is diagnostic only. It is used to decide whether planner/binder evidence is headline-safe, not to redefine official BFCL correctness.

## system

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline | 4291 | 0.0291 | 0.4265 | 0.0291 | 0.3873 | 0.7135 | 0.3805 | `{"missing_required": 1060, "multi_turn_mismatch": 788, "multi_turn_other": 12, "official_success_or_safe_failure": 1249, "other_official_failure": 67, "value_error": 410, "wrong_count": 440, "wrong_func_name": 265}` |
| system=a1_recovery | 4291 | 0.0280 | 0.4265 | 0.0280 | 0.3873 | 0.7135 | 0.3805 | `{"missing_required": 1060, "multi_turn_mismatch": 788, "multi_turn_other": 12, "official_success_or_safe_failure": 1244, "other_official_failure": 72, "value_error": 410, "wrong_count": 440, "wrong_func_name": 265}` |
| system=a2_planner | 4291 | 0.0226 | 0.3407 | 0.0226 | 0.3020 | 0.6170 | 0.3418 | `{"missing_required": 808, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1221, "other_official_failure": 129, "value_error": 287, "wrong_count": 404, "wrong_func_name": 642}` |
| system=a3_interaction | 4291 | 0.0221 | 0.3409 | 0.0221 | 0.3018 | 0.6172 | 0.3414 | `{"missing_required": 809, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1219, "other_official_failure": 129, "value_error": 287, "wrong_count": 405, "wrong_func_name": 642}` |
| system=a4_reuse | 4291 | 0.0221 | 0.3409 | 0.0221 | 0.3018 | 0.6172 | 0.3414 | `{"missing_required": 809, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1219, "other_official_failure": 129, "value_error": 287, "wrong_count": 405, "wrong_func_name": 642}` |

## system__bfcl_group

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live | 2251 | 0.0431 | 0.4834 | 0.0431 | 0.4758 | 0.8761 | 0.5071 | `{"missing_required": 573, "official_success_or_safe_failure": 981, "other_official_failure": 53, "value_error": 348, "wrong_count": 43, "wrong_func_name": 253}` |
| system=a0_baseline / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1341 | 0.1404 | `{"multi_turn_mismatch": 788, "multi_turn_other": 12}` |
| system=a0_baseline / bfcl_group=non_live | 1240 | 0.0226 | 0.5985 | 0.0226 | 0.4766 | 0.7921 | 0.3055 | `{"missing_required": 487, "official_success_or_safe_failure": 268, "other_official_failure": 14, "value_error": 62, "wrong_count": 397, "wrong_func_name": 12}` |
| system=a1_recovery / bfcl_group=live | 2251 | 0.0409 | 0.4834 | 0.0409 | 0.4758 | 0.8761 | 0.5071 | `{"missing_required": 573, "official_success_or_safe_failure": 976, "other_official_failure": 58, "value_error": 348, "wrong_count": 43, "wrong_func_name": 253}` |
| system=a1_recovery / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1341 | 0.1404 | `{"multi_turn_mismatch": 788, "multi_turn_other": 12}` |
| system=a1_recovery / bfcl_group=non_live | 1240 | 0.0226 | 0.5985 | 0.0226 | 0.4766 | 0.7921 | 0.3055 | `{"missing_required": 487, "official_success_or_safe_failure": 268, "other_official_failure": 14, "value_error": 62, "wrong_count": 397, "wrong_func_name": 12}` |
| system=a2_planner / bfcl_group=live | 2251 | 0.0329 | 0.3614 | 0.0329 | 0.3545 | 0.7541 | 0.4816 | `{"missing_required": 407, "official_success_or_safe_failure": 958, "other_official_failure": 79, "value_error": 242, "wrong_count": 36, "wrong_func_name": 529}` |
| system=a2_planner / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a2_planner / bfcl_group=non_live | 1240 | 0.0185 | 0.5229 | 0.0185 | 0.4016 | 0.7165 | 0.2900 | `{"missing_required": 401, "official_success_or_safe_failure": 263, "other_official_failure": 50, "value_error": 45, "wrong_count": 368, "wrong_func_name": 113}` |
| system=a3_interaction / bfcl_group=live | 2251 | 0.0333 | 0.3622 | 0.0333 | 0.3554 | 0.7550 | 0.4812 | `{"missing_required": 408, "official_success_or_safe_failure": 959, "other_official_failure": 79, "value_error": 242, "wrong_count": 34, "wrong_func_name": 529}` |
| system=a3_interaction / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a3_interaction / bfcl_group=non_live | 1240 | 0.0161 | 0.5219 | 0.0161 | 0.3992 | 0.7155 | 0.2892 | `{"missing_required": 401, "official_success_or_safe_failure": 260, "other_official_failure": 50, "value_error": 45, "wrong_count": 371, "wrong_func_name": 113}` |
| system=a4_reuse / bfcl_group=live | 2251 | 0.0333 | 0.3622 | 0.0333 | 0.3554 | 0.7550 | 0.4812 | `{"missing_required": 408, "official_success_or_safe_failure": 959, "other_official_failure": 79, "value_error": 242, "wrong_count": 34, "wrong_func_name": 529}` |
| system=a4_reuse / bfcl_group=multi_turn | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a4_reuse / bfcl_group=non_live | 1240 | 0.0161 | 0.5219 | 0.0161 | 0.3992 | 0.7155 | 0.2892 | `{"missing_required": 401, "official_success_or_safe_failure": 260, "other_official_failure": 50, "value_error": 45, "wrong_count": 371, "wrong_func_name": 113}` |

## system__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_call_pattern=parallel | 440 | 0.0068 | 0.3894 | 0.0068 | 0.0068 | 0.3894 | 0.0930 | `{"official_success_or_safe_failure": 3, "wrong_count": 437}` |
| system=a0_baseline / bfcl_call_pattern=serial | 3851 | 0.0317 | 0.4308 | 0.0317 | 0.4308 | 0.7505 | 0.4133 | `{"missing_required": 1060, "multi_turn_mismatch": 788, "multi_turn_other": 12, "official_success_or_safe_failure": 1246, "other_official_failure": 67, "value_error": 410, "wrong_count": 3, "wrong_func_name": 265}` |
| system=a1_recovery / bfcl_call_pattern=parallel | 440 | 0.0068 | 0.3894 | 0.0068 | 0.0068 | 0.3894 | 0.0930 | `{"official_success_or_safe_failure": 3, "wrong_count": 437}` |
| system=a1_recovery / bfcl_call_pattern=serial | 3851 | 0.0304 | 0.4308 | 0.0304 | 0.4308 | 0.7505 | 0.4133 | `{"missing_required": 1060, "multi_turn_mismatch": 788, "multi_turn_other": 12, "official_success_or_safe_failure": 1241, "other_official_failure": 72, "value_error": 410, "wrong_count": 3, "wrong_func_name": 265}` |
| system=a2_planner / bfcl_call_pattern=parallel | 440 | 0.0068 | 0.4065 | 0.0068 | 0.0295 | 0.4065 | 0.0787 | `{"official_success_or_safe_failure": 3, "other_official_failure": 35, "wrong_count": 402}` |
| system=a2_planner / bfcl_call_pattern=serial | 3851 | 0.0244 | 0.3332 | 0.0244 | 0.3332 | 0.6411 | 0.3719 | `{"missing_required": 808, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1218, "other_official_failure": 94, "value_error": 287, "wrong_count": 2, "wrong_func_name": 642}` |
| system=a3_interaction / bfcl_call_pattern=parallel | 440 | 0.0000 | 0.4036 | 0.0000 | 0.0227 | 0.4036 | 0.0764 | `{"other_official_failure": 35, "wrong_count": 405}` |
| system=a3_interaction / bfcl_call_pattern=serial | 3851 | 0.0247 | 0.3337 | 0.0247 | 0.3337 | 0.6416 | 0.3716 | `{"missing_required": 809, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1219, "other_official_failure": 94, "value_error": 287, "wrong_func_name": 642}` |
| system=a4_reuse / bfcl_call_pattern=parallel | 440 | 0.0000 | 0.4036 | 0.0000 | 0.0227 | 0.4036 | 0.0764 | `{"other_official_failure": 35, "wrong_count": 405}` |
| system=a4_reuse / bfcl_call_pattern=serial | 3851 | 0.0247 | 0.3337 | 0.0247 | 0.3337 | 0.6416 | 0.3716 | `{"missing_required": 809, "multi_turn_mismatch": 797, "multi_turn_other": 3, "official_success_or_safe_failure": 1219, "other_official_failure": 94, "value_error": 287, "wrong_func_name": 642}` |

## system__bfcl_group__bfcl_call_pattern

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4279 | 0.0000 | 0.0000 | 0.4279 | 0.1062 | `{"wrong_count": 40}` |
| system=a0_baseline / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.0439 | 0.4844 | 0.0439 | 0.4844 | 0.8842 | 0.5144 | `{"missing_required": 573, "official_success_or_safe_failure": 981, "other_official_failure": 53, "value_error": 348, "wrong_count": 3, "wrong_func_name": 253}` |
| system=a0_baseline / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1341 | 0.1404 | `{"multi_turn_mismatch": 788, "multi_turn_other": 12}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0075 | 0.3855 | 0.0075 | 0.0075 | 0.3855 | 0.0917 | `{"official_success_or_safe_failure": 3, "wrong_count": 397}` |
| system=a0_baseline / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.0298 | 0.7000 | 0.0298 | 0.7000 | 0.9857 | 0.4073 | `{"missing_required": 487, "official_success_or_safe_failure": 265, "other_official_failure": 14, "value_error": 62, "wrong_func_name": 12}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4279 | 0.0000 | 0.0000 | 0.4279 | 0.1062 | `{"wrong_count": 40}` |
| system=a1_recovery / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.0416 | 0.4844 | 0.0416 | 0.4844 | 0.8842 | 0.5144 | `{"missing_required": 573, "official_success_or_safe_failure": 976, "other_official_failure": 58, "value_error": 348, "wrong_count": 3, "wrong_func_name": 253}` |
| system=a1_recovery / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1341 | 0.1404 | `{"multi_turn_mismatch": 788, "multi_turn_other": 12}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0075 | 0.3855 | 0.0075 | 0.0075 | 0.3855 | 0.0917 | `{"official_success_or_safe_failure": 3, "wrong_count": 397}` |
| system=a1_recovery / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.0298 | 0.7000 | 0.0298 | 0.7000 | 0.9857 | 0.4073 | `{"missing_required": 487, "official_success_or_safe_failure": 265, "other_official_failure": 14, "value_error": 62, "wrong_func_name": 12}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4350 | 0.0000 | 0.0500 | 0.4350 | 0.0529 | `{"other_official_failure": 6, "wrong_count": 34}` |
| system=a2_planner / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.0335 | 0.3600 | 0.0335 | 0.3600 | 0.7598 | 0.4894 | `{"missing_required": 407, "official_success_or_safe_failure": 958, "other_official_failure": 73, "value_error": 242, "wrong_count": 2, "wrong_func_name": 529}` |
| system=a2_planner / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0075 | 0.4036 | 0.0075 | 0.0275 | 0.4036 | 0.0813 | `{"official_success_or_safe_failure": 3, "other_official_failure": 29, "wrong_count": 368}` |
| system=a2_planner / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.0238 | 0.5798 | 0.0238 | 0.5798 | 0.8655 | 0.3893 | `{"missing_required": 401, "official_success_or_safe_failure": 260, "other_official_failure": 21, "value_error": 45, "wrong_func_name": 113}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4350 | 0.0000 | 0.0500 | 0.4350 | 0.0529 | `{"other_official_failure": 6, "wrong_count": 34}` |
| system=a3_interaction / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.0339 | 0.3609 | 0.0339 | 0.3609 | 0.7607 | 0.4889 | `{"missing_required": 408, "official_success_or_safe_failure": 959, "other_official_failure": 73, "value_error": 242, "wrong_func_name": 529}` |
| system=a3_interaction / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0000 | 0.4005 | 0.0000 | 0.0200 | 0.4005 | 0.0788 | `{"other_official_failure": 29, "wrong_count": 371}` |
| system=a3_interaction / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.0238 | 0.5798 | 0.0238 | 0.5798 | 0.8655 | 0.3893 | `{"missing_required": 401, "official_success_or_safe_failure": 260, "other_official_failure": 21, "value_error": 45, "wrong_func_name": 113}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=parallel | 40 | 0.0000 | 0.4350 | 0.0000 | 0.0500 | 0.4350 | 0.0529 | `{"other_official_failure": 6, "wrong_count": 34}` |
| system=a4_reuse / bfcl_group=live / bfcl_call_pattern=serial | 2211 | 0.0339 | 0.3609 | 0.0339 | 0.3609 | 0.7607 | 0.4889 | `{"missing_required": 408, "official_success_or_safe_failure": 959, "other_official_failure": 73, "value_error": 242, "wrong_func_name": 529}` |
| system=a4_reuse / bfcl_group=multi_turn / bfcl_call_pattern=serial | 800 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0772 | 0.0289 | `{"multi_turn_mismatch": 797, "multi_turn_other": 3}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=parallel | 400 | 0.0000 | 0.4005 | 0.0000 | 0.0200 | 0.4005 | 0.0788 | `{"other_official_failure": 29, "wrong_count": 371}` |
| system=a4_reuse / bfcl_group=non_live / bfcl_call_pattern=serial | 840 | 0.0238 | 0.5798 | 0.0238 | 0.5798 | 0.8655 | 0.3893 | `{"missing_required": 401, "official_success_or_safe_failure": 260, "other_official_failure": 21, "value_error": 45, "wrong_func_name": 113}` |

## system__official_failure_bucket

| slice | rows | success | tool_selection | argument | structure | binder_match | param_fill | failure_bucket_counts |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system=a0_baseline / official_failure_bucket=missing_required | 1060 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1173 | `{"missing_required": 1060}` |
| system=a0_baseline / official_failure_bucket=multi_turn_mismatch | 788 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1320 | 0.1273 | `{"multi_turn_mismatch": 788}` |
| system=a0_baseline / official_failure_bucket=multi_turn_other | 12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2778 | 1.0000 | `{"multi_turn_other": 12}` |
| system=a0_baseline / official_failure_bucket=official_success_or_safe_failure | 1249 | 0.1001 | 0.1001 | 0.1001 | 0.1001 | 1.0000 | 0.9706 | `{"official_success_or_safe_failure": 1249}` |
| system=a0_baseline / official_failure_bucket=other_official_failure | 67 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2749 | `{"other_official_failure": 67}` |
| system=a0_baseline / official_failure_bucket=value_error | 410 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2359 | `{"value_error": 410}` |
| system=a0_baseline / official_failure_bucket=wrong_count | 440 | 0.0000 | 0.3825 | 0.0000 | 0.0000 | 0.3825 | 0.0930 | `{"wrong_count": 440}` |
| system=a0_baseline / official_failure_bucket=wrong_func_name | 265 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1043 | `{"wrong_func_name": 265}` |
| system=a1_recovery / official_failure_bucket=missing_required | 1060 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1173 | `{"missing_required": 1060}` |
| system=a1_recovery / official_failure_bucket=multi_turn_mismatch | 788 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1320 | 0.1273 | `{"multi_turn_mismatch": 788}` |
| system=a1_recovery / official_failure_bucket=multi_turn_other | 12 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2778 | 1.0000 | `{"multi_turn_other": 12}` |
| system=a1_recovery / official_failure_bucket=official_success_or_safe_failure | 1244 | 0.0965 | 0.0965 | 0.0965 | 0.0965 | 1.0000 | 0.9713 | `{"official_success_or_safe_failure": 1244}` |
| system=a1_recovery / official_failure_bucket=other_official_failure | 72 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.3113 | `{"other_official_failure": 72}` |
| system=a1_recovery / official_failure_bucket=value_error | 410 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2359 | `{"value_error": 410}` |
| system=a1_recovery / official_failure_bucket=wrong_count | 440 | 0.0000 | 0.3825 | 0.0000 | 0.0000 | 0.3825 | 0.0930 | `{"wrong_count": 440}` |
| system=a1_recovery / official_failure_bucket=wrong_func_name | 265 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1043 | `{"wrong_func_name": 265}` |
| system=a2_planner / official_failure_bucket=missing_required | 808 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1143 | `{"missing_required": 808}` |
| system=a2_planner / official_failure_bucket=multi_turn_mismatch | 797 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0768 | 0.0290 | `{"multi_turn_mismatch": 797}` |
| system=a2_planner / official_failure_bucket=multi_turn_other | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2000 | 0.0000 | `{"multi_turn_other": 3}` |
| system=a2_planner / official_failure_bucket=official_success_or_safe_failure | 1221 | 0.0794 | 0.0794 | 0.0794 | 0.0794 | 1.0000 | 0.9781 | `{"official_success_or_safe_failure": 1221}` |
| system=a2_planner / official_failure_bucket=other_official_failure | 129 | 0.0000 | 0.9031 | 0.0000 | 0.8062 | 0.9031 | 0.2462 | `{"other_official_failure": 129}` |
| system=a2_planner / official_failure_bucket=value_error | 287 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2134 | `{"value_error": 287}` |
| system=a2_planner / official_failure_bucket=wrong_count | 404 | 0.0000 | 0.3796 | 0.0000 | 0.0000 | 0.3796 | 0.0788 | `{"wrong_count": 404}` |
| system=a2_planner / official_failure_bucket=wrong_func_name | 642 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0502 | `{"wrong_func_name": 642}` |
| system=a3_interaction / official_failure_bucket=missing_required | 809 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1141 | `{"missing_required": 809}` |
| system=a3_interaction / official_failure_bucket=multi_turn_mismatch | 797 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0768 | 0.0290 | `{"multi_turn_mismatch": 797}` |
| system=a3_interaction / official_failure_bucket=multi_turn_other | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2000 | 0.0000 | `{"multi_turn_other": 3}` |
| system=a3_interaction / official_failure_bucket=official_success_or_safe_failure | 1219 | 0.0779 | 0.0779 | 0.0779 | 0.0779 | 1.0000 | 0.9781 | `{"official_success_or_safe_failure": 1219}` |
| system=a3_interaction / official_failure_bucket=other_official_failure | 129 | 0.0000 | 0.9031 | 0.0000 | 0.8062 | 0.9031 | 0.2462 | `{"other_official_failure": 129}` |
| system=a3_interaction / official_failure_bucket=value_error | 287 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2134 | `{"value_error": 287}` |
| system=a3_interaction / official_failure_bucket=wrong_count | 405 | 0.0000 | 0.3830 | 0.0000 | 0.0000 | 0.3830 | 0.0786 | `{"wrong_count": 405}` |
| system=a3_interaction / official_failure_bucket=wrong_func_name | 642 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0502 | `{"wrong_func_name": 642}` |
| system=a4_reuse / official_failure_bucket=missing_required | 809 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.1141 | `{"missing_required": 809}` |
| system=a4_reuse / official_failure_bucket=multi_turn_mismatch | 797 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0768 | 0.0290 | `{"multi_turn_mismatch": 797}` |
| system=a4_reuse / official_failure_bucket=multi_turn_other | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.2000 | 0.0000 | `{"multi_turn_other": 3}` |
| system=a4_reuse / official_failure_bucket=official_success_or_safe_failure | 1219 | 0.0779 | 0.0779 | 0.0779 | 0.0779 | 1.0000 | 0.9781 | `{"official_success_or_safe_failure": 1219}` |
| system=a4_reuse / official_failure_bucket=other_official_failure | 129 | 0.0000 | 0.9031 | 0.0000 | 0.8062 | 0.9031 | 0.2462 | `{"other_official_failure": 129}` |
| system=a4_reuse / official_failure_bucket=value_error | 287 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.2134 | `{"value_error": 287}` |
| system=a4_reuse / official_failure_bucket=wrong_count | 405 | 0.0000 | 0.3830 | 0.0000 | 0.0000 | 0.3830 | 0.0786 | `{"wrong_count": 405}` |
| system=a4_reuse / official_failure_bucket=wrong_func_name | 642 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0502 | `{"wrong_func_name": 642}` |
