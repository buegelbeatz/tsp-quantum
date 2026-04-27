#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-pr-create workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
base_branch="${2:-main}"
head_branch="${3:-}"
pr_title="${4:-}"
pr_body_input="${5:-}"

[[ -n "$repo_slug" ]] || die "Usage: gh-pr-create.sh <owner/repo> <base> <head> <title> [body-or-file]"
[[ -n "$head_branch" ]] || die "Head branch is required"
[[ -n "$pr_title" ]] || die "PR title is required"

github_require_token || die "GH_TOKEN is required"

pr_body=""
if [[ -n "$pr_body_input" ]]; then
  if [[ -f "$pr_body_input" ]]; then
    pr_body="$(cat "$pr_body_input")"
  else
    pr_body="$pr_body_input"
  fi
fi

if [[ -n "$pr_body" ]]; then
  pr_url="$(github_run_gh pr create --repo "$repo_slug" --base "$base_branch" --head "$head_branch" --title "$pr_title" --body "$pr_body")"
else
  pr_url="$(github_run_gh pr create --repo "$repo_slug" --base "$base_branch" --head "$head_branch" --title "$pr_title" --body "")"
fi

json_payload="$(python3 - <<'PY' "$repo_slug" "$base_branch" "$head_branch" "$pr_title" "$pr_url"
import json
import sys

repo, base, head, title, url = sys.argv[1:6]
print(json.dumps({
    "api_version": "v1",
    "kind": "github_pr_create",
    "status": "ok",
    "repository": repo,
    "base": base,
    "head": head,
    "title": title,
    "pr_url": url.strip(),
}))
PY
)"

printf '%s\n' "$json_payload" | github_json_to_yaml
