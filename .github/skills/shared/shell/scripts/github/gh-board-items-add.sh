#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-board-items-add workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-board-items-add.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Add an issue URL to a GitHub Project board and emit structured YAML.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

owner="${1:-${GITHUB_OWNER:-}}"
project_number="${2:-}"
issue_url="${3:-}"

if [[ -z "$owner" ]]; then
    owner="$(github_default_owner 2>/dev/null || true)"
fi

[[ -n "$owner" ]] || die "Owner is required. Usage: gh-board-items-add.sh <owner> <project-number> <issue-url>"
[[ -n "$project_number" ]] || die "Project number is required"
[[ -n "$issue_url" ]] || die "Issue URL is required"

github_require_token || die "GH_TOKEN is required"

add_json="$(github_run_gh project item-add "$project_number" --owner "$owner" --url "$issue_url" --format json 2>/dev/null || echo '{}')"

final_json="$(python3 - <<'PY' "$owner" "$project_number" "$issue_url" "$add_json"
import json
import sys

owner = sys.argv[1]
project_number = int(sys.argv[2])
issue_url = sys.argv[3]
raw = json.loads(sys.argv[4]) if sys.argv[4].strip() else {}

print(json.dumps({
    "api_version": "v1",
    "kind": "github_board_item_add_result",
    "owner": owner,
    "project_number": project_number,
    "issue_url": issue_url,
    "result": raw,
}))
PY
)"

printf '%s\n' "$final_json" | github_json_to_yaml
