#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Optional SOCKS/VPN proxy wrapper for stdio MCP servers.
#   Detects proxy availability and conditionally injects proxy env vars
#   before delegating to the actual server command.
# Security:
#   No credentials are hardcoded. Proxy address is read from environment
#   or defaults. Wrapper preserves original server args and exit codes.
#   Scope is strictly server-local — no global side effects.

set -euo pipefail

# =============================================================================
# Configuration — override via environment variables
# =============================================================================

# Proxy endpoint to test (host:port)
PROXY_HOST="${MCP_PROXY_HOST:-127.0.0.1}"
PROXY_PORT="${MCP_PROXY_PORT:-1080}"

# Timeout in seconds for proxy availability check
PROXY_CHECK_TIMEOUT="${MCP_PROXY_CHECK_TIMEOUT:-1}"

# Set to "1" to force direct mode (skip proxy detection)
PROXY_DISABLED="${MCP_PROXY_DISABLED:-0}"

# Set to "1" to force proxy mode (skip detection, fail if proxy down)
PROXY_REQUIRED="${MCP_PROXY_REQUIRED:-0}"

# Log prefix for diagnostics
LOG_PREFIX="${MCP_PROXY_LOG_PREFIX:-[mcp-proxy-wrapper]}"

# =============================================================================
# Usage validation
# =============================================================================

if [[ $# -lt 2 ]]; then
  printf '%s ERROR: usage: %s <server-id> <command> [args...]\n' \
    "$LOG_PREFIX" "$(basename "$0")" >&2
  printf '%s   server-id: identifier for log output (e.g., fetch, git)\n' \
    "$LOG_PREFIX" >&2
  printf '%s   command:   MCP server command to execute\n' "$LOG_PREFIX" >&2
  exit 2
fi

SERVER_ID="$1"
shift
SERVER_CMD=("$@")

# =============================================================================
# Proxy availability detection
# =============================================================================

_proxy_available() {
  # Use bash's /dev/tcp to check TCP reachability without external tools
  # This is a POSIX-compatible connection check
  (
    timeout "$PROXY_CHECK_TIMEOUT" bash -c \
      ">/dev/tcp/${PROXY_HOST}/${PROXY_PORT}" 2>/dev/null
  ) && return 0 || return 1
}

# =============================================================================
# Mode resolution
# =============================================================================

proxy_mode="unknown"

if [[ "$PROXY_DISABLED" == "1" ]]; then
  proxy_mode="direct"
  printf '%s server=%s mode=direct reason=MCP_PROXY_DISABLED=1\n' \
    "$LOG_PREFIX" "$SERVER_ID" >&2
elif [[ "$PROXY_REQUIRED" == "1" ]]; then
  if _proxy_available; then
    proxy_mode="proxy"
    printf '%s server=%s mode=proxy reason=MCP_PROXY_REQUIRED=1 endpoint=%s:%s\n' \
      "$LOG_PREFIX" "$SERVER_ID" "$PROXY_HOST" "$PROXY_PORT" >&2
  else
    printf '%s server=%s ERROR: MCP_PROXY_REQUIRED=1 but proxy not reachable at %s:%s\n' \
      "$LOG_PREFIX" "$SERVER_ID" "$PROXY_HOST" "$PROXY_PORT" >&2
    exit 1
  fi
else
  # Auto-detect mode
  if _proxy_available; then
    proxy_mode="proxy"
    printf '%s server=%s mode=proxy endpoint=%s:%s detected=auto\n' \
      "$LOG_PREFIX" "$SERVER_ID" "$PROXY_HOST" "$PROXY_PORT" >&2
  else
    proxy_mode="direct"
    printf '%s server=%s mode=direct reason=proxy-not-reachable endpoint=%s:%s\n' \
      "$LOG_PREFIX" "$SERVER_ID" "$PROXY_HOST" "$PROXY_PORT" >&2
  fi
fi

# =============================================================================
# Environment injection and server launch
# =============================================================================

if [[ "$proxy_mode" == "proxy" ]]; then
  export ALL_PROXY="socks5://${PROXY_HOST}:${PROXY_PORT}"
  export HTTP_PROXY="socks5://${PROXY_HOST}:${PROXY_PORT}"
  export HTTPS_PROXY="socks5://${PROXY_HOST}:${PROXY_PORT}"
  export NO_PROXY="${MCP_NO_PROXY:-localhost,127.0.0.1,::1}"
fi

# Delegate to actual server command, preserving args and exit code
exec "${SERVER_CMD[@]}"
