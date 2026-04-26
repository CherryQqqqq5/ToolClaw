# ToolSandbox Core Strict Ladder Formal — 2026-04-26

## Verdict

The strict `s0-s4` ladder passed the 3-run formal non-regression check on the executed ToolSandbox core reproducible frozen export. The result supports primary-success adjacent non-regression for the strict ladder only; it does not promote planner overlay or reuse overlay to broad independent improvement claims.

## Source

- Frozen source: `data/toolsandbox.official_core_reproducible.frozen.json`
- Frozen manifest: `data/toolsandbox.official_core_reproducible.frozen.manifest.json`
- Official scenario inventory entries: `1032`
- Eligible core reproducible scenarios: `405`
- Attempted scenarios: `405`
- Export rows: `405`
- Trajectories: `405`
- `result_summary` scenario count: `405`
- Failed scenarios: `0`
- External/RapidAPI primary exclusions: `523`
- Missing-milestone primary exclusions: `104`
- Exclusion reason counts are multi-label diagnostics; primary exclusion counts are mutually exclusive.

## Provenance

- ToolClaw commit for strict ladder code: `b82cf4e0062d654dd841d94439840a3119306058`
- Official ToolSandbox commit: `165848b9a78cead7ca7fe7c89c688b58e6501219`
- ToolSandbox source includes an intentional local OpenRouter client patch under `data/external/ToolSandbox`; this patch is execution provenance and is not part of the strict ladder code commit.
- ToolSandbox Python: `/cephfs/qiuyn/venvs/toolsandbox-py310/bin/python` (`3.10.20`)
- ToolSandbox runtime Python: `/cephfs/qiuyn/venvs/toolsandbox-official-py310/bin/python` (`3.10.20`)
- ToolClaw Python: `/usr/bin/python3` (`3.8.10`)
- `networkx`: `3.2.1`
- OpenRouter-compatible endpoint configured: yes
- API key recorded in artifacts: no

## Formal Command

```bash
PYTHONPATH=src python3 scripts/run_toolsandbox_bench.py \
  --source data/toolsandbox.official_core_reproducible.frozen.json \
  --outdir outputs/paper_suite/toolsandbox_official_core_reproducible_strict \
  --systems s0_baseline,s1_recovery,s2_planner_overlay,s3_interaction_overlay,s4_reuse_overlay \
  --num-runs 3
```

## Formal Outputs

- Scoreboard: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict/scoreboard.json`
- Per-system summary: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict/per_system_summary.json`
- Scored rows: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict/comparison.scored.csv`
- Monotonicity audit: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict/strict_layer_monotonicity_audit.json`
- Monotonicity audit note: `outputs/paper_suite/toolsandbox_official_core_reproducible_strict/strict_layer_monotonicity_audit.md`

## Formal Metrics

- Samples: `405`
- Runs: `3`
- Scored rows: `6075`
- Rows per strict system: `1215`
- Adjacent comparisons: `4860`
- Adjacent primary-success regressions: `0`

| System | Strict success | Execution-verified success | Mean user queries |
| --- | ---: | ---: | ---: |
| `s0_baseline` | `0.659259` | `0.953086` | `0.000000` |
| `s1_recovery` | `0.703704` | `0.997531` | `0.000000` |
| `s2_planner_overlay` | `0.703704` | `0.997531` | `0.000000` |
| `s3_interaction_overlay` | `0.706173` | `1.000000` | `0.002469` |
| `s4_reuse_overlay` | `0.706173` | `1.000000` | `0.002469` |

| Adjacent check | Wins | Losses | Ties | Comparisons |
| --- | ---: | ---: | ---: | ---: |
| `s1_recovery >= s0_baseline` | `54` | `0` | `1161` | `1215` |
| `s2_planner_overlay >= s1_recovery` | `0` | `0` | `1215` | `1215` |
| `s3_interaction_overlay >= s2_planner_overlay` | `3` | `0` | `1212` | `1215` |
| `s4_reuse_overlay >= s3_interaction_overlay` | `0` | `0` | `1215` | `1215` |

Coverage checks remained complete: result-summary coverage, milestone-signal coverage, and reference-summary coverage were all `1.0` for every strict system.

## Boundary

This formal run supports a narrow strict-ladder claim: primary success does not regress when moving from baseline to recovery, planner overlay, interaction overlay, and reuse overlay on the 405-row ToolSandbox core reproducible frozen export.

It does not show that planner overlay broadly improves ToolSandbox core: `s2_planner_overlay` tied `s1_recovery` on strict success. It does not show that reuse overlay improves ToolSandbox core or reduces cost: `s4_reuse_overlay` tied `s3_interaction_overlay` on strict success and user queries. Cost, tool-call, and user-turn metrics are reported diagnostics, not acceptance criteria for this result.

Evidence roles remain separate: atomic `a0-a4` systems retain mechanism-diagnostic semantics, planner-sensitive F2/held-out remains the HTGP structural mechanism evidence, reuse v3 remains future matched-signature cost-reduction evidence, and BFCL remains a frozen boundary/limitation diagnostic.
