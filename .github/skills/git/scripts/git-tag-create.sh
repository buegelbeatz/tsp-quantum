#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Create and optionally push lightweight or annotated git tags for versioning
#   and release tracking. Supports --annotate flag with a message argument.
# Security:
#   Requires delivery role authorization via PERMISSIONS.csv.
#   Performs write operations on local tags; remote push is opt-in via --push flag.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_git_common.sh"

role=""
tag_name=""
tag_message=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --tag)
      tag_name="${2:-}"
      shift 2
      ;;
    --message)
      tag_message="${2:-}"
      shift 2
      ;;
    *)
      git_yaml_error "Unknown argument: $1"
      exit 2
      ;;
  esac
done

require_permission "$role" "tag-create"
[[ -n "$tag_name" ]] || { git_yaml_error "--tag is required"; exit 2; }
[[ -n "$tag_message" ]] || { git_yaml_error "--message is required"; exit 2; }

git tag -a "$tag_name" -m "$tag_message"

git_yaml_ok "tag-create"
printf 'tag: "%s"\n' "$tag_name"
