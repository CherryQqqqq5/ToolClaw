# BFCL Candidate Coverage Rerun Diagnostic (2026-04-24)

## Scope

This note records two guarded `bfcl_fc_core` reruns. The first rerun at `046d24d066d2844399dac2d6edf22b0b29f7d3eb` added the candidate coverage funnel and localized a large apparent `prepared_to_runtime_drop`. The second rerun at `869a72e1cc946a0e5e93117d7ac31ebb1f408e2c` added BFCL runtime candidate-pool preservation and is now the current diagnostic source of truth.

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

The `869a72e` rerun remains **Case D** for paper claims.

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
a0_baseline: success=0.308786, tool_selection=0.484607, argument=0.308786, structure=0.470287
a2_planner: success=0.303193, tool_selection=0.485792, argument=0.303193, structure=0.471452
a3_interaction: success=0.303892, tool_selection=0.698940, argument=0.303892, structure=0.661151
```

## Coverage Funnel After Candidate Preservation

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
  "selected_expected_success": 267,
  "coverage_raw": 0.37869960382195295,
  "coverage_prepared": 0.37869960382195295,
  "coverage_runtime": 0.1859706362153344,
  "coverage_top5": 0.1859706362153344,
  "ranker_top1": 1.0,
  "selection_accuracy": 1.0,
  "arg_success_given_correct_tool": 0.06691729323308271
}
```

Drop-stage counts:

```json
{
  "bfcl_abstain_candidate_elision": 4120,
  "no_expected_function": 13330,
  "selected_correct_arg_or_shape_error": 3723,
  "selected_correct_success": 267,
  "prepared_to_runtime_drop": 15
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
  "selected_expected_success": 53,
  "drop_stage_counts": {
    "bfcl_abstain_candidate_elision": 824,
    "no_expected_function": 2666,
    "selected_correct_arg_or_shape_error": 745,
    "selected_correct_success": 53,
    "prepared_to_runtime_drop": 3
  }
}
```

## Dominant Blocker

The candidate preservation patch succeeded for the executable path. The old apparent coverage loss was mostly intentional BFCL abstain/relevance elision, not ordinary candidate-pool narrowing.

Evidence:

- Raw and prepared coverage match exactly: `expected_in_raw_function_docs = expected_in_prepared_schema = 8125` overall.
- The previous `prepared_to_runtime_drop = 4135` is now split into `bfcl_abstain_candidate_elision = 4120` and true `prepared_to_runtime_drop = 15` overall.
- `a2_planner` true `prepared_to_runtime_drop` is now `3`, all in `non_live:parallel`; the rows are official-success-or-safe-failure examples where the expected function is also the selected tool.
- On rows where expected reaches runtime candidates, it reaches schema top-5/top-1 and is selected: `expected_in_runtime_candidates = expected_in_schema_top5 = expected_is_schema_top1 = selected_is_expected = 3990`.
- Correct-function rows still mostly fail downstream: `selected_correct_arg_or_shape_error = 3723` overall and `745` for `a2_planner`.

Next implementation target:

1. Treat BFCL candidate visibility as effectively repaired except for the small `non_live:parallel` diagnostic residue.
2. Move the next BFCL repair step to argument grounding and call-shape canonicalization on selected-correct rows.
3. Do not tune planner override or schema-ranker weights before analyzing `selected_correct_arg_or_shape_error` into missing-required, wrong-arg, wrong-count, order, parallel-structure, and multi-turn-shape buckets.

## Claim Discipline

This rerun should be cited as a diagnostic funnel result, not positive BFCL evidence. The claim matrix should remain conservative: `planner_binding_headline` is a limitation, `bfcl_exact_function_guard` is unsupported after Case D, and `bfcl_missing_required_guarded_reduction` is unsupported.
