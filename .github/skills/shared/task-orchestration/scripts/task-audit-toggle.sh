#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Toggle repository-local audit logging state for prompt and task hooks.
# Security:
#   Writes only to .digital-runtime under the current repository.

state=""
repo_root=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --state)
      state="${2:-}"
      shift 2
      ;;
    --repo-root)
      repo_root="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$state" ]]; then
  echo "--state is required (on|off|status)" >&2
  exit 2
fi

if [[ -z "$repo_root" ]]; then
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

layer_id="${DIGITAL_LAYER_ID:-$(basename "$repo_root") }"
layer_id="${layer_id% }"
state_dir="$repo_root/.digital-runtime/layers/$layer_id/audit"
state_file="$state_dir/state.env"

enabled="1"
if [[ -f "$state_file" ]]; then
  current_line="$(grep -E '^DIGITAL_AUDIT_ENABLED=' "$state_file" 2>/dev/null || true)"
  if [[ "$current_line" == "DIGITAL_AUDIT_ENABLED=0" ]]; then
    enabled="0"
  fi
fi

case "$state" in
  on)
    mkdir -p "$state_dir"
    printf 'DIGITAL_AUDIT_ENABLED=1\n' >"$state_file"
    enabled="1"
    ;;
  off)
    mkdir -p "$state_dir"
    printf 'DIGITAL_AUDIT_ENABLED=0\n' >"$state_file"
    enabled="0"
    ;;
  status)
    ;;
  *)
    echo "--state must be on|off|status" >&2
    exit 2
    ;;
esac

cat <<EOF
api_version: "v1"
kind: "task_audit_toggle"
status: "ok"
state: "${state}"
enabled: "${enabled}"
state_file: "${state_file}"
EOF
