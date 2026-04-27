#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the session end workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Hook: session-end
# Logs the end of a Copilot agent session to .digital-artifacts/70-audits/.
# Called automatically by the layer orchestration at session close.
#
# Environment Variables:
#   DIGITAL_SESSION_ID   — session identifier (must match session-start)
#   DIGITAL_TASK_ID      — optional task/ticket reference
#   DIGITAL_ROLE         — agent role performing the session (default: copilot)
#   DIGITAL_SESSION_STATUS — ok | error | cancelled (default: ok)
#   DIGITAL_AUDIT_ROOT   — override for audit output directory

script_root="$(cd "$(dirname "$0")" && pwd)"
audit_log="${script_root}/../skills/shared/task-orchestration/scripts/task-audit-log.sh"

session_id="${DIGITAL_SESSION_ID:-session-unknown}"
task_id="${DIGITAL_TASK_ID:-session-task}"
role="${DIGITAL_ROLE:-copilot}"
status="${DIGITAL_SESSION_STATUS:-ok}"
audit_root="${DIGITAL_AUDIT_ROOT:-.digital-artifacts/70-audits}"

bash "$audit_log" \
  --mode short \
  --task-id "$task_id" \
  --role "$role" \
  --action "session-end" \
  --status "$status" \
  --session-id "$session_id" \
  --audits-root "$audit_root" \
  --notes "event=session-end status=${status}"
