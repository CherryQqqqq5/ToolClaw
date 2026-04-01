#!/usr/bin/env bash
# Shared git helper functions for the local gpush/gpull wrappers.

set -euo pipefail

readonly TOOLCLAW_GIT_REMOTE_URL="https://github.com/CherryQqqqq5/ToolClaw.git"
readonly TOOLCLAW_GIT_USER_NAME="Yuning Qiu"
readonly TOOLCLAW_GIT_USER_EMAIL="231880296@smail.nju.edu.cn"

toolclaw_repo_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  printf '%s\n' "$script_dir"
}

toolclaw_require_git_repo() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not inside a git repository" >&2
    exit 1
  fi
}

toolclaw_ensure_identity() {
  git config user.name "$TOOLCLAW_GIT_USER_NAME"
  git config user.email "$TOOLCLAW_GIT_USER_EMAIL"
}

toolclaw_ensure_origin() {
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$TOOLCLAW_GIT_REMOTE_URL"
  else
    git remote add origin "$TOOLCLAW_GIT_REMOTE_URL"
  fi
}

toolclaw_current_branch() {
  local branch
  branch="$(git branch --show-current)"
  if [[ -z "$branch" ]]; then
    branch="main"
  fi
  printf '%s\n' "$branch"
}

toolclaw_print_repo_config() {
  echo "repo: $(pwd)"
  echo "origin: $(git remote get-url origin)"
  echo "user.name: $(git config user.name)"
  echo "user.email: $(git config user.email)"
}
