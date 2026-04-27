#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Detection helpers for Chrome binary, profile/process state, and CDP reachability.
# Security:
#   Reads local process table and localhost CDP endpoints only.

find_chrome_binary() {
  local candidate
  if [[ -n "${CHROME_BIN:-}" ]]; then
    if [[ -x "${CHROME_BIN}" ]]; then
      printf '%s\n' "${CHROME_BIN}"
      return 0
    fi
    return 1
  fi

  for candidate in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  for candidate in google-chrome-beta google-chrome-stable google-chrome chromium-browser chromium; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

detect_chrome_state() {
  chrome_bin="$(find_chrome_binary 2>/dev/null || true)"
  chrome_available=$([[ -n "$chrome_bin" ]] && echo true || echo false)
  chrome_version=""
  [[ "$chrome_available" == true ]] && chrome_version="$("$chrome_bin" --version 2>/dev/null || true)"

  OS="$(uname -s)"
  vscode_profile_path="${MCP_CHROME_USER_DATA_DIR}/${VSCODE_PROFILE}"
  profile_exists=$([[ -d "$vscode_profile_path" ]] && echo true || echo false)

  cdp_url_ipv4="http://127.0.0.1:${CDP_PORT}/json/version"
  cdp_url_ipv6="http://[::1]:${CDP_PORT}/json/version"

  local process_commands
  process_commands="$(ps axww -o command= 2>/dev/null || true)"

  chrome_process_with_debug=false
  if printf '%s\n' "$process_commands" | grep -qE "[Cc]hrome.*remote-debugging-port=${CDP_PORT}"; then
    chrome_process_with_debug=true
  fi

  requested_profile_running=false
  requested_profile_with_debug=false
  local escaped_data_dir="${MCP_CHROME_USER_DATA_DIR//\//\\/}"

  if printf '%s\n' "$process_commands" | grep -qE "[Cc]hrome.*--user-data-dir=${escaped_data_dir}( |$).*--profile-directory=${VSCODE_PROFILE}( |$)"; then
    requested_profile_running=true
  fi
  if printf '%s\n' "$process_commands" | grep -qE "[Cc]hrome.*--user-data-dir=${escaped_data_dir}( |$).*--profile-directory=${VSCODE_PROFILE}( |$).*remote-debugging-port=${CDP_PORT}"; then
    requested_profile_with_debug=true
  fi

  chrome_debugging=false
  cdp_browser_info=""
  cdp_active_endpoint=""
  if curl -sf --connect-timeout 2 "$cdp_url_ipv4" >/dev/null 2>&1; then
    chrome_debugging=true
    cdp_active_endpoint="$cdp_url_ipv4"
    cdp_browser_info="$(curl -sf --connect-timeout 2 "$cdp_url_ipv4" 2>/dev/null || true)"
  elif curl -sf --connect-timeout 2 "$cdp_url_ipv6" >/dev/null 2>&1; then
    chrome_debugging=true
    cdp_active_endpoint="$cdp_url_ipv6"
    cdp_browser_info="$(curl -sf --connect-timeout 2 "$cdp_url_ipv6" 2>/dev/null || true)"
  fi
}
