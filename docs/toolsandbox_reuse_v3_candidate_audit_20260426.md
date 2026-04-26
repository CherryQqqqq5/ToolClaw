# ToolSandbox Reuse V3 Candidate Rejection Audit (2026-04-26)

## Summary

This audit diagnoses the reuse v3 evidence-generation funnel. It is not benchmark evidence and does not promote the reuse claim.

- inventory scenarios: `1032`
- frozen export rows: `88`
- matched frozen rows: `88`
- candidate families: `34`
- potential exact candidates: `7`
- no-headroom controls: `26`
- transfer controls: `1`
- final formal families: `0`
- formal source status: `awaiting_pilot_confirmation`

## Rejection Buckets

| bucket | count |
| --- | ---: |
| `inventory_not_in_frozen_export` | 944 |
| `external_api_only_no_trace` | 510 |
| `insufficient_paired_frozen_evidence` | 43 |
| `rejected_no_exact_signature` | 0 |
| `rejected_toolset_mismatch` | 1 |
| `rejected_no_headroom_static` | 26 |
| `transfer_only` | 1 |
| `awaiting_pilot` | 7 |
| `missing_success_run_evidence` | 0 |
| `final_source_empty_pending_pilot` | 1 |

## Gate Gaps

| gate | value |
| --- | ---: |
| `target_family_count` | 20 |
| `target_exact_claim_family_count` | 12 |
| `target_headroom_candidate_count` | 10 |
| `final_exact_claim_family_gap` | 12 |
| `potential_exact_candidate_gap_before_pilot` | 5 |
| `pilot_confirmed_headroom_gap` | 10 |

## Interpretation

The v3 runner/scorer pipeline is ready for separated exact/control evidence, but the current frozen export is too small to produce enough pilot-confirmed primary exact families. The immediate bottleneck is evidence source coverage and pilot confirmation, not reuse runtime behavior.

Recommended next step: generate a core reproducible official-run export, re-derive v3 candidates, then run a one-run pilot before any formal reuse experiment.

## Claim Boundary

- Candidate inventory is not evidence.
- Final v3 source remains pending while pilot-confirmed family count is zero.
- No reuse claim should be marked supported from this audit.
