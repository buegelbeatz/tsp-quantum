#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-issue-checklist-set workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-issue-checklist-set.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Set or create a markdown checklist marker in issue body.
#   Example marker: "Acceptance Kriterien erledigt"
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
issue_number="${2:-}"
check_label="${3:-}"
check_state="${4:-false}"

[[ -n "$repo_slug" ]] || die "Usage: gh-issue-checklist-set.sh <owner/repo> <issue-number> <check-label> <true|false>"
[[ -n "$issue_number" ]] || die "Issue number is required"
[[ -n "$check_label" ]] || die "Checklist label is required"

github_require_token || die "GH_TOKEN is required"

current_body="$(github_run_gh issue view "$issue_number" --repo "$repo_slug" --json body --jq '.body')"
updated_body="$(python3 - <<'PY' "$current_body" "$check_label" "$check_state"
import re
import sys

body = sys.argv[1]
label = sys.argv[2]
state = sys.argv[3].lower() == "true"
mark = "x" if state else " "
line = f"- [{mark}] {label}"

pattern = re.compile(rf"^- \[[ xX]\] {re.escape(label)}$", re.MULTILINE)
if pattern.search(body):
    body = pattern.sub(line, body)
else:
    if body and not body.endswith("\n"):
        body += "\n"
    if "## Checklist" not in body:
        body += "\n## Checklist\n"
    body += f"{line}\n"

print(body)
PY
)"

github_run_gh issue edit "$issue_number" --repo "$repo_slug" --body "$updated_body" >/dev/null

printf '%b\n' "api_version: \"v1\"\nkind: \"github_issue_checklist_update\"\nrepository: \"$repo_slug\"\nissue_number: $issue_number\ncheck_label: \"$check_label\"\ncheck_state: $check_state\nupdated: true"
