# ToolSandbox Semantic Repair Official V2 — 2026-04-27

## Verdict

`toolsandbox_semantic_repair_official_v2` refreshes the targeted semantic-repair official slice from the 405-row ToolSandbox core reproducible frozen export. The 3-run formal bundle passes the existing semantic-repair mechanism gates, but this note does not promote or rewrite the paper claim matrix beyond registering the v2 suite for review.

## Source

- Source export: `data/toolsandbox.official_core_reproducible.frozen.json`
- Derived dataset: `data/toolsandbox_semantic_repair_official_v2.jsonl`
- Manifest: `data/toolsandbox_semantic_repair_official_v2.manifest.json`
- Rows: `12`
- Repair-semantic-positive rows: `6`
- Probe-only control rows: `6`
- Trace evidence seed: `outputs/paper_final_freeze_20260423/toolsandbox_interaction_causality_formal/comparison.scored.csv`

The v2 source rows come from the 405-core frozen export. The trace seed remains the prior human-reviewed interaction evidence used to extract oracle replies, decoded signal, target-aligned patch, effective patch, and post-query progress labels for the same task ids.

## Formal Run

- Output bundle: `outputs/paper_suite/toolsandbox_semantic_repair_official_v2`
- Systems: `a2_planner`, `a3_full_interaction`, `a3_no_query`, `a3_noisy_user`
- Runs: `3`
- Scored rows: `144`
- Rows per system: `36`
- Claim summary: `primary_result_ready=true`, `semantic_repair_mechanism_supported=true`, `interaction_not_cheating_supported=true`, `probe_only_success_caveat_present=true`

## Key Metrics

Repair-semantic-positive slice:

| system | rows | strict success | reply usable | target aligned | effective patch | post-query progress | useful round |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a2_planner` | `18` | `0.166667` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| `a3_full_interaction` | `18` | `1.000000` | `0.833333` | `0.833333` | `0.833333` | `0.833333` | `0.833333` |
| `a3_no_query` | `18` | `0.166667` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| `a3_noisy_user` | `18` | `0.166667` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |

Paired repair-semantic-positive deltas:

| comparison | wins | losses | ties | mean delta |
| --- | ---: | ---: | ---: | ---: |
| `a3_full_interaction - a2_planner` | `15` | `0` | `3` | `0.833333` |
| `a3_full_interaction - a3_no_query` | `15` | `0` | `3` | `0.833333` |
| `a3_full_interaction - a3_noisy_user` | `15` | `0` | `3` | `0.833333` |

Probe-only controls remain caveats: `a3_full_interaction` and `a3_noisy_user` can reach strict success on probe-only rows, but usefulness/patch/progress metrics remain `0.000000`.

## Boundary

This is a targeted semantic-repair mechanism refresh on a small official-derived slice. It should not be interpreted as a whole-ToolSandbox headline, a planner claim, or a reuse claim. Claim promotion from v1 to v2 should be a separate claim-boundary update after review.
