# BFCL Guarded fc_core Rerun Diagnostic (2026-04-24)

## Scope

This note records the first full guarded `bfcl_fc_core` rerun after commit `e58b905657f8482869ffa8c7ca169539ed6690eb`. It is diagnostic only: no code, claim matrix, or BFCL headline wording is changed by this result.

Command:

```bash
PYTHONPATH=src python3 scripts/run_paper_bench_suite.py bfcl_fc_core
```

Output root:

```text
outputs/paper_suite/bfcl_fc_core
```

Canonical artifacts inspected:

- `claim_summary.json`
- `bfcl_failure_slice_summary.json`
- `bfcl_failure_slice_summary.md`
- `bfcl_function_selection_audit.json`
- `bfcl_function_selection_audit.md`
- `official_scoreboard.json`
- `toolclaw_diagnostics.json`

## Claim Gate Result

The guarded full rerun is paper-safe, but it does not support a BFCL claim upgrade.

```json
{
  "paper_safe_for_claim": true,
  "headline_supported": false,
  "headline_blockers": [
    "a2_success_not_above_a0",
    "a2_success_not_above_a1",
    "a2_not_better_on_two_headline_submetrics"
  ],
  "reuse_claim_enabled_for_bfcl": false,
  "a4_interpreted_as_guarded_execution_variant_only": true
}
```

BFCL guard gates:

```json
{
  "a2_wrong_func_name_le_a0": true,
  "a2_missing_required_lt_a0": false,
  "a2_tool_selection_ge_a0": true,
  "a2_success_ge_a0": false,
  "wrong_function_non_regression_ready": false,
  "missing_required_reduction_ready": false,
  "full_suite_supporting_ready": false,
  "baseline_missing_required_slice_ready": false
}
```

Claim interpretation:

```json
{
  "planner_binding_headline": "limitation",
  "bfcl_exact_function_guard": "unsupported",
  "bfcl_missing_required_guarded_reduction": "unsupported",
  "bfcl_broad_transfer": "unsupported",
  "bfcl_reuse_lift": "unsupported"
}
```

## Case Classification

This rerun is **Case D** under the pre-registered BFCL interpretation rules.

Reason:

- `a2_wrong_func_name_le_a0 = true`: wrong-function regression is suppressed for `a2_planner` versus `a0_baseline`.
- `a2_tool_selection_ge_a0 = true`: tool-selection non-regression passes.
- `a2_success_ge_a0 = false`: official success remains below baseline.
- `a2_missing_required_lt_a0 = false`: no missing-required reduction is available; `a0_baseline` has no `missing_required` rows in this run.
- `baseline_missing_required_slice_ready = false`: the pre-registered baseline-missing-required slice has zero rows.

Therefore BFCL remains a limitation. Any slice-level or guard-level improvement is appendix diagnostic only, not claim-matrix support.

## Official Metrics

```text
a0_baseline: success=0.3085527849, tool_selection=0.4836945545, argument=0.3085527849, structure=0.4688883710
a1_recovery: success=0.3085527849, tool_selection=0.4851705119, argument=0.3085527849, structure=0.4700536006
a2_planner: success=0.3029596831, tool_selection=0.4848403636, argument=0.3029596831, structure=0.4698205546
a3_interaction: success=0.3036588208, tool_selection=0.6948807582, argument=0.3036588208, structure=0.6555581450
a4_reuse: success=0.3036588208, tool_selection=0.6948807582, argument=0.3036588208, structure=0.6555581450
```

## Failure Buckets

```json
{
  "a0_baseline": {
    "official_success_or_safe_failure": 1340,
    "value_error": 537,
    "wrong_func_name": 83,
    "other_official_failure": 153,
    "wrong_count": 1378,
    "multi_turn_mismatch": 730,
    "multi_turn_other": 70
  },
  "a2_planner": {
    "official_success_or_safe_failure": 1316,
    "value_error": 542,
    "wrong_func_name": 83,
    "other_official_failure": 182,
    "wrong_count": 1368,
    "multi_turn_mismatch": 752,
    "multi_turn_other": 48
  },
  "a3_interaction": {
    "official_success_or_safe_failure": 1319,
    "value_error": 859,
    "wrong_func_name": 178,
    "other_official_failure": 277,
    "missing_required": 400,
    "wrong_count": 458,
    "multi_turn_mismatch": 784,
    "multi_turn_other": 16
  },
  "a4_reuse": {
    "official_success_or_safe_failure": 1319,
    "value_error": 859,
    "wrong_func_name": 178,
    "other_official_failure": 277,
    "missing_required": 400,
    "wrong_count": 458,
    "multi_turn_mismatch": 784,
    "multi_turn_other": 16
  }
}
```

## Function-Selection Audit

Runtime safety fields passed:

```json
{
  "audit_schema_version": "bfcl_function_selection_audit_v1",
  "guard_policy_version": "strict_schema_top1_tie_drop_v1",
  "runtime_diagnostics_gold_free": true,
  "runtime_gold_field_leak_count": 0,
  "gold_fields_added_after_execution": true
}
```

Guardability bucket counts are identical across systems:

```json
{
  "schema_top1_expected": 798,
  "expected_absent_from_schema_top5": 827,
  "schema_top1_wrong_expected_in_top5": 0,
  "planner_wrong_schema_top1_expected": 0,
  "planner_wrong_schema_also_wrong": 0,
  "planner_correct_schema_wrong": 0
}
```

This indicates the guarded path is obeying the gold-free schema-top1 policy, but BFCL still has substantial candidate/schema coverage gaps: 827 rows have the expected function absent from schema top-5. The next BFCL debugging target is candidate extraction, schema normalization, or ranker coverage, not planner override behavior.

## Recommended Next Step

Do not update the claim matrix based on this rerun. Keep BFCL in the paper as a limitation:

- `planner_binding_headline`: limitation
- `bfcl_exact_function_guard`: unsupported
- `bfcl_missing_required_guarded_reduction`: unsupported
- `bfcl_broad_transfer`: unsupported
- `bfcl_reuse_lift`: unsupported

If continuing BFCL work, the next implementation should add a schema/candidate coverage audit for rows where `expected_absent_from_schema_top5` is true, then inspect whether the expected function is absent because of candidate narrowing, schema name normalization, multi-turn candidate construction, or function-call source parsing.
