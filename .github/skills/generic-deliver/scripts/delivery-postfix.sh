#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Finalize deterministic delivery handoff after implementation.
# Security:
#   Emits structured workflow output and mandatory human approval reminder.

role=""
branch_name=""
base_ref="master"
review_report=""
workspace="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --branch)
      branch_name="${2:-}"
      shift 2
      ;;
    --base-ref)
      base_ref="${2:-master}"
      shift 2
      ;;
    --review-report)
      review_report="${2:-}"
      shift 2
      ;;
    --workspace)
      workspace="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$role" ]] || { echo "--role is required" >&2; exit 2; }
[[ -n "$branch_name" ]] || { echo "--branch is required" >&2; exit 2; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bridge_script="$script_dir/delivery-language-bridge.sh"
bridge_output="$({ bash "$bridge_script" --mode review --workspace "$workspace"; } 2>&1 || true)"

cat <<EOF
api_version: "v1"
kind: "generic_delivery_postfix"
status: "ok"
role: "${role}"
branch: "${branch_name}"
base_ref: "${base_ref}"
review_report: "${review_report}"
language_guidance_hook: "${bridge_script} --mode review --workspace ${workspace}"
language_guidance: |
$(printf '%s\n' "$bridge_output" | sed 's/^/  /')
human_approval_required: true
message: "A human must approve and merge this pull request."
EOF
