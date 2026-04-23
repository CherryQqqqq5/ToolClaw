# Experiment Data Consistency Audit 2026-04-23

This audit records the current paper-facing result bundles checked against repository documentation.

## Source Of Truth

| Area | Current result bundle | Checked status |
| --- | --- | --- |
| ToolSandbox official headline | `outputs/paper_final_freeze_20260423/toolsandbox_official_post8249ee1` | aligned after post-8249ee1 rerun |
| ToolSandbox interaction causality | `outputs/paper_final_freeze_20260423/toolsandbox_interaction_causality_formal` | aligned |
| Interaction Live V1 | `outputs/interaction_live_v1_formal` | aligned |
| BFCL `fc_core` formal | `outputs/paper_suite_formal/bfcl_fc_core` | aligned |
| BFCL grounding formal fix1 | `outputs/paper_suite_grounding_formal_20260421_fix1/bfcl_fc_core` | historical/diagnostic only |
| Tau2 dual-control / compound approval current | `outputs/tau2_dual_control_after_compound_fix_20260423_v2` and `outputs/tau2_compound_approval_fix_r10_20260423_v2` | aligned after this audit |
| ToolSandbox persistent reuse V1 | `outputs/reuse_persistent_v1_smoke_scope` | aligned after this audit |

## Corrections Made

### ToolSandbox Official

Previous docs still reported the older archived official numbers:

- `a0_baseline = 0.659`
- `a1_recovery = 0.693`
- `a2_planner = 0.693`
- `a3_interaction = 1.000`
- `a4_reuse = 1.000`

Current superseded 2026-04-22 frozen bundle reported:

- `a0_baseline = 0.636`
- `a1_recovery = 0.682`
- `a2_planner = 0.625`
- `a3_interaction = 1.000`
- `a4_reuse = 1.000`

The post-8249ee1 structural-fallback confirmation bundle reports:

- `a0_baseline = 0.636`
- `a1_recovery = 0.682`
- `a2_planner = 0.693`
- `a3_interaction = 1.000`
- `a4_reuse = 1.000`

This fixes the earlier `a2_planner < a1_recovery` anomaly caused by planner-generated workflows with unbound steps on low-battery state-dependency tasks.
The current bundle manifest records `git_commit = 8249ee1cd1ffffe7355d2f561664b75a214fc7dc`, so the result is tied to the commit that contains the fallback code.

Updated docs:

- `README.md`
- `docs/toolsandbox_all_experiments_report.md`

### Tau2 Compound Approval

Previous docs still described the historical isolated 10-run compound approval stress as failing:

- `a3_interaction = 0.000`
- `a4_reuse = 0.000`
- `stop_reason = max_user_turns_exceeded`

Current fixed rerun reports:

- `a3_interaction = 1.000`
- `a4_reuse = 1.000`
- `approval_following = 1.000`
- `interactive_correction = 6.0`

Updated docs:

- `docs/tau2_claim_experiments_report.md`
- `docs/toolsandbox_all_experiments_report.md`
- `docs/paper_claim_freeze_plan.md`

The corrected claim is now interaction-enabled compound approval repair, not reuse-over-interaction.

### ToolSandbox Persistent Reuse V1

Current smoke bundle reports:

- `paper_safe_reuse_evidence = false`
- `reuse_scope = exact`
- `warm_claim_reuse_hit_rate = 0.667`
- `warm_claim_correct_source_match_rate = 1.000`
- `sham_false_positive_rate = 0.667`
- `headroom_pair_count = 0`
- gate failures:
  - `sham_false_positive_rate_above_0.05`
  - `cold_headroom_filter_failed`
  - `no_positive_primary_cost_reduction`

Updated docs/config:

- `configs/paper_claim_matrix.yaml`
- `docs/paper_benchmark_portfolio.md`
- `README.md`

The corrected claim status is diagnostic / pending, not supported paper-safe evidence.

## Checked And Already Aligned

### ToolSandbox Interaction Causality

Current formal bundle:

- `overall_interaction_query_contribution_supported = true`
- `repair_semantic_usefulness_supported = true`
- `probe_only_success_caveat_present = true`
- `interaction_not_cheating_supported = true`
- `no_query_repair_mechanism_supported = false`
- `interaction_success_metric_caveat = true`

Key slice values in `docs/paper_benchmark_portfolio.md` match the current bundle:

- repair-semantic: `a3_full_interaction = 1.000`, `a2_planner = 0.500`, `a3_no_query = 0.500`, `a3_noisy_user = 0.500`
- repair-semantic usefulness for full interaction: all five usefulness/progress metrics are `0.500`
- noisy usefulness metrics remain `0.000`
- probe-only: full/noisy strict success can be `1.000`, but usefulness remains `0.000`

### Interaction Live V1

Current formal bundle:

- `interaction_as_control_signal_supported = true`
- `semantic_usefulness_supported_on_repair_semantic = true`
- `probe_only_success_caveat_present = true`
- `noisy_user_not_counted_as_useful_repair = true`
- `irrelevant_user_not_counted_as_useful_repair = true`
- `wrong_parameter_not_counted_as_effective_patch = true`
- `extraction_f1_gate_passed = true`

The values reported in `docs/paper_benchmark_portfolio.md` match `outputs/interaction_live_v1_formal/claim_summary.json`.

### BFCL

Current `bfcl_fc_core` formal bundle:

- `paper_safe_for_claim = true`
- `headline_supported = false`
- `a0_baseline.success = 0.0291`
- `a1_recovery.success = 0.0280`
- `a2_planner.success = 0.0226`
- `a3_interaction.success = 0.0221`
- `a4_reuse.success = 0.0221`

The values reported in `docs/paper_benchmark_portfolio.md` match `outputs/paper_suite_formal/bfcl_fc_core/claim_summary.json`.

## Remaining Hygiene

- `data/external/ToolSandbox` is still dirty in the worktree and was not touched by this audit.
- Local AppleDouble `._*` files under `docs/` were removed from the server tree when present; they are not part of paper-facing artifacts.
