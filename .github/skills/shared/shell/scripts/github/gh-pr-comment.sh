#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-pr-comment workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
pr_number="${2:-}"
comment_input="${3:-}"

[[ -n "$repo_slug" ]] || die "Usage: gh-pr-comment.sh <owner/repo> <pr-number> <comment-or-file>"
[[ -n "$pr_number" ]] || die "PR number is required"
[[ -n "$comment_input" ]] || die "Comment input is required"

github_require_token || die "GH_TOKEN is required"

comment_body="$comment_input"
if [[ -f "$comment_input" ]]; then
  comment_body="$(cat "$comment_input")"
fi

github_run_gh pr comment "$pr_number" --repo "$repo_slug" --body "$comment_body" >/dev/null

json_payload="$(python3 - <<'PY' "$repo_slug" "$pr_number"
import json
import sys

repo, number = sys.argv[1:3]
print(json.dumps({
    "api_version": "v1",
    "kind": "github_pr_comment",
    "status": "ok",
    "repository": repo,
    "pr_number": number,
}))
PY
)"

printf '%s\n' "$json_payload" | github_json_to_yaml
