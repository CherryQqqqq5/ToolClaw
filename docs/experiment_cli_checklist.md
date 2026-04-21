# Clean Experiment CLI Checklist (Paper-Useful)

This checklist defines a clean, reproducible experiment workspace so every run maps to paper claims.

## 1) Clean workspace layout

- manifest: `data/experiments/paper_clean_v1/manifests/experiment_manifest.json`
- run outputs: `outputs/paper_clean_v1/`
- reusable assets: `outputs/paper_clean_v1/asset_registry/`
- run logs: `logs/paper_clean_v1/`

## 2) Data-source guardrail

- If `data/external/ToolSandbox/data/**/result_summary.json` is missing, ToolSandbox formal runs may fall back to bundled core data.
- Fallback/core runs are valid for mechanism claims and ablations.
- Any "official" claim must be backed by an official run export with `result_summary.json`.
- BFCL headline runs must not use `data/bfcl/manifest.json` scaffold data.
- BFCL `fc_core` headline runs must resolve to the tracked formal source manifest or tracked formal lock artifact and must produce:
  - `official_scoreboard.json`
  - `toolclaw_diagnostics.json`
  - `claim_summary.json`
- Until that formal BFCL bundle is frozen, BFCL should be described as protocol/readiness plus small-probe connectivity, not completed paper evidence.

## 3) Experiment order (locked)

1. `exp01_toolsandbox_core_a0_a4` (P0)
2. ToolSandbox failtax/focused/reuse summaries (P0 follow-up analysis)
3. `exp02_tau_a0_a4` and `exp03_tau2_a0_a4` (P1)
4. `exp04_bfcl_fc_core` (P2 headline planner/binder protocol)
5. `exp05_bfcl_agentic_ext` (supporting-only appendix protocol)
6. robustness and budget sweeps (P2)
7. TRAJECT-Bench (optional diagnostic extension)

## 4) First experiment command

Run the first P0 experiment from repo root:

```bash
scripts/run_toolsandbox_formal.sh \
  --refresh \
  --num-runs 3 \
  --outdir outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4 \
  --asset-registry-root outputs/paper_clean_v1/asset_registry/exp01 \
  --keep-normalized-taskset
```

## 5) Expected output artifacts

At minimum, keep these files for writeup:

- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/scoreboard.json`
- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/per_system_summary.json`
- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/per_category_summary.json`
- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/per_failtax_summary.json`
- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/focused_slice_summary.json`
- `outputs/paper_clean_v1/exp01_toolsandbox_core_a0_a4/runs/run_01/comparison.csv`
