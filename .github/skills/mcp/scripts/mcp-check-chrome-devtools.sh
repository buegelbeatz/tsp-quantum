#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Check availability of npx and Chrome/Chromium binaries for Chrome DevTools MCP.
# Security:
#   Performs local binary probing only and emits structured non-secret status output.

probe_package=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --probe-package) probe_package=1; shift ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

find_chrome_binary() {
  local candidate
  if [[ -n "${CHROME_BIN:-}" && -x "${CHROME_BIN}" ]]; then
    printf '%s\n' "${CHROME_BIN}"
    return 0
  fi
  for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

npx_bin="${NPX_BIN:-}"
npx_bin="${npx_bin:-$(command -v npx 2>/dev/null || true)}"
chrome_bin=""
chrome_bin_detected="$(find_chrome_binary 2>/dev/null || true)"
[[ -n "$chrome_bin_detected" ]] && chrome_bin="$chrome_bin_detected"

npx_available=$([[ -n "$npx_bin" && -x "$npx_bin" ]] && echo true || echo false)
chrome_available=$([[ -n "$chrome_bin" && -x "$chrome_bin" ]] && echo true || echo false)
probe_ok=false
status="warn"

if [[ "$npx_available" == false ]]; then
  status="fail"
elif [[ "$chrome_available" == false ]]; then
  status="warn"
else
  status="ok"
fi

if [[ "$probe_package" == 1 && "$npx_available" == true ]]; then
  if "$npx_bin" -y chrome-devtools-mcp@latest --help >/dev/null 2>&1; then
    probe_ok=true
  else
    probe_ok=false
    if [[ "$status" == "ok" ]]; then
      status="warn"
    fi
  fi
fi

chrome_version=""
[[ "$chrome_available" == true ]] && chrome_version="$("$chrome_bin" --version 2>/dev/null || true)"

printf '%s\n' "api_version: \"v1\""
printf '%s\n' "kind: \"mcp_chrome_devtools_check\""
printf '%s\n' "status: \"$status\""
printf '%s\n' "npx_available: $npx_available"
printf '%s\n' "chrome_available: $chrome_available"
printf '%s\n' "npx_path: \"${npx_bin}\""
printf '%s\n' "chrome_path: \"${chrome_bin}\""
printf '%s\n' "chrome_version: \"${chrome_version}\""
printf '%s\n' "probe_requested: $([[ "$probe_package" == 1 ]] && echo true || echo false)"
printf '%s\n' "probe_ok: $probe_ok"
cat <<'EOF'
setup_steps:
  - "Install Node.js so the npx command is available."
  - "Install Google Chrome."
  - "Start Chrome with dedicated MCP profile and user-data-dir plus --remote-debugging-port=9222."
  - "Verify CDP responds at http://127.0.0.1:9222/json/version or http://[::1]:9222/json/version."
  - "Use MCP args: chrome-devtools-mcp@latest --browserUrl http://[::1]:9222 --no-usage-statistics."
EOF

if [[ "$status" == fail ]]; then
  exit 1
fi
