#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Print setup guidance for Chrome MCP profile and CDP configuration.
# Security:
#   Emits static instructions only.

print_guidance() {
  cat <<GUIDANCE
Chrome MCP Setup Guide
======================
Required for: MCP chrome-devtools integration with visible browser and
              dedicated profile and isolated user-data-dir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 — Install Chrome Beta (or stable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  macOS:  https://www.google.com/chrome/
  Linux:  https://www.google.com/chrome/
          (or distro package manager)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 2 — Launch Chrome with the dedicated "${VSCODE_PROFILE}" profile,
         isolated user-data-dir, and
         remote debugging enabled (port ${CDP_PORT})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  macOS (Chrome stable):
    open -na "Google Chrome" --args \
      --user-data-dir="${MCP_CHROME_USER_DATA_DIR}" \
      --profile-directory="${VSCODE_PROFILE}" \
      --remote-debugging-port=${CDP_PORT} \
      --no-first-run \
      --no-default-browser-check

  Linux:
    google-chrome-beta \
      --user-data-dir="${MCP_CHROME_USER_DATA_DIR}" \
      --profile-directory="${VSCODE_PROFILE}" \
      --remote-debugging-port=${CDP_PORT} \
      --no-first-run &

  Tip: Run this ONCE manually; afterwards use '--ensure' to auto-launch.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 3 — Verify CDP is reachable
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  curl http://localhost:${CDP_PORT}/json/version
  curl http://127.0.0.1:${CDP_PORT}/json/version
  curl http://[::1]:${CDP_PORT}/json/version

  Expected: JSON response with Chrome version and WebSocket URL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 4 — Log in to required websites in the "${VSCODE_PROFILE}" profile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open websites manually in the Chrome window that just appeared.
  Login sessions are stored in:
    ${vscode_profile_path}
  They persist across VS Code / MCP restarts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Notes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• The "${VSCODE_PROFILE}" profile is isolated from your default browser
  history, cookies, and extensions.
• This dedicated vscode profile should be used only for MCP/automation tasks.
• Remote debugging (CDP) is restricted to localhost — not exposed externally.
• MCP server config: chrome-devtools-mcp@latest --browserUrl http://[::1]:${CDP_PORT}
• This script can be run with --ensure to auto-launch Chrome automatically.
• If this dedicated user-data-dir is already open WITHOUT --remote-debugging-port,
  close that instance first.
GUIDANCE
}
