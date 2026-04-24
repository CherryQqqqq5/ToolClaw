# BFCL Function Selection Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_function_selection_audit_v1`
- guard_policy_version: `strict_schema_top1_tie_drop_v1`
- runtime_diagnostics_gold_free: `True`

## Guardability Buckets

| system | bucket | count |
|---|---|---:|
| a0_baseline | expected_absent_from_schema_top5 | 827 |
| a0_baseline | schema_top1_expected | 798 |
| a1_recovery | expected_absent_from_schema_top5 | 827 |
| a1_recovery | schema_top1_expected | 798 |
| a2_planner | expected_absent_from_schema_top5 | 827 |
| a2_planner | schema_top1_expected | 798 |
| a3_interaction | expected_absent_from_schema_top5 | 827 |
| a3_interaction | schema_top1_expected | 798 |
| a4_reuse | expected_absent_from_schema_top5 | 827 |
| a4_reuse | schema_top1_expected | 798 |
