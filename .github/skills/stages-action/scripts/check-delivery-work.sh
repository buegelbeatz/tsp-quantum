#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Scan runtime work_handoff_v1 files for a stage, summarize pending delivery work,
#   and emit a deterministic status artifact.
# Exit codes:
#   0 -> no pending work handoffs
#   3 -> pending work handoffs detected
#   2 -> usage/config error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${DIGITAL_REPO_ROOT:-$(cd "$SCRIPT_DIR/../../../.." && pwd)}"
RUN_TOOL_SH="$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh"
PATH_GUARD_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/path_guard.sh"

if [[ -f "$PATH_GUARD_LIB" ]]; then
  # shellcheck source=/dev/null
  source "$PATH_GUARD_LIB"
fi

# Test/standalone fallback when path_guard helpers are unavailable.
if ! command -v safe_mkdir_p >/dev/null 2>&1; then
  safe_mkdir_p() {
    mkdir -p "$1"
  }
fi

STAGE="${1:-${STAGE:-}}"
if [[ -z "$STAGE" ]]; then
  echo "usage: check-delivery-work.sh <stage>"
  exit 2
fi

handoff_dir="$REPO_ROOT/.digital-runtime/handoffs/$STAGE"
status_dir="$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
status_file="$status_dir/CHECK_DELIVERY_WORK_STATUS.md"
safe_mkdir_p "$status_dir" "check-delivery-work status directory"

_handoff_age_minutes() {
  local generated_at="$1"
  if [[ -z "$generated_at" ]]; then
  printf 'unknown'
  return 0
  fi

  RUN_TOOL_PREFER_CONTAINER=0 SHARED_SHELL_REPO_ROOT="$REPO_ROOT" bash "$RUN_TOOL_SH" python3 - "$generated_at" <<'PY'
from datetime import datetime, timezone
import sys

raw = (sys.argv[1] or "").strip().strip('"')
if not raw:
  print("unknown")
  raise SystemExit(0)

try:
  if raw.endswith("Z"):
    raw = raw[:-1] + "+00:00"
  ts = datetime.fromisoformat(raw)
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  delta_min = int((datetime.now(timezone.utc) - ts).total_seconds() // 60)
  print(str(max(delta_min, 0)))
except Exception:
  print("unknown")
PY
}

pending_count=0
done_count=0
active_count=0
active_ready_count=0
active_blocked_count=0
total_count=0
pending_lines=""
active_lines=""
active_ready_lines=""
active_blocked_lines=""
stale_count=0
stale_lines=""

echo "[check-delivery-work] HEARTBEAT: poll-start stage=${STAGE} at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -d "$handoff_dir" ]]; then
  while IFS= read -r handoff_file; do
    [[ -n "$handoff_file" ]] || continue
    echo "[check-delivery-work] HEARTBEAT: inspecting=$(basename "$handoff_file")"
    if ! grep -qi 'work_handoff_v1' "$handoff_file" 2>/dev/null; then
      continue
    fi

    total_count=$((total_count + 1))

    status="$(awk -F': ' '$1 == "status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    [[ -n "$status" ]] || status="pending"

    task_id="$(awk -F': ' '$1 == "task_id" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$task_id" ]]; then
      task_id="$(awk -F': ' '$1 == "  task_id" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$task_id" ]] || task_id="$(basename "$handoff_file" .yaml)"

    receiver="$(awk -F': ' '$1 == "receiver" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$receiver" ]]; then
      receiver="$(awk -F': ' '$1 == "  assignee" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$receiver" ]] || receiver="unknown"

    intent="$(awk -F': ' '$1 == "intent" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    [[ -n "$intent" ]] || intent="none"
    if [[ "${#intent}" -gt 88 ]]; then
      intent="${intent:0:85}..."
    fi

    pr_url="$(awk -F': ' '$1 == "pr_url" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$pr_url" ]]; then
      pr_url="$(awk -F': ' '$1 == "  pr_url" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$pr_url" ]] || pr_url="none"

    approved_by="$(awk -F': ' '$1 == "approved_by" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$approved_by" ]]; then
      approved_by="$(awk -F': ' '$1 == "  approved_by" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$approved_by" ]] || approved_by="none"

    make_test_status="$(awk -F': ' '$1 == "make_test_status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$make_test_status" ]]; then
      make_test_status="$(awk -F': ' '$1 == "  make_test_status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$make_test_status" ]] || make_test_status="unknown"

    make_quality_status="$(awk -F': ' '$1 == "make_quality_status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$make_quality_status" ]]; then
      make_quality_status="$(awk -F': ' '$1 == "  make_quality_status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$make_quality_status" ]] || make_quality_status="unknown"

    quality_gate_passed="$(awk -F': ' '$1 == "quality_gate_passed" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$quality_gate_passed" ]]; then
      quality_gate_passed="$(awk -F': ' '$1 == "  quality_gate_passed" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$quality_gate_passed" ]] || quality_gate_passed="unknown"

    blocker="$(awk -F': ' '$1 == "blocker" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$blocker" ]]; then
      blocker="$(awk -F': ' '$1 == "  blocker" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    [[ -n "$blocker" ]] || blocker="none"
    if [[ "${#blocker}" -gt 110 ]]; then
      blocker="${blocker:0:107}..."
    fi

    generated_at="$(awk -F': ' '$1 == "  generated_at" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$generated_at" ]]; then
      generated_at="$(awk -F': ' '$1 == "generated_at" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    age_min="$(_handoff_age_minutes "$generated_at")"

    source_document="$(awk -F': ' '$1 == "source_document" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    if [[ -z "$source_document" ]]; then
      source_document="$(awk -F': ' '$1 == "  source_document" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    fi
    if [[ -n "$source_document" && ! -f "$source_document" ]]; then
      stale_count=$((stale_count + 1))
      missing_source_rel="$source_document"
      if [[ "$missing_source_rel" == "$REPO_ROOT"/* ]]; then
        missing_source_rel="${missing_source_rel#"$REPO_ROOT"/}"
      fi
      stale_lines+="- ${task_id} | receiver=${receiver} | status=stale | age_min=${age_min} | intent=${intent} | missing_source=${missing_source_rel} | path=${handoff_file#"$REPO_ROOT"/}"$'\n'
      continue
    fi

    source_rel="none"
    if [[ -n "$source_document" ]]; then
      source_rel="$source_document"
      if [[ "$source_rel" == "$REPO_ROOT"/* ]]; then
        source_rel="${source_rel#"$REPO_ROOT"/}"
      fi
    fi

    case "$(printf '%s' "$status" | tr '[:upper:]' '[:lower:]')" in
      done|closed|completed)
        done_count=$((done_count + 1))
        ;;
      in-progress|active|working)
        active_count=$((active_count + 1))
        quality_state="unknown"
        case "$(printf '%s' "$quality_gate_passed" | tr '[:upper:]' '[:lower:]')" in
          true|yes|passed|ok)
            quality_state="pass"
            ;;
          false|no|failed|fail)
            quality_state="fail"
            ;;
          *)
            if [[ "$(printf '%s' "$make_test_status" | tr '[:upper:]' '[:lower:]')" == "pass" && "$(printf '%s' "$make_quality_status" | tr '[:upper:]' '[:lower:]')" == "pass" ]]; then
              quality_state="pass"
            elif [[ "$(printf '%s' "$make_test_status" | tr '[:upper:]' '[:lower:]')" == "fail" || "$(printf '%s' "$make_quality_status" | tr '[:upper:]' '[:lower:]')" == "fail" ]]; then
              quality_state="fail"
            fi
            ;;
        esac

        review_lane="no-pr"
        if [[ "$pr_url" != "none" ]]; then
          if [[ "$quality_state" == "pass" ]]; then
            review_lane="ready-for-review"
            active_ready_count=$((active_ready_count + 1))
          else
            review_lane="blocked:quality-gate"
            active_blocked_count=$((active_blocked_count + 1))
          fi
        else
          active_blocked_count=$((active_blocked_count + 1))
        fi

        active_entry="- ${task_id} | receiver=${receiver} | status=${status} | lane=${review_lane} | age_min=${age_min} | source=${source_rel} | pr=${pr_url} | approved_by=${approved_by} | make_test=${make_test_status} | make_quality=${make_quality_status} | quality_gate=${quality_gate_passed} | blocker=${blocker} | intent=${intent} | path=${handoff_file#"$REPO_ROOT"/}"
        active_lines+="${active_entry}"$'\n'
        if [[ "$review_lane" == "ready-for-review" ]]; then
          active_ready_lines+="${active_entry}"$'\n'
        else
          active_blocked_lines+="${active_entry}"$'\n'
        fi
        ;;
      *)
        pending_count=$((pending_count + 1))
        pending_lines+="- ${task_id} | receiver=${receiver} | status=${status} | age_min=${age_min} | source=${source_rel} | intent=${intent} | path=${handoff_file#"$REPO_ROOT"/}"$'\n'
        ;;
    esac
  done < <(find "$handoff_dir" -type f -name '*-handoff.yaml' | sort)
fi

overall_status="clear"
if [[ "$pending_count" != "0" ]]; then
  overall_status="pending"
fi

{
  echo "# Delivery Work Check (${STAGE})"
  echo ""
  echo "- generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- stage: ${STAGE}"
  echo "- status: ${overall_status}"
  echo "- handoff_dir: .digital-runtime/handoffs/${STAGE}"
  echo "- total_work_handoffs: ${total_count}"
  echo "- pending_work_handoffs: ${pending_count}"
  echo "- active_work_handoffs: ${active_count}"
  echo "- active_ready_for_review: ${active_ready_count}"
  echo "- active_blocked_for_review: ${active_blocked_count}"
  echo "- done_work_handoffs: ${done_count}"
  echo "- stale_work_handoffs: ${stale_count}"
  echo ""
  echo "## Active"
  echo ""
  if [[ -n "$active_lines" ]]; then
    printf '%s' "$active_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "## Active Ready For Review"
  echo ""
  if [[ -n "$active_ready_lines" ]]; then
    printf '%s' "$active_ready_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "## Active Blocked For Review"
  echo ""
  if [[ -n "$active_blocked_lines" ]]; then
    printf '%s' "$active_blocked_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "## Pending"
  echo ""
  if [[ -n "$pending_lines" ]]; then
    printf '%s' "$pending_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "## Stale"
  echo ""
  if [[ -n "$stale_lines" ]]; then
    printf '%s' "$stale_lines"
  else
    echo "- none"
  fi
} > "$status_file"

if [[ -n "$active_lines" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    echo "[check-delivery-work] ACTIVE: ${line#- }"
  done <<< "$active_lines"
fi

if [[ -n "$pending_lines" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    echo "[check-delivery-work] PENDING: ${line#- }"
  done <<< "$pending_lines"
fi

echo "[check-delivery-work] INFO: status=${overall_status} pending=${pending_count} active=${active_count} done=${done_count} stale=${stale_count} total=${total_count} -> ${status_file#"$REPO_ROOT"/}"
echo "[check-delivery-work] INFO: active_ready_for_review=${active_ready_count} active_blocked_for_review=${active_blocked_count}"
echo "[check-delivery-work] HEARTBEAT: poll-end stage=${STAGE} at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$pending_count" != "0" ]]; then
  pending_exit_code="${CHECK_DELIVERY_WORK_EXIT_PENDING:-3}"
  case "$pending_exit_code" in
    ''|*[!0-9]*)
      pending_exit_code="3"
      ;;
  esac
  exit "$pending_exit_code"
fi

exit 0