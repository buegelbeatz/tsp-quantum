#!/usr/bin/env bash
# layer: digital-generic-team

# =============================================================================
# Enterprise Shared Shell Library: github.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Reusable GitHub helper functions for Layer 1 skills.
#
# Provides:
#   - GH token preflight checks
#   - runtime/cache/report path handling under `.digital-runtime`
#   - authenticated `gh` and `git` execution via shared run-tool
#   - JSON -> YAML conversion for machine-reusable outputs
#
# Security:
#   - Tokens are never persisted in repository paths.
#   - Cached runtime assets are written under `.digital-runtime` only.
# =============================================================================

# shellcheck shell=bash
set -euo pipefail

GITHUB_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_SHELL_SCRIPTS_DIR="$(cd "$GITHUB_LIB_DIR/.." && pwd)"
SHARED_SHELL_RUN_TOOL="$SHARED_SHELL_SCRIPTS_DIR/run-tool.sh"
SHARED_SHELL_REPO_ROOT="$(git -C "$SHARED_SHELL_SCRIPTS_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
GITHUB_YAML_LIB="$GITHUB_LIB_DIR/github-yaml.sh"
SHARED_COMMON_LIB="$GITHUB_LIB_DIR/common.sh"

if [[ -f "$SHARED_COMMON_LIB" ]]; then
  # shellcheck source=/dev/null
  source "$SHARED_COMMON_LIB"
fi

GITHUB_RUNTIME_ROOT="$SHARED_SHELL_REPO_ROOT/.digital-runtime/github"
GITHUB_REPORT_DIR="$GITHUB_RUNTIME_ROOT/reports"
GITHUB_CACHE_DIR="$GITHUB_RUNTIME_ROOT/cache"
GITHUB_WIKI_CACHE_DIR="$GITHUB_RUNTIME_ROOT/wiki-cache"

# shellcheck source=/dev/null
source "$GITHUB_YAML_LIB"

ensure_github_runtime_dirs() {
  mkdir -p "$GITHUB_REPORT_DIR" "$GITHUB_CACHE_DIR" "$GITHUB_WIKI_CACHE_DIR"
}

github_require_token() {
  if [[ -z "${GH_TOKEN:-}" ]]; then
    github_load_token_from_env_file || true
  fi
  if [[ -z "${GH_TOKEN:-}" ]]; then
    return 1
  fi
  return 0
}

github_load_token_from_env_file() {
  local env_file token_line token_value
  env_file="$SHARED_SHELL_REPO_ROOT/.env"
  [[ -f "$env_file" ]] || return 1

  token_line="$(grep -E '^(GITHUB_TOKEN|GH_TOKEN)=' "$env_file" 2>/dev/null | head -n1 || true)"
  [[ -n "$token_line" ]] || return 1

  token_value="${token_line#*=}"
  token_value="${token_value%$'\r'}"
  token_value="${token_value%\"}"
  token_value="${token_value#\"}"
  token_value="${token_value%\'}"
  token_value="${token_value#\'}"
  token_value="$(printf '%s' "$token_value" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"

  [[ -n "$token_value" ]] || return 1
  export GH_TOKEN="$token_value"
  export GITHUB_TOKEN="$token_value"
  return 0
}

github_timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

github_run_tool() {
  "$SHARED_SHELL_RUN_TOOL" "$@"
}

github_run_gh() {
  if [[ -z "${GH_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
    export GH_TOKEN="$GITHUB_TOKEN"
  fi
  if [[ -z "${GH_TOKEN:-}" ]]; then
    github_load_token_from_env_file || true
  fi
  if GH_TOKEN="${GH_TOKEN:-}" GITHUB_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}" github_run_tool gh "$@"; then
    return 0
  fi

  return 1
}

github_run_git() {
  if [[ -n "${GH_TOKEN:-}" ]]; then
    if [[ "${GH_TOKEN}" == *$'\n'* || "${GH_TOKEN}" == *$'\r'* ]]; then
      printf '%s\n' '[ERROR] GH_TOKEN contains unsupported characters.' >&2
      return 1
    fi
    if printf '%s' "${GH_TOKEN}" | tr -d 'A-Za-z0-9._~+-' | grep -q .; then
      printf '%s\n' '[ERROR] GH_TOKEN contains unsupported characters.' >&2
      return 1
    fi
    local basic_auth
    basic_auth="$(printf 'x-access-token:%s' "${GH_TOKEN}" | base64 | tr -d '\n')"
    github_run_tool git -c "http.extraHeader=Authorization: Basic ${basic_auth}" "$@"
    return
  fi
  github_run_tool git "$@"
}

github_repo_slug_from_git() {
  local remote_url
  remote_url="$(git -C "$SHARED_SHELL_REPO_ROOT" remote get-url origin 2>/dev/null || true)"

  if [[ -z "$remote_url" ]]; then
    return 1
  fi

  if [[ "$remote_url" =~ github.com[:/]([^/]+/[^/.]+)(\.git)?$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi

  return 1
}

github_current_login() {
  github_run_gh api /user --jq '.login' 2>/dev/null || return 1
}

github_default_owner() {
  if [[ -n "${GITHUB_OWNER:-}" ]]; then
    printf '%s\n' "$GITHUB_OWNER"
    return 0
  fi

  local slug
  slug="$(github_repo_slug_from_git 2>/dev/null || true)"
  if [[ -n "$slug" ]]; then
    printf '%s\n' "${slug%%/*}"
    return 0
  fi

  github_current_login 2>/dev/null || return 1
}

github_default_repo_slug() {
  if [[ -n "${GITHUB_REPO:-}" ]]; then
    printf '%s\n' "$GITHUB_REPO"
    return 0
  fi

  github_repo_slug_from_git 2>/dev/null || return 1
}

github_default_repo_name() {
  local slug
  slug="$(github_default_repo_slug 2>/dev/null || true)"
  [[ -n "$slug" ]] || return 1
  printf '%s\n' "${slug##*/}"
}
