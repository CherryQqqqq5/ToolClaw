# ToolSandbox Layered Monotonicity Fix Report

## Scope

This report documents the A0-A4 layering fix for the 14-sample ToolSandbox core slice in `data/toolsandbox.formal.json`.

Goals:

- make `a1_recovery` operationally equal to `a0_baseline + recovery`
- make `a4_reuse` operationally equal to `a3_interaction + reuse + compile_on_success`
- make approval interactions emit scorer-visible trace events so `a3/a4` no longer diverge due to missing interaction-contract evidence

## Code Changes

Files updated:

- `scripts/run_eval.py`
- `src/toolclaw/interaction/irc.py`
- `src/toolclaw/benchmarks/adapters.py`
- `tests/test_eval_script.py`
- `tests/test_irc.py`
- `tests/test_toolsandbox_adapter.py`

Key changes:

- `a0_baseline` now runs through the same `executor` branch as `a1_recovery`, with `allow_repair=False` and `allow_fallback=False`.
- `a1_recovery` remains the same demo-workflow executor path, but with recovery enabled.
- `a4_reuse` now passes `compile_on_success=True` through the same interaction shell path as `a3_interaction`, including reuse rollback fallback.
- ToolSandbox approval interactions now emit explicit `approval_request` and `approval_response` trace events in addition to `user_query` and `user_reply`.
- ToolSandbox scoring now:
  - accepts approval events as valid interaction-contract evidence
  - keeps `execution_verified_success` separate from the stricter interaction-gated `strict_scored_success`

## Validation

Targeted validation was run directly in the mounted server repo with Python assertions covering:

- layered A0-A4 spec semantics
- `a0_baseline` executor-path behavior
- `a4_reuse` compile-on-success preservation across reuse rollback
- approval trace event emission
- ToolSandbox adapter contract scoring and execution-vs-strict separation

## Experiment Runs

Smoke run:

- `outputs/toolsandbox_layered_monotonicity_smoke_20260423`

Formal 3-run:

- `outputs/toolsandbox_layered_monotonicity_r3_20260423`

## 3-Run Aggregate Results

Per-system success:

- `a0_baseline = 0.2143`
- `a1_recovery = 0.3571`
- `a2_planner = 0.4286`
- `a3_interaction = 0.8571`
- `a4_reuse = 0.8571`

Task-level monotonicity check on scored `success`:

- no `a1_recovery < a0_baseline`
- no `a2_planner < a1_recovery`
- no `a3_interaction < a2_planner`
- no `a4_reuse < a3_interaction`

## Residual Caveats

The layering fix restores monotonic scored success on this 14-sample slice, but it does not make every internal metric monotonic.

Observed residuals:

- `toolsandbox_reuse_transfer_001__pass2` remains a hard failure for `a2/a3/a4`
- `toolsandbox_planner_sensitive_003` still shows `a1_recovery` failing while `a2/a3/a4` succeed
- `toolsandbox_multi_turn_approval_002` no longer shows the old `a4<a3` interaction-contract mismatch, but it still depends on stricter execution-verification semantics

Interpretation:

- the historical `a1<a0` issue on this slice has been removed
- the historical `a4<a3` issue caused by missing interaction-contract trace evidence has been removed
- remaining failures are benchmark/task difficulties, not the old layering or trace-contract bugs
