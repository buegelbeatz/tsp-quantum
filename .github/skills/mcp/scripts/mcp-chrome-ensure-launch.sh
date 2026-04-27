#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Launch Chrome with isolated profile and CDP when --ensure is requested.
# Security:
#   Starts local browser process only; no external network calls except localhost checks.

launch_chrome() {
  if [[ "$chrome_available" == false ]]; then
    echo "ERROR: Chrome binary not found." >&2
    echo "" >&2
    print_guidance >&2
    return 1
  fi

  if [[ "$chrome_debugging" == true && "$requested_profile_with_debug" == true ]]; then
    return 0
  fi
  if [[ "$chrome_debugging" == true && "$requested_profile_with_debug" == false ]]; then
    echo "WARNING: CDP port ${CDP_PORT} is already active, but not for ${VSCODE_PROFILE} in ${MCP_CHROME_USER_DATA_DIR}." >&2
    echo "Close the conflicting Chrome debugging instance or choose another port via --port." >&2
    return 1
  fi

  mkdir -p "$MCP_CHROME_USER_DATA_DIR"

  if [[ "$requested_profile_running" == true && "$requested_profile_with_debug" == false ]]; then
    echo "WARNING: Chrome profile '${VSCODE_PROFILE}' is already running WITHOUT --remote-debugging-port." >&2
    echo "Refusing to launch a second browser instance for the same profile." >&2
    echo "Close that browser first, or restart it manually with remote debugging enabled." >&2
    return 1
  fi

  if [[ "$OS" == "Darwin" ]]; then
    open -na "Google Chrome" --args \
      --user-data-dir="${MCP_CHROME_USER_DATA_DIR}" \
      --profile-directory="${VSCODE_PROFILE}" \
      --remote-debugging-port="${CDP_PORT}" \
      --no-first-run \
      --no-default-browser-check
  else
    "$chrome_bin" \
      --user-data-dir="${MCP_CHROME_USER_DATA_DIR}" \
      --profile-directory="${VSCODE_PROFILE}" \
      --remote-debugging-port="${CDP_PORT}" \
      --no-first-run \
      --no-default-browser-check &
    disown
  fi

  local attempts=0
  while [[ $attempts -lt 15 ]]; do
    if curl -sf --connect-timeout 1 "$cdp_url_ipv4" >/dev/null 2>&1 || curl -sf --connect-timeout 1 "$cdp_url_ipv6" >/dev/null 2>&1; then
      chrome_debugging=true
      chrome_process_with_debug=true
      profile_exists=true
      return 0
    fi
    sleep 1
    ((attempts++))
  done

  echo "Chrome launched but CDP on port ${CDP_PORT} is not yet reachable after 15s." >&2
  return 1
}
