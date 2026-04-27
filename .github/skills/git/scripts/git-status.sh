#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Retrieve the current branch name and working tree status, emitted as YAML.
#   Provides a structured status snapshot for delivery agents.
# Security:
#   Restricted to generic-deliver role via PERMISSIONS.csv.
#   Performs read-only git status and branch operations; no modifications.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "read-status"

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")"
porcelain="$(git status --porcelain 2>/dev/null || true)"

git_yaml_ok "read-status"
printf 'branch: "%s"\n' "$branch"
printf 'porcelain: |\n'
if [[ -n "$porcelain" ]]; then
  while IFS= read -r line; do
    printf '  %s\n' "$line"
  done <<< "$porcelain"
fi
