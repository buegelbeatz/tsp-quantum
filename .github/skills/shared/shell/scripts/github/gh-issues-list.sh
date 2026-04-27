#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-issues-list workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-issues-list.sh
# -----------------------------------------------------------------------------
# Purpose:
#   List issues for a repository in structured YAML for downstream skills.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
state="${2:-open}"
limit="${3:-50}"

if [[ -z "$repo_slug" ]]; then
  repo_slug="$(github_repo_slug_from_git 2>/dev/null || true)"
fi

[[ -n "$repo_slug" ]] || die "Repository slug required. Usage: gh-issues-list.sh <owner/repo> [state] [limit]"

github_require_token || die "GH_TOKEN is required"

issues_json="$(github_run_gh issue list --repo "$repo_slug" --state "$state" --limit "$limit" --json number,title,state,url,labels,assignees,updatedAt,projectItems)"

final_json="$(python3 - <<'PY' "$repo_slug" "$state" "$issues_json"
import json
import sys

repo = sys.argv[1]
state = sys.argv[2]
issues = json.loads(sys.argv[3])
print(json.dumps({
    "api_version": "v1",
    "kind": "github_issue_list",
    "repository": repo,
    "state": state,
    "issues": issues,
}))
PY
)"

printf '%s\n' "$final_json" | github_json_to_yaml
