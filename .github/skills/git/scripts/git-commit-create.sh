#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Create a git commit with a provided message through controlled git skill permissions.
#   Validates role authorization before any commit operation is performed.
# Security:
#   Restricted by role permissions via PERMISSIONS.csv.
#   Requires an explicit commit message argument; rejects empty messages.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
message=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --message)
      message="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "commit-create"
[[ -n "$message" ]] || { git_yaml_error "--message is required"; exit 2; }

if git diff --cached --quiet; then
  git_yaml_error "No staged changes available for commit"
  exit 2
fi

git commit -m "$message" >/dev/null 2>&1
commit_sha="$(git rev-parse --short HEAD)"

git_yaml_ok "commit-create"
printf 'commit: "%s"\n' "$commit_sha"
printf 'message: "%s"\n' "$message"
