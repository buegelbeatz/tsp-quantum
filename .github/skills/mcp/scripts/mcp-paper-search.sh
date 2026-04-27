#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Wrapper for the arXiv paper search MCP tool with rate-limiting and caching.
#   Queries the paper search MCP server and returns structured metadata results.
# Security:
#   Reads paper metadata from the MCP server only; validates search query inputs.
#   No file writes outside of designated cache paths; no credential exposure.
set -euo pipefail

# Purpose:
#   Launch the paper-search MCP server with container-first execution while
#   keeping runtime state under .digital-runtime.
# Security|Compliance:
#   Uses mounted workspace runtime only; avoids hardcoded secrets and keeps
#   mutable runtime artifacts out of .digital-team.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LAYER_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
LAYER_ID="$(basename "$LAYER_DIR")"

if command -v git >/dev/null 2>&1; then
  REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
fi

RUNTIME_ROOT="${DIGITAL_TEAM_RUNTIME_ROOT:-$REPO_ROOT/.digital-runtime}"
HOST_LAYER_RUNTIME_DIR="$RUNTIME_ROOT/layers/$LAYER_ID"
HOST_LAYER_VENV="$HOST_LAYER_RUNTIME_DIR/venv"
HOST_CONTAINER_VENV="$HOST_LAYER_RUNTIME_DIR/venv-container-paper-search"
HOST_REQUIREMENTS_MERGED="$HOST_LAYER_RUNTIME_DIR/requirements.merged.txt"

SHARED_LIB_DIR="$(cd "$SCRIPT_DIR/../../shared/shell/scripts/lib" && pwd)"
MCP_LIB_DIR="$SCRIPT_DIR/lib"
# shellcheck source=/dev/null
source "$SHARED_LIB_DIR/containers.sh"
# shellcheck source=/dev/null
source "$MCP_LIB_DIR/mcp-paper-search-lib.sh"

BOOTSTRAP_VERBOSE=0
FORWARDED_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --verbose)
      BOOTSTRAP_VERBOSE=1
      ;;
    --quiet)
      BOOTSTRAP_VERBOSE=0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        FORWARDED_ARGS+=("$1")
        shift
      done
      break
      ;;
    *)
      FORWARDED_ARGS+=("$1")
      ;;
  esac
  shift
done

if detect_container_tool >/dev/null 2>&1; then
  run_container_venv "${FORWARDED_ARGS[@]}"
else
  run_local_venv "${FORWARDED_ARGS[@]}"
fi
