# BFCL Grounding Repair Update (2026-04-22)

## What changed

This repair pass focused on the **selection-to-execution grounding gap** without adding BFCL-specific heuristics into the shared executor.

Implemented changes:

- BFCL shaping now **merges** generic grounding metadata instead of overwriting it.
- `repair_default_inputs` is recomputed from final step inputs after shaping.
- Recovery now patches **all recoverable unresolved required inputs** in one pass.
- Required inputs are no longer patched with placeholder values such as `auto_filled_value`.
- Repair now refreshes:
  - `repair_default_inputs`
  - `unresolved_required_inputs`
  - `grounding_sources`
  - `grounding_confidence`
- BFCL no-tool tasks now enforce a hard abstain invariant:
  - empty candidate tool space
  - `bfcl_abstained = true`
  - empty execution plan
- Diagnostics now include:
  - `repair_applied_count`
  - `repair_success_count`
- BFCL runtime extraction was strengthened for:
  - concrete `loc` extraction
  - search/news keyword extraction
  - appliance command extraction
  - arithmetic `a/b` extraction
  - explicit news intent routing (`뉴스` / news queries prefer `HNA_NEWS.search`)

## Focused smoke results

Result bundle:
- [outputs/bfcl_grounding_fix_smoke_v4/official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_smoke_v4/official_scoreboard.json)
- [outputs/bfcl_grounding_fix_smoke_v4/toolclaw_diagnostics.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_smoke_v4/toolclaw_diagnostics.json)
- [outputs/bfcl_grounding_fix_smoke_v4/claim_summary.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_smoke_v4/claim_summary.json)

Official success:

- `a0_baseline = 0.8182`
- `fc_preflight_only = 0.1818`
- `fc_grounding_recovery = 0.8182`
- `a4_reuse = 0.8182`

Key interpretation:

- `fc_preflight_only` still shows the intended causal gap: correct-ish tool choice is frequently blocked by schema-aware preflight.
- `fc_grounding_recovery` and `a4_reuse` recover to baseline-level success.
- The earlier no-tool regression is gone.

## Targeted news-routing validation

Result bundle:
- [outputs/bfcl_grounding_news_fix_smoke/official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_news_fix_smoke/official_scoreboard.json)

This smoke specifically included:

- `live_irrelevance_120-9-0`
- `live_multiple_3-2-0`
- `live_multiple_16-4-8`

Official success:

- `a0_baseline = 1.0`
- `fc_preflight_only = 0.3333`
- `fc_grounding_recovery = 1.0`
- `a4_reuse = 1.0`

Important consequence:

- The last remaining medium-slice mismatch caused by `HNA_WQA.search` vs `HNA_NEWS.search` on explicit news queries was removed.

## Medium repair validation

Latest credible medium bundle:

- [outputs/bfcl_grounding_fix_medium_v4/official_scoreboard.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_medium_v4/official_scoreboard.json)
- [outputs/bfcl_grounding_fix_medium_v4/toolclaw_diagnostics.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_medium_v4/toolclaw_diagnostics.json)
- [outputs/bfcl_grounding_fix_medium_v4/claim_summary.json](/Users/cherry/mnt/ToolClaw/outputs/bfcl_grounding_fix_medium_v4/claim_summary.json)

Official success:

- `a0_baseline = 0.4375`
- `fc_preflight_only = 0.0625`
- `fc_grounding_recovery = 0.4375`
- `a4_reuse = 0.4375`

Official selection / structure:

- `a0_baseline`
  - tool selection `0.6250`
  - structure `0.6250`
- `fc_grounding_recovery`
  - tool selection `0.6563`
  - structure `0.6563`
- `a4_reuse`
  - tool selection `0.6563`
  - structure `0.6563`

Diagnostics:

- `fc_preflight_only`
  - `missing_required_arg_rate = 0.8125`
  - `preflight_interception_rate = 0.8125`
  - `exec_verified = 0.1875`
- `fc_grounding_recovery`
  - `missing_required_arg_rate = 0.1979`
  - `preflight_interception_rate = 0.2188`
  - `repair_success_rate = 0.0313`
  - `repair_applied_count = 0.2188`
  - `repair_success_count = 0.0313`
  - `exec_verified = 0.7813`
- `a4_reuse`
  - same as `fc_grounding_recovery` on this slice

Triggered-preflight slice:

- `a0_baseline success = 0.4000`
- `fc_preflight_only success = 0.0000`
- `fc_grounding_recovery success = 0.4000`
- `a4_reuse success = 0.4000`

Key interpretation:

- Grounding repair now cleanly closes the worst preflight-only failure mode on the targeted slice.
- On the repaired medium slice, the grounded arms are no longer below baseline.
- However, they still do **not** exceed baseline on official success.

## What can be claimed now

Stronger, supportable statement:

> ToolClaw’s Core Grounding V1 now closes the most obvious selection-to-execution gap on required-arg-sensitive BFCL slices: preflight-only ablations fail heavily, while grounded arms recover to baseline-level executable performance and improve tool-selection/structure quality.

What is **not** yet supportable:

- A headline claim that grounding repair already yields a large net top-line BFCL lift over baseline.
- A claim that repair alone is the dominant source of BFCL headline gain.

## Why there was no full rerun tonight

The latest medium slice is now **stable and clean**, but it only brings `fc_grounding_recovery` back to baseline-level success rather than above it.

That is enough for a report update about:

- the mechanism fix
- the causal ablation
- the removal of regressions
- the improvement of selection/structure metrics

It is **not** yet enough to justify a fresh full BFCL rerun if the only goal is to maximize headline success before the report.

## Recommended report framing

Use this wording:

> We implemented a core grounding repair pass that preserves binder-generated grounding metadata, enforces schema-aware preflight, removes placeholder-value repairs, and keeps no-tool BFCL tasks on a strict abstain path. On targeted BFCL slices, the preflight-only ablation collapses, while grounding-recovery and full ToolClaw recover to baseline-level success and improve tool-selection/structure quality. The remaining bottleneck is no longer the basic grounding path itself, but converting those execution-quality gains into a net headline lift over the baseline arm.
