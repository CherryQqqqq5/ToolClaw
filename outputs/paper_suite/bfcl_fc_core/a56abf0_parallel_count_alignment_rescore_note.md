# BFCL a56abf0 Parallel Count Alignment Rescore Diagnostic Note

## Provenance
- Scorer commit: `a56abf03ebae516da0235287c9cc4266d83e6552`
- Executor traces: existing `outputs/paper_suite/bfcl_fc_core` traces from the prior `21e70bf` full run
- Mode: scorer-only rescore with official evaluator enabled; no executor rerun

## Main Result
The new count-alignment audit splits the prior parallel wrong-count bucket without changing runtime traces. For `a2_planner`, the dominant count issue is under-extraction relative to scorer-stage expected call count, not trace-to-answer loss.

## A2 Parallel Count Alignment
- `parallel_count_alignment_bucket_counts`: `{"count_aligned": 11, "emitted_less_than_materialized": 28, "extracted_too_few_argument_sets": 143, "extracted_too_many_argument_sets": 29}`
- `extracted_too_few_argument_sets`: 143
- `extracted_too_many_argument_sets`: 29
- `emitted_less_than_materialized`: 28
- `materialized_count_matches_emitted_but_not_expected`: 0
- `count_aligned`: 11

## Bridge Audit Cross-Check
- `parallel_bridge_drop_stage_counts`: `{"parallel_emitted_calls_success": 2, "parallel_emitted_calls_wrong_args": 9, "parallel_emitted_calls_wrong_count": 131, "parallel_workflow_steps_built_but_preflight_blocked": 69}`
- `parallel_workflow_steps_built_but_preflight_blocked`: 69
- `parallel_emitted_calls_wrong_count`: 131
- `trace_gt0_emitted0`: 0

## Interpretation
- `trace_gt0_emitted0=0` continues to rule out trace-to-answer extraction as the next target.
- `extracted_too_few_argument_sets` dominates the count-alignment breakdown, so future parallel count repair should focus on observable argument-set granularity only after the partial-call bridge is validated.
- `emitted_less_than_materialized` remains a bridge signal that the `a56abf0` runtime bypass should address in the next full executor run.

## Claim Status
BFCL remains Case D after this scorer-only rescore. Current gates remain `a2_wrong_func_name_le_a0=True`, `a2_tool_selection_ge_a0=True`, and `a2_success_ge_a0=False`. No claim matrix or paper doc update is supported by this rescore.
