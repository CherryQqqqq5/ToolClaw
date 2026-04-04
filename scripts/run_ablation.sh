#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKSET="${1:-$ROOT_DIR/data/eval_tasks.sample.json}"
OUTROOT="${2:-$ROOT_DIR/outputs/ablation}"
REUSE_TASKSET="${3:-$TASKSET}"
SYSTEMS="${4:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"
RUN_TOOLSANDBOX_FORMAL_IN_ABLATION="${RUN_TOOLSANDBOX_FORMAL_IN_ABLATION:-1}"
TOOLSANDBOX_ABLATION_OUTDIR="${TOOLSANDBOX_ABLATION_OUTDIR:-$OUTROOT/toolsandbox_formal}"
TOOLSANDBOX_ABLATION_NUM_RUNS="${TOOLSANDBOX_ABLATION_NUM_RUNS:-3}"
TOOLSANDBOX_ABLATION_INCLUDE_AUGMENTED="${TOOLSANDBOX_ABLATION_INCLUDE_AUGMENTED:-1}"
TOOLSANDBOX_ABLATION_REQUIRE_OFFICIAL="${TOOLSANDBOX_ABLATION_REQUIRE_OFFICIAL:-0}"
TOOLSANDBOX_ABLATION_ASSET_ROOT="${TOOLSANDBOX_ABLATION_ASSET_ROOT:-}"

mkdir -p "$OUTROOT"

"$ROOT_DIR/scripts/run_eval.sh" "$TASKSET" "$OUTROOT/matrix" "$SYSTEMS" planner

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT_DIR/scripts/run_reuse_experiment.py" \
  --taskset "$REUSE_TASKSET" \
  --outdir "$OUTROOT/reuse" \
  --systems "a3_interaction,a4_reuse"

if [[ "$RUN_TOOLSANDBOX_FORMAL_IN_ABLATION" == "1" ]]; then
  TOOLSANDBOX_ARGS=(
    --outdir "$TOOLSANDBOX_ABLATION_OUTDIR"
    --systems "$SYSTEMS"
    --num-runs "$TOOLSANDBOX_ABLATION_NUM_RUNS"
    --refresh
  )
  if [[ "$TOOLSANDBOX_ABLATION_INCLUDE_AUGMENTED" == "1" ]]; then
    TOOLSANDBOX_ARGS+=(--include-augmented)
  fi
  if [[ "$TOOLSANDBOX_ABLATION_REQUIRE_OFFICIAL" == "1" ]]; then
    TOOLSANDBOX_ARGS+=(--require-official-run)
  fi
  if [[ -n "$TOOLSANDBOX_ABLATION_ASSET_ROOT" ]]; then
    TOOLSANDBOX_ARGS+=(--asset-registry-root "$TOOLSANDBOX_ABLATION_ASSET_ROOT")
  fi
  "$ROOT_DIR/scripts/run_toolsandbox_formal.sh" "${TOOLSANDBOX_ARGS[@]}"
fi

echo "matrix: $OUTROOT/matrix"
echo "reuse: $OUTROOT/reuse"
if [[ "$RUN_TOOLSANDBOX_FORMAL_IN_ABLATION" == "1" ]]; then
  echo "toolsandbox_formal: $TOOLSANDBOX_ABLATION_OUTDIR"
  if [[ -n "$TOOLSANDBOX_ABLATION_ASSET_ROOT" ]]; then
    echo "toolsandbox_assets: $TOOLSANDBOX_ABLATION_ASSET_ROOT"
  fi
fi
