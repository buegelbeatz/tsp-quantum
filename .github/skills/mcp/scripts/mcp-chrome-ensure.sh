#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Ensure Chrome runs with isolated profile and localhost CDP for MCP usage.
# Security:
#   Local-only process/file probing and optional local process launch.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v git >/dev/null 2>&1; then
	REPO_ROOT="$(git -C "$SKILL_DIR" rev-parse --show-toplevel)"
else
	REPO_ROOT="$(cd "$SKILL_DIR/../../../.." && pwd)"
fi

DETECT_LIB="$SCRIPT_DIR/mcp-chrome-ensure-detect.sh"
GUIDANCE_LIB="$SCRIPT_DIR/mcp-chrome-ensure-guidance.sh"
LAUNCH_LIB="$SCRIPT_DIR/mcp-chrome-ensure-launch.sh"
for lib in "$DETECT_LIB" "$GUIDANCE_LIB" "$LAUNCH_LIB"; do
	[[ -f "$lib" ]] || { echo "Missing helper: $lib" >&2; exit 2; }
done
# shellcheck source=/dev/null
source "$DETECT_LIB"
# shellcheck source=/dev/null
source "$GUIDANCE_LIB"
# shellcheck source=/dev/null
source "$LAUNCH_LIB"

CDP_PORT="${CHROME_CDP_PORT:-9222}"
VSCODE_PROFILE="${CHROME_VSCODE_PROFILE:-VSCode}"
MCP_CHROME_USER_DATA_DIR="${CHROME_MCP_USER_DATA_DIR:-$REPO_ROOT/.digital-runtime/chrome/VScode}"
MODE="check"

while [[ $# -gt 0 ]]; do
	case "$1" in
		--check)    MODE="check";   shift ;;
		--ensure)   MODE="ensure";  shift ;;
		--guidance) MODE="guidance"; shift ;;
		--port)     CDP_PORT="${2:?'--port requires a value'}"; shift 2 ;;
		--profile)  VSCODE_PROFILE="${2:?'--profile requires a value'}"; shift 2 ;;
		--user-data-dir) MCP_CHROME_USER_DATA_DIR="${2:?'--user-data-dir requires a value'}"; shift 2 ;;
		*)
			echo "Unknown argument: $1" >&2
			exit 2
			;;
	esac
done

detect_chrome_state
status="ok"
[[ "$chrome_available" == false ]] && status="fail"
[[ "$chrome_debugging" == false && "$status" != "fail" ]] && status="warn"

# ---------------------------------------------------------------------------
# Mode dispatch
# ---------------------------------------------------------------------------
case "$MODE" in
	guidance)
		print_guidance
		exit 0
		;;
	ensure)
		launch_chrome
		detect_chrome_state
		status="ok"
		[[ "$chrome_available" == false ]] && status="fail"
		[[ "$chrome_debugging" == false && "$status" != "fail" ]] && status="warn"
		;;
	check) ;;
esac

# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------
printf '%s\n' "api_version: \"v1\""
printf '%s\n' "kind: \"mcp_chrome_ensure\""
printf '%s\n' "status: \"$status\""
printf '%s\n' "chrome_available: $chrome_available"
printf '%s\n' "chrome_path: \"${chrome_bin}\""
printf '%s\n' "chrome_version: \"${chrome_version}\""
printf '%s\n' "chrome_debugging: $chrome_debugging"
printf '%s\n' "chrome_process_with_debug: $chrome_process_with_debug"
printf '%s\n' "requested_profile_running: $requested_profile_running"
printf '%s\n' "requested_profile_with_debug: $requested_profile_with_debug"
printf '%s\n' "cdp_port: $CDP_PORT"
printf '%s\n' "cdp_endpoint: \"${cdp_active_endpoint}\""
printf '%s\n' "profile_name: \"${VSCODE_PROFILE}\""
printf '%s\n' "user_data_dir: \"${MCP_CHROME_USER_DATA_DIR}\""
printf '%s\n' "profile_path: \"${vscode_profile_path}\""
printf '%s\n' "profile_exists: $profile_exists"
if [[ "$status" != "ok" ]]; then
	printf '%s\n' "guidance: \"Run: mcp-chrome-ensure.sh --guidance\""
fi

[[ "$status" == "fail" ]] && exit 1
exit 0
