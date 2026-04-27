# ToolSandbox Reuse V3 Formal - 2026-04-27

## Verdict

Reuse v3 passed the 3-run formal gate for a narrow exact matched-signature second-run cost claim. This is mechanism-supporting evidence for guarded exact reuse on pilot-confirmed high-headroom ToolSandbox core families. It is not evidence for transfer reuse, BFCL reuse lift, broad ToolSandbox `a4 > a3` success, or verifier-backed skill learning.

## Source And Run

- source: `data/toolsandbox_reuse_persistent_v3.jsonl`
- manifest: `data/toolsandbox_reuse_persistent_v3.manifest.json`
- formal outdir: `outputs/paper_suite/toolsandbox_reuse_persistent_v3`
- command log: `outputs/toolclaw_logs/toolsandbox_reuse_persistent_v3_formal_20260427.log`
- ToolClaw commit: `412a817923ed215cda5a8d173fc6c51f8a6bb242`
- reuse scope: `exact`
- runs: 3

## Family Composition

- total formal families: 38
- primary exact/headroom families: 18
- no-headroom controls: 12
- transfer controls: 8
- paired effects: 114
- primary paired effects: 54
- no-headroom paired effects: 36
- transfer-control paired effects: 24

## Primary Exact Claim Metrics

- warm exact reuse hit rate: 1.0
- warm exact correct-source match rate: 1.0
- sham false-positive rate: 0.0
- sham exact reuse hit rate: 0.0
- sham transfer reuse hit rate: 0.0
- headroom filter passed: true
- warm success >= cold success: true
- gate failures: none
- `paper_safe_reuse_evidence`: true
- `strong_second_run_claim_supported`: true

## Cost Effects

- primary warm average tool calls: 1.0
- primary cold average tool calls: 2.0
- primary mean tool-call reduction: 1.0
- primary tool-call paired wins/losses/ties: 54 / 0 / 0
- primary repair-action reduction: 0.0
- primary turn reduction: 0.0
- all-paired tool-call reduction mean: 0.47368421052631576
- all-paired tool-call reduction bootstrap CI: [0.37719298245614036, 0.5701754385964912]
- all-paired tool-call reduction sign test: 54 positive / 0 negative, two-sided p = 1.1102230246251565e-16

## Controls And Safety

- no-headroom controls are reported separately and do not contribute to primary exact claim gates.
- transfer controls are reported separately and do not count as exact claim evidence.
- sham audit rows: 114
- sham reuse hits: 0
- sham exact false positives: 0
- sham transfer false positives: 0

## Boundary

The supported claim is: exact matched-signature reuse reduces second-run tool-call cost on pilot-confirmed high-headroom ToolSandbox core families while preserving success and passing sham safety gates. Do not describe this as broad transfer reuse, general ToolSandbox success lift, BFCL reuse evidence, or cost monotonicity across all metrics.
