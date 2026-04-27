#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Stage selected files for commit through controlled git skill permissions.
#   Requires explicit file path arguments and role authorization.
# Security:
#   Restricted by role permissions via PERMISSIONS.csv.
#   Accepts only explicit file paths as arguments; no wildcard expansion via this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
paths_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --paths-file)
      paths_file="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "stage-add"
[[ -n "$paths_file" ]] || { git_yaml_error "--paths-file is required"; exit 2; }
[[ -f "$paths_file" ]] || { git_yaml_error "paths file not found: $paths_file"; exit 2; }

paths=()
while IFS= read -r line; do
  [[ -n "$line" ]] || continue
  paths+=("$line")
done <"$paths_file"

if [[ ${#paths[@]} -eq 0 ]]; then
  git_yaml_error "paths file is empty"
  exit 2
fi

git add -- "${paths[@]}"

git_yaml_ok "stage-add"
printf 'paths_count: "%s"\n' "${#paths[@]}"
