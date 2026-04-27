# ToolSandbox Reuse V3 Pilot - 2026-04-27

## Verdict

Reuse v3 advanced from a static candidate pool to a pilot-confirmed final source, and the exact-scope admission fix now passes the final-source smoke safety gate. This is still not paper evidence: reuse v3 remains pending until a 3-run formal passes the same gates.

## Source And Pilot

- source frozen export: `data/toolsandbox.official_core_reproducible.frozen.json`
- static candidates: 190 families
- pilot source: 59 families
- pilot source composition: 39 exact, 12 no-headroom controls, 8 transfer controls
- original pilot run: one run at `outputs/paper_suite/toolsandbox_reuse_persistent_v3_pilot`
- exact-scope fixed pilot run: one run at `outputs/paper_suite/toolsandbox_reuse_persistent_v3_pilot_exact_scope_fix`
- registry preflight: passed
- exact-scope admission: runtime filters now require `reuse_mode == exact_reuse` and `source_reuse_family_id == target_family_id`

## Final Source Generated From Pilot

- final source: `data/toolsandbox_reuse_persistent_v3.jsonl`
- final families: 38
- pilot-confirmed exact families: 18
- no-headroom controls: 12
- transfer controls: 8
- `statistical_claim_allowed`: true at the source-size gate

## Final-Source Smoke

- blocked smoke outdir: `outputs/paper_suite/toolsandbox_reuse_persistent_v3_smoke`
- exact-scope fixed smoke outdir: `outputs/paper_suite/toolsandbox_reuse_persistent_v3_smoke_exact_scope_fix`
- family count: 38
- primary exact families: 18
- warm exact reuse hit rate: 1.0
- warm exact correct-source match rate: 1.0
- headroom pair count: 18
- headroom filter passed: true
- mean tool-call reduction: 1.0
- warm success >= cold success: true
- sham false-positive rate: 0.0
- sham exact reuse hit rate: 0.0
- sham transfer reuse hit rate: 0.0
- gate failures: none in the 1-run smoke
- `paper_safe_reuse_evidence`: true for the 1-run smoke only
- `strong_second_run_claim_supported`: true for the 1-run smoke only

## Sham False-Positive Diagnosis

The blocked smoke exposed exact-mode source-family mismatches, not a valid exact reuse signal:

- blocked smoke sham row count: 38
- blocked smoke sham reuse hits after audit: 18
- blocked smoke bucket: `exact_source_mismatch_false_positive`
- fixed smoke sham row count: 38
- fixed smoke sham reuse hits: 0

The fix is admission-side, not scorer-side: exact-scope runtime admission rejects matches unless the selected asset is `exact_reuse` from the target family. Transfer or broad reuse remains a no-op in the exact suite.

## Boundary

Do not promote reuse v3 from this source yet. The pilot and 1-run smoke confirm that exact reuse can hit, reduce tool calls on selected high-headroom families, and pass the sham safety gate after exact-scope admission enforcement. The reuse claim remains pending until the same source passes 3-run formal; this result is a safety-passed pilot/smoke diagnosis, not paper evidence for a reuse cost-reduction claim.
