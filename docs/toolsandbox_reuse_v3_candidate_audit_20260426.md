# ToolSandbox Reuse V3 Candidate Rejection Audit (2026-04-26)

## Summary

This audit diagnoses the reuse v3 evidence-generation funnel. It is not benchmark evidence and does not promote the reuse claim.

- inventory scenarios: `1032`
- frozen export rows: `405`
- matched frozen rows: `405`
- candidate families: `190`
- potential exact candidates: `39`
- no-headroom controls: `135`
- transfer controls: `16`
- final formal families: `0`
- formal source status: `awaiting_pilot_confirmation`

## Rejection Buckets

| bucket | count |
| --- | ---: |
| `inventory_not_in_frozen_export` | 627 |
| `external_api_only_no_trace` | 523 |
| `insufficient_paired_frozen_evidence` | 113 |
| `rejected_no_exact_signature` | 0 |
| `rejected_toolset_mismatch` | 16 |
| `rejected_no_headroom_static` | 135 |
| `transfer_only` | 16 |
| `awaiting_pilot` | 39 |
| `missing_success_run_evidence` | 0 |
| `final_source_empty_pending_pilot` | 1 |

## Gate Gaps

| gate | value |
| --- | ---: |
| `target_family_count` | 20 |
| `target_exact_claim_family_count` | 12 |
| `target_headroom_candidate_count` | 10 |
| `final_exact_claim_family_gap` | 12 |
| `potential_exact_candidate_gap_before_pilot` | 0 |
| `pilot_confirmed_headroom_gap` | 10 |

## Interpretation

The v3 runner/scorer pipeline is ready for separated exact/control evidence, but the current candidates still require pilot-confirmed primary exact headroom families before any claim. The immediate bottleneck is pilot confirmation and exact high-headroom selection, not reuse runtime behavior.

Recommended next step: run a one-run pilot on the core-derived candidates, promote only pilot-confirmed exact high-headroom families into the final source, then consider any formal reuse experiment.

## Claim Boundary

- Candidate inventory is not evidence.
- Final v3 source remains pending while pilot-confirmed family count is zero.
- No reuse claim should be marked supported from this audit.
