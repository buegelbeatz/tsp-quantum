#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Display the commit log in oneline format with role-based access control.
#   Supports optional max-count parameter to limit log output.
# Security:
#   Restricted to authorized delivery roles via PERMISSIONS.csv.
#   Performs read-only git log operations; no repository state is modified.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
limit="10"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --limit)
      limit="${2:-10}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "read-log"

log_lines="$(git log --pretty=format:'%H|%s' -n "$limit" 2>/dev/null || true)"

git_yaml_ok "read-log"
printf 'limit: %s\n' "$limit"
printf 'entries:\n'
if [[ -n "$log_lines" ]]; then
  while IFS='|' read -r sha subject; do
    printf '  - sha: "%s"\n' "$sha"
    printf '    subject: "%s"\n' "${subject//\"/\\\"}"
  done <<< "$log_lines"
fi
