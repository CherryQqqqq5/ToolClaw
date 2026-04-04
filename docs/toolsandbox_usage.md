# ToolSandbox In ToolClaw

This repo now includes a ToolSandbox-style benchmark runner:

```bash
python3 scripts/run_toolsandbox_bench.py
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
- `per_category_summary.md`
- `prepared/toolsandbox.normalized.json`

## Current Limitation

This is a ToolSandbox-style harness inside the current ToolClaw phase-1 runtime.
It does **not** execute the official ToolSandbox environment yet.

That means:

- scoring can use ToolSandbox-like fields (`categories`, `milestones`, `result_summary`)
- execution still runs through the repo's current ToolClaw planner/executor path
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
