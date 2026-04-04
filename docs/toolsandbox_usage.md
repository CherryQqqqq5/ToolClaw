# ToolSandbox In ToolClaw

This repo now includes a ToolSandbox-style benchmark runner.

By default, it now prefers formal ToolSandbox data:

- `data/toolsandbox.formal.official.json` if present
- otherwise `data/toolsandbox.formal.json`
- otherwise `data/toolsandbox.sample.json` for smoke only

General runner:

```bash
python3 scripts/run_toolsandbox_bench.py
```

Compatibility alias:

```bash
python3 scripts/run_toolsandbox.py
```

For the fixed formal ToolSandbox entrypoint, use:

```bash
scripts/run_toolsandbox_formal.sh
```

That wrapper:

- defaults to `data/toolsandbox.formal.official.json`
- auto-builds that frozen dataset from the latest official ToolSandbox run if it does not exist yet
- then runs the benchmark into `outputs/toolsandbox_bench_official_formal`

If you already ran the vendored official ToolSandbox CLI, you can auto-discover the latest official run directory and feed it into the current ToolClaw runner directly:

```bash
python3 scripts/run_toolsandbox.py \
  --official-run-dir latest \
  --require-result-summary
```

For formal runs, use the dedicated wrapper:

```bash
scripts/run_toolsandbox_formal.sh
```

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

Or use the dedicated formal wrapper so you do not need to retype the path plumbing:

```bash
scripts/run_toolsandbox_formal.sh
```

Force a rebuild from the latest official run before benchmarking:

```bash
scripts/run_toolsandbox_formal.sh --refresh
```

Keep augmentation slices in the rebuilt formal dataset:

```bash
scripts/run_toolsandbox_formal.sh --refresh --include-augmented
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
- `reference_summary_coverage`

## Current Limitation

There are two different evaluation modes in this repo. Do not mix them in writeups.

### 1. Official ToolSandbox execution

- Executed by the vendored official ToolSandbox CLI
- Command path: `scripts/run_toolsandbox_official.sh`
- Ground truth lives under `data/external/ToolSandbox/data/<run_dir>/...`
- Use this mode when you want to make claims about the official ToolSandbox environment

### 2. ToolClaw proxy evaluation over ToolSandbox-style tasks

- Executed by `scripts/run_toolsandbox.py`, `scripts/run_toolsandbox_bench.py`, or `scripts/run_toolsandbox_formal.sh`
- Runs through the current ToolClaw phase-1 planner / executor / interaction stack
- Each current ToolClaw trace is annotated with a fresh `toolsandbox_result` proxy summary generated from that run
- Imported external ToolSandbox summaries are kept only as reference (`toolsandbox_reference_result`) for dataset freezing or offline comparison

This means the current ToolClaw runner does **not** execute the official ToolSandbox environment yet.

That means:

- scoring uses the current ToolClaw run's proxy `toolsandbox_result`, not the imported external summary
- execution still runs through the repo's current ToolClaw planner/executor path, while normalized tasks preserve `messages`, `milestones`, `tool_allow_list`, and optional reference summaries
- the sample file is only for smoke / interface validation, not for official benchmark claims

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
