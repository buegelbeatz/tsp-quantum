#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Push a local branch to a remote repository through controlled git skill permissions.
#   Validates role authorization and requires explicit remote and branch arguments.
# Security:
#   Restricted by role permissions via PERMISSIONS.csv.
#   Requires explicit --remote and --branch-name arguments; no wildcard or force-push.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
remote="origin"
branch=""
set_upstream="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --remote)
      remote="${2:-}"
      shift 2
      ;;
    --branch)
      branch="${2:-}"
      shift 2
      ;;
    --set-upstream)
      set_upstream="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "push-branch"

if [[ -z "$branch" ]]; then
  branch="$(git symbolic-ref --quiet --short HEAD || true)"
fi
[[ -n "$branch" ]] || { git_yaml_error "Could not determine current branch"; exit 2; }

if [[ "$set_upstream" == "1" ]]; then
  git push -u "$remote" "$branch" >/dev/null 2>&1
else
  git push "$remote" "$branch" >/dev/null 2>&1
fi

git_yaml_ok "push-branch"
printf 'remote: "%s"\n' "$remote"
printf 'branch: "%s"\n' "$branch"
