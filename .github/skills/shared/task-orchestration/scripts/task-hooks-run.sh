#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the task hooks run workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

hook=""
mode="short"
task_id=""
role="developer"
action="hook"
audits_root=".digital-artifacts/70-audits"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hook)
      hook="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-short}"
      shift 2
      ;;
    --task-id)
      task_id="${2:-}"
      shift 2
      ;;
    --role)
      role="${2:-developer}"
      shift 2
      ;;
    --action)
      action="${2:-hook}"
      shift 2
      ;;
    --audits-root)
      audits_root="${2:-.digital-artifacts/70-audits}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -n "$hook" ]] || { echo "--hook is required" >&2; exit 2; }
[[ -n "$task_id" ]] || task_id="hook-${hook}"

script_root="$(cd "$(dirname "$0")" && pwd)"

bash "${script_root}/task-audit-log.sh" \
  --mode "$mode" \
  --task-id "$task_id" \
  --role "$role" \
  --action "$action" \
  --status ok \
  --audits-root "$audits_root" \
  --notes "hook=${hook}"
