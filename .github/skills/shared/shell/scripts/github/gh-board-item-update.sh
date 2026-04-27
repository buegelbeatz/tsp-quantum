#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# =============================================================================
# Enterprise Script: gh-board-item-update.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Update issue labels/comments/checklist and optionally project status.
#
# Usage:
#   gh-board-item-update.sh <owner/repo> <issue-number> [--status "In Progress" --owner <owner> --project-number <n> --add-label a,b --comment "text" --check-label "Acceptance Kriterien erledigt" --check-state true]
# =============================================================================

# Security:
#   Validates required arguments, enforces token presence, and avoids eval/dynamic execution.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"
GITHUB_DIR="$(cd "$SCRIPT_DIR" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"
repo_slug="${1:-}"
issue_number="${2:-}"
shift 2 || true

[[ -n "$repo_slug" ]] || die "Repository is required"
[[ -n "$issue_number" ]] || die "Issue number is required"
github_require_token || die "GH_TOKEN is required"

board_owner="${GITHUB_OWNER:-}"
project_number=""
project_status=""
add_labels=""
comment_body=""
check_label=""
check_state="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner)
      board_owner="$2"
      shift 2
      ;;
    --project-number)
      project_number="$2"
      shift 2
      ;;
    --status)
      project_status="$2"
      shift 2
      ;;
    --add-label)
      add_labels="$2"
      shift 2
      ;;
    --comment)
      comment_body="$2"
      shift 2
      ;;
    --check-label)
      check_label="$2"
      shift 2
      ;;
    --check-state)
      check_state="$2"
      shift 2
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

if [[ -n "$add_labels" ]]; then
  github_run_gh issue edit "$issue_number" --repo "$repo_slug" --add-label "$add_labels" >/dev/null
fi

if [[ -n "$comment_body" ]]; then
  "$GITHUB_DIR/gh-issue-comment.sh" "$repo_slug" "$issue_number" "$comment_body" >/dev/null
fi

if [[ -n "$check_label" ]]; then
  "$GITHUB_DIR/gh-issue-checklist-set.sh" "$repo_slug" "$issue_number" "$check_label" "$check_state" >/dev/null
fi

status_updated="false"
if [[ -n "$project_status" ]]; then
  [[ -n "$board_owner" ]] || die "--owner is required when --status is used"
  [[ -n "$project_number" ]] || die "--project-number is required when --status is used"

  issue_url="$(github_run_gh issue view "$issue_number" --repo "$repo_slug" --json url --jq '.url')"
  project_id="$(github_run_gh project view "$project_number" --owner "$board_owner" --format json --jq '.id')"
  status_field_id="$(github_run_gh project field-list "$project_number" --owner "$board_owner" --format json --jq '.fields[] | select(.name=="Status") | .id' | head -n1)"
  option_id="$(github_run_gh project field-list "$project_number" --owner "$board_owner" --format json --jq '.fields[] | select(.name=="Status") | .options[] | select(.name=="'"$project_status"'") | .id' | head -n1)"
  item_id="$(github_run_gh project item-list "$project_number" --owner "$board_owner" --format json --jq '.items[] | select(.content.url=="'"$issue_url"'") | .id' | head -n1)"

  [[ -n "$status_field_id" ]] || die "Status field not found in project"
  [[ -n "$option_id" ]] || die "Status option '$project_status' not found"
  [[ -n "$item_id" ]] || die "Issue is not part of the target project"
  github_run_gh project item-edit --id "$item_id" --project-id "$project_id" --field-id "$status_field_id" --single-select-option-id "$option_id" >/dev/null
  status_updated="true"
fi

printf '%b\n' "api_version: \"v1\"\nkind: \"github_board_item_update_result\"\nrepository: \"$repo_slug\"\nissue_number: $issue_number\nlabels_updated: $( [[ -n "$add_labels" ]] && echo true || echo false )\ncomment_added: $( [[ -n "$comment_body" ]] && echo true || echo false )\nchecklist_updated: $( [[ -n "$check_label" ]] && echo true || echo false )\nproject_status_updated: $status_updated"
