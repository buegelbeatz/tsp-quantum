#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the pre message workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Hook: pre-message
# Logs an agent message request (user turn) before processing.
# Called by delivery prefix scripts for each agent interaction.
#
# Usage:
#   bash pre-message.sh [--message-id <id>] [--summary <text>]
#
# Environment Variables:
#   DIGITAL_SESSION_ID   — active session identifier
#   DIGITAL_TASK_ID      — optional task/ticket reference
#   DIGITAL_ROLE         — agent role (default: copilot)
#   DIGITAL_AUDIT_ROOT   — override for audit output directory

script_root="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "${script_root}/../.." && pwd)"
audit_log="${script_root}/../skills/shared/task-orchestration/scripts/task-audit-log.sh"

if [[ -d "${repo_root}/.venv" ]]; then
  echo "[ERROR] Forbidden environment detected: ${repo_root}/.venv" >&2
  echo "[ERROR] Use layer runtime environments under .digital-runtime/layers/... only." >&2
  exit 1
fi

message_id=""
summary=""
handoff_expected=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message-id) message_id="${2:-}"; shift 2 ;;
    --summary)    summary="${2:-}"; shift 2 ;;
    --handoff-expected) handoff_expected="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

session_id="${DIGITAL_SESSION_ID:-}"
task_id="${DIGITAL_TASK_ID:-session-task}"
role="${DIGITAL_ROLE:-copilot}"
audit_root="${DIGITAL_AUDIT_ROOT:-.digital-artifacts/70-audits}"

notes="event=pre-message"
[[ -n "$message_id" ]] && notes="${notes} message_id=${message_id}"
[[ -n "$summary"    ]] && notes="${notes} summary=${summary}"

extra_args=()
[[ -n "$handoff_expected" ]] && extra_args+=(--handoff-expected "$handoff_expected")

bash "$audit_log" \
  --mode short \
  --task-id "$task_id" \
  --role "$role" \
  --action "pre-message" \
  --status ok \
  --message-id "$message_id" \
  --session-id "$session_id" \
  --audits-root "$audit_root" \
  --notes "$notes" \
  "${extra_args[@]}"
