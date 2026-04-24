# BFCL Function Selection Audit

This report is gold-enriched after execution. Runtime diagnostics remain gold-free.

- audit_schema_version: `bfcl_function_selection_audit_v1`
- guard_policy_version: `strict_schema_top1_tie_drop_v1`
- runtime_diagnostics_gold_free: `True`

## Guardability Buckets

| system | bucket | count |
|---|---|---:|
| a0_baseline | schema_top1_expected | 1625 |
| a1_recovery | schema_top1_expected | 1625 |
| a2_planner | schema_top1_expected | 1625 |
| a3_interaction | schema_top1_expected | 1625 |
| a4_reuse | schema_top1_expected | 1625 |
