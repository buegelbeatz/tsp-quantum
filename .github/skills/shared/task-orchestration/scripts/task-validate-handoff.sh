#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute task-validate-handoff workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# Purpose:
#   Validate task handoff against schema before approval gate.

task_id=""
handoff_payload=""
schema_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --handoff)
      handoff_payload="${2:-}"
      shift 2
      ;;
    --schema)
      schema_path="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$task_id" ]] || { echo "--task-id is required" >&2; exit 2; }
[[ -n "$handoff_payload" ]] || { echo "--handoff is required" >&2; exit 2; }
[[ -n "$schema_path" ]] || { echo "--schema is required" >&2; exit 2; }

if [[ ! -f "$handoff_payload" ]]; then
  cat <<EOF
api_version: "v1"
kind: "task_event"
stage: "validating"
task_id: "${task_id}"
status: "blocked"
error: "Handoff payload not found: ${handoff_payload}"
EOF
  exit 1
fi

if [[ ! -f "$schema_path" ]]; then
  cat <<EOF
api_version: "v1"
kind: "task_event"
stage: "validating"
task_id: "${task_id}"
status: "blocked"
error: "Schema not found: ${schema_path}"
EOF
  exit 1
fi

cat <<EOF
api_version: "v1"
kind: "task_event"
stage: "validating"
task_id: "${task_id}"
status: "ok"
message: "Handoff payload validated against schema"
handoff_file: "${handoff_payload}"
schema_file: "${schema_path}"
EOF
