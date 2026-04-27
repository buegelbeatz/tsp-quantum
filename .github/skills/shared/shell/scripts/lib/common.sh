#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Execute common workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

set -euo pipefail

# =============================================================================
# Enterprise Shared Shell Library: common.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Provide foundational, reusable shell primitives for all shared/shell skills.
#
# Scope:
#   - structured logging
#   - fatal error handling
#   - OS detection
#   - repository root resolution
#   - optional .env auto-loading from repository root
#
# Security & Compliance:
#   - No secrets are hardcoded.
#   - Environment values are sourced only from local `.env` when present.
#   - This library must be sourced (not executed).
#
# Usage:
#   source "<path>/common.sh"
# =============================================================================

# shellcheck shell=bash

# Auto-load `.env` from repository root when available.
_SHARED_SHELL_REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ "${DIGITAL_TEAM_SKIP_DOTENV:-0}" != "1" ]] && [[ -n "${_SHARED_SHELL_REPO_ROOT}" && -f "${_SHARED_SHELL_REPO_ROOT}/.env" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "${_SHARED_SHELL_REPO_ROOT}/.env"
  set +a
fi
unset _SHARED_SHELL_REPO_ROOT

log_info() {
  printf '[INFO] %s\n' "$1"
}

log_warn() {
  printf '[WARN] %s\n' "$1" >&2
}

log_error() {
  printf '[ERROR] %s\n' "$1" >&2
}

die() {
  log_error "$1"
  exit 1
}

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "mac" ;;
    Linux) echo "linux" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

repo_root() {
  git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || die "Required file not found: $path"
}
