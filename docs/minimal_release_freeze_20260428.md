# Minimal Release Freeze 2026-04-28

This file defines the current release/refactor target. It is a risk-control
document, not a new claim source.

## Release Entries

| Role | Claim Boundary | Dataset Entry | Runner | Required Kept Artifacts |
| --- | --- | --- | --- | --- |
| ToolSandbox headline/boundary | Full-core strict is boundary/contract validation; do not claim broad planner/reuse/LLM-interaction lift without current evidence. | `data/toolsandbox.official_core_reproducible.frozen.json` | `scripts/run_toolsandbox_bench.py` | manifest, scoreboard, per-system summary, claim summary, concise report |
| Planner mechanism | Planner-sensitive heldout only; mechanism evidence, not broad ToolSandbox/BFCL headline. | `data/toolsandbox_planner_sensitive_v2_heldout.jsonl` | `scripts/run_toolsandbox_bench.py` | manifest, scoreboard, structure audit, report |
| Reuse mechanism | Exact-match continuation cost/no-regression under matched signatures. Do not claim `s4 > s3` full-core success. | VCR/reuse exact-match frozen source from claim matrix | `scripts/run_toolsandbox_vcr_frozen_suite.py` | manifest, cost summary, no-regression controls, report |
| BFCL grounding | Separate function-calling grounding/repair slice. Do not blend into ToolSandbox workflow headline. | `data/bfcl_slices/grounding_delta_cases_v1.jsonl` and companion manifests | BFCL formal runner/score scripts from claim matrix | manifest, official scoreboard, diagnostics, claim summary |

## Artifact Policy

Keep in git:

- source code, tests, configs, and documentation
- small frozen datasets required to reproduce paper-facing claims
- manifests, scoreboards, claim summaries, and concise reports

Keep outside git, referenced by manifest:

- full traces
- raw logs
- repeated run directories
- large vendored benchmark exports
- exploratory outputs not bound to a release entry

Existing tracked artifacts should be migrated in a dedicated pruning change.
Do not mix artifact deletion with algorithm, runner, or scorer changes.

## Interface Freeze

The following interfaces are frozen for paper-facing runs unless a release note
explicitly revs them:

- system ladder names and their mapping to legacy `a0`-`a4`
- planner admission decision schema
- benchmark sample -> workflow construction entry points in `scripts/run_eval.py`
- benchmark score row fields used by the claim matrix
- reuse artifact compatibility metadata

## Claim Downgrades

Forbidden until separately re-established:

- broad full-core LLM interaction lift
- broad full-core planner lift
- broad full-core reuse lift over interaction
- transfer-reuse headline claims
- BFCL as proof of ToolSandbox workflow intelligence

Allowed:

- ToolSandbox full-core boundary/contract validation
- planner-sensitive mechanism evidence
- exact-match reuse cost/no-regression evidence
- BFCL grounding evidence as a separate benchmark line
