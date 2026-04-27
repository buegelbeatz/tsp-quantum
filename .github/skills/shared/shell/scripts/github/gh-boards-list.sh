#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-boards-list workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-boards-list.sh
# -----------------------------------------------------------------------------
# Purpose:
#   List GitHub Projects (boards) for an owner and emit structured YAML.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

owner="${1:-${GITHUB_OWNER:-}}"
limit="${2:-100}"

if [[ -z "$owner" ]]; then
  owner="$(github_default_owner 2>/dev/null || true)"
fi

[[ -n "$owner" ]] || die "Owner is required. Usage: gh-boards-list.sh <owner> [limit]"

github_require_token || die "GH_TOKEN is required"

boards_json="$(github_run_gh project list --owner "$owner" --limit "$limit" --format json)"

final_json="$(python3 - <<'PY' "$owner" "$boards_json"
import json
import sys

owner = sys.argv[1]
payload = json.loads(sys.argv[2])
print(json.dumps({
    "api_version": "v1",
    "kind": "github_board_list",
    "owner": owner,
    "boards": payload.get("projects", []),
}))
PY
)"

printf '%s\n' "$final_json" | github_json_to_yaml
