# BFCL babdf1b Parallel Partial-Call Full Rerun Diagnostic Note

## Provenance
- Runtime/scorer commit: `babdf1b51dfd7315886c9a1a88635eea93ba5cc5`
- Code change under test: `a56abf0` parallel count-alignment audit plus BFCL non-live parallel partial-call preflight bypass
- Suite: `bfcl_fc_core` full formal run

## Official Gates
- `a0_official_success`: 0.2528548123980424
- `a2_official_success`: 0.247494756467024
- `a0_tool_selection`: 0.6525246640254797
- `a2_tool_selection`: 0.6375825370931407
- `a2_wrong_func_name_le_a0`: True
- `a2_tool_selection_ge_a0`: False
- `a2_success_ge_a0`: False

## Parallel Bridge Outcome
The partial-call bypass worked at the bridge layer but did not produce official success lift.
- A2 `parallel_workflow_steps_built_but_preflight_blocked`: 2 (prior bridge rescore baseline: 69)
- A2 `materialized_gt0_trace0`: 2 (prior bridge rescore baseline: 69)
- A2 `emitted_less_than_materialized`: 1 (prior count-alignment baseline: 28)
- A2 `trace_gt0_emitted0`: 0

## Remaining Parallel Failure Shape
- A2 `parallel_bridge_drop_stage_counts`: `{"parallel_emitted_calls_success": 2, "parallel_emitted_calls_wrong_args": 36, "parallel_emitted_calls_wrong_count": 171, "parallel_workflow_steps_built_but_preflight_blocked": 2}`
- A2 `parallel_count_alignment_bucket_counts`: `{"count_aligned": 38, "emitted_less_than_materialized": 1, "extracted_too_few_argument_sets": 143, "extracted_too_many_argument_sets": 29}`
- A2 `parallel_shape_error_given_selected_is_expected`: 173
- A2 `wrong_call_count_given_selected_is_expected`: 171
- A2 `parallel_emitted_calls_wrong_args`: 36

## Interpretation
- The runtime bridge repair converted most preflight-blocked materialized clauses into scorer-visible calls.
- The new scorer-visible calls mostly moved into wrong-count / wrong-args buckets rather than official success.
- Count alignment remains dominated by `extracted_too_few_argument_sets`, so the next parallel blocker is observable argument-set granularity and parallel argument grounding, not trace-to-answer serialization.
- `a2_tool_selection_ge_a0=false` means the run is not claim-ready even before considering success.

## Claim Status
BFCL remains Case D / limitation. No claim matrix or paper doc update is justified by this run.
