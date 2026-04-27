#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Create feature or bugfix branches from current HEAD.
#   Enforces delivery role authorization before creating or checking out a branch.
# Security:
#   Restricted to authorized delivery roles via PERMISSIONS.csv.
#   Writes local branch refs only; no remote push is performed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
branch_name=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --branch-name)
      branch_name="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "branch-create"
require_permission "$role" "branch-checkout"
[[ -n "$branch_name" ]] || { git_yaml_error "--branch-name is required"; exit 2; }

git checkout -b "$branch_name" >/dev/null 2>&1

git_yaml_ok "branch-create"
printf 'branch: "%s"\n' "$branch_name"
