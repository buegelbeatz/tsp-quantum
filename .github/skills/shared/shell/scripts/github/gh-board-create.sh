#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-board-create workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-board-create.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Create a GitHub Project board and emit structured YAML for downstream use.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

owner="${1:-${GITHUB_OWNER:-}}"
title="${2:-}"
repo_slug="${3:-}"

if [[ -z "$owner" ]]; then
  owner="$(github_default_owner 2>/dev/null || true)"
fi

if [[ -z "$repo_slug" ]]; then
  repo_slug="$(github_default_repo_slug 2>/dev/null || true)"
fi

[[ -n "$owner" ]] || die "Owner is required. Usage: gh-board-create.sh <owner> <title> [owner/repo]"
[[ -n "$title" ]] || die "Title is required. Usage: gh-board-create.sh <owner> <title> [owner/repo]"

github_require_token || die "GH_TOKEN is required"

github_run_gh project create --owner "$owner" --title "$title" >/dev/null
boards_json="$(github_run_gh project list --owner "$owner" --limit 200 --format json)"

created_number="$(python3 - <<'PY' "$title" "$boards_json"
import json
import sys

title = sys.argv[1]
payload = json.loads(sys.argv[2])
projects = payload.get("projects", [])
matching = [item for item in projects if item.get("title") == title]
matching.sort(key=lambda item: item.get("number", 0), reverse=True)
created = matching[0] if matching else None
print("" if created is None else created.get("number", ""))
PY
)"

link_owner="$owner"
if [[ "$link_owner" == "@me" ]]; then
  link_owner="$(github_run_gh api /user --jq '.login')"
fi

linked_repo=""
if [[ -n "$repo_slug" && -n "$created_number" ]]; then
  github_run_gh project link "$created_number" --owner "$link_owner" --repo "$repo_slug" >/dev/null
  linked_repo="$repo_slug"
fi

final_json="$(python3 - <<'PY' "$owner" "$title" "$boards_json" "$linked_repo"
import json
import sys

owner = sys.argv[1]
title = sys.argv[2]
payload = json.loads(sys.argv[3])
linked_repo = sys.argv[4]
projects = payload.get("projects", [])
matching = [item for item in projects if item.get("title") == title]
matching.sort(key=lambda item: item.get("number", 0), reverse=True)
created = matching[0] if matching else None

print(json.dumps({
    "api_version": "v1",
    "kind": "github_board_create_result",
    "owner": owner,
    "title": title,
    "created": bool(created),
    "linked_repository": linked_repo or None,
    "board": created,
}))
PY
)"

printf '%s\n' "$final_json" | github_json_to_yaml
