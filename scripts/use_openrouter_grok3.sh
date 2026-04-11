#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BASE_URL="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
KEY_CHECK_MODEL="${OPENROUTER_KEY_CHECK_MODEL:-x-ai/grok-3}"
GROK_PROBE_MODE="${OPENROUTER_GROK_PROBE_MODE:-tools}"

usage() {
  cat <<EOF
usage:
  eval "\$(scripts/use_openrouter_grok3.sh)"

optional env vars:
  OPENAI_API_KEY                OpenRouter API key (required)
  OPENROUTER_BASE_URL           Override OpenRouter-compatible base URL
  OPENROUTER_KEY_CHECK_MODEL    Model used for generic key health check (default: x-ai/grok-3)
  OPENROUTER_GROK_PROBE_MODE    none|basic|tools|both (default: tools)

what it does:
  1. validates the current OPENAI_API_KEY against OpenRouter
  2. finds callable Grok-3 slugs
  3. prints export lines you can eval into the current shell
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required" >&2
  exit 2
fi

echo "[openrouter] checking key using model: ${KEY_CHECK_MODEL}" >&2
python3 "$ROOT_DIR/scripts/check_openrouter_key.py" \
  --base-url "$BASE_URL" \
  --model "$KEY_CHECK_MODEL" \
  --probe-mode both >&2

echo "[openrouter] probing Grok-3 candidates" >&2
probe_output="$(
  python3 "$ROOT_DIR/scripts/find_openrouter_grok3_slug.py" \
    --base-url "$BASE_URL" \
    --probe "$GROK_PROBE_MODE"
)"
printf '%s\n' "$probe_output" >&2

recommended_model="$(printf '%s\n' "$probe_output" | awk -F= '/^RECOMMENDED_MODEL=/{print $2}' | tail -n 1)"
if [[ -z "$recommended_model" ]]; then
  echo "failed to resolve RECOMMENDED_MODEL from Grok-3 probe output" >&2
  exit 3
fi

cat <<EOF
export TOOLCLAW_BENCHMARK_PROXY_PROVIDER='openrouter'
export TOOLCLAW_BENCHMARK_PROXY_FORCE='1'
export OPENAI_API_KEY='${OPENAI_API_KEY}'
export TOOLSANDBOX_OPENAI_MODEL='${recommended_model}'
unset RAPID_API_KEY
EOF
