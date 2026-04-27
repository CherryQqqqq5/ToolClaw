# ToolSandbox Final Response Synthesis V1 - 2026-04-27

## Verdict

Generic final response synthesis is implemented as a gold-free finalization signal. It writes a runtime-visible `final_response_synthesized` event before successful stop events and mirrors the response into `evt_stop_success.output.final_response`.

The 405-core strict 1-run smoke did not improve strict success. The remaining s4 failures are now explained more precisely: final responses are present, but the multiple-turn / insufficient-information interaction contract remains unsatisfied. The next behavior-changing patch should therefore target generic interaction triggers, not additional final-response templates.

## Source And Run

- Source: `data/toolsandbox.official_core_reproducible.frozen.json`
- Smoke output: `outputs/paper_suite/toolsandbox_official_core_reproducible_final_response_smoke`
- Systems: `s0_baseline`, `s1_recovery`, `s2_planner_overlay`, `s3_interaction_overlay`, `s4_reuse_overlay`
- Runs: `1`
- Samples: `405`
- Scored rows: `2025`

## Scores

| system | strict success | final_response_present rows |
|---|---:|---:|
| s0_baseline | 0.659259 | 386 |
| s1_recovery | 0.703704 | 404 |
| s2_planner_overlay | 0.703704 | 404 |
| s3_interaction_overlay | 0.706173 | 405 |
| s4_reuse_overlay | 0.706173 | 405 |

Adjacent strict regressions remained `0 / 1620`.

## Failure Taxonomy After Synthesis

For `s4_reuse_overlay`:

- failed rows: `119`
- unique failed tasks: `119`
- raw-success / strict-fail rows: `119`
- runtime execution failures: `0`
- final_response_present: `119`
- final_response_absent: `0`
- failure_subcause: `interaction_contract_still_blocked = 119`

The previous `final_response_milestone_gap` diagnosis was therefore narrowed to a contract blocker: finalization text is available, but it is not a substitute for required interaction.

## Boundary

The synthesizer is gold-free. It must not use milestones, reference summaries, official mappings, scorer gold messages, official expected answers, scenario-specific branching, or benchmark-specific tool conditionals.

This patch does not update claim matrix status, BFCL status, reuse v3 evidence, official ToolSandbox artifacts, or paper headline wording.

## Next Step

The appropriate next implementation line is generic interaction trigger expansion for missing required information, ambiguous references, approvals, state confirmation, and typed reply decoding. Final response synthesis should remain a finalization signal and should not be counted as user interaction.

## Follow-Up Resolution

The subsequent generic interaction probe V1 patch admitted strict `s3_` and `s4_` runs to the same generic post-success interaction probe path used by atomic interaction systems. In 3-run formal, `s3_interaction_overlay` and `s4_reuse_overlay` reached `1.000000` strict success with `0 / 4860` adjacent regressions and no remaining `s4` strict failures.

