#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DATASET_PATH="${TOOLSANDBOX_FORMAL_DATASET:-$ROOT_DIR/data/toolsandbox.formal.official.json}"
OUTDIR="${TOOLSANDBOX_FORMAL_OUTDIR:-$ROOT_DIR/outputs/toolsandbox_bench_official_formal}"
SYSTEMS="${TOOLSANDBOX_FORMAL_SYSTEMS:-a0_baseline,a1_recovery,a2_planner,a3_interaction,a4_reuse}"
MODE="${TOOLSANDBOX_FORMAL_MODE:-planner}"
NUM_RUNS="${TOOLSANDBOX_FORMAL_NUM_RUNS:-1}"
OFFICIAL_RUN_DIR="${TOOLSANDBOX_OFFICIAL_RUN_DIR:-latest}"
OFFICIAL_DATA_ROOT="${TOOLSANDBOX_OFFICIAL_DATA_ROOT:-$ROOT_DIR/data/external/ToolSandbox/data}"
FALLBACK_DATASET_PATH="${TOOLSANDBOX_FALLBACK_DATASET:-$ROOT_DIR/data/toolsandbox.formal.json}"
LIMIT="${TOOLSANDBOX_FORMAL_LIMIT:-}"
REFRESH_DATASET="${TOOLSANDBOX_FORMAL_REFRESH:-0}"
EXCLUDE_AUGMENTED="${TOOLSANDBOX_FORMAL_EXCLUDE_AUGMENTED:-1}"
KEEP_NORMALIZED_TASKSET="${TOOLSANDBOX_FORMAL_KEEP_NORMALIZED_TASKSET:-0}"
REQUIRE_OFFICIAL_RUN="${TOOLSANDBOX_REQUIRE_OFFICIAL_RUN:-0}"
FULL_BENCHMARK="${TOOLSANDBOX_FULL_BENCHMARK:-0}"
ASSET_REGISTRY_ROOT="${TOOLSANDBOX_ASSET_REGISTRY_ROOT:-}"

usage() {
  cat <<EOF
usage: scripts/run_toolsandbox_formal.sh [options]

Run the fixed ToolSandbox formal benchmark entrypoint.

Defaults:
  dataset: $ROOT_DIR/data/toolsandbox.formal.official.json
  outdir:  $ROOT_DIR/outputs/toolsandbox_bench_official_formal

Behavior:
  - If the formal dataset file already exists, run the benchmark against it.
  - If it does not exist, build it once from the latest official ToolSandbox run.
  - Pass --refresh to rebuild the frozen dataset from the official run before benchmarking.

Options:
  --dataset PATH              Formal dataset JSON path
  --outdir PATH               Benchmark output directory
  --systems CSV               Systems list
  --mode MODE                 planner|demo
  --num-runs N                Repeat count
  --official-run-dir VALUE    Official ToolSandbox run dir or 'latest'
  --official-data-root PATH   Root containing official ToolSandbox run dirs
  --fallback-dataset PATH     Bundled formal dataset used when official data is unavailable
  --limit N                   Limit formal dataset size when rebuilding
  --require-official-run      Fail instead of falling back to bundled formal dataset
  --full-benchmark            Force rebuild with augmentations included and require official data
  --asset-registry-root PATH  Persist reusable assets under PATH/run_<n> across CLI invocations
  --refresh                   Rebuild the formal dataset before running
  --include-augmented         Keep distraction/scrambled augmentations
  --keep-normalized-taskset   Preserve normalized taskset emitted by runner
  -h, --help                  Show this message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset)
      DATASET_PATH="$2"
      shift 2
      ;;
    --outdir)
      OUTDIR="$2"
      shift 2
      ;;
    --systems)
      SYSTEMS="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --num-runs)
      NUM_RUNS="$2"
      shift 2
      ;;
    --official-run-dir)
      OFFICIAL_RUN_DIR="$2"
      shift 2
      ;;
    --official-data-root)
      OFFICIAL_DATA_ROOT="$2"
      shift 2
      ;;
    --fallback-dataset)
      FALLBACK_DATASET_PATH="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --require-official-run)
      REQUIRE_OFFICIAL_RUN=1
      shift
      ;;
    --full-benchmark)
      FULL_BENCHMARK=1
      REFRESH_DATASET=1
      EXCLUDE_AUGMENTED=0
      REQUIRE_OFFICIAL_RUN=1
      shift
      ;;
    --asset-registry-root)
      ASSET_REGISTRY_ROOT="$2"
      shift 2
      ;;
    --refresh)
      REFRESH_DATASET=1
      shift
      ;;
    --include-augmented)
      EXCLUDE_AUGMENTED=0
      shift
      ;;
    --keep-normalized-taskset)
      KEEP_NORMALIZED_TASKSET=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

build_dataset() {
  local cmd=(
    python3 "$ROOT_DIR/scripts/prepare_toolsandbox_formal_dataset.py"
    --official-run-dir "$OFFICIAL_RUN_DIR"
    --official-data-root "$OFFICIAL_DATA_ROOT"
    --out "$DATASET_PATH"
  )
  if [[ "$EXCLUDE_AUGMENTED" == "1" ]]; then
    cmd+=(--exclude-augmented)
  fi
  if [[ -n "$LIMIT" ]]; then
    cmd+=(--limit "$LIMIT")
  fi
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" "${cmd[@]}"
}

seed_dataset_from_fallback() {
  if [[ ! -f "$FALLBACK_DATASET_PATH" ]]; then
    return 1
  fi

  mkdir -p "$(dirname "$DATASET_PATH")"
  if [[ "$FALLBACK_DATASET_PATH" != "$DATASET_PATH" ]]; then
    cp "$FALLBACK_DATASET_PATH" "$DATASET_PATH"
  fi
  echo "seeded ToolSandbox formal dataset from fallback: $FALLBACK_DATASET_PATH" >&2
}

ensure_dataset() {
  if [[ "$REFRESH_DATASET" != "1" && -f "$DATASET_PATH" ]]; then
    return 0
  fi

  if build_dataset; then
    return 0
  fi

  if [[ "$REQUIRE_OFFICIAL_RUN" == "1" ]]; then
    echo "failed to prepare ToolSandbox formal dataset from official run and fallback is disabled" >&2
    return 1
  fi

  echo "official ToolSandbox data unavailable; falling back to bundled formal dataset: $FALLBACK_DATASET_PATH" >&2
  echo "this fallback dataset is not an official ToolSandbox run export and should not be treated as a full benchmark" >&2
  if [[ "$EXCLUDE_AUGMENTED" == "0" ]]; then
    echo "augmentations were requested, but fallback content depends on the bundled dataset and may still cover only the core benchmark slice" >&2
  fi
  if ! seed_dataset_from_fallback; then
    echo "failed to prepare ToolSandbox formal dataset: official source unavailable and fallback dataset missing: $FALLBACK_DATASET_PATH" >&2
    return 1
  fi
}

ensure_dataset

if [[ "$FULL_BENCHMARK" == "1" ]]; then
  echo "running ToolSandbox full benchmark: official run required, augmentations included" >&2
elif [[ "$EXCLUDE_AUGMENTED" == "1" ]]; then
  echo "running ToolSandbox core benchmark only: augmentations excluded" >&2
fi

if [[ "$NUM_RUNS" == "1" ]]; then
  echo "ToolSandbox num_runs=1: pass@k and consistency are single-run statistics only" >&2
fi

RUN_CMD=(
  python3 "$ROOT_DIR/scripts/run_toolsandbox.py"
  --source "$DATASET_PATH"
  --outdir "$OUTDIR"
  --systems "$SYSTEMS"
  --mode "$MODE"
  --num-runs "$NUM_RUNS"
)
if [[ "$KEEP_NORMALIZED_TASKSET" == "1" ]]; then
  RUN_CMD+=(--keep-normalized-taskset)
fi
if [[ -n "$ASSET_REGISTRY_ROOT" ]]; then
  RUN_CMD+=(--asset-registry-root "$ASSET_REGISTRY_ROOT")
fi

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" "${RUN_CMD[@]}"
