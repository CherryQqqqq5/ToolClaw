# ToolSandbox Generic Interaction Probe V1 - 2026-04-27

## Verdict

Generic interaction probe coverage was extended to the strict ladder systems. The existing post-success interaction probe already handled atomic `a3_` and `a4_` runs, but strict `s3_` and `s4_` runs were not admitted to the same generic probe path.

This was a ladder wiring gap, not a ToolSandbox task patch: the probe remains driven by generic interaction categories and task-family metadata, and it does not branch on scenario names, benchmark tool identifiers, milestones, or scorer gold.

## Source And Run

- Source: `data/toolsandbox.official_core_reproducible.frozen.json`
- Smoke output: `outputs/paper_suite/toolsandbox_official_core_reproducible_interaction_probe_smoke`
- Systems: `s0_baseline`, `s1_recovery`, `s2_planner_overlay`, `s3_interaction_overlay`, `s4_reuse_overlay`
- Runs: `1`
- Samples: `405`
- Scored rows: `2025`

## Scores

| system | strict success | user queries | final_response_present rows |
|---|---:|---:|---:|
| s0_baseline | 0.659259 | 0 | 386 |
| s1_recovery | 0.703704 | 0 | 404 |
| s2_planner_overlay | 0.703704 | 0 | 404 |
| s3_interaction_overlay | 1.000000 | 120 | 405 |
| s4_reuse_overlay | 1.000000 | 120 | 405 |

Adjacent strict regressions remained `0 / 1620`.

## Before/After

Before this probe wiring fix, the final-response smoke showed:

- `s3_interaction_overlay = 0.706173`
- `s4_reuse_overlay = 0.706173`
- `s4` failed rows: `119`
- failure subcause: `interaction_contract_still_blocked = 119`

After admitting strict interaction systems to the same generic probe path:

- `s3_interaction_overlay = 1.000000`
- `s4_reuse_overlay = 1.000000`
- `s4` failed rows: `0`
- unique failed tasks: `0`
- raw-success / strict-fail rows: `0`

## Boundary

This is an execution-layer performance fix for the strict ladder. It does not promote a new claim by itself and does not change BFCL, reuse v3, official ToolSandbox artifacts, or the claim matrix.

The interaction probe is still a generic mechanism. It may be used for multiple-turn or insufficient-information tasks, but it must not use milestones, reference summaries, official mappings, scorer gold messages, official expected answers, scenario-specific branching, or benchmark-specific tool conditionals.

## Next Step

Run a 3-run strict formal only after reviewing this smoke and confirming that the stricter interaction probe remains regression-free across repeated runs. If the formal result holds, update the strict ladder formal note and claim boundary separately.

## 3-Run Formal

Formal output: `outputs/paper_suite/toolsandbox_official_core_reproducible_interaction_probe_formal`.

- Runs: `3`
- Samples per run: `405`
- Scored rows: `6075`
- Adjacent strict regressions: `0 / 4860`
- `s4` failed rows: `0`
- `s4` unique failed tasks: `0`

| system | scored rows | strict successes | strict success | user queries | final_response_present rows |
|---|---:|---:|---:|---:|---:|
| s0_baseline | 1215 | 801 | 0.659259 | 0 | 1158 |
| s1_recovery | 1215 | 855 | 0.703704 | 0 | 1212 |
| s2_planner_overlay | 1215 | 855 | 0.703704 | 0 | 1212 |
| s3_interaction_overlay | 1215 | 1215 | 1.000000 | 360 | 1215 |
| s4_reuse_overlay | 1215 | 1215 | 1.000000 | 360 | 1215 |

The formal taxonomy reports no remaining `s4` strict failures. This confirms that the previous raw-success / strict-fail gap was the strict interaction probe admission gap, not a need for task-specific response templates.

