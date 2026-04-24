# BFCL Candidate Coverage Rerun Diagnostic (2026-04-24)

## Scope

This note records the full guarded `bfcl_fc_core` rerun at commit `046d24d066d2844399dac2d6edf22b0b29f7d3eb` after the candidate coverage funnel audit was added. The rerun is diagnostic only. It does not upgrade BFCL claims or change the BFCL planner/binder headline limitation.

Command:

```bash
PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core
```

Output root:

```text
outputs/paper_suite/bfcl_fc_core
```

Canonical small artifacts:

- `claim_summary.json`
- `bfcl_candidate_coverage_summary.json`
- `bfcl_candidate_coverage_summary.md`
- `bfcl_failure_slice_summary.json`
- `bfcl_failure_slice_summary.md`
- `bfcl_function_selection_audit.md`
- `official_scoreboard.json`
- `toolclaw_diagnostics.json`

The large row-level audits remain available in the output directory but are not required for the claim boundary: `bfcl_candidate_coverage_audit.json` and `bfcl_function_selection_audit.json`.

## Claim Gate Result

The rerun remains **Case D**.

```json
{
  "paper_safe_for_claim": true,
  "wrong_function_non_regression_ready": false,
  "missing_required_reduction_ready": false,
  "full_suite_supporting_ready": false,
  "baseline_missing_required_slice_ready": false,
  "full_suite_gates": {
    "a2_wrong_func_name_le_a0": true,
    "a2_missing_required_lt_a0": false,
    "a2_tool_selection_ge_a0": true,
    "a2_success_ge_a0": false
  },
  "reuse_claim_enabled_for_bfcl": false,
  "a4_interpreted_as_guarded_execution_variant_only": true
}
```

Interpretation:

- `a2_wrong_func_name_le_a0 = true`: the guard suppresses the previous wrong-function regression for `a2_planner`.
- `a2_tool_selection_ge_a0 = true`: tool-selection non-regression passes by a small margin.
- `a2_success_ge_a0 = false`: official success is still below baseline, so BFCL remains a limitation.
- `a2_missing_required_lt_a0 = false`: missing-required reduction is not demonstrated.
- `baseline_missing_required_slice_ready = false`: the pre-registered baseline-missing-required slice has zero `a0_baseline` rows in this rerun.

Claim status remains:

```text
planner_binding_headline: limitation
bfcl_exact_function_guard: unsupported
bfcl_missing_required_guarded_reduction: unsupported
bfcl_broad_transfer: unsupported
bfcl_reuse_lift: unsupported
```

## Official Metrics

```text
a0_baseline: success=0.308553, tool_selection=0.483695, argument=0.308553, structure=0.468888
a2_planner: success=0.302960, tool_selection=0.484840, argument=0.302960, structure=0.469821
a3_interaction: success=0.303659, tool_selection=0.694881, argument=0.303659, structure=0.655558
```

## Coverage Funnel

Overall funnel:

```json
{
  "total_rows": 21455,
  "expected_in_raw_function_docs": 8125,
  "expected_in_prepared_schema": 8125,
  "expected_in_runtime_candidates": 3990,
  "expected_in_schema_top5": 3990,
  "expected_is_schema_top1": 3990,
  "selected_is_expected": 3990,
  "selected_expected_success": 262,
  "coverage_raw": 0.37869960382195295,
  "coverage_prepared": 0.37869960382195295,
  "coverage_runtime": 0.1859706362153344,
  "coverage_top5": 0.1859706362153344,
  "ranker_top1": 1.0,
  "selection_accuracy": 1.0,
  "arg_success_given_correct_tool": 0.06566416040100251
}
```

Drop-stage counts:

```json
{
  "prepared_to_runtime_drop": 4135,
  "no_expected_function": 13330,
  "selected_correct_arg_or_shape_error": 3728,
  "selected_correct_success": 262
}
```

Per-system `a2_planner` funnel:

```json
{
  "expected_in_raw_function_docs": 1625,
  "expected_in_prepared_schema": 1625,
  "expected_in_runtime_candidates": 798,
  "expected_in_schema_top5": 798,
  "selected_is_expected": 798,
  "selected_expected_success": 52,
  "drop_stage_counts": {
    "prepared_to_runtime_drop": 827,
    "no_expected_function": 2666,
    "selected_correct_arg_or_shape_error": 746,
    "selected_correct_success": 52
  }
}
```

## Dominant Blocker

The actionable blocker is **prepared-to-runtime candidate loss**, followed by argument/call-shape failure after the correct function is selected.

Evidence:

- Raw and prepared coverage match exactly: `expected_in_raw_function_docs = expected_in_prepared_schema = 8125` overall, so the current blocker is not raw source alignment or preparation loss.
- Runtime coverage drops to `3990` overall; for each system, `prepared_to_runtime_drop = 827`.
- When expected reaches runtime candidates, it also reaches schema top-5 and top-1: `expected_in_runtime_candidates = expected_in_schema_top5 = expected_is_schema_top1 = selected_is_expected`.
- The ranker is not the first-order blocker in this run: `ranker_top1 = 1.0` on rows where expected is in runtime candidates.
- Correct-function rows still mostly fail downstream: `selected_correct_arg_or_shape_error = 3728` overall and `746` for `a2_planner`.

Next implementation target:

1. Fix BFCL adapter/runtime candidate preservation so planner and canonicalization cannot shrink the benchmark-provided function pool before schema ranking.
2. After runtime candidate coverage is close to prepared coverage, rerun smoke/full and only then inspect ranker ordering or argument/call-shape repair.
3. Do not tune planner override or ranker weights before the prepared-to-runtime drop is explained.

## Claim Discipline

This rerun should be cited as a diagnostic funnel result, not positive BFCL evidence. The claim matrix should remain conservative: `planner_binding_headline` is a limitation, `bfcl_exact_function_guard` is unsupported after Case D, and `bfcl_missing_required_guarded_reduction` is unsupported.
