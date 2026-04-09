#!/usr/bin/env bash
# Remote-friendly wrapper for tau-bench runs with smoke/full presets and logging.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${1:-}"
OUTDIR="${2:-$ROOT_DIR/outputs/tau_bench_remote}"
MODE="${3:-planner}"
SYSTEMS="${4:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"
RUN_KIND="${5:-smoke}" # smoke | full
NUM_RUNS="${6:-1}"

if [[ -z "$SOURCE" ]]; then
  echo "usage: scripts/run_tau_bench_remote.sh <tau_bench_source.json|jsonl> [outdir] [mode] [systems] [smoke|full] [num_runs]" >&2
  exit 1
fi

resolve_source_path() {
  local requested="$1"
  local normalized="$requested"
  if [[ "$requested" != /* ]]; then
    local from_cwd="$PWD/$requested"
    local from_root="$ROOT_DIR/$requested"
    if [[ -f "$from_cwd" ]]; then
      normalized="$from_cwd"
    elif [[ -f "$from_root" ]]; then
      normalized="$from_root"
    fi
  fi
  if [[ -f "$normalized" ]]; then
    printf '%s\n' "$normalized"
    return 0
  fi

  # Backward-compatible alias for an older documented sample path.
  if [[ "$requested" == "data/tau_bench.sample.json" && -f "$ROOT_DIR/data/tau_bench/tau_bench.aligned.jsonl" ]]; then
    printf '%s\n' "$ROOT_DIR/data/tau_bench/tau_bench.aligned.jsonl"
    return 0
  fi
  return 1
}

if ! RESOLVED_SOURCE="$(resolve_source_path "$SOURCE")"; then
  echo "tau-bench source not found: $SOURCE" >&2
  echo "checked: $SOURCE, $PWD/$SOURCE, $ROOT_DIR/$SOURCE" >&2
  if [[ -f "$ROOT_DIR/data/tau_bench/tau_bench.aligned.jsonl" ]]; then
    echo "hint: try source path data/tau_bench/tau_bench.aligned.jsonl" >&2
  fi
  exit 1
fi

mkdir -p "$OUTDIR/logs" "$OUTDIR/prepared"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python interpreter not found: $PYTHON_BIN" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
export TOOLCLAW_REMOTE_RUN=1

LIMIT_ARGS=()
if [[ "$RUN_KIND" == "smoke" ]]; then
  LIMIT_ARGS+=(--smoke --limit 10)
fi

set -x
"$PYTHON_BIN" "$ROOT_DIR/scripts/run_tau_bench.py" \
  --source "$RESOLVED_SOURCE" \
  --outdir "$OUTDIR" \
  --mode "$MODE" \
  --systems "$SYSTEMS" \
  --num-runs "$NUM_RUNS" \
  "${LIMIT_ARGS[@]}" \
  2>&1 | tee "$OUTDIR/logs/run_tau_bench_remote.log"
set +x

echo "tau-bench remote run finished"
echo "comparison: $OUTDIR/comparison.csv"
echo "report: $OUTDIR/report.md"
echo "scoreboard: $OUTDIR/scoreboard.json"
echo "per-system summary: $OUTDIR/per_system_summary.json"
