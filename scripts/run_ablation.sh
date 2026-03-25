#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKSET="${1:-$ROOT_DIR/data/eval_tasks.sample.json}"
AB_ROOT="${2:-$ROOT_DIR/outputs/ablation}"

mkdir -p "$AB_ROOT"

# Ablation A3: demo workflow path (no planner-generated workflow)
PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/scripts/run_eval.py" \
  --taskset "$TASKSET" \
  --outdir "$AB_ROOT/a3_demo_mode" \
  --mode demo

# Ablation A4: planner workflow path
PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/scripts/run_eval.py" \
  --taskset "$TASKSET" \
  --outdir "$AB_ROOT/a4_planner_mode" \
  --mode planner
