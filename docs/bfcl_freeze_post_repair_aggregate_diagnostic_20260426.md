# BFCL Freeze Post-Repair Aggregate Diagnostic (2026-04-26)

## Summary

This note freezes the current BFCL adapter-repair line at commit `9d79d95`. The post-repair aggregate diagnostic was run from a temporary filtered source, not the formal `bfcl_fc_core` paper suite. BFCL remains a limitation / boundary diagnostic: the aggregate still fails the hard success gate, so no claim matrix, paper docs, or headline claim should be updated from this result.

Temporary run root:

```text
/tmp/toolclaw_bfcl_freeze_aggregate_20260426T021235Z/out
```

Filtered source composition:

```text
live:serial rows:      2,211
non_live:serial rows:    840
total tasks:           3,051
systems:               a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse
```

## Freeze Decision

Stop BFCL per-tool runtime repair after the current adapter state:

```text
completed targeted repairs / diagnostics:
- wrong-function regression guard
- candidate visibility and selected-correct diagnostics
- live-serial irrelevance no-call abstention
- schema-driven location/unit/date grounding
- schema-driven command grounding
- movie search argument audit

not continuing now:
- Movies_3_FindMovies runtime grounding
- requests.get runtime grounding
- further per-tool BFCL offender chasing
```

Rationale: weather/location and command repairs are schema-driven and gold-free, but continuing `weather -> command -> movies -> requests.get -> ...` would move the BFCL line from adapter repair into benchmark-offender tuning. BFCL should remain an exact function-calling boundary diagnostic, not a primary ToolClaw claim target.

## Aggregate Results

Official success on the filtered aggregate remains below baseline for `a2_planner`:

```text
a0_baseline official success: 0.458866
a1_recovery official success: 0.458866
a2_planner  official success: 0.451327
a3_interaction official success: 0.452311
a4_reuse official success: 0.452311
```

Hard gates on this filtered diagnostic:

```text
a2_wrong_func_name_le_a0 = true
a2_tool_selection_ge_a0 = true
a2_success_ge_a0 = false
a2_missing_required_lt_a0 = false
```

No-call / over-abstention controls:

```text
live_irrelevance tool_calls=0: 884/884 rows for each system
selected-correct live:serial expected>0 emitted=0: 0 rows
```

Targeted repair signals remain visible:

```text
get_current_weather::live:serial
selected=90, success=25, wrong_call_count=0, wrong_arg_value=50, missing_required=15

Weather_1_GetWeather::live:serial
selected=80, success=40, wrong_arg_value=25, missing_required=15

cmd_controller.execute::live:serial
selected=90, success=25, wrong_arg_value=40, missing_required=20, wrong_arg_type=5
split: dev success=15/45, heldout success=10/45
```

Current top selected-correct offenders after the freeze aggregate:

```text
Movies_3_FindMovies::live:serial failures=75 dominant=missing_required
cmd_controller.execute::live:serial failures=65 dominant=wrong_arg_value
get_current_weather::live:serial failures=65 dominant=wrong_arg_value
requests.get::live:serial failures=55 dominant=wrong_arg_structure
ThinQ_Connect::live:serial failures=45 dominant=wrong_arg_structure
```

Movies audit localizes the next possible repair target but does not justify another runtime patch now:

```text
Movies_3_FindMovies::live:serial
selected=90, success=15, missing_required=40, wrong_arg_value=35
argument failures: cast=80, directed_by=75, genre=25
value_filtered_count=50
split: dev success=0/30, heldout success=15/60
```

## Interpretation

The accumulated BFCL adapter repairs are useful diagnostic progress, but they do not make BFCL claim-ready. The remaining failures are selected-correct argument/value/structure failures and tool-specific schema semantics, not function-selection or trace-serialization failures.

BFCL should be reported as a boundary condition: ToolClaw workflow-level planning and interaction benefits do not automatically transfer to exact BFCL function-call argument and call-shape correctness. The next project effort should shift back to higher-value claim lines: planner F2 held-out robustness, semantic repair expansion, and reuse formalization.

## Artifact Policy

The `/tmp` aggregate artifacts are intentionally not committed. This note records only the freeze decision and compact diagnostic results. No full `bfcl_fc_core` rerun was performed, and no claim matrix or paper claim documents were changed.
