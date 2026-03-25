#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKSET="${1:-$ROOT_DIR/data/eval_tasks.sample.json}"
OUTDIR="${2:-$ROOT_DIR/outputs/phase1}"
MODE="${3:-planner}"

PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/scripts/run_eval.py" \
  --taskset "$TASKSET" \
  --outdir "$OUTDIR" \
  --mode "$MODE"
