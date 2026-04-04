# Tau2-Bench In ToolClaw

This repo now includes a tau2-style interaction benchmark runner:

```bash
python3 scripts/run_tau2_bench.py
```

By default it uses the local smoke dataset:

- `data/tau2_bench.sample.json`

You can also provide a custom source:

```bash
python3 scripts/run_tau2_bench.py \
  --source path/to/tau2_like.jsonl \
  --outdir outputs/tau2_bench \
  --mode planner \
  --systems baseline,toolclaw_lite \
  --num-runs 3
```

## Accepted Source Shape

Recommended fields per sample:

- `sample_id`
- `scenario`
- `query`
- `simulated_policy`
- `backup_tool_map`
- `candidate_tools`
- `expected_user_turns`
- `expected_repairs`

## Outputs

The runner reuses `scripts/run_eval.py` for trace generation, then writes tau2-oriented summaries:

- `comparison.csv`
- `report.md`
- `scoreboard.json`
- `per_system_summary.json`
- `per_system_summary.md`
- `prepared/tau2_bench.normalized.json`

## Current Focus

This harness is aimed at interaction-centric failure slices such as:

- `binding_failure`
- `environment_failure`
- `approval_required`
- `policy_failure`
- `dual_control`

The primary metrics are:

- `interactive_correction`
- `interaction_efficiency`
- `repair_salvage`
- `repair_efficiency`
