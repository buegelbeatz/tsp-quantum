#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute task-approve-gate workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# Purpose:
#   Emit explicit human approval gate for task progression.
#   This script does NOT approve; it records that approval is required and who can grant it.

task_id=""
role=""
required_approvers=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --role)
      role="${2:-}"
      shift 2
      ;;
    --approvers)
      required_approvers="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$task_id" ]] || { echo "--task-id is required" >&2; exit 2; }
[[ -n "$role" ]] || { echo "--role is required" >&2; exit 2; }

cat <<EOF
api_version: "v1"
kind: "task_event"
stage: "approval_gate"
task_id: "${task_id}"
role: "${role}"
status: "requires_approval"
message: "Human approval required before task can proceed"
required_approvers: "${required_approvers:-maintainers}"
approval_url: "https://github.com/<org>/<repo>/pulls"
instructions: "Review changes and approve the pull request to proceed with task handoff"
EOF
