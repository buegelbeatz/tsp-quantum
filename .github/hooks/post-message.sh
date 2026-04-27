#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the post message workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Hook: post-message
# Logs an agent message completion (assistant turn) after processing.
# Writes a full audit entry including artifacts produced and handoff details.
#
# Usage:
#   bash post-message.sh [--message-id <id>] [--artifacts <csv>]
#                        [--handoff-file <path>] [--status ok|error]
#                        [--assumptions <text>] [--open-questions <text>]
#
# Environment Variables:
#   DIGITAL_SESSION_ID   — active session identifier
#   DIGITAL_TASK_ID      — optional task/ticket reference
#   DIGITAL_ROLE         — agent role (default: copilot)
#   DIGITAL_AUDIT_ROOT   — override for audit output directory

script_root="$(cd "$(dirname "$0")" && pwd)"
audit_log="${script_root}/../skills/shared/task-orchestration/scripts/task-audit-log.sh"

message_id=""
summary=""
artifacts=""
handoff_file=""
status="ok"
assumptions=""
open_questions=""
status_summary=""
next_step=""
execution_stack=""
skills_trace=""
agents_trace=""
instructions_trace=""
communication_flow=""
mcp_endpoints_trace=""
handoff_expected=""
timing_total_ms=""
timing_pre_hook_ms=""
timing_command_ms=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --message-id)      message_id="${2:-}";      shift 2 ;;
    --summary)         summary="${2:-}";         shift 2 ;;
    --artifacts)       artifacts="${2:-}";        shift 2 ;;
    --handoff-file)    handoff_file="${2:-}";     shift 2 ;;
    --status)          status="${2:-ok}";         shift 2 ;;
    --assumptions)     assumptions="${2:-}";      shift 2 ;;
    --open-questions)  open_questions="${2:-}";   shift 2 ;;
    --status-summary)  status_summary="${2:-}";   shift 2 ;;
    --next-step)       next_step="${2:-}";        shift 2 ;;
    --execution-stack) execution_stack="${2:-}"; shift 2 ;;
    --skills-trace) skills_trace="${2:-}"; shift 2 ;;
    --agents-trace) agents_trace="${2:-}"; shift 2 ;;
    --instructions-trace) instructions_trace="${2:-}"; shift 2 ;;
    --communication-flow) communication_flow="${2:-}"; shift 2 ;;
    --mcp-endpoints-trace) mcp_endpoints_trace="${2:-}"; shift 2 ;;
    --handoff-expected) handoff_expected="${2:-}"; shift 2 ;;
    --timing-total-ms) timing_total_ms="${2:-}"; shift 2 ;;
    --timing-pre-hook-ms) timing_pre_hook_ms="${2:-}"; shift 2 ;;
    --timing-command-ms) timing_command_ms="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

session_id="${DIGITAL_SESSION_ID:-}"
task_id="${DIGITAL_TASK_ID:-session-task}"
role="${DIGITAL_ROLE:-copilot}"
audit_root="${DIGITAL_AUDIT_ROOT:-.digital-artifacts/70-audits}"

notes="event=post-message"
[[ -n "$message_id" ]] && notes="${notes} message_id=${message_id}"
[[ -n "$summary"    ]] && notes="${notes} summary=${summary}"

extra_args=()
[[ -n "$artifacts"      ]] && extra_args+=(--artifacts "$artifacts")
[[ -n "$handoff_file"   ]] && extra_args+=(--handoff-file "$handoff_file")
[[ -n "$assumptions"    ]] && extra_args+=(--assumptions "$assumptions")
[[ -n "$open_questions" ]] && extra_args+=(--open-questions "$open_questions")
[[ -n "$status_summary" ]] && extra_args+=(--status-summary "$status_summary")
[[ -n "$next_step" ]] && extra_args+=(--next-step "$next_step")
[[ -n "$message_id"      ]] && extra_args+=(--message-id "$message_id")
[[ -n "$execution_stack" ]] && extra_args+=(--execution-stack "$execution_stack")
[[ -n "$skills_trace"    ]] && extra_args+=(--skills-trace "$skills_trace")
[[ -n "$agents_trace"    ]] && extra_args+=(--agents-trace "$agents_trace")
[[ -n "$instructions_trace" ]] && extra_args+=(--instructions-trace "$instructions_trace")
[[ -n "$communication_flow" ]] && extra_args+=(--communication-flow "$communication_flow")
[[ -n "$mcp_endpoints_trace" ]] && extra_args+=(--mcp-endpoints-trace "$mcp_endpoints_trace")
[[ -n "$handoff_expected" ]] && extra_args+=(--handoff-expected "$handoff_expected")
[[ -n "$timing_total_ms" ]] && extra_args+=(--timing-total-ms "$timing_total_ms")
[[ -n "$timing_pre_hook_ms" ]] && extra_args+=(--timing-pre-hook-ms "$timing_pre_hook_ms")
[[ -n "$timing_command_ms" ]] && extra_args+=(--timing-command-ms "$timing_command_ms")

audit_cmd=(
  bash "$audit_log"
  --mode full
  --task-id "$task_id"
  --role "$role"
  --action "post-message"
  --status "$status"
  --session-id "$session_id"
  --audits-root "$audit_root"
  --notes "$notes"
)

if (( ${#extra_args[@]} > 0 )); then
  audit_cmd+=("${extra_args[@]}")
fi

"${audit_cmd[@]}"
