#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the artifacts testdata 2 input workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Prompt entrypoint: /artifacts-testdata-2-input
# Skill owner: agile-coach

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

[[ -f "$REPO_ROOT/.env" ]] && set -a && source "$REPO_ROOT/.env" && set +a

ARTIFACTS_BOOTSTRAP="$SCRIPT_DIR/artifacts-bootstrap.sh"
TESTDATA_SRC="$REPO_ROOT/.github/skills/artifacts/templates/digital-artifacts/99-testdata"
DOCUMENTS_TARGET="$REPO_ROOT/.digital-artifacts/00-input/documents"
I2D_SCRIPT="$SCRIPT_DIR/artifacts-input-2-data.sh"

progress() { printf '[progress][artifacts-testdata-2-input] step=%s action=%s\n' "$1" "$2"; }

progress "1/5" "bootstrap"
bash "$ARTIFACTS_BOOTSTRAP" "$REPO_ROOT/.digital-artifacts"

progress "2/5" "fixture-refill"
mkdir -p "$DOCUMENTS_TARGET"
cp "$TESTDATA_SRC"/* "$DOCUMENTS_TARGET/"
COPIED="$(find "$DOCUMENTS_TARGET" -maxdepth 1 -type f | wc -l | tr -d ' ')"
printf 'fixtures: %s file(s) copied to %s\n' "$COPIED" "$DOCUMENTS_TARGET"

progress "3/5" "environment-summary"
printf '\nIntegration readiness:\n'

check_var() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    printf '  SET      %s\n' "$name"
  else
    printf '  NOT SET  %s\n' "$name"
  fi
}

check_var DIGITAL_TEAM_VISION_API_URL
check_var DIGITAL_TEAM_VISION_API_KEY
check_var DIGITAL_TEAM_VISION_MODEL
check_var KLAXOON_API_URL
check_var KLAXOON_CLIENT_ID
check_var KLAXOON_CLIENT_SECRET

progress "4/5" "completion"
printf '\nResult:\n'
printf '  input files ready: %s\n' "$COPIED"
printf '  input path:        %s\n' "$DOCUMENTS_TARGET"
printf '  status:            ok\n'
