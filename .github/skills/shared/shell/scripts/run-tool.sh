#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute run-tool workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Shared Shell Entry Script: run-tool.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Execute a requested tool using this order by default:
#   1) container runtime from the registry
#   2) local binary fallback
#
# Enterprise Behavior:
#   - Auto-register unknown tools in metadata for traceability.
#   - Use CSV-backed install guidance per OS.
#   - Fail with explicit, actionable error messages.
#   - Keep execution routing centralized in this wrapper.
#
# Usage:
#   run-tool.sh <tool-name> <command-or-arg> [args...]
#
# Example:
#   run-tool.sh python3 --version
#   run-tool.sh ruff check .
# =============================================================================

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <tool-name> <command> [args...]" >&2
  exit 1
fi

TOOL_NAME="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
SHARED_SHELL_REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/tools.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/containers.sh"

CSV_FILE="${TOOL_REGISTRY_CSV:-$SCRIPT_DIR/metadata/tools.csv}"
OS_NAME="$(detect_os)"
PREFER_CONTAINER="${RUN_TOOL_PREFER_CONTAINER:-1}"

register_tool_if_missing() {
  local csv_file="$1"
  local tool_name="$2"
  local lock_file="$SCRIPT_DIR/.runtime/locks/.tools-csv.lock"

  mkdir -p "$(dirname "$lock_file")"

  if csv_get_row_by_name "$csv_file" "$tool_name" | grep -q .; then
    return 0
  fi

  local attempts=0
  until { set -C; true >"$lock_file"; } 2>/dev/null; do
    attempts=$((attempts + 1))
    [[ "$attempts" -lt 50 ]] || die "Could not acquire tools.csv lock for auto-registration"
    sleep 0.1
  done

  if ! csv_get_row_by_name "$csv_file" "$tool_name" | grep -q .; then
    printf '%s\n' "$tool_name,unknown,,Install $tool_name for macOS or configure container image,Install $tool_name for Windows or configure container image" >> "$csv_file"
    log_warn "Auto-registered unknown tool '$tool_name' in $csv_file"
  fi

  rm -f "$lock_file"
}

require_file "$CSV_FILE"
register_tool_if_missing "$CSV_FILE" "$TOOL_NAME"

run_registered_container() {
  local engine image

  engine="$(detect_container_tool)" || return 1
  image="$(get_tool_public_container "$CSV_FILE" "$TOOL_NAME")"
  [[ -n "$image" ]] || return 1

  printf '[INFO] %s\n' "Running '$TOOL_NAME' via container ($engine)" >&2
  if [[ "$TOOL_NAME" == "mmdc" || "$TOOL_NAME" == "gh" || "$TOOL_NAME" == "git" ]]; then
    CONTAINER_MOUNT_ROOT="$SHARED_SHELL_REPO_ROOT" \
    CONTAINER_ENV_PASSTHROUGH="GH_TOKEN,GITHUB_TOKEN,GITHUB_OWNER,GH_REQUIRED_SCOPES,DIGITAL_TEAM_SKIP_DOTENV,CONTAINER_TOOL" \
      run_in_container "$image" "$@"
  else
    # First try explicit binary invocation (works for images without entrypoint).
    CONTAINER_MOUNT_ROOT="$SHARED_SHELL_REPO_ROOT" \
    CONTAINER_ENV_PASSTHROUGH="GH_TOKEN,GITHUB_TOKEN,GITHUB_OWNER,GH_REQUIRED_SCOPES,DIGITAL_TEAM_SKIP_DOTENV,CONTAINER_TOOL" \
      run_in_container "$image" "$TOOL_NAME" "$@" && return 0

    # Retry with image entrypoint for tool-images that already define the binary.
    log_warn "Container invocation with explicit tool failed for '$TOOL_NAME'; retrying via image entrypoint"
    CONTAINER_MOUNT_ROOT="$SHARED_SHELL_REPO_ROOT" \
    CONTAINER_ENV_PASSTHROUGH="GH_TOKEN,GITHUB_TOKEN,GITHUB_OWNER,GH_REQUIRED_SCOPES,DIGITAL_TEAM_SKIP_DOTENV,CONTAINER_TOOL" \
      run_in_container "$image" "$@"
  fi
}

run_local_tool() {
  tool_exists "$TOOL_NAME" || return 1
  exec "$TOOL_NAME" "$@"
}

if [[ "$PREFER_CONTAINER" == "0" ]]; then
  if run_local_tool "$@"; then
    exit 0
  fi
  if run_registered_container "$@"; then
    exit 0
  fi
else
  if run_registered_container "$@"; then
    exit 0
  fi
  if run_local_tool "$@"; then
    exit 0
  fi
fi

help_msg="$(get_tool_install_help "$CSV_FILE" "$TOOL_NAME" "$OS_NAME")"
die "Tool '$TOOL_NAME' not available locally and no container engine found. $help_msg"
