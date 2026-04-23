# Paper Final Freeze Plan (2026-04-22)

## Decision

The paper should now freeze around the following narrative:

- **ToolSandbox official** carries the main headline for interaction and stateful workflow intelligence.
- **Tau2 dual-control** carries the main headline for dual-control interaction and interactive correction.
- **BFCL fc_core** carries the planner/binder/**grounding mechanism** evidence.
- **Reuse** remains a narrow exact-match cost-reduction claim only.

The BFCL line should **not** be stretched into a top-line performance headline unless one final frozen confirm clearly beats baseline on a core official metric. Current frozen BFCL evidence is strong enough for a mechanism headline, not for a general “headline win” claim.

## Why BFCL is Frozen as Mechanism Evidence

The current frozen BFCL story is consistent across the tracked bundles:

- `fc_preflight_only` collapses on required-arg-sensitive BFCL slices.
- `fc_grounding_recovery` and `a4_reuse` recover to **baseline-level** success.
- the observed improvement is driven by **adapter-side extraction strengthening**.
- `repair_success_count` remains `0` in the latest repair audit slice, so repair is not yet the dominant source of gain.

This supports a paper-safe mechanism claim:

> Without a grounding path, correct-enough tool selection still fails to yield executable actions; stronger grounding/extraction restores those actions to baseline-level executable performance.

It does **not** yet support:

> Grounding repair produces a stable top-line BFCL win over baseline.

## Main Table vs Appendix

### Main paper

- ToolSandbox official
  - interaction headline
  - stateful workflow headline
- Tau2 dual-control
  - dual-control / interactive correction headline
- BFCL fc_core
  - mechanism headline for planner / binder / grounding

### Appendix / analysis

- BFCL grounded slice analysis
  - [outputs/bfcl_grounding_triggered_preflight_v3/official_scoreboard.json](../outputs/bfcl_grounding_triggered_preflight_v3/official_scoreboard.json)
  - [outputs/bfcl_grounding_fix_medium_v5/official_scoreboard.json](../outputs/bfcl_grounding_fix_medium_v5/official_scoreboard.json)
  - [outputs/bfcl_grounding_repair_audit_v3/official_scoreboard.json](../outputs/bfcl_grounding_repair_audit_v3/official_scoreboard.json)
- BFCL repair evolution analysis
  - [docs/bfcl_grounding_repair_audit_progress_20260422_zh.md](../docs/bfcl_grounding_repair_audit_progress_20260422_zh.md)
- Tau-bench supporting-only results
- reuse exact-match narrow evidence

## Frozen BFCL Assets

### Versioned inputs

- [data/bfcl_slices/grounding_triggered_preflight_v1.jsonl](../data/bfcl_slices/grounding_triggered_preflight_v1.jsonl)
- [data/bfcl_slices/grounding_delta_cases_v1.jsonl](../data/bfcl_slices/grounding_delta_cases_v1.jsonl)
- [data/bfcl_slices/grounding_repair_applied_audit_v1.jsonl](../data/bfcl_slices/grounding_repair_applied_audit_v1.jsonl)
- [data/bfcl_slices/manifest.json](../data/bfcl_slices/manifest.json)

### Summary bundles

- [outputs/bfcl_grounding_triggered_preflight_v3/claim_summary.json](../outputs/bfcl_grounding_triggered_preflight_v3/claim_summary.json)
- [outputs/bfcl_grounding_fix_medium_v5/claim_summary.json](../outputs/bfcl_grounding_fix_medium_v5/claim_summary.json)
- [outputs/bfcl_grounding_repair_audit_v3/claim_summary.json](../outputs/bfcl_grounding_repair_audit_v3/claim_summary.json)

## Remaining Work

### P0

- final freeze ToolSandbox official bundle on frozen code
- final freeze Tau2 dual-control bundle on frozen code
- choose whether BFCL needs one final formal confirm or should be accepted immediately as mechanism headline only

### Optional BFCL final confirm

Only run a final BFCL confirm if it answers a binary question:

- can frozen-code grounding beat baseline on at least one core official metric?

If not, do **not** continue iterating broadly on BFCL.

## Verification

- ensure `main` and `origin/main` point at the intended freeze commit
- ensure all paper-facing bundles have:
  - `experiment_manifest.json`
  - `official_scoreboard.json`
  - `toolclaw_diagnostics.json`
  - `claim_summary.json`
  - `report.md`
  - `latest_run_report.md`
- ensure no paper-facing BFCL bundle depends on `/tmp/...` inputs
- ensure the final claim wording in [configs/paper_claim_matrix.yaml](../configs/paper_claim_matrix.yaml) matches the frozen evidence level
