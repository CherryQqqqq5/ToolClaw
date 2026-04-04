# ToolSandbox In ToolClaw

This repo now includes a ToolSandbox-style benchmark runner:

```bash
python3 scripts/run_toolsandbox_bench.py
```

Compatibility alias:

```bash
python3 scripts/run_toolsandbox.py
```

If you already ran the vendored official ToolSandbox CLI, you can auto-discover the latest official run directory and feed it into the current ToolClaw runner directly:

```bash
python3 scripts/run_toolsandbox.py \
  --official-run-dir latest \
  --require-result-summary
```

By default it uses the local smoke dataset:

- `data/toolsandbox.sample.json`

You can also provide a custom source:

```bash
python3 scripts/run_toolsandbox_bench.py \
  --source path/to/toolsandbox_like.jsonl \
  --outdir outputs/toolsandbox_bench \
  --mode planner \
  --systems baseline,toolclaw_lite \
  --num-runs 3
```

If later you get raw ToolSandbox-style scenario/result exports, normalize them first:

```bash
python3 scripts/prepare_toolsandbox_source.py \
  --source path/to/raw_toolsandbox.json \
  --result-source path/to/raw_results.jsonl \
  --out data/toolsandbox/toolsandbox.aligned.jsonl
```

Or let the runner do that merge step directly:

```bash
python3 scripts/run_toolsandbox.py \
  --source path/to/raw_toolsandbox.json \
  --result-source path/to/raw_results.jsonl \
  --outdir outputs/toolsandbox_bench \
  --require-result-summary
```

Or extract aligned source from a specific official ToolSandbox run directory:

```bash
python3 scripts/prepare_toolsandbox_official_run.py \
  --run-dir data/external/ToolSandbox/data/<official_run_dir> \
  --out data/toolsandbox/toolsandbox.official.aligned.jsonl
```

If you want a fixed, reproducible formal dataset JSON in the same schema as `data/toolsandbox.formal.json`, build it directly from an official run:

```bash
python3 scripts/prepare_toolsandbox_formal_dataset.py \
  --official-run-dir latest \
  --exclude-augmented \
  --out data/toolsandbox.formal.official.json
```

Then run the benchmark on that frozen dataset:

```bash
python3 scripts/run_toolsandbox.py \
  --source data/toolsandbox.formal.official.json \
  --outdir outputs/toolsandbox_bench_official_formal
```

## Accepted Source Shape

Recommended fields per sample:

- `name` or `sample_id`
- `query` or `messages`
- `tool_allow_list`
- `candidate_tools`
- `categories`
- `milestones`
- `ideal_turn_count`
- `ideal_tool_calls`
- `result_summary` (optional)

## Outputs

The runner reuses `scripts/run_eval.py` for trace generation, then writes ToolSandbox-oriented summaries:

- `comparison.csv`
- `report.md`
- `scoreboard.json`
- `per_system_summary.json`
- `per_system_summary.md`
- `per_category_summary.json`
- `per_category_summary.md`
- `prepared/toolsandbox.normalized.json`

The ToolSandbox report now surfaces benchmark-native signals directly:

- `milestone_similarity`
- `milestone_coverage`
- `hallucination_avoidance`
- `state_dependency_score`
- `turn_efficiency`
- `tool_efficiency`
- `result_summary_coverage`

## Current Limitation

This is a ToolSandbox-style harness inside the current ToolClaw phase-1 runtime.
It does **not** execute the official ToolSandbox environment yet.

That means:

- scoring can use ToolSandbox-like fields (`categories`, `milestones`, `result_summary`)
- execution still runs through the repo's current ToolClaw planner/executor path, but the normalized task now preserves `messages`, `milestones`, `tool_allow_list`, and imported `result_summary`
- the included sample file is only for smoke / interface validation, not for official benchmark claims

## Official ToolSandbox Wrapper

The official ToolSandbox repository is vendored under:

- `data/external/ToolSandbox`

You can bootstrap and run the official CLI through the wrapper:

```bash
scripts/run_toolsandbox_official.sh --test_mode
```

Single scenario:

```bash
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY> \
scripts/run_toolsandbox_official.sh \
  --agent GPT_4_o_2024_05_13 \
  --user GPT_4_o_2024_05_13 \
  --scenarios wifi_off
```

Full official run:

```bash
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY> \
RAPID_API_KEY=<YOUR_RAPID_API_KEY> \
scripts/run_toolsandbox_official.sh \
  --agent GPT_4_o_2024_05_13 \
  --user GPT_4_o_2024_05_13
```

The first run automatically creates:

- `data/external/ToolSandbox/.venv`

and installs the official package in editable mode.
