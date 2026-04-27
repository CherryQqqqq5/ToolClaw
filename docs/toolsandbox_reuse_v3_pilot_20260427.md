# ToolSandbox Reuse V3 Pilot - 2026-04-27

## Verdict

Reuse v3 advanced from a static candidate pool to a pilot-confirmed final source, but it is not paper evidence. The final-source smoke fails the safety gate because sham reuse false positives remain uncontrolled.

## Source And Pilot

- source frozen export: `data/toolsandbox.official_core_reproducible.frozen.json`
- static candidates: 190 families
- pilot source: 59 families
- pilot source composition: 39 exact, 12 no-headroom controls, 8 transfer controls
- pilot run: one run at `outputs/paper_suite/toolsandbox_reuse_persistent_v3_pilot`
- registry preflight: passed

## Final Source Generated From Pilot

- final source: `data/toolsandbox_reuse_persistent_v3.jsonl`
- final families: 38
- pilot-confirmed exact families: 18
- no-headroom controls: 12
- transfer controls: 8
- `statistical_claim_allowed`: true at the source-size gate

## Final-Source Smoke

- smoke outdir: `outputs/paper_suite/toolsandbox_reuse_persistent_v3_smoke`
- family count: 38
- primary exact families: 18
- warm exact reuse hit rate: 1.0
- warm exact correct-source match rate: 1.0
- headroom pair count: 18
- headroom filter passed: true
- mean tool-call reduction: 1.0
- warm success >= cold success: true
- sham false-positive rate: 1.0
- gate failures: `sham_false_positive_rate_above_0.05`

## Boundary

Do not run reuse v3 3-run formal from this source yet. The pilot confirms that exact reuse can hit and reduce tool calls on selected high-headroom families, but sham false positives are uncontrolled. The reuse claim remains pending; this result is a safety-blocked pilot diagnosis, not evidence for a paper-safe reuse cost-reduction claim.
