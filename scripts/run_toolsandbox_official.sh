#!/usr/bin/env bash
# Bootstrap and run the official ToolSandbox CLI from the vendored repo.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLSANDBOX_DIR="${TOOLSANDBOX_DIR:-$ROOT_DIR/data/external/ToolSandbox}"
LOCAL_IO_ROOT="${TOOLCLAW_LOCAL_IO_ROOT:-/tmp/toolclaw_toolsandbox}"
mkdir -p "$LOCAL_IO_ROOT"
VENV_DIR="${TOOLSANDBOX_VENV_DIR:-$LOCAL_IO_ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ONLY=0
USE_ACTIVE_ENV="${TOOLSANDBOX_USE_ACTIVE_ENV:-0}"
FORCE_REINSTALL="${TOOLSANDBOX_FORCE_REINSTALL:-0}"
PIP_MAX_RETRIES="${TOOLSANDBOX_PIP_MAX_RETRIES:-3}"
PIP_RETRY_DELAY_SECONDS="${TOOLSANDBOX_PIP_RETRY_DELAY_SECONDS:-3}"
INSTALL_TARGET="${TOOLSANDBOX_INSTALL_TARGET:-.}"
HTTPX_COMPAT_SPEC="${TOOLSANDBOX_HTTPX_COMPAT_SPEC:-httpx<0.28}"
PATCH_ROLES="${TOOLSANDBOX_PATCH_OPENAI_ROLES:-1}"
export TMPDIR="${TMPDIR:-$LOCAL_IO_ROOT/tmp}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$LOCAL_IO_ROOT/.cache}"
export HF_HOME="${HF_HOME:-$LOCAL_IO_ROOT/hf}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$XDG_CACHE_HOME/pip}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$HF_HOME" "$PIP_CACHE_DIR"

# Benchmark proxy routing defaults (OpenAI-compatible):
#   TOOLCLAW_BENCHMARK_PROXY_PROVIDER=novacode|openrouter|custom|direct
#   TOOLCLAW_BENCHMARK_PROXY_BASE_URL=<custom url>
#   TOOLCLAW_BENCHMARK_PROXY_FORCE=1 (override explicit OPENAI_BASE_URL / OPENAI_API_BASE)
# Explicit OPENAI_BASE_URL / OPENAI_API_BASE values still take precedence.
PROXY_PROVIDER="${TOOLCLAW_BENCHMARK_PROXY_PROVIDER:-novacode}"
PROXY_PROVIDER="$(printf '%s' "$PROXY_PROVIDER" | tr '[:upper:]' '[:lower:]')"
PROXY_FORCE="${TOOLCLAW_BENCHMARK_PROXY_FORCE:-0}"
case "$PROXY_PROVIDER" in
  nova|novacode)
    DEFAULT_PROXY_BASE_URL="${TOOLCLAW_BENCHMARK_NOVACODE_BASE_URL:-https://ai.novacode.top/v1}"
    ;;
  openrouter|router)
    DEFAULT_PROXY_BASE_URL="${TOOLCLAW_BENCHMARK_OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
    ;;
  direct|openai)
    DEFAULT_PROXY_BASE_URL=""
    ;;
  custom|*)
    DEFAULT_PROXY_BASE_URL="${TOOLCLAW_BENCHMARK_PROXY_BASE_URL:-}"
    ;;
esac

if [[ "$PROXY_FORCE" == "1" && -n "$DEFAULT_PROXY_BASE_URL" ]]; then
  export OPENAI_BASE_URL="$DEFAULT_PROXY_BASE_URL"
  export OPENAI_API_BASE="$DEFAULT_PROXY_BASE_URL"
elif [[ -z "${OPENAI_BASE_URL:-}" && -z "${OPENAI_API_BASE:-}" && -n "$DEFAULT_PROXY_BASE_URL" ]]; then
  export OPENAI_BASE_URL="$DEFAULT_PROXY_BASE_URL"
  export OPENAI_API_BASE="$DEFAULT_PROXY_BASE_URL"
fi

usage() {
  cat >&2 <<'EOF'
usage: scripts/run_toolsandbox_official.sh [--install-only] [--use-active-env] [--force-reinstall] [official-tool-sandbox-args...]

This wrapper bootstraps the vendored official ToolSandbox repo under:
  data/external/ToolSandbox

Examples:
  scripts/run_toolsandbox_official.sh --test_mode
  conda activate tooluse && scripts/run_toolsandbox_official.sh --use-active-env --install-only
  OPENAI_API_KEY=... RAPID_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13
  OPENAI_API_KEY=... scripts/run_toolsandbox_official.sh --agent GPT_4_o_2024_05_13 --user GPT_4_o_2024_05_13 --scenarios wifi_off

Notes:
  - By default the first run creates the ToolSandbox venv under TOOLCLAW_LOCAL_IO_ROOT (default: /tmp/toolclaw_toolsandbox).
  - Default installs runtime dependencies only. Set TOOLSANDBOX_INSTALL_TARGET='.[dev]' to include upstream dev extras.
  - The wrapper auto-pins a compatible httpx version for the vendored OpenAI client when needed.
  - The wrapper also defaults TMPDIR/XDG_CACHE_HOME/HF_HOME/PIP_CACHE_DIR to local scratch paths to avoid slow shared filesystems.
  - --use-active-env installs into the currently active Python/conda environment instead of creating a venv.
  - If python -m venv fails, the script falls back to python -m virtualenv when possible.
  - API keys still need to be provided via environment variables as required by the selected agent/user roles.
EOF
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --install-only)
      INSTALL_ONLY=1
      shift
      ;;
    --use-active-env)
      USE_ACTIVE_ENV=1
      shift
      ;;
    --force-reinstall)
      FORCE_REINSTALL=1
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -d "$TOOLSANDBOX_DIR" ]]; then
  echo "official ToolSandbox repo not found: $TOOLSANDBOX_DIR" >&2
  echo "expected clone location: data/external/ToolSandbox" >&2
  exit 1
fi

patch_toolsandbox_roles() {
  if [[ "$PATCH_ROLES" != "1" ]]; then
    return 0
  fi
  "$PYTHON_EXEC" "$ROOT_DIR/scripts/patch_toolsandbox_openai_roles.py" --root "$TOOLSANDBOX_DIR" >/dev/null
}

contains_placeholder() {
  case "$1" in
    *"你的真实_"*|*"YOUR_"*|*"your_"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

validate_env() {
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "OPENAI_API_KEY is required" >&2
    exit 2
  fi
  if contains_placeholder "${OPENAI_API_KEY:-}"; then
    echo "OPENAI_API_KEY is still a placeholder" >&2
    exit 2
  fi
  if [[ -n "${RAPID_API_KEY:-}" ]] && contains_placeholder "${RAPID_API_KEY:-}"; then
    echo "RAPID_API_KEY is still a placeholder" >&2
    exit 2
  fi
  if [[ -n "${RAPID_API_KEY:-}" && "${RAPID_API_KEY:-}" == sk-or-v1-* ]]; then
    echo "RAPID_API_KEY must be a real RapidAPI key, not an OpenRouter key" >&2
    exit 2
  fi

  case "$PROXY_PROVIDER" in
    nova|novacode)
      if [[ "${OPENAI_API_KEY:-}" == sk-or-v1-* ]]; then
        echo "novacode provider selected, but OPENAI_API_KEY looks like an OpenRouter key" >&2
        exit 2
      fi
      ;;
    openrouter|router)
      export TOOLSANDBOX_OPENAI_MODEL="${TOOLSANDBOX_OPENAI_MODEL:-openai/gpt-4.1}"
      ;;
  esac
}

preflight_model_probe() {
  "$RUN_PYTHON" - <<'PY'
import os
from openai import OpenAI

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
model = os.environ.get("TOOLSANDBOX_OPENAI_MODEL", "gpt-5.4")

if not api_key:
    raise SystemExit("OPENAI_API_KEY is missing")

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
        temperature=0,
    )
    print(f"[preflight] model ok: {model}")
except Exception as e:
    raise SystemExit(f"[preflight] model probe failed for {model}: {e}")
PY
}

resolve_python_bin() {
  if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    printf '%s\n' "$PYTHON_BIN"
    return 0
  fi
  if [[ "$PYTHON_BIN" != "python" ]] && command -v python >/dev/null 2>&1; then
    printf '%s\n' "python"
    return 0
  fi
  echo "python executable not found: $PYTHON_BIN" >&2
  return 1
}

module_available() {
  local python_exec="$1"
  "$python_exec" - <<'PY' >/dev/null 2>&1
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("tool_sandbox.cli") else 1)
PY
}

install_into_python() {
  local python_exec="$1"
  echo "installing official ToolSandbox dependencies using: $python_exec"
  echo "install target: -e $INSTALL_TARGET"
  pip_install_with_retry "$python_exec" install --upgrade pip
  (
    cd "$TOOLSANDBOX_DIR"
    pip_install_with_retry "$python_exec" install -e "$INSTALL_TARGET"
  )
  ensure_runtime_compat "$python_exec"
}

pip_install_with_retry() {
  local python_exec="$1"
  shift
  local attempt=1
  local exit_code=0

  while (( attempt <= PIP_MAX_RETRIES )); do
    if (( attempt > 1 )); then
      local wait_seconds=$(( PIP_RETRY_DELAY_SECONDS * (attempt - 1) ))
      echo "pip install retry ${attempt}/${PIP_MAX_RETRIES} in ${wait_seconds}s..." >&2
      sleep "$wait_seconds"
    fi

    if "$python_exec" -m pip --retries 10 --timeout 120 "$@"; then
      return 0
    fi

    exit_code=$?
    echo "pip command failed on attempt ${attempt}/${PIP_MAX_RETRIES} (exit=${exit_code})." >&2
    attempt=$((attempt + 1))
  done

  return "$exit_code"
}

create_venv() {
  local python_exec="$1"
  echo "creating ToolSandbox virtualenv at: $VENV_DIR"
  if "$python_exec" -m venv "$VENV_DIR"; then
    return 0
  fi
  echo "python -m venv failed; attempting virtualenv fallback" >&2
  pip_install_with_retry "$python_exec" install --upgrade pip
  pip_install_with_retry "$python_exec" install virtualenv
  "$python_exec" -m virtualenv "$VENV_DIR"
}

httpx_compatible() {
  local python_exec="$1"
  "$python_exec" - <<'PY' >/dev/null 2>&1
import importlib.metadata as metadata
import sys

def version_tuple(raw: str) -> tuple[int, ...]:
    parts = []
    for token in raw.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)

try:
    openai_version = metadata.version("openai")
    httpx_version = metadata.version("httpx")
except metadata.PackageNotFoundError:
    sys.exit(0)

if version_tuple(openai_version) < (1, 18) and version_tuple(httpx_version) >= (0, 28):
    sys.exit(1)
sys.exit(0)
PY
}

ensure_runtime_compat() {
  local python_exec="$1"
  if httpx_compatible "$python_exec"; then
    return 0
  fi
  echo "detected incompatible openai/httpx combination; installing $HTTPX_COMPAT_SPEC"
  pip_install_with_retry "$python_exec" install "$HTTPX_COMPAT_SPEC"
}

PYTHON_EXEC="$(resolve_python_bin)"
RUN_PYTHON=""
ENV_LABEL=""

if [[ "$USE_ACTIVE_ENV" == "1" ]]; then
  RUN_PYTHON="$PYTHON_EXEC"
  ENV_LABEL="${CONDA_PREFIX:-active_python_env}"
  if [[ "$FORCE_REINSTALL" == "1" ]] || ! module_available "$RUN_PYTHON"; then
    install_into_python "$RUN_PYTHON"
  fi
else
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    create_venv "$PYTHON_EXEC"
  fi
  RUN_PYTHON="$VENV_DIR/bin/python"
  ENV_LABEL="$VENV_DIR"
  if [[ "$FORCE_REINSTALL" == "1" ]] || ! module_available "$RUN_PYTHON"; then
    install_into_python "$RUN_PYTHON"
  fi
fi

ensure_runtime_compat "$RUN_PYTHON"
patch_toolsandbox_roles

if [[ "$INSTALL_ONLY" -eq 1 ]]; then
  echo "ToolSandbox environment is ready:"
  echo "  repo: $TOOLSANDBOX_DIR"
  if [[ "$USE_ACTIVE_ENV" == "1" ]]; then
    echo "  python_env: $ENV_LABEL"
  else
    echo "  venv: $ENV_LABEL"
  fi
  echo "  python: $RUN_PYTHON"
  exit 0
fi

if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(--test_mode)
fi

validate_env
echo "[ToolSandbox] provider=${PROXY_PROVIDER} base_url=${OPENAI_BASE_URL:-${OPENAI_API_BASE:-<unset>}} model=${TOOLSANDBOX_OPENAI_MODEL:-<default>}"
preflight_model_probe

exec "$RUN_PYTHON" -c 'import sys; from tool_sandbox.cli import main; sys.argv = ["tool_sandbox", *sys.argv[1:]]; main()' "${ARGS[@]}"
