#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Prepare deterministic delivery work context for a role.
# Security:
#   Validates required inputs and emits structured output without exposing secrets.

role=""
ticket_id=""
slug=""
workspace="$(pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --ticket-id)
      ticket_id="${2:-}"
      shift 2
      ;;
    --slug)
      slug="${2:-}"
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
[[ -n "$ticket_id" ]] || { echo "--ticket-id is required" >&2; exit 2; }
[[ -n "$slug" ]] || { echo "--slug is required" >&2; exit 2; }

branch_name="feature/${ticket_id}-${slug}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bridge_script="$script_dir/delivery-language-bridge.sh"
bridge_output="$({ bash "$bridge_script" --mode deliver --workspace "$workspace"; } 2>&1 || true)"

cat <<EOF
api_version: "v1"
kind: "generic_delivery_prefix"
status: "ok"
role: "${role}"
ticket_id: "${ticket_id}"
branch_name: "${branch_name}"
language_guidance_hook: "${bridge_script} --mode deliver --workspace ${workspace}"
language_guidance: |
$(printf '%s\n' "$bridge_output" | sed 's/^/  /')
next_step: "implementation"
EOF
