#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute task-assign workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# Purpose:
#   Assign a task to a role with explicit context capture.

role=""
task_id=""
owner_agent=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      role="${2:-}"
      shift 2
      ;;
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --owner-agent)
      owner_agent="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$role" ]] || { echo "--role is required" >&2; exit 2; }
[[ -n "$task_id" ]] || { echo "--task-id is required" >&2; exit 2; }
[[ -n "$owner_agent" ]] || { echo "--owner-agent is required" >&2; exit 2; }

cat <<EOF
api_version: "v1"
kind: "task_event"
stage: "assigned"
task_id: "${task_id}"
role: "${role}"
owner_agent: "${owner_agent}"
assigned_at: "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
status: "ok"
message: "Task assigned to role ${role}"
EOF
