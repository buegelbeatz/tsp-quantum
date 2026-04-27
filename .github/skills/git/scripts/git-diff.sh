#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Display unified or staged-only diff output for the working tree.
#   Validates role authorization before executing any diff operation.
# Security:
#   Restricted to authorized delivery roles via PERMISSIONS.csv.
#   Performs read-only git diff operations; no file modifications.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
mode="head"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-head}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "read-diff"

if [[ "$mode" == "staged" ]]; then
  diff_text="$(git diff --staged 2>/dev/null || true)"
else
  diff_text="$(git diff HEAD 2>/dev/null || true)"
fi

git_yaml_ok "read-diff"
printf 'mode: "%s"\n' "$mode"
printf 'diff: |\n'
if [[ -n "$diff_text" ]]; then
  while IFS= read -r line; do
    printf '  %s\n' "$line"
  done <<< "$diff_text"
fi
