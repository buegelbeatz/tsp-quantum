#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-issue-comment workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-issue-comment.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Add a comment to an issue and emit a structured YAML acknowledgement.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
issue_number="${2:-}"
comment_body="${3:-}"

[[ -n "$repo_slug" ]] || die "Usage: gh-issue-comment.sh <owner/repo> <issue-number> <comment>"
[[ -n "$issue_number" ]] || die "Issue number is required"
[[ -n "$comment_body" ]] || die "Comment body is required"

github_require_token || die "GH_TOKEN is required"

github_run_gh issue comment "$issue_number" --repo "$repo_slug" --body "$comment_body" >/dev/null

printf '%b\n' "api_version: \"v1\"\nkind: \"github_issue_comment_result\"\nrepository: \"$repo_slug\"\nissue_number: $issue_number\ncomment_added: true"
