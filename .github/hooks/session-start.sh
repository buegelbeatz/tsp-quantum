#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the session start workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Hook: session-start
# Logs the start of a Copilot agent session to .digital-artifacts/70-audits/.
# Called automatically by the layer orchestration at session open.
#
# Environment Variables:
#   DIGITAL_SESSION_ID   — session identifier (auto-generated if unset)
#   DIGITAL_TASK_ID      — optional task/ticket reference
#   DIGITAL_ROLE         — agent role performing the session (default: copilot)
#   DIGITAL_AUDIT_ROOT   — override for audit output directory

script_root="$(cd "$(dirname "$0")" && pwd)"
audit_log="${script_root}/../skills/shared/task-orchestration/scripts/task-audit-log.sh"

session_id="${DIGITAL_SESSION_ID:-session-$(date +%Y%m%d-%H%M%S)-$$}"
task_id="${DIGITAL_TASK_ID:-session-task}"
role="${DIGITAL_ROLE:-copilot}"
audit_root="${DIGITAL_AUDIT_ROOT:-.digital-artifacts/70-audits}"

export DIGITAL_SESSION_ID="$session_id"

bash "$audit_log" \
  --mode short \
  --task-id "$task_id" \
  --role "$role" \
  --action "session-start" \
  --status ok \
  --session-id "$session_id" \
  --audits-root "$audit_root" \
  --notes "event=session-start"
