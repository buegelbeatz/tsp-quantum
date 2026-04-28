#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the canonical stage workflow with progress markers.
# Security:
#   Uses repository-local scripts and writes artifacts only under governed paths.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ARTIFACTS_SCRIPTS_DIR="$REPO_ROOT/.github/skills/artifacts/scripts"
SHARED_GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
CHECK_DELIVERY_WORK_SCRIPT="$REPO_ROOT/.github/skills/stages-action/scripts/check-delivery-work.sh"
VALIDATE_SVG_ASSETS_SCRIPT="$REPO_ROOT/.github/skills/stages-action/scripts/validate-svg-assets.sh"
BOARD_CLEANUP_SCRIPT="$REPO_ROOT/.github/skills/board/scripts/board-cleanup.sh"
MARKDOWN_ARTIFACTS_CONFIG="$REPO_ROOT/.github/skills/artifacts/config/markdown-artifacts.env"
PATH_GUARD_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/path_guard.sh"

TARGET_REPO_ROOT_EFFECTIVE="${TARGET_REPO_ROOT:-${DIGITAL_TARGET_REPO_ROOT:-}}"
if [[ -n "$TARGET_REPO_ROOT_EFFECTIVE" ]]; then
  TARGET_REPO_ROOT_EFFECTIVE="$(cd "$TARGET_REPO_ROOT_EFFECTIVE" && pwd)"
  if [[ "${STAGES_ACTION_DELEGATED:-0}" != "1" && "$TARGET_REPO_ROOT_EFFECTIVE" != "$REPO_ROOT" ]]; then
    target_stages_action_script="$TARGET_REPO_ROOT_EFFECTIVE/.github/skills/stages-action/scripts/stages-action.sh"
    if [[ ! -f "$target_stages_action_script" ]]; then
      echo "[stages-action] ERROR: target stages-action script missing at ${target_stages_action_script}"
      exit 2
    fi
    echo "[stages-action] INFO: delegating execution to target repository: ${TARGET_REPO_ROOT_EFFECTIVE}"
    exec env \
      STAGES_ACTION_DELEGATED=1 \
      TARGET_REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE" \
      DIGITAL_TARGET_REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE" \
      TARGET_REPO_SLUG="${TARGET_REPO_SLUG:-${DIGITAL_TARGET_REPO_SLUG:-}}" \
      DIGITAL_TARGET_REPO_SLUG="${DIGITAL_TARGET_REPO_SLUG:-${TARGET_REPO_SLUG:-}}" \
      bash "$target_stages_action_script" "$@"
  fi
  REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE"
  ARTIFACTS_SCRIPTS_DIR="$REPO_ROOT/.github/skills/artifacts/scripts"
  SHARED_GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
  CHECK_DELIVERY_WORK_SCRIPT="$REPO_ROOT/.github/skills/stages-action/scripts/check-delivery-work.sh"
  VALIDATE_SVG_ASSETS_SCRIPT="$REPO_ROOT/.github/skills/stages-action/scripts/validate-svg-assets.sh"
  BOARD_CLEANUP_SCRIPT="$REPO_ROOT/.github/skills/board/scripts/board-cleanup.sh"
  MARKDOWN_ARTIFACTS_CONFIG="$REPO_ROOT/.github/skills/artifacts/config/markdown-artifacts.env"
  PATH_GUARD_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/path_guard.sh"
fi

_resolve_python_runtime() {
  local candidate
  for candidate in \
    "$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python3" \
    "$REPO_ROOT/.digital-runtime/layers/digital-generic-team/bin/python3" \
    "$REPO_ROOT/.digital-runtime/layers/digital-generic-team/venv/bin/python3"
  do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  return 1
}

if ! PYTHON_RUNTIME="$(_resolve_python_runtime)"; then
  echo "[stages-action] ERROR: unable to resolve python runtime (.digital-runtime layers and system python3 not found)"
  exit 2
fi

if [[ -f "$SHARED_GITHUB_LIB" ]]; then
  # shellcheck source=/dev/null
  source "$SHARED_GITHUB_LIB"
fi

if [[ -f "$PATH_GUARD_LIB" ]]; then
  # shellcheck source=/dev/null
  source "$PATH_GUARD_LIB"
fi

STAGE="${1:-}"
if [[ -z "$STAGE" ]]; then
  echo "usage: stages-action.sh <stage>"
  exit 2
fi

RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_START_EPOCH="$(date +%s)"
COMPLETION_BRIEF_TEMPLATE="$REPO_ROOT/.github/skills/stages-action/templates/completion-brief.txt"

if [[ -f "$MARKDOWN_ARTIFACTS_CONFIG" ]]; then
  # shellcheck source=/dev/null
  source "$MARKDOWN_ARTIFACTS_CONFIG"
fi

: "${STAGE_HANDOFF_FILENAME:=stage-handoff.md}"
: "${DELIVERY_STATUS_FILENAME:=delivery-automation-status.md}"
: "${DELIVERY_STATUS_LEGACY_FILENAMES:=DELIVERY_AUTOMATION_STATUS.md}"
: "${DELIVERY_REVIEW_FILENAME:=delivery-review-status.md}"
: "${DELIVERY_REVIEW_LEGACY_FILENAMES:=DELIVERY_REVIEW_STATUS.md}"
: "${STAGE_COMPLETION_FILENAME:=stage-completion-status.md}"
: "${STAGE_COMPLETION_LEGACY_FILENAMES:=STAGE_COMPLETION_STATUS.md}"
: "${WHY_NOT_PROGRESSING_FILENAME:=why-not-progressing.md}"
: "${WHY_NOT_PROGRESSING_LEGACY_FILENAMES:=WHY_NOT_PROGRESSING.md}"
: "${PROJECT_ASSESSMENT_FILENAME:=project-assessment.md}"
: "${PROJECT_ASSESSMENT_LEGACY_FILENAMES:=PROJECT_ASSESSMENT.md}"

_elapsed_seconds() {
  local now
  now="$(date +%s)"
  echo "$((now - RUN_START_EPOCH))"
}

_stage_powerpoint_source_relpath() {
  local stage_name="${1:-$STAGE}"
  local layer_id
  layer_id="$(_active_layer_id)"
  echo "docs/powerpoints/${layer_id}_${stage_name}.pptx"
}

_active_layer_id() {
  local configured
  configured="${DIGITAL_LAYER_ID:-${DIGITAL_TEAM_LAYER_ID:-}}"
  if [[ -n "$configured" ]]; then
    echo "$configured"
    return 0
  fi
  basename "$REPO_ROOT"
}

_cleanup_legacy_markdown_aliases() {
  local canonical_path="$1"
  local legacy_csv="${2:-}"
  local legacy_name legacy_path
  local -a legacy_names=()

  [[ -f "$canonical_path" ]] || return 0
  if [[ -n "$legacy_csv" ]]; then
    IFS=',' read -r -a legacy_names <<< "$legacy_csv"
  fi

  for legacy_name in "${legacy_names[@]:-}"; do
    legacy_name="$(printf '%s' "$legacy_name" | tr -d '[:space:]')"
    [[ -n "$legacy_name" ]] || continue
    legacy_path="$(dirname "$canonical_path")/$legacy_name"
    if [[ "$legacy_path" != "$canonical_path" && -f "$legacy_path" ]]; then
      rm -f "$legacy_path"
    fi
  done
}

_latest_stage_review_file() {
  local canonical_name="$1"
  local legacy_csv="${2:-}"
  local candidate latest_path=""
  local -a names=()

  names+=("$canonical_name")
  if [[ -n "$legacy_csv" ]]; then
    local -a legacy_names=()
    IFS=',' read -r -a legacy_names <<< "$legacy_csv"
    for candidate in "${legacy_names[@]:-}"; do
      candidate="$(printf '%s' "$candidate" | tr -d '[:space:]')"
      [[ -n "$candidate" ]] || continue
      names+=("$candidate")
    done
  fi

  latest_path="$({
    for candidate in "${names[@]}"; do
      find "$REPO_ROOT/.digital-artifacts/60-review" -type f -path "*/${STAGE}/${candidate}" 2>/dev/null || true
    done
  } | sort | tail -n1)"
  printf '%s\n' "$latest_path"
}

_stage_review_status_dir() {
  echo "$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
}

_stage_handoff_path() {
  echo "$(_stage_review_status_dir)/$STAGE_HANDOFF_FILENAME"
}

_flatten_pr_lines_for_brief() {
  _flatten_section_lines_for_brief "pull-requests" "$1"
}

_flatten_section_lines_for_brief() {
  local label="$1"
  local raw_lines="$2"

  if [[ -z "$(printf '%s' "$raw_lines" | tr -d '[:space:]')" ]]; then
    echo "[stages-action][brief] ${label}: none"
    return 0
  fi

  while IFS= read -r raw_line; do
    [[ -n "$raw_line" ]] || continue
    echo "[stages-action][brief] ${label}: ${raw_line#- }"
  done <<< "$raw_lines"
}

_reason_lines_to_section_lines() {
  local raw_lines="$1"
  local line found_any="0"

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    if [[ "$line" == *": none" ]]; then
      continue
    fi
    found_any="1"
    echo "- ${line#*: }"
  done <<< "$raw_lines"

  if [[ "$found_any" != "1" ]]; then
    echo "- none"
  fi
}

_ticket_record_for_id() {
  local ticket_records="$1"
  local ticket_id="$2"

  printf '%s\n' "$ticket_records" | awk -F '\t' -v id="$ticket_id" '$1 == id { print; exit }'
}

_stage_label_titlecase() {
  local stage_name="$1"
  printf '%s\n' "$stage_name" | awk -F'-' '{
    for (i = 1; i <= NF; i++) {
      part = $i
      if (part == "") {
        continue
      }
      printf toupper(substr(part, 1, 1)) substr(part, 2)
      if (i < NF) {
        printf "-"
      }
    }
    printf "\n"
  }'
}

_stage_wiki_powerpoint_relpath() {
  local stage_name="${1:-$STAGE}"
  local stage_title

  if [[ "$stage_name" == "project" ]]; then
    echo "docs/wiki/assets/Project-Summary.pptx"
    return 0
  fi

  stage_title="$(_stage_label_titlecase "$stage_name")"
  echo "docs/wiki/assets/${stage_title}-Summary.pptx"
}

_work_item_id_for_board_ticket() {
  local board_ticket="$1"
  local trimmed theme_id artifact_kind

  trimmed="${board_ticket#PRO-}"
  theme_id="${trimmed%-*}"
  artifact_kind="${trimmed##*-}"

  case "$artifact_kind" in
    TASK|BUG)
      echo "${artifact_kind}-${theme_id}"
      ;;
    *)
      return 1
      ;;
  esac
}

_handoff_state_for_board_ticket() {
  local board_ticket="$1"
  local work_item_id prefix slug slug_without_prefix handoff_path handoff_status receiver

  work_item_id="$(_work_item_id_for_board_ticket "$board_ticket" 2>/dev/null || true)"
  if [[ -z "$work_item_id" ]]; then
    echo "none|unknown|none"
    return 0
  fi

  if [[ "$work_item_id" == BUG-* ]]; then
    prefix="bug"
  else
    prefix="task"
  fi

  slug="$(printf '%s' "$work_item_id" | tr '[:upper:]' '[:lower:]')"
  slug_without_prefix="${slug#${prefix}-}"
  handoff_path="$REPO_ROOT/.digital-runtime/handoffs/${STAGE}/${prefix}-${slug_without_prefix}-handoff.yaml"

  if [[ ! -f "$handoff_path" ]]; then
    echo "none|unknown|none"
    return 0
  fi

  handoff_status="$(grep -E '^status:' "$handoff_path" 2>/dev/null | head -n1 | sed -E 's/^status:[[:space:]]*//' | tr -d '"' || true)"
  receiver="$(grep -E '^receiver:' "$handoff_path" 2>/dev/null | head -n1 | sed -E 's/^receiver:[[:space:]]*//' | tr -d '"' || true)"

  [[ -n "$handoff_status" ]] || handoff_status="pending"
  [[ -n "$receiver" ]] || receiver="unknown"
  echo "${handoff_status}|${receiver}|${handoff_path#"$REPO_ROOT"/}"
}

_board_ticket_reason_lines() {
  local state="$1"
  local found_any="0"
  local ticket_ref board_ticket handoff_status receiver handoff_relpath reason

  while IFS= read -r ticket_ref; do
    [[ -n "$ticket_ref" ]] || continue
    found_any="1"
    board_ticket="${ticket_ref##*/}"
    IFS='|' read -r handoff_status receiver handoff_relpath <<< "$(_handoff_state_for_board_ticket "$board_ticket")"

    case "$state" in
      backlog)
        if [[ "$handoff_status" == "done" ]]; then
          reason="handoff is done (${handoff_relpath}) but board ref is still backlog; board reconciliation is required"
        elif [[ "$handoff_status" == "in-progress" ]]; then
          reason="handoff is already in-progress for ${receiver} (${handoff_relpath}); board ref is stale backlog"
        elif [[ "$handoff_status" == "pending" ]]; then
          reason="handoff exists and is pending for ${receiver} (${handoff_relpath}); delivery not yet started"
        else
          reason="no runtime handoff found under .digital-runtime/handoffs/${STAGE}; delivery has not started"
        fi
        ;;
      in-progress)
        if [[ "$handoff_status" == "done" ]]; then
          reason="handoff is done (${handoff_relpath}); waiting for PR merge evidence + human approval before board transition"
        elif [[ "$handoff_status" == "in-progress" ]]; then
          reason="handoff is in-progress for ${receiver} (${handoff_relpath}); waiting for implementation and review"
        elif [[ "$handoff_status" == "pending" ]]; then
          reason="board is in-progress but handoff remains pending (${handoff_relpath}); investigate dispatcher lag"
        else
          reason="board is in-progress without runtime handoff; investigate handoff generation/discovery"
        fi
        ;;
      blocked)
        if [[ "$handoff_status" == "done" ]]; then
          reason="handoff is done (${handoff_relpath}); blocked board state is stale and needs approval/board reconciliation"
        elif [[ "$handoff_status" == "in-progress" ]]; then
          reason="handoff is in-progress for ${receiver} (${handoff_relpath}); delivery is blocked until blocker metadata is resolved"
        elif [[ "$handoff_status" == "pending" ]]; then
          reason="handoff exists and is pending for ${receiver} (${handoff_relpath}); blocker prevents delivery start"
        else
          reason="board is blocked without runtime handoff; investigate blocker source and handoff generation"
        fi
        ;;
      *)
        reason="state analysis not implemented"
        ;;
    esac

    echo "[stages-action][brief] why-${state}: ${board_ticket} -> ${reason}"
  done < <(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/${state}" 2>/dev/null | sort)

  if [[ "$found_any" != "1" ]]; then
    echo "[stages-action][brief] why-${state}: none"
  fi
}

_project_github_wiki_status() {
  local stage_doc repo_slug wiki_cache_dir wiki_url local_stage_file cached_stage_file
  local local_ppt_file stage_sync_status ppt_sync_status cached_ppt_candidate

  stage_doc="$(_stage_doc_path)"
  wiki_url="$(grep -E '^wiki_url:' "$stage_doc" 2>/dev/null | head -n1 | sed -E 's/^wiki_url:[[:space:]]*//' | tr -d '"' || true)"
  [[ -n "$wiki_url" ]] || wiki_url="none"

  if [[ "$STAGE" != "project" ]]; then
    echo "not-applicable|${wiki_url}"
    return 0
  fi

  repo_slug="$(_resolve_github_repo_slug)"
  if [[ -z "$repo_slug" ]]; then
    echo "unavailable|${wiki_url}"
    return 0
  fi

  wiki_cache_dir="$REPO_ROOT/.digital-runtime/github/wiki-cache/${repo_slug//\//_}"
  if [[ ! -d "$wiki_cache_dir/.git" ]]; then
    echo "missing-cache|${wiki_url}"
    return 0
  fi

  local_stage_file="$REPO_ROOT/docs/wiki/Project.md"
  cached_stage_file="$wiki_cache_dir/Project.md"
  local_ppt_file="$REPO_ROOT/$(_stage_wiki_powerpoint_relpath "$STAGE")"

  stage_sync_status="pending"
  ppt_sync_status="pending"

  if [[ -f "$local_stage_file" && -f "$cached_stage_file" ]] && cmp -s "$local_stage_file" "$cached_stage_file"; then
    stage_sync_status="updated"
  fi
  if [[ -f "$local_ppt_file" ]]; then
    for cached_ppt_candidate in \
      "$wiki_cache_dir/Project-Summary.pptx" \
      "$wiki_cache_dir/Project-Stakeholder-Briefing.pptx"; do
      if [[ -f "$cached_ppt_candidate" ]] && cmp -s "$local_ppt_file" "$cached_ppt_candidate"; then
        ppt_sync_status="updated"
        break
      fi
    done
  fi

  if [[ "$stage_sync_status" == "updated" && "$ppt_sync_status" == "updated" ]]; then
    echo "updated|${wiki_url}"
  elif [[ "$stage_sync_status" == "updated" ]]; then
    echo "page-updated-ppt-pending|${wiki_url}"
  else
    echo "pending|${wiki_url}"
  fi
}

_github_open_issue_total() {
  local repo_slug

  repo_slug="$(_resolve_github_repo_slug)"
  if [[ -z "$repo_slug" ]] || ! _stages_can_query_github; then
    echo "unavailable"
    return 0
  fi

  _stages_run_gh issue list --repo "$repo_slug" --state open --limit 200 --json number --jq 'length' 2>/dev/null || echo "unavailable"
}

_sync_project_wiki_post_gate() {
  if [[ "$STAGE" != "project" ]]; then
    return 0
  fi
  if [[ ! -x "$PYTHON_RUNTIME" ]]; then
    echo "[stages-action] ERROR: post-stage wiki sync requires python runtime at ${PYTHON_RUNTIME#"$REPO_ROOT"/}"
    return 1
  fi

  "$PYTHON_RUNTIME" - "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

repo_root = Path(sys.argv[1])
sys.path.insert(0, str(repo_root / ".github" / "skills" / "artifacts" / "scripts"))
import artifacts_flow_github  # type: ignore

stage_path = repo_root / ".digital-artifacts" / "40-stage" / "PROJECT.md"
result = artifacts_flow_github.ensure_stage_wiki(repo_root, "project", stage_path, "")
print(json.dumps(result, sort_keys=True))
status = str(result.get("status", ""))
raise SystemExit(0 if status in {"created", "updated", "unchanged"} else 1)
PY
}

_stages_run_gh() {
  if declare -F github_run_gh >/dev/null 2>&1; then
    github_run_gh "$@"
    return $?
  fi
  local run_tool_sh="${REPO_ROOT}/.github/skills/shared/shell/scripts/run-tool.sh"
  if [[ -f "$run_tool_sh" ]]; then
    GH_TOKEN="${GH_TOKEN:-}" GITHUB_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}" bash "$run_tool_sh" gh "$@"
    return $?
  fi
  return 127
}

_stages_can_query_github() {
  if declare -F github_require_token >/dev/null 2>&1; then
    github_require_token || true
  fi
  _stages_run_gh api /user >/dev/null 2>&1
}

_stages_pr_is_approved() {
  local pr_number="$1"
  local decision review_states normalized_decision

  decision="$(_stages_run_gh pr view "$pr_number" --json reviewDecision --jq '.reviewDecision // ""' 2>/dev/null || true)"
  normalized_decision="$(printf '%s' "$decision" | tr '[:lower:]' '[:upper:]')"
  if [[ "$normalized_decision" == "APPROVED" ]]; then
    return 0
  fi

  review_states="$(_stages_run_gh pr view "$pr_number" --json reviews --jq '.reviews[]?.state // empty' 2>/dev/null || true)"
  if printf '%s\n' "$review_states" | tr '[:lower:]' '[:upper:]' | grep -q '^APPROVED$'; then
    return 0
  fi
  return 1
}

DRY_RUN_MODE_RAW="${DRY_RUN:-}"
DRY_RUN_MODE="0"
case "$DRY_RUN_MODE_RAW" in
  ""|"0")
    DRY_RUN_MODE="0"
    ;;
  "1"|"2")
    DRY_RUN_MODE="$DRY_RUN_MODE_RAW"
    ;;
  *)
    echo "[stages-action] ERROR: unsupported DRY_RUN='$DRY_RUN_MODE_RAW' (allowed: unset|0|1|2)"
    exit 2
    ;;
esac

snapshot_file_list() {
  local target_file="$1"
  find "$REPO_ROOT/.digital-artifacts" -type f | sort > "$target_file"
}

BEFORE_SNAPSHOT="$(mktemp)"
AFTER_SNAPSHOT="$(mktemp)"
NEW_ARTIFACTS="$(mktemp)"

cleanup_snapshots() {
  rm -f "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" "$NEW_ARTIFACTS"
}
trap cleanup_snapshots EXIT

_write_audit_capture() {
  if [[ -z "${DIGITAL_PROMPT_AUDIT_CAPTURE_FILE:-}" ]]; then
    return 0
  fi

  safe_mkdir_p "$(dirname "$DIGITAL_PROMPT_AUDIT_CAPTURE_FILE")" "stages-action audit capture directory"

  local artifacts_csv assumptions open_questions comm_flow
  local status_summary next_step board_backlog board_in_progress board_blocked board_done
  local delivery_status_file delivery_review_file stage_completion_file stagnation_report
  local ready_tasks triggered_tasks delivery_phase_status ready_lines delivery_review_status
  local files_delta loc_delta workflow_code_debt_delta workflow_code_debt_monotonic_status
  local new_artifact_count stage_doc resume_marker stage_handoff_root handoff_count
  local handoff_file rel_artifact candidate artifact request_count response_count
  local -a audit_artifacts

  artifacts_csv=""
  audit_artifacts=()

  new_artifact_count="$(sed '/^$/d' "$NEW_ARTIFACTS" | wc -l | tr -d ' ')"
  stage_doc="$(_stage_doc_path)"
  [[ -f "$stage_doc" ]] && audit_artifacts+=("${stage_doc#"$REPO_ROOT"/}")

  board_backlog="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_in_progress="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/in-progress" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_blocked="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/blocked" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_done="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/done" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  status_summary="board=${STAGE}; backlog=${board_backlog}; in_progress=${board_in_progress}; blocked=${board_blocked}; done=${board_done}"
  if [[ -n "$new_artifact_count" && "$new_artifact_count" != "0" ]]; then
    status_summary+="; new_artifacts=${new_artifact_count}"
  fi

  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  [[ -n "$delivery_status_file" && -f "$delivery_status_file" ]] && audit_artifacts+=("${delivery_status_file#"$REPO_ROOT"/}")
  delivery_review_file="$(_latest_stage_review_file "$DELIVERY_REVIEW_FILENAME" "$DELIVERY_REVIEW_LEGACY_FILENAMES")"
  [[ -n "$delivery_review_file" && -f "$delivery_review_file" ]] && audit_artifacts+=("${delivery_review_file#"$REPO_ROOT"/}")
  stage_completion_file="$(_latest_stage_review_file "$STAGE_COMPLETION_FILENAME" "$STAGE_COMPLETION_LEGACY_FILENAMES")"
  [[ -n "$stage_completion_file" && -f "$stage_completion_file" ]] && audit_artifacts+=("${stage_completion_file#"$REPO_ROOT"/}")
  stagnation_report="$(_latest_stage_review_file "$WHY_NOT_PROGRESSING_FILENAME" "$WHY_NOT_PROGRESSING_LEGACY_FILENAMES")"
  [[ -n "$stagnation_report" && -f "$stagnation_report" ]] && audit_artifacts+=("${stagnation_report#"$REPO_ROOT"/}")
  resume_marker="$REPO_ROOT/.digital-artifacts/50-planning/${STAGE}/RESUME_STATE.yaml"
  [[ -f "$resume_marker" ]] && audit_artifacts+=("${resume_marker#"$REPO_ROOT"/}")

  ready_tasks="0"
  triggered_tasks="0"
  delivery_phase_status=""
  delivery_review_status=""
  ready_lines=""
  if [[ -n "$delivery_status_file" && -f "$delivery_status_file" ]]; then
    ready_tasks="$(grep -E '^- ready_tasks:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- ready_tasks:[[:space:]]*//' | tr -d '"' || true)"
    if [[ -z "$ready_tasks" ]]; then
      ready_tasks="$(grep -E '^- ready:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- ready:[[:space:]]*//' | tr -d '"' || true)"
    fi
    triggered_tasks="$(grep -E '^- triggered_tasks:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- triggered_tasks:[[:space:]]*//' | tr -d '"' || true)"
    delivery_phase_status="$(grep -E '^- status:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$ready_tasks" ]] || ready_tasks="0"
    [[ -n "$triggered_tasks" ]] || triggered_tasks="0"
    ready_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Triggered$/ { in_section = 1; next }
      /^## Triggered Tasks$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$delivery_status_file" | paste -sd ';' -)"
    if [[ "$ready_tasks" != "0" ]]; then
      status_summary+="; ready_tasks=${ready_tasks}"
    fi
    if [[ "$triggered_tasks" != "0" ]]; then
      status_summary+="; triggered_tasks=${triggered_tasks}"
    fi
  fi
  if [[ -n "$delivery_review_file" && -f "$delivery_review_file" ]]; then
    delivery_review_status="$(grep -E '^- status:' "$delivery_review_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$delivery_review_status" ]] && status_summary+="; delivery_review=${delivery_review_status}"
  fi
  if [[ -n "$stage_completion_file" && -f "$stage_completion_file" ]]; then
    files_delta="$(grep -E '^- files_delta:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- files_delta:[[:space:]]*//' | tr -d '"' || true)"
    loc_delta="$(grep -E '^- loc_delta:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- loc_delta:[[:space:]]*//' | tr -d '"' || true)"
    workflow_code_debt_delta="$(grep -E '^- workflow_code_debt_delta:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- workflow_code_debt_delta:[[:space:]]*//' | tr -d '"' || true)"
    workflow_code_debt_monotonic_status="$(grep -E '^- workflow_code_debt_monotonic_status:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- workflow_code_debt_monotonic_status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$files_delta" ]] && status_summary+="; files_delta=${files_delta}"
    [[ -n "$loc_delta" ]] && status_summary+="; loc_delta=${loc_delta}"
    [[ -n "$workflow_code_debt_delta" ]] && status_summary+="; workflow_code_debt_delta=${workflow_code_debt_delta}"
    [[ -n "$workflow_code_debt_monotonic_status" ]] && status_summary+="; workflow_code_debt_status=${workflow_code_debt_monotonic_status}"
  fi

  stage_handoff_root="$REPO_ROOT/.digital-runtime/handoffs/${STAGE}"
  handoff_count="0"
  request_count="0"
  response_count="0"
  if [[ -d "$stage_handoff_root" ]]; then
    while IFS= read -r handoff_file; do
      [[ -n "$handoff_file" ]] || continue
      handoff_count=$((handoff_count + 1))
      case "$(basename "$handoff_file")" in
        *_REQUEST.yaml|*.expert_request.yaml)
          request_count=$((request_count + 1))
          ;;
        *_RESPONSE.yaml|*.expert_response.yaml)
          response_count=$((response_count + 1))
          ;;
      esac
      if [[ "${#audit_artifacts[@]}" -lt 9 ]]; then
        audit_artifacts+=("${handoff_file#"$REPO_ROOT"/}")
      fi
    done < <(find "$stage_handoff_root" -type f -name '*.yaml' 2>/dev/null | sort)
  fi
  if [[ "$handoff_count" != "0" ]]; then
    status_summary+="; runtime_handoffs=${handoff_count}"
    if [[ "$request_count" != "0" || "$response_count" != "0" ]]; then
      status_summary+="; request_handoffs=${request_count}; response_handoffs=${response_count}"
    fi
  fi

  while IFS= read -r artifact; do
    [[ -n "$artifact" ]] || continue
    rel_artifact="${artifact#"$REPO_ROOT"/}"
    candidate_seen="0"
    for candidate in "${audit_artifacts[@]}"; do
      if [[ "$candidate" == "$rel_artifact" ]]; then
        candidate_seen="1"
        break
      fi
    done
    if [[ "$candidate_seen" == "0" && "${#audit_artifacts[@]}" -lt 12 ]]; then
      audit_artifacts+=("$rel_artifact")
    fi
  done < "$NEW_ARTIFACTS"

  for artifact in "${audit_artifacts[@]}"; do
    [[ -n "$artifact" ]] || continue
    if [[ -z "$artifacts_csv" ]]; then
      artifacts_csv="$artifact"
    else
      artifacts_csv+=", $artifact"
    fi
  done

  if [[ -n "$artifacts_csv" ]]; then
    assumptions="Stage pipeline executed for ${STAGE} with 6 deterministic trigger steps. Audit output is intentionally curated to stage status, review artifacts, and runtime handoff evidence."
    open_questions="none"
  else
    assumptions="Stage pipeline executed for ${STAGE}; existing artifacts were updated in place."
    open_questions="Confirm whether in-place updates should be listed explicitly in audit output."
  fi

  next_step="No action required."
  if [[ "$DRY_RUN_MODE" == "1" || "$DRY_RUN_MODE" == "2" ]]; then
    next_step="Delivery was skipped because DRY_RUN=${DRY_RUN_MODE}. Review seeded board tickets under refs/board/${STAGE}/* or rerun without DRY_RUN to continue."
    status_summary+="; delivery=skipped_dry_run"
  elif [[ -n "$delivery_status_file" && -f "$delivery_status_file" && "$triggered_tasks" != "0" ]]; then
    next_step="Delivery handoffs were created and auto-checked. Await assigned delivery-agent implementation and human review evidence, then rerun make ${STAGE} to refresh status."
    status_summary+="; delivery=triggered"
    if [[ -n "$ready_lines" ]]; then
      open_questions="Triggered delivery tasks awaiting implementation feedback: ${ready_lines}"
    fi
  elif [[ -n "$delivery_status_file" && -f "$delivery_status_file" && "$ready_tasks" != "0" ]]; then
    next_step="Inspect the delivery dispatch step because ready tasks were found but no delivery handoff was triggered."
    status_summary+="; delivery=dispatch_check_required"
    if [[ -n "$ready_lines" ]]; then
      open_questions="Ready tasks without triggered delivery dispatch: ${ready_lines}"
    fi
  elif [[ "$delivery_phase_status" == "no_ready_tasks" ]]; then
    status_summary+="; delivery=no_ready_tasks"
  fi
  if [[ "$handoff_count" != "0" && "$open_questions" == "none" ]]; then
    open_questions="Runtime handoff files are present under .digital-runtime/handoffs/${STAGE}; verify implementation progress against those handoffs before marking board tickets done."
  fi

  comm_flow="copilot -> agile-coach: request /${STAGE}; agile-coach -> artifacts-bootstrap: verify scaffold and inventories; agile-coach -> artifacts-input-2-data: normalize all input documents to bundles; artifacts-input-2-data -> agile-coach: provide bundle inventory + normalization status; agile-coach -> expert-agents: dispatch expert_request_v1 per eligible reviewer/expert intersection; expert-agents -> agile-coach: return expert_response_v1 with recommendation + confidence; agile-coach -> artifacts-data-2-specification: write agent-focused specifications + handoffs + cumulative reviews; artifacts-data-2-specification -> agile-coach: report touched/created specifications; agile-coach -> artifacts-specification-2-stage(${STAGE}): synthesize canonical stage doc + readiness gate; artifacts-specification-2-stage(${STAGE}) -> agile-coach: return ready/blocked bundle summary; agile-coach -> artifacts-specification-2-planning(${STAGE}): create thematic epics/stories/tasks from approved context; artifacts-specification-2-planning(${STAGE}) -> refs/board/${STAGE}: seed/update board tickets; artifacts-specification-2-planning(${STAGE}) -> docs/wiki: update stage wiki + home page; agile-coach -> generic-deliver: trigger delivery only if ready_for_planning=true; generic-deliver -> agile-coach: report execution status + unresolved blockers; agile-coach -> github: sync project items/issues/wiki when enabled; github -> human-reviewer: await approval gate; human-reviewer -> agile-coach: approval/change request; agile-coach -> audit-log: persist full communication flow, assumptions, open questions, and resume marker for next /${STAGE}"

  {
    printf 'AUDIT_ARTIFACTS=%s\n' "$artifacts_csv"
    printf 'AUDIT_ASSUMPTIONS=%s\n' "$assumptions"
    printf 'AUDIT_OPEN_QUESTIONS=%s\n' "$open_questions"
    printf 'AUDIT_COMMUNICATION_FLOW=%s\n' "$comm_flow"
    printf 'AUDIT_STATUS_SUMMARY=%s\n' "$status_summary"
    printf 'AUDIT_NEXT_STEP=%s\n' "$next_step"
  } > "$DIGITAL_PROMPT_AUDIT_CAPTURE_FILE"
}

_enforce_workflow_code_debt_gate() {
  local stage_completion_file status
  stage_completion_file="$(_latest_stage_review_file "$STAGE_COMPLETION_FILENAME" "$STAGE_COMPLETION_LEGACY_FILENAMES")"
  [[ -n "$stage_completion_file" && -f "$stage_completion_file" ]] || return 0

  status="$(grep -E '^- workflow_code_debt_monotonic_status:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- workflow_code_debt_monotonic_status:[[:space:]]*//' | tr -d '"' || true)"
  if [[ "$status" == "regression-detected" ]]; then
    echo "[stages-action] ERROR: workflow code debt regression detected -> blocking stage completion"
    return 1
  fi
  return 0
}

_restore_done_documents_to_input() {
  local artifacts_root done_root input_documents tmp_restore restored_count src_file base_name base_upper clean_name target_path suffix
  artifacts_root="$REPO_ROOT/.digital-artifacts"
  done_root="$artifacts_root/20-done"
  input_documents="$artifacts_root/00-input/documents"
  tmp_restore="$(mktemp -d)"
  restored_count=0

  if [[ -d "$done_root" ]]; then
    while IFS= read -r -d '' src_file; do
      base_name="$(basename "$src_file")"
      base_upper="$(printf '%s' "$base_name" | tr '[:lower:]' '[:upper:]')"
      if [[ "$base_upper" == *"INVENTORY.MD"* ]]; then
        continue
      fi
      clean_name="$base_name"

      # Remove repeated ingest prefixes such as 00000__00000__file.md
      while [[ "$clean_name" =~ ^[0-9]{5}__(.+)$ ]]; do
        clean_name="${BASH_REMATCH[1]}"
      done
      if [[ -z "$clean_name" ]]; then
        clean_name="$base_name"
      fi

      target_path="$tmp_restore/$clean_name"
      if [[ -e "$target_path" ]]; then
        suffix=1
        while [[ -e "$tmp_restore/${suffix}__${clean_name}" ]]; do
          suffix=$((suffix + 1))
        done
        target_path="$tmp_restore/${suffix}__${clean_name}"
      fi
      cp "$src_file" "$target_path"
      restored_count=$((restored_count + 1))
    done < <(find "$done_root" -type f -print0)
  fi

  rm -rf "$artifacts_root"
  safe_mkdir_p "$input_documents" "stages-action input documents directory"

  if [[ -d "$tmp_restore" ]]; then
    while IFS= read -r -d '' src_file; do
      mv "$src_file" "$input_documents/"
    done < <(find "$tmp_restore" -type f -print0)
  fi
  rm -rf "$tmp_restore"

  echo "[stages-action] INFO: DRY_RUN cleanup restored $restored_count document(s) to .digital-artifacts/00-input/documents"
}

_cleanup_stage_board_and_wiki() {
  if [[ -x "$BOARD_CLEANUP_SCRIPT" ]] && bash "$BOARD_CLEANUP_SCRIPT" --board "$STAGE" --remote --yes; then
    echo "[stages-action] INFO: stage board cleanup completed for '$STAGE'"
  else
    board_cleanup_exit=$?
    echo "[stages-action] INFO: stage board cleanup returned exit code $board_cleanup_exit"
  fi

  rm -rf "$REPO_ROOT/docs/wiki"
  echo "[stages-action] INFO: docs/wiki removed"
}

_cleanup_stage_primary_system_assets() {
  if [[ ! -x "$PYTHON_RUNTIME" ]]; then
    echo "[stages-action] INFO: python runtime missing; GitHub primary cleanup skipped"
    return 0
  fi

  if "$PYTHON_RUNTIME" -c 'import json, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); import artifacts_flow_github; result = artifacts_flow_github.cleanup_stage_primary_assets(Path(sys.argv[2]), sys.argv[3]); print(json.dumps(result, sort_keys=True))' "$ARTIFACTS_SCRIPTS_DIR" "$REPO_ROOT" "$STAGE"; then
    echo "[stages-action] INFO: DRY_RUN=2 GitHub primary cleanup attempted for '$STAGE'"
  else
    cleanup_exit=$?
    echo "[stages-action] INFO: DRY_RUN=2 GitHub primary cleanup returned exit code $cleanup_exit"
  fi
}

_stage_doc_path() {
  local stage_upper
  stage_upper="$(printf '%s' "$STAGE" | tr '[:lower:]' '[:upper:]')"
  echo "$REPO_ROOT/.digital-artifacts/40-stage/${stage_upper}.md"
}

_stage_doc_field() {
  local key="$1"
  local stage_doc
  stage_doc="$(_stage_doc_path)"
  if [[ ! -f "$stage_doc" ]]; then
    return 1
  fi
  grep -i "^${key}:" "$stage_doc" | head -n1 | sed -E "s/^${key}:[[:space:]]*//I" | tr -d '"' || true
}

_stage_doc_list_values() {
  local key="$1"
  local stage_doc
  stage_doc="$(_stage_doc_path)"
  if [[ ! -f "$stage_doc" ]]; then
    return 1
  fi
  awk -v key="$key" '
    BEGIN { in_list = 0 }
    tolower($0) ~ "^" tolower(key) ":[[:space:]]*$" { in_list = 1; next }
    in_list == 1 && $0 ~ /^[[:space:]]*-[[:space:]]*/ {
      value = $0
      sub(/^[[:space:]]*-[[:space:]]*/, "", value)
      gsub(/^"|"$/, "", value)
      print value
      next
    }
    in_list == 1 && $0 !~ /^[[:space:]]*$/ { exit }
  ' "$stage_doc"
}

_emit_gate_observability() {
  local ready_for_planning gate_reason selected_count blocked_count delivery_status_file delivery_status
  local blocked_bundle_ids
  ready_for_planning="$(_stage_doc_field "ready_for_planning" || true)"
  gate_reason="$(_stage_doc_field "gate_reason" || true)"
  selected_count="$(_stage_doc_field "selected_bundle_count" || true)"
  blocked_count="$(_stage_doc_field "blocked_bundle_count" || true)"
  blocked_bundle_ids="$(_stage_doc_list_values "blocked_bundle_ids" | paste -sd ',' - || true)"
  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  delivery_status="not-available"
  if [[ -n "$delivery_status_file" && -f "$delivery_status_file" ]]; then
    delivery_status="$(grep -E '^- status:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$delivery_status" ]] || delivery_status="unknown"
  fi
  [[ -n "$selected_count" ]] || selected_count="0"
  [[ -n "$blocked_count" ]] || blocked_count="0"
  [[ -n "$ready_for_planning" ]] || ready_for_planning="false"
  [[ -n "$gate_reason" ]] || gate_reason="gate_reason missing in stage frontmatter"
  [[ -n "$blocked_bundle_ids" ]] || blocked_bundle_ids="none"
  echo "[stages-action] OBSERVABILITY ready_for_planning=${ready_for_planning} gate_reason=${gate_reason}"
  echo "[stages-action] OBSERVABILITY selected_bundle_count=${selected_count} blocked_bundle_count=${blocked_count} blocked_bundle_ids=${blocked_bundle_ids}"
  echo "[stages-action] OBSERVABILITY delivery_automation_status=${delivery_status}"
}

_emit_delivery_activity_snapshot() {
  local handoff_dir handoff_file task_id receiver raw_status state rel_path
  local queued_count active_count done_count total_count
  handoff_dir="$REPO_ROOT/.digital-runtime/handoffs/${STAGE}"
  queued_count=0
  active_count=0
  done_count=0
  total_count=0

  if [[ ! -d "$handoff_dir" ]]; then
    echo "[stages-action][delivery] no handoff directory found for stage '${STAGE}'"
    return 0
  fi

  while IFS= read -r handoff_file; do
    [[ -n "$handoff_file" ]] || continue
    total_count=$((total_count + 1))

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

    raw_status="$(awk -F': ' '$1 == "status" {print $2; exit}' "$handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
    raw_status="${raw_status:-pending}"
    case "$(printf '%s' "$raw_status" | tr '[:upper:]' '[:lower:]')" in
      done|closed|completed)
        state="done"
        done_count=$((done_count + 1))
        ;;
      in-progress|active|working)
        state="active"
        active_count=$((active_count + 1))
        ;;
      *)
        state="queued"
        queued_count=$((queued_count + 1))
        ;;
    esac

    rel_path="${handoff_file#"$REPO_ROOT"/}"
    echo "[stages-action][delivery] task=${task_id} assignee=${receiver} state=${state} handoff=${rel_path}"
  done < <(find "$handoff_dir" -type f -name '*-handoff.yaml' | sort)

  if [[ "$total_count" == "0" ]]; then
    echo "[stages-action][delivery] no handoff files found in .digital-runtime/handoffs/${STAGE}"
    return 0
  fi

  echo "[stages-action][delivery] summary queued=${queued_count} active=${active_count} done=${done_count} total=${total_count}"
  if [[ "$queued_count" != "0" ]]; then
    echo "[stages-action][delivery] queued means handoff exists but no delivery agent has started it yet"
  fi
}

_emit_board_sync_conflict_guidance() {
  local delivery_status_file conflicts
  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  if [[ -z "$delivery_status_file" || ! -f "$delivery_status_file" ]]; then
    return 0
  fi

  conflicts="$(grep -E '^- board_sync_conflicts:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- board_sync_conflicts:[[:space:]]*//' | tr -d '"' || true)"
  [[ -n "$conflicts" ]] || conflicts="0"

  if [[ "$conflicts" != "0" ]]; then
    echo "[stages-action][delivery] board_sync_conflicts=${conflicts} means board refs had concurrent/stale updates during dispatch reconciliation"
    echo "[stages-action][delivery] impact: no data loss; ticket stays visible and will be reconciled on next run"
  fi
}

_validate_svg_assets() {
  if [[ ! -f "$VALIDATE_SVG_ASSETS_SCRIPT" ]]; then
    return 0
  fi

  if bash "$VALIDATE_SVG_ASSETS_SCRIPT" "$STAGE" "$PYTHON_RUNTIME"; then
    echo "[stages-action] INFO: svg asset validation passed"
  else
    local svg_exit=$?
    echo "[stages-action] WARN: svg asset validation reported issues (exit code: $svg_exit)"
  fi
}

_write_stagnation_report() {
  local status_dir report_path stage_doc gate_ready gate_reason selected_count blocked_count blocked_bundle_ids
  local delivery_status_file delivery_review_file delivery_state review_state next_action
  local check_delivery_status_file pending_from_check active_from_check
  status_dir="$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
  report_path="$status_dir/$WHY_NOT_PROGRESSING_FILENAME"
  safe_mkdir_p "$status_dir" "stages-action status directory"
  stage_doc="$(_stage_doc_path)"
  gate_ready="$(_stage_doc_field "ready_for_planning" || true)"
  gate_reason="$(_stage_doc_field "gate_reason" || true)"
  selected_count="$(_stage_doc_field "selected_bundle_count" || true)"
  blocked_count="$(_stage_doc_field "blocked_bundle_count" || true)"
  blocked_bundle_ids="$(_stage_doc_list_values "blocked_bundle_ids" | paste -sd ', ' - || true)"
  [[ -n "$gate_ready" ]] || gate_ready="false"
  [[ -n "$gate_reason" ]] || gate_reason="stage document missing gate_reason"
  [[ -n "$selected_count" ]] || selected_count="0"
  [[ -n "$blocked_count" ]] || blocked_count="0"
  [[ -n "$blocked_bundle_ids" ]] || blocked_bundle_ids="none"

  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  delivery_review_file="$(_latest_stage_review_file "$DELIVERY_REVIEW_FILENAME" "$DELIVERY_REVIEW_LEGACY_FILENAMES")"
  delivery_state="not-generated"
  review_state="not-generated"
  if [[ -n "$delivery_status_file" && -f "$delivery_status_file" ]]; then
    delivery_state="$(grep -E '^- status:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$delivery_state" ]] || delivery_state="unknown"
  fi
  if [[ -n "$delivery_review_file" && -f "$delivery_review_file" ]]; then
    review_state="$(grep -E '^- status:' "$delivery_review_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$review_state" ]] || review_state="unknown"
  fi

  check_delivery_status_file="$(_latest_stage_review_file "CHECK_DELIVERY_WORK_STATUS.md" "")"
  pending_from_check=""
  active_from_check=""
  if [[ -n "$check_delivery_status_file" && -f "$check_delivery_status_file" ]]; then
    pending_from_check="$(grep -E '^- pending_work_handoffs:' "$check_delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- pending_work_handoffs:[[:space:]]*//' | tr -d '"' || true)"
    active_from_check="$(grep -E '^- active_work_handoffs:' "$check_delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- active_work_handoffs:[[:space:]]*//' | tr -d '"' || true)"
  fi

  next_action="Run: /project"
  if [[ "$gate_ready" != "true" ]]; then
    next_action="Resolve blocked bundles listed below, then rerun: /project"
  elif [[ "$delivery_state" == "no_ready_tasks" ]]; then
    next_action="No dispatchable tasks found. Update TASK_* status to open and rerun: /project"
  elif [[ "$delivery_state" == "triggered" || "$delivery_state" == "already_dispatched" ]]; then
    next_action="Delivery handoffs were generated and checked. Process pending handoffs first; for active handoffs ensure PR links are created and reviewer approval evidence is recorded, then rerun: /project"
  elif [[ "$review_state" == "stopped" ]]; then
    next_action="Aggregate review decisions manually using ${DELIVERY_REVIEW_FILENAME} guidance."
  fi

  if [[ "$review_state" == "awaiting_human_review" && "$delivery_state" == "triggered" ]]; then
    if [[ "$pending_from_check" == "0" && -n "$active_from_check" && "$active_from_check" != "0" ]]; then
      next_action="All handoffs are active (no pending). Next mandatory step: ensure each active ticket has a real PR URL plus human approval evidence in review artifacts, then rerun: /project"
    fi
  fi

  cat > "$report_path" <<EOF
# Why Not Progressing (${STAGE})

- generated_at: ${RUN_STARTED_AT}
- elapsed_seconds: $(_elapsed_seconds)
- stage_document: ${stage_doc}
- ready_for_planning: ${gate_ready}
- gate_reason: ${gate_reason}
- selected_bundle_count: ${selected_count}
- blocked_bundle_count: ${blocked_count}
- blocked_bundle_ids: ${blocked_bundle_ids}
- delivery_status_file: ${delivery_status_file:-none}
- delivery_status: ${delivery_state}
- delivery_review_status_file: ${delivery_review_file:-none}
- delivery_review_status: ${review_state}
- next_action: ${next_action}

## Authentication and Environment Guidance

- Required for GitHub sync: \`GITHUB_TOKEN\` (preferred) or \`GH_TOKEN\`.
- Optional fallback source: repository root \`.env\` with one of the token variables.
- If token is missing, local board fallback remains default-safe under \`refs/board/${STAGE}/*\`.
- Enable local-only mode explicitly: \`DIGITAL_STAGE_PRIMARY_SYNC=0 make ${STAGE}\` (CLI fallback when chat frontdoor \`/${STAGE}\` is not used).
EOF

  _cleanup_legacy_markdown_aliases "$report_path" "$WHY_NOT_PROGRESSING_LEGACY_FILENAMES"

  while IFS= read -r dispatch_file; do
    [[ -n "$dispatch_file" ]] || continue
    if ! grep -q "^## Runtime Diagnostics" "$dispatch_file" 2>/dev/null; then
      {
        echo ""
        echo "## Runtime Diagnostics"
        echo ""
        echo "- why_not_progressing: ${report_path#"$REPO_ROOT"/}"
      } >> "$dispatch_file"
    fi
  done < <(find "$REPO_ROOT/.digital-artifacts/50-planning/$STAGE" -maxdepth 1 -type f -name 'DISPATCH_*.md' 2>/dev/null | sort)

  echo "[stages-action] DIAGNOSTICS report=${report_path#"$REPO_ROOT"/}"
}

_resolve_github_repo_slug() {
  if [[ -n "${TARGET_REPO_SLUG:-}" ]]; then
    printf '%s' "$TARGET_REPO_SLUG"
    return 0
  fi
  if [[ -n "${DIGITAL_TARGET_REPO_SLUG:-}" ]]; then
    printf '%s' "$DIGITAL_TARGET_REPO_SLUG"
    return 0
  fi
  local remote_url
  remote_url="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
  [[ -n "$remote_url" ]] || { printf ''; return 0; }

  if [[ "$remote_url" =~ ^git@github.com:([^/]+/[^.]+)(\.git)?$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$remote_url" =~ ^https://github.com/([^/]+/[^.]+)(\.git)?$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
    return 0
  fi
  printf ''
}

_enforce_mandatory_primary_sync_gate() {
  local primary_sync_raw dispatch_found dispatch_file
  local local_board_ref_count remote_board_ref_count
  local repo_slug wiki_cache_dir

  if [[ "$DRY_RUN_MODE" != "0" ]]; then
    return 0
  fi

  primary_sync_raw="$(echo "${DIGITAL_STAGE_PRIMARY_SYNC:-1}" | tr '[:upper:]' '[:lower:]')"
  case "${primary_sync_raw}" in
    0|false|off|no)
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: DIGITAL_STAGE_PRIMARY_SYNC is disabled"
      return 1
      ;;
  esac

  dispatch_found="0"
  while IFS= read -r dispatch_file; do
    [[ -n "$dispatch_file" ]] || continue
    dispatch_found="1"
    if grep -Eiq 'primary-sync-status:(manual-required|skipped|partial)' "$dispatch_file"; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: project sync not successful in ${dispatch_file#"$REPO_ROOT"/}"
      return 1
    fi
    if grep -Eiq 'primary-wiki-status:(manual-required|skipped|partial)' "$dispatch_file"; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: wiki sync not successful in ${dispatch_file#"$REPO_ROOT"/}"
      return 1
    fi
    if grep -Eiq 'primary-issue-[^:]+:(manual-required|skipped|partial)' "$dispatch_file"; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: issue sync not successful in ${dispatch_file#"$REPO_ROOT"/}"
      return 1
    fi
    if grep -Eiq 'primary-project-item-[^:]+:(manual-required|skipped|partial)' "$dispatch_file"; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: project-item sync not successful in ${dispatch_file#"$REPO_ROOT"/}"
      return 1
    fi
  done < <(find "$REPO_ROOT/.digital-artifacts/50-planning/$STAGE" -maxdepth 1 -type f -name 'DISPATCH_*.md' 2>/dev/null | sort)

  if [[ "$dispatch_found" != "1" ]]; then
    echo "[stages-action] ERROR: mandatory GitHub sync gate failed: no dispatch traces found for stage '$STAGE'"
    return 1
  fi

  local_board_ref_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  if [[ "$local_board_ref_count" != "0" ]]; then
    remote_board_ref_count="$({ git ls-remote origin "refs/board/${STAGE}/*" 2>/dev/null || true; } | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$remote_board_ref_count" == "0" ]]; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: remote refs/board/${STAGE}/* not found on origin"
      return 1
    fi
    if (( remote_board_ref_count < local_board_ref_count )); then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: remote board refs count (${remote_board_ref_count}) is below local count (${local_board_ref_count})"
      return 1
    fi
  fi

  repo_slug="$(_resolve_github_repo_slug)"
  if [[ -z "$repo_slug" ]]; then
    echo "[stages-action] ERROR: mandatory GitHub sync gate failed: cannot resolve GitHub repository slug"
    return 1
  fi

  wiki_cache_dir="$REPO_ROOT/.digital-runtime/github/wiki-cache/${repo_slug//\//_}"
  if [[ ! -d "$wiki_cache_dir/.git" ]]; then
    echo "[stages-action] ERROR: mandatory GitHub sync gate failed: wiki cache repository missing at ${wiki_cache_dir#"$REPO_ROOT"/}"
    return 1
  fi

  if ! git -C "$wiki_cache_dir" pull --rebase >/dev/null 2>&1; then
    echo "[stages-action] ERROR: mandatory GitHub sync gate failed: unable to refresh wiki cache"
    return 1
  fi

  if [[ "$STAGE" == "project" ]]; then
    local ppt_source_path ppt_wiki_path ppt_source_sha256 ppt_wiki_sha256 ppt_remote_count

    ppt_source_path="$REPO_ROOT/$(_stage_powerpoint_source_relpath "$STAGE")"
    ppt_wiki_path="$REPO_ROOT/$(_stage_wiki_powerpoint_relpath "$STAGE")"
    if [[ ! -f "$ppt_source_path" || ! -f "$ppt_wiki_path" ]]; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: local PowerPoint artifacts are incomplete"
      return 1
    fi

    ppt_source_sha256="$(_sha256_file "$ppt_source_path")"
    ppt_wiki_sha256="$(_sha256_file "$ppt_wiki_path")"
    if [[ "$ppt_source_sha256" == "unavailable" || "$ppt_wiki_sha256" == "unavailable" || "$ppt_source_sha256" != "$ppt_wiki_sha256" ]]; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: Project-Summary.pptx does not match generated stage deck"
      return 1
    fi

    ppt_remote_count="$(find "$wiki_cache_dir" -maxdepth 3 -type f \( -name 'Project-Summary.pptx' -o -name '*-Stakeholder-Briefing.pptx' \) 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$ppt_remote_count" == "0" ]]; then
      echo "[stages-action] ERROR: mandatory GitHub sync gate failed: no PowerPoint attachment detected in wiki repository"
      return 1
    fi
  fi

  echo "[stages-action] INFO: mandatory GitHub sync gate passed (refs/board, wiki, powerpoint)"
  return 0
}

_sha256_file() {
  local file_path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file_path" | awk '{print $1}'
    return 0
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file_path" | awk '{print $1}'
    return 0
  fi
  printf 'unavailable'
}

_file_mtime_utc() {
  local file_path="$1"
  local epoch
  epoch="$(stat -f %m "$file_path" 2>/dev/null || true)"
  if [[ -z "$epoch" ]]; then
    printf 'unavailable'
    return 0
  fi
  date -u -r "$epoch" +%Y-%m-%dT%H:%M:%SZ
}

_stage_ticket_ids() {
  git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" "refs/board/${STAGE}/in-progress" "refs/board/${STAGE}/blocked" "refs/board/${STAGE}/done" 2>/dev/null \
    | awk -F'/' '{print $NF}' \
    | sed '/^$/d' \
    | sort -u
}

_ensure_stage_sprint_ref() {
  local sprint_count board_script stage_upper sprint_id stage_title stage_goal
  sprint_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/sprints" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  if [[ "${sprint_count}" != "0" ]]; then
    return 0
  fi

  board_script="$REPO_ROOT/.github/skills/board/scripts/board-ticket.sh"
  if [[ ! -f "$board_script" ]]; then
    echo "[stages-action] INFO: sprint bootstrap skipped (missing board-ticket script)"
    return 0
  fi

  stage_upper="$(printf '%s' "$STAGE" | tr '[:lower:]' '[:upper:]')"
  sprint_id="${stage_upper}-SPRINT-$(date -u +%Y%m%d)"
  stage_title="$(_stage_doc_field "title" || true)"
  [[ -n "$stage_title" ]] || stage_title="${stage_upper} Stage Delivery"
  stage_goal="Automated sprint bootstrap for stage ${STAGE}: ${stage_title}"

  BOARD_NAME="$STAGE" BOARD_SYNC_MILESTONES=1 bash "$board_script" sprint-create "$sprint_id" "$stage_goal" >/dev/null 2>&1 || true
  if git rev-parse --verify "refs/board/${STAGE}/sprints/${sprint_id}" >/dev/null 2>&1; then
    echo "[stages-action] INFO: initialized sprint ref ${sprint_id} for stage ${STAGE}"
  else
    echo "[stages-action] INFO: sprint bootstrap skipped (unable to create sprint ref)"
  fi
}

_close_stage_sprints_if_completed() {
  local board_script backlog_count in_progress_count blocked_count done_count sprint_ref sprint_id
  board_script="$REPO_ROOT/.github/skills/board/scripts/board-ticket.sh"
  if [[ ! -f "$board_script" ]]; then
    return 0
  fi

  backlog_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  in_progress_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/in-progress" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  blocked_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/blocked" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  done_count="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/done" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"

  # Close only when no active tickets remain and at least one ticket reached done.
  if [[ "$backlog_count" != "0" || "$in_progress_count" != "0" || "$blocked_count" != "0" || "$done_count" == "0" ]]; then
    return 0
  fi

  while IFS= read -r sprint_ref; do
    [[ -n "$sprint_ref" ]] || continue
    sprint_id="${sprint_ref##*/}"
    BOARD_NAME="$STAGE" BOARD_SYNC_MILESTONES=1 bash "$board_script" sprint-close "$sprint_id" >/dev/null 2>&1 || true
    echo "[stages-action] INFO: attempted sprint close for ${sprint_id} (stage=${STAGE})"
  done < <(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/sprints" 2>/dev/null)
}

_write_stage_completion_report() {
  local status_dir report_path board_backlog board_in_progress board_blocked board_done
  local repo_slug pr_scan_mode pr_open_total pr_merged_total pr_approved_merged_total
  local ticket_id open_prs merged_prs open_pr_details merged_pr_details approved ticket_lines
  local search_query search_open search_merged work_item_search_id
  local ticket_records done_summary_lines approval_link_lines incomplete_lines recommendation_lines
  local backlog_reason_lines in_progress_reason_lines blocked_reason_lines
  local ticket_ref board_ticket work_item_id ticket_record merged_details approved_status
  local ppt_wiki_path ppt_source_path ppt_wiki_exists ppt_source_exists
  local ppt_wiki_sha256 ppt_source_sha256 ppt_hash_match
  local ppt_wiki_mtime_utc ppt_source_mtime_utc ppt_post_gate_executed
  local files_delta loc_delta workflow_code_debt_delta workflow_code_debt_monotonic_status

  status_dir="$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
  report_path="$status_dir/$STAGE_COMPLETION_FILENAME"
  safe_mkdir_p "$status_dir" "stages-action completion status directory"

  board_backlog="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_in_progress="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/in-progress" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_blocked="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/blocked" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  board_done="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/done" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"

  pr_open_total=0
  pr_merged_total=0
  pr_approved_merged_total=0
  ticket_lines=""
  ticket_records=""
  pr_scan_mode="disabled"
  repo_slug="$(_resolve_github_repo_slug)"

  if [[ -n "$repo_slug" ]] && _stages_can_query_github; then
    pr_scan_mode="enabled"
    while IFS= read -r ticket_id; do
      [[ -n "$ticket_id" ]] || continue
      work_item_search_id="$(_work_item_id_for_board_ticket "$ticket_id" 2>/dev/null || true)"
      search_query="\"${ticket_id}\""
      if [[ -n "$work_item_search_id" && "$work_item_search_id" != "$ticket_id" ]]; then
        search_query+=" OR \"${work_item_search_id}\""
      fi

      search_open="${search_query} is:open"
      search_merged="${search_query} is:merged"

      open_prs="$(_stages_run_gh pr list --search "$search_open" --json number --jq '.[].number' 2>/dev/null || true)"
      merged_prs="$(_stages_run_gh pr list --search "$search_merged" --json number --jq '.[].number' 2>/dev/null || true)"
      open_pr_details="$(_stages_run_gh pr list --search "$search_open" --json number,url,title --jq '.[] | "#\(.number) \(.url) | \(.title)"' 2>/dev/null || true)"
      merged_pr_details="$(_stages_run_gh pr list --search "$search_merged" --json number,url,title --jq '.[] | "#\(.number) \(.url) | \(.title)"' 2>/dev/null || true)"
      local open_count merged_count
      open_count="$(printf '%s\n' "$open_prs" | sed '/^$/d' | wc -l | tr -d ' ')"
      merged_count="$(printf '%s\n' "$merged_prs" | sed '/^$/d' | wc -l | tr -d ' ')"
      pr_open_total=$((pr_open_total + open_count))
      pr_merged_total=$((pr_merged_total + merged_count))

      approved="no"
      while IFS= read -r merged_pr; do
        [[ -n "$merged_pr" ]] || continue
        if _stages_pr_is_approved "$merged_pr"; then
          approved="yes"
          pr_approved_merged_total=$((pr_approved_merged_total + 1))
          break
        fi
      done <<< "$merged_prs"

      if [[ -n "$(printf '%s' "$open_pr_details" | tr -d '[:space:]')" ]]; then
        open_pr_details="$(printf '%s' "$open_pr_details" | paste -sd '; ' -)"
      else
        open_pr_details="none"
      fi
      if [[ -n "$(printf '%s' "$merged_pr_details" | tr -d '[:space:]')" ]]; then
        merged_pr_details="$(printf '%s' "$merged_pr_details" | paste -sd '; ' -)"
      else
        merged_pr_details="none"
      fi

      ticket_lines+="- ${ticket_id}: open_prs=${open_count} [${open_pr_details}] | merged_prs=${merged_count} [${merged_pr_details}] | approved_merged=${approved}"$'\n'
      ticket_records+="${ticket_id}\t${open_count}\t${open_pr_details}\t${merged_count}\t${merged_pr_details}\t${approved}"$'\n'
      if [[ -n "$work_item_search_id" && "$work_item_search_id" != "$ticket_id" ]]; then
        ticket_records+="${work_item_search_id}\t${open_count}\t${open_pr_details}\t${merged_count}\t${merged_pr_details}\t${approved}"$'\n'
      fi
    done < <(_stage_ticket_ids)
  else
    ticket_lines="- PR scan unavailable (GitHub runtime/auth unavailable or non-GitHub remote)"$'\n'
  fi

  done_summary_lines=""
  while IFS= read -r ticket_ref; do
    [[ -n "$ticket_ref" ]] || continue
    board_ticket="${ticket_ref##*/}"
    work_item_id="$(_work_item_id_for_board_ticket "$board_ticket" 2>/dev/null || true)"
    [[ -n "$work_item_id" ]] || work_item_id="$board_ticket"
    ticket_record="$(_ticket_record_for_id "$ticket_records" "$work_item_id")"
    merged_details="none"
    approved_status="no"
    if [[ -n "$ticket_record" ]]; then
      merged_details="$(printf '%s\n' "$ticket_record" | cut -f5)"
      approved_status="$(printf '%s\n' "$ticket_record" | cut -f6)"
    fi

    done_summary_lines+="- ${board_ticket}: completed and reconciled on board=done"
    if [[ "$merged_details" != "none" ]]; then
      done_summary_lines+=" | merged_prs=[${merged_details}]"
    fi
    if [[ "$approved_status" == "yes" ]]; then
      done_summary_lines+=" | human_approval=recorded"
    fi
    done_summary_lines+=$'\n'
  done < <(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/done" 2>/dev/null | sort)
  if [[ -z "$(printf '%s' "$done_summary_lines" | tr -d '[:space:]')" ]]; then
    done_summary_lines="- none"$'\n'
  fi

  approval_link_lines=""
  while IFS= read -r ticket_ref; do
    [[ -n "$ticket_ref" ]] || continue
    board_ticket="${ticket_ref##*/}"
    work_item_id="$(_work_item_id_for_board_ticket "$board_ticket" 2>/dev/null || true)"
    [[ -n "$work_item_id" ]] || continue
    ticket_record="$(_ticket_record_for_id "$ticket_records" "$work_item_id")"
    [[ -n "$ticket_record" ]] || continue
    merged_details="$(printf '%s\n' "$ticket_record" | cut -f5)"
    approved_status="$(printf '%s\n' "$ticket_record" | cut -f6)"
    if [[ "$approved_status" == "yes" && "$merged_details" != "none" ]]; then
      approval_link_lines+="- ${board_ticket}: ${merged_details} | rerun_required=/${STAGE} to reconcile approval and fully close the ticket"$'\n'
    fi
  done < <({
    git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" 2>/dev/null
    git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/in-progress" 2>/dev/null
    git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/blocked" 2>/dev/null
  } | sort -u)
  if [[ -z "$(printf '%s' "$approval_link_lines" | tr -d '[:space:]')" ]]; then
    approval_link_lines="- none"$'\n'
  fi

  backlog_reason_lines="$(_board_ticket_reason_lines backlog)"
  in_progress_reason_lines="$(_board_ticket_reason_lines in-progress)"
  blocked_reason_lines="$(_board_ticket_reason_lines blocked)"
  incomplete_lines="$(
    {
      _reason_lines_to_section_lines "$backlog_reason_lines"
      _reason_lines_to_section_lines "$in_progress_reason_lines"
      _reason_lines_to_section_lines "$blocked_reason_lines"
    } | awk '!seen[$0]++'
  )"
  if [[ -z "$(printf '%s' "$incomplete_lines" | tr -d '[:space:]')" ]]; then
    incomplete_lines="- none"
  fi

  recommendation_lines=""
  if [[ "$board_backlog" != "0" || "$board_blocked" != "0" ]]; then
    recommendation_lines+="- Review ${WHY_NOT_PROGRESSING_FILENAME} and unblock remaining board items before the next /${STAGE} run"$'\n'
  fi
  if [[ "$approval_link_lines" != "- none"$'\n' ]]; then
    recommendation_lines+="- After approval evidence is available, rerun /${STAGE} so the board can reconcile remaining tickets to done"$'\n'
  fi
  if [[ -z "$(printf '%s' "$recommendation_lines" | tr -d '[:space:]')" ]]; then
    recommendation_lines="- none"$'\n'
  fi

  local github_issue_open_total github_wiki_status github_wiki_url

  ppt_wiki_path="$(_stage_wiki_powerpoint_relpath "$STAGE")"
  ppt_source_path="$(_stage_powerpoint_source_relpath "$STAGE")"
  ppt_wiki_exists="false"
  ppt_source_exists="false"
  ppt_wiki_sha256="missing"
  ppt_source_sha256="missing"
  ppt_hash_match="false"
  ppt_wiki_mtime_utc="n/a"
  ppt_source_mtime_utc="n/a"
  ppt_post_gate_executed="false"

  if [[ -f "$REPO_ROOT/$ppt_wiki_path" ]]; then
    ppt_wiki_exists="true"
    ppt_wiki_sha256="$(_sha256_file "$REPO_ROOT/$ppt_wiki_path")"
    ppt_wiki_mtime_utc="$(_file_mtime_utc "$REPO_ROOT/$ppt_wiki_path")"
  fi
  if [[ -f "$REPO_ROOT/$ppt_source_path" ]]; then
    ppt_source_exists="true"
    ppt_source_sha256="$(_sha256_file "$REPO_ROOT/$ppt_source_path")"
    ppt_source_mtime_utc="$(_file_mtime_utc "$REPO_ROOT/$ppt_source_path")"
  fi
  if [[ "$ppt_wiki_exists" == "true" && "$ppt_source_exists" == "true" && "$ppt_wiki_sha256" == "$ppt_source_sha256" ]]; then
    ppt_hash_match="true"
  fi
  if [[ "$STAGE" == "project" && "$ppt_hash_match" == "true" ]]; then
    ppt_post_gate_executed="true"
  fi
  # Explicit regeneration signal: true when post-gate passed (deck exists, matches wiki copy).
  ppt_regenerated="${ppt_post_gate_executed}"
  # Canonical generation timestamp: use source mtime when available, otherwise wiki mtime.
  ppt_generated_at="${ppt_source_mtime_utc}"
  [[ "$ppt_generated_at" == "n/a" ]] && ppt_generated_at="${ppt_wiki_mtime_utc}"

  files_delta="$(git -C "$REPO_ROOT" diff --numstat -- . ':(exclude).digital-runtime' ':(exclude).tests' 2>/dev/null | wc -l | tr -d ' ')"
  loc_delta="$(git -C "$REPO_ROOT" diff --numstat -- . ':(exclude).digital-runtime' ':(exclude).tests' 2>/dev/null | awk '{if ($1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/) delta += ($1 - $2)} END {print delta+0}')"
  workflow_code_debt_delta="n/a"
  workflow_code_debt_monotonic_status="not-run"
  if [[ -x "$PYTHON_RUNTIME" ]]; then
    workflow_code_debt_delta="$($PYTHON_RUNTIME -c 'from pathlib import Path; import sys; sys.path.insert(0, sys.argv[1]); import workflow_code_debt as debt; repo=Path(sys.argv[2]); snap=debt.scan_snapshot(repo); prev=debt.read_previous_total(repo / ".digital-artifacts/70-audits/workflow-code-debt/history.csv"); print("n/a" if prev is None else str(snap.total_decision_lines - prev))' "$REPO_ROOT/.github/skills/distribution/scripts" "$REPO_ROOT" 2>/dev/null || echo "n/a")"
    if "$PYTHON_RUNTIME" "$REPO_ROOT/.github/skills/distribution/scripts/workflow_code_debt.py" --repo-root "$REPO_ROOT" --record --check-monotonic >/dev/null 2>&1; then
      workflow_code_debt_monotonic_status="ok"
    else
      workflow_code_debt_monotonic_status="regression-detected"
    fi
  fi

  github_issue_open_total="$(_github_open_issue_total)"
  IFS='|' read -r github_wiki_status github_wiki_url <<< "$(_project_github_wiki_status)"
  [[ -n "$github_wiki_status" ]] || github_wiki_status="unavailable"
  [[ -n "$github_wiki_url" ]] || github_wiki_url="none"

  cat > "$report_path" <<EOF
# Stage Completion Status (${STAGE})

- generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- stage: ${STAGE}
- dry_run_mode: $([[ "$DRY_RUN_MODE" == "0" ]] && echo false || echo true)
- agile_coach_first: true
- agile_coach_first_evidence: "progress step 1 is ingest-input-to-data under stages-action orchestration"
- progress_steps: "1/6 ingest-input-to-data, 2/6 specification-synthesis, 3/6 stage-readiness-gate, 4/6 planning-synchronization, 5/6 delivery-dispatch, 6/6 review-status"
- board_backlog: ${board_backlog}
- board_in_progress: ${board_in_progress}
- board_blocked: ${board_blocked}
- board_done: ${board_done}
- pr_scan_mode: ${pr_scan_mode}
- pr_open_total: ${pr_open_total}
- pr_merged_total: ${pr_merged_total}
- pr_approved_merged_total: ${pr_approved_merged_total}
- github_issue_open_total: ${github_issue_open_total}
- github_wiki_status: ${github_wiki_status}
- github_wiki_url: ${github_wiki_url}
- files_delta: ${files_delta}
- loc_delta: ${loc_delta}
- workflow_code_debt_delta: ${workflow_code_debt_delta}
- workflow_code_debt_monotonic_status: ${workflow_code_debt_monotonic_status}
- powerpoint_required: $([[ "$STAGE" == "project" ]] && echo true || echo false)
- powerpoint_post_gate_executed: ${ppt_post_gate_executed}
- powerpoint_regenerated: ${ppt_regenerated}
- powerpoint_generated_at: ${ppt_generated_at}
- powerpoint_wiki_path: ${ppt_wiki_path}
- powerpoint_wiki_exists: ${ppt_wiki_exists}
- powerpoint_wiki_sha256: ${ppt_wiki_sha256}
- powerpoint_wiki_mtime_utc: ${ppt_wiki_mtime_utc}
- powerpoint_source_path: ${ppt_source_path}
- powerpoint_source_exists: ${ppt_source_exists}
- powerpoint_source_sha256: ${ppt_source_sha256}
- powerpoint_source_mtime_utc: ${ppt_source_mtime_utc}
- powerpoint_hash_match: ${ppt_hash_match}

## PR Status by Ticket

${ticket_lines}

## Completed Successfully

${done_summary_lines}

## Approval Links Requiring Re-run

${approval_link_lines}

## Not Completed and Why

${incomplete_lines}

## Recommendations

${recommendation_lines}
EOF

  _cleanup_legacy_markdown_aliases "$report_path" "$STAGE_COMPLETION_LEGACY_FILENAMES"

  echo "[stages-action] INFO: stage completion report -> ${report_path#"$REPO_ROOT"/}"
}

_write_stage_handoff() {
  local status_dir handoff_path completion_path stagnation_path delivery_path review_path
  local planning_assessment_path gate_reason next_action

  status_dir="$(_stage_review_status_dir)"
  handoff_path="$status_dir/$STAGE_HANDOFF_FILENAME"
  completion_path="$status_dir/$STAGE_COMPLETION_FILENAME"
  stagnation_path="$status_dir/$WHY_NOT_PROGRESSING_FILENAME"
  delivery_path="$status_dir/$DELIVERY_STATUS_FILENAME"
  review_path="$status_dir/$DELIVERY_REVIEW_FILENAME"
  planning_assessment_path="$REPO_ROOT/.digital-artifacts/50-planning/$STAGE/$PROJECT_ASSESSMENT_FILENAME"
  safe_mkdir_p "$status_dir" "stages-action handoff status directory"

  if [[ ! -f "$planning_assessment_path" ]]; then
    planning_assessment_path="$REPO_ROOT/.digital-artifacts/50-planning/$STAGE/$PROJECT_ASSESSMENT_LEGACY_FILENAMES"
  fi

  gate_reason="not available"
  next_action="not available"
  if [[ -f "$stagnation_path" ]]; then
    gate_reason="$(grep -E '^- gate_reason:' "$stagnation_path" 2>/dev/null | head -n1 | sed -E 's/^- gate_reason:[[:space:]]*//' | tr -d '"' || true)"
    next_action="$(grep -E '^- next_action:' "$stagnation_path" 2>/dev/null | head -n1 | sed -E 's/^- next_action:[[:space:]]*//' | tr -d '"' || true)"
  fi
  [[ -n "$gate_reason" ]] || gate_reason="not available"
  [[ -n "$next_action" ]] || next_action="not available"

  cat > "$handoff_path" <<EOF
# Stage Handoff (${STAGE})

- generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- stage: ${STAGE}
- purpose: canonical entrypoint for stage follow-up, report discovery, and legacy markdown cleanup
- gate_reason: ${gate_reason}
- next_action: ${next_action}

## Canonical Files

- stage_completion_status: ${completion_path#"$REPO_ROOT"/}
- why_not_progressing: ${stagnation_path#"$REPO_ROOT"/}
- delivery_automation_status: ${delivery_path#"$REPO_ROOT"/}
- delivery_review_status: ${review_path#"$REPO_ROOT"/}
- planning_assessment: ${planning_assessment_path#"$REPO_ROOT"/}

## Garbage Collection

- policy: legacy UpperCase markdown aliases are removed once the canonical lowercase artifact has been written
- scope: dated stage review artifacts and the planning assessment entrypoint
EOF
}

_print_stage_completion_brief() {
  local stage_completion_file stagnation_report delivery_status_file review_status_file
  local board_backlog board_in_progress board_blocked board_done
  local open_total gate_reason next_action delivery_status review_status
  local ppt_required ppt_post_gate ppt_hash_match
  local github_issue_open_total github_wiki_status github_wiki_url
  local workflow_code_debt_delta workflow_code_debt_monotonic_status
  local backlog_reason_lines in_progress_reason_lines blocked_reason_lines pr_summary_lines template_text
  local completed_lines approval_lines incomplete_lines recommendation_lines
  local review_evidence_lines
  local ppt_source_path ppt_wiki_path

  stage_completion_file="$(_latest_stage_review_file "$STAGE_COMPLETION_FILENAME" "$STAGE_COMPLETION_LEGACY_FILENAMES")"
  stagnation_report="$(_latest_stage_review_file "$WHY_NOT_PROGRESSING_FILENAME" "$WHY_NOT_PROGRESSING_LEGACY_FILENAMES")"
  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  review_status_file="$(_latest_stage_review_file "$DELIVERY_REVIEW_FILENAME" "$DELIVERY_REVIEW_LEGACY_FILENAMES")"

  board_backlog="0"
  board_in_progress="0"
  board_blocked="0"
  board_done="0"
  delivery_status="unknown"
  review_status="unknown"
  gate_reason="not available"
  next_action="not available"
  ppt_required="false"
  ppt_post_gate="false"
  ppt_hash_match="false"
  github_issue_open_total="unavailable"
  github_wiki_status="unavailable"
  github_wiki_url="none"
  workflow_code_debt_delta="n/a"
  workflow_code_debt_monotonic_status="unknown"
  ppt_source_path="$(_stage_powerpoint_source_relpath "$STAGE")"
  ppt_wiki_path="$(_stage_wiki_powerpoint_relpath "$STAGE")"

  if [[ -n "$stage_completion_file" && -f "$stage_completion_file" ]]; then
    board_backlog="$(grep -E '^- board_backlog:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- board_backlog:[[:space:]]*//' | tr -d '"' || true)"
    board_in_progress="$(grep -E '^- board_in_progress:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- board_in_progress:[[:space:]]*//' | tr -d '"' || true)"
    board_blocked="$(grep -E '^- board_blocked:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- board_blocked:[[:space:]]*//' | tr -d '"' || true)"
    board_done="$(grep -E '^- board_done:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- board_done:[[:space:]]*//' | tr -d '"' || true)"
    ppt_required="$(grep -E '^- powerpoint_required:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- powerpoint_required:[[:space:]]*//' | tr -d '"' || true)"
    ppt_post_gate="$(grep -E '^- powerpoint_post_gate_executed:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- powerpoint_post_gate_executed:[[:space:]]*//' | tr -d '"' || true)"
    ppt_hash_match="$(grep -E '^- powerpoint_hash_match:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- powerpoint_hash_match:[[:space:]]*//' | tr -d '"' || true)"
    github_issue_open_total="$(grep -E '^- github_issue_open_total:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- github_issue_open_total:[[:space:]]*//' | tr -d '"' || true)"
    github_wiki_status="$(grep -E '^- github_wiki_status:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- github_wiki_status:[[:space:]]*//' | tr -d '"' || true)"
    github_wiki_url="$(grep -E '^- github_wiki_url:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- github_wiki_url:[[:space:]]*//' | tr -d '"' || true)"
    workflow_code_debt_delta="$(grep -E '^- workflow_code_debt_delta:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- workflow_code_debt_delta:[[:space:]]*//' | tr -d '"' || true)"
    workflow_code_debt_monotonic_status="$(grep -E '^- workflow_code_debt_monotonic_status:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- workflow_code_debt_monotonic_status:[[:space:]]*//' | tr -d '"' || true)"
    ppt_source_path="$(grep -E '^- powerpoint_source_path:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- powerpoint_source_path:[[:space:]]*//' | tr -d '"' || true)"
    ppt_wiki_path="$(grep -E '^- powerpoint_wiki_path:' "$stage_completion_file" 2>/dev/null | head -n1 | sed -E 's/^- powerpoint_wiki_path:[[:space:]]*//' | tr -d '"' || true)"
  fi

  if [[ -n "$delivery_status_file" && -f "$delivery_status_file" ]]; then
    delivery_status="$(grep -E '^- status:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$delivery_status" ]] || delivery_status="unknown"
  fi
  if [[ -n "$review_status_file" && -f "$review_status_file" ]]; then
    review_status="$(grep -E '^- status:' "$review_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$review_status" ]] || review_status="unknown"
  fi
  if [[ -n "$stagnation_report" && -f "$stagnation_report" ]]; then
    gate_reason="$(grep -E '^- gate_reason:' "$stagnation_report" 2>/dev/null | head -n1 | sed -E 's/^- gate_reason:[[:space:]]*//' | tr -d '"' || true)"
    next_action="$(grep -E '^- next_action:' "$stagnation_report" 2>/dev/null | head -n1 | sed -E 's/^- next_action:[[:space:]]*//' | tr -d '"' || true)"
    [[ -n "$gate_reason" ]] || gate_reason="not available"
    [[ -n "$next_action" ]] || next_action="not available"
  fi

  [[ -n "$board_backlog" ]] || board_backlog="0"
  [[ -n "$board_in_progress" ]] || board_in_progress="0"
  [[ -n "$board_blocked" ]] || board_blocked="0"
  [[ -n "$board_done" ]] || board_done="0"
  [[ -n "$github_issue_open_total" ]] || github_issue_open_total="unavailable"
  [[ -n "$github_wiki_status" ]] || github_wiki_status="unavailable"
  [[ -n "$github_wiki_url" ]] || github_wiki_url="none"
  [[ -n "$workflow_code_debt_delta" ]] || workflow_code_debt_delta="n/a"
  [[ -n "$workflow_code_debt_monotonic_status" ]] || workflow_code_debt_monotonic_status="unknown"
  [[ -n "$ppt_source_path" ]] || ppt_source_path="$(_stage_powerpoint_source_relpath "$STAGE")"
  [[ -n "$ppt_wiki_path" ]] || ppt_wiki_path="$(_stage_wiki_powerpoint_relpath "$STAGE")"
  open_total=$((board_backlog + board_in_progress + board_blocked))

  backlog_reason_lines="$(_board_ticket_reason_lines backlog)"
  in_progress_reason_lines="$(_board_ticket_reason_lines in-progress)"
  blocked_reason_lines="$(_board_ticket_reason_lines blocked)"
  pr_summary_lines="none"
  completed_lines="none"
  approval_lines="none"
  incomplete_lines="none"
  recommendation_lines="none"
  review_evidence_lines="none"
  if [[ -n "$stage_completion_file" && -f "$stage_completion_file" ]]; then
    pr_summary_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## PR Status by Ticket$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$stage_completion_file")"
    completed_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Completed Successfully$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$stage_completion_file")"
    approval_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Approval Links Requiring Re-run$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$stage_completion_file")"
    incomplete_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Not Completed and Why$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$stage_completion_file")"
    recommendation_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Recommendations$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$stage_completion_file")"
  fi
  if [[ -n "$review_status_file" && -f "$review_status_file" ]]; then
    review_evidence_lines="$(awk '
      BEGIN { in_section = 0 }
      /^## Review Evidence Matrix$/ { in_section = 1; next }
      /^## / && in_section == 1 { exit }
      in_section == 1 && /^- / { print }
    ' "$review_status_file")"
  fi
  pr_summary_lines="$(_flatten_pr_lines_for_brief "$pr_summary_lines")"
  completed_lines="$(_flatten_section_lines_for_brief "completed" "$completed_lines")"
  approval_lines="$(_flatten_section_lines_for_brief "approval-links" "$approval_lines")"
  incomplete_lines="$(_flatten_section_lines_for_brief "not-completed" "$incomplete_lines")"
  recommendation_lines="$(_flatten_section_lines_for_brief "recommendations" "$recommendation_lines")"

  if [[ ! -f "$COMPLETION_BRIEF_TEMPLATE" ]]; then
    echo "[stages-action] ERROR: completion brief template missing: ${COMPLETION_BRIEF_TEMPLATE#"$REPO_ROOT"/}"
    return 1
  fi
  template_text="$(cat "$COMPLETION_BRIEF_TEMPLATE")"
  printf "$template_text\n" \
    "$STAGE" \
    "$delivery_status" \
    "$review_status" \
    "$board_done" \
    "$github_issue_open_total" \
    "$github_wiki_status" \
    "$github_wiki_url" \
    "$board_backlog" \
    "$board_in_progress" \
    "$board_blocked" \
    "$open_total" \
    "$pr_summary_lines" \
    "$completed_lines" \
    "$approval_lines" \
    "$incomplete_lines" \
    "$recommendation_lines" \
    "$backlog_reason_lines" \
    "$in_progress_reason_lines" \
    "$gate_reason" \
    "$ppt_required" \
    "$ppt_post_gate" \
    "$ppt_hash_match" \
    "$ppt_source_path" \
    "$ppt_wiki_path" \
    "$next_action"

  # Human-readable Markdown completion report — surfaced directly to the agent chat.
  # This block must remain even when board has open items; it IS the required report.
  _status_icon() {
    local raw="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
    case "$raw" in
      ready_for_done|done|clear|ok|updated|true|yes) printf '🟢' ;;
      awaiting_human_review|already_dispatched|pending|in-progress|active|partial|unknown|unavailable) printf '🟡' ;;
      fail|failed|error|blocked|false|no|regression-detected) printf '🔴' ;;
      *) printf '⚪' ;;
    esac
  }

  delivery_icon="$(_status_icon "$delivery_status")"
  review_icon="$(_status_icon "$review_status")"
  wiki_icon="$(_status_icon "$github_wiki_status")"
  debt_icon="$(_status_icon "$workflow_code_debt_monotonic_status")"

  echo ""
  echo "## 📊 $(printf '%s' "$STAGE" | tr '[:lower:]' '[:upper:]') Stage — Completion Dashboard"
  echo ""
  echo "### Status at a Glance"
  echo ""
  echo "| Signal | Value |"
  echo "|---|---|"
  echo "| Stage | ${STAGE} |"
  echo "| Delivery | ${delivery_icon} ${delivery_status} |"
  echo "| Review | ${review_icon} ${review_status} |"
  echo "| Board done | $(if [[ "${board_done}" -gt 0 ]]; then printf '🟢'; else printf '🟡'; fi) ${board_done} |"
  echo "| Open items | $(if [[ "${open_total}" -eq 0 ]]; then printf '🟢'; else printf '🟡'; fi) ${open_total} (backlog=${board_backlog}, in-progress=${board_in_progress}, blocked=${board_blocked}) |"
  echo "| GitHub issues open | $(if [[ "$github_issue_open_total" == "0" ]]; then printf '🟢'; else printf '🟡'; fi) ${github_issue_open_total} |"
  echo "| Wiki sync | ${wiki_icon} ${github_wiki_status} |"
  echo "| Workflow code debt | ${debt_icon} ${workflow_code_debt_monotonic_status} (delta=${workflow_code_debt_delta}) |"
  echo ""
  echo "### 🔗 Pull Request Batch"
  if [[ -n "$(printf '%s' "$pr_summary_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r pr_line; do
      [[ -n "$pr_line" ]] || continue
      echo "- ${pr_line#[stages-action][brief] pull-requests: }"
    done <<< "$pr_summary_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "### 🧪 Review Evidence Batch"
  if [[ -n "$(printf '%s' "$review_evidence_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r evidence_line; do
      [[ -n "$evidence_line" ]] || continue
      echo "- ${evidence_line#- }"
    done <<< "$review_evidence_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "### ✅ Completed Successfully"
  if [[ -n "$(printf '%s' "$completed_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r completed_line; do
      [[ -n "$completed_line" ]] || continue
      echo "- ${completed_line#[stages-action][brief] completed: }"
    done <<< "$completed_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "### 🔁 Approval Links Requiring Re-run"
  if [[ -n "$(printf '%s' "$approval_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r approval_line; do
      [[ -n "$approval_line" ]] || continue
      echo "- ${approval_line#[stages-action][brief] approval-links: }"
    done <<< "$approval_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "### ⚠️ Not Completed and Why"
  if [[ -n "$(printf '%s' "$incomplete_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r incomplete_line; do
      [[ -n "$incomplete_line" ]] || continue
      echo "- ${incomplete_line#[stages-action][brief] not-completed: }"
    done <<< "$incomplete_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "### 💡 Recommendations"
  if [[ -n "$(printf '%s' "$recommendation_lines" | tr -d '[:space:]')" ]]; then
    while IFS= read -r recommendation_line; do
      [[ -n "$recommendation_line" ]] || continue
      echo "- ${recommendation_line#[stages-action][brief] recommendations: }"
    done <<< "$recommendation_lines"
  else
    echo "- none"
  fi
  echo ""
  if [[ "${board_backlog}" -gt 0 ]] 2>/dev/null; then
    echo "### 📥 Open Tickets (backlog)"
    echo "${backlog_reason_lines}"
    echo ""
  fi
  if [[ "${board_in_progress}" -gt 0 ]] 2>/dev/null; then
    echo "### 🛠️ Open Tickets (in-progress)"
    echo "${in_progress_reason_lines}"
    echo ""
  fi
  if [[ "${board_blocked}" -gt 0 ]] 2>/dev/null; then
    echo "### ⛔ Open Tickets (blocked)"
    echo "${blocked_reason_lines}"
    echo ""
  fi
  echo "### 🧭 Gate reason"
  echo "${gate_reason}"
  echo ""
  echo "### 📽️ PowerPoint"
  echo "required=${ppt_required}; post_gate=${ppt_post_gate}; hash_match=${ppt_hash_match}"
  echo "source: ${ppt_source_path}"
  echo "wiki:   ${ppt_wiki_path}"
  echo ""
  echo "### 🚀 Next Required Action"
  echo "${next_action}"
}

_render_mermaid_diagrams() {
  # Renders all .mmd source files under docs/diagrams/mermaid/ to SVG under
  # docs/images/mermaid/ using the mermaid CLI (mmdc). Falls back to container
  # execution via the shared tool registry when mmdc is not installed locally.
  local src_dir="${REPO_ROOT}/docs/diagrams/mermaid"
  local out_dir="${REPO_ROOT}/docs/images/mermaid"
  local mmdc_bin rendered=0 failed=0 use_relative_paths=0
  local status_dir log_file

  if [[ ! -d "$src_dir" ]]; then
    echo "[stages-action] INFO: mermaid source dir missing (${src_dir#"$REPO_ROOT"/}), skipping diagram render"
    return 0
  fi

  safe_mkdir_p "$out_dir" "stages-action audit output directory"
  status_dir="$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
  safe_mkdir_p "$status_dir" "stages-action audit status directory"
  log_file="$status_dir/MERMAID_RENDER_STATUS.md"
  {
    echo "# Mermaid Render Status (${STAGE})"
    echo ""
    echo "- generated_at: ${RUN_STARTED_AT}"
    echo "- source_dir: ${src_dir#"$REPO_ROOT"/}"
    echo "- output_dir: ${out_dir#"$REPO_ROOT"/}"
    echo ""
    echo "## Failures"
    echo ""
  } > "$log_file"

  # Prefer the registry-backed wrapper so Mermaid rendering follows the same
  # container-first path as other external tools.
  local run_tool_sh="${REPO_ROOT}/.github/skills/shared/shell/scripts/run-tool.sh"
  if [[ -f "$run_tool_sh" ]]; then
    mmdc_bin="bash ${run_tool_sh} mmdc"
    use_relative_paths=1
  elif command -v mmdc >/dev/null 2>&1; then
    mmdc_bin="mmdc"
  else
    echo "[stages-action] INFO: mmdc not found and run-tool.sh missing, skipping diagram render"
    return 0
  fi

  while IFS= read -r mmd_file; do
    local filename input_file output_file
    filename="$(basename "$mmd_file" .mmd)"
    input_file="$mmd_file"
    output_file="${out_dir}/${filename}.svg"
    if [[ "$use_relative_paths" == "1" ]]; then
      input_file="${mmd_file#"$REPO_ROOT"/}"
      output_file="${output_file#"$REPO_ROOT"/}"
    fi

    local render_output
    render_output="$(mktemp)"
    if bash -c "${mmdc_bin} -i '${input_file}' -o '${output_file}' -b white" >"$render_output" 2>&1; then
      rendered=$((rendered + 1))
    else
      echo "[stages-action] WARN: failed to render ${filename}.mmd"
      {
        echo "- ${filename}.mmd"
        echo ""
        echo "\`\`\`text"
        sed -n '1,40p' "$render_output"
        echo "\`\`\`"
        echo ""
      } >> "$log_file"
      failed=$((failed + 1))
    fi
    rm -f "$render_output"
  done < <(find "$src_dir" -name "*.mmd" -type f | sort)

  echo "[stages-action] INFO: mermaid diagrams rendered=${rendered} failed=${failed} -> ${out_dir#"$REPO_ROOT"/}"
  if [[ "$failed" != "0" ]]; then
    echo "[stages-action] INFO: mermaid failure details -> ${log_file#"$REPO_ROOT"/}"
  fi
}

_run_project_powerpoint_post_gate() {
  local prompt_invoke_script powerpoint_script stage_doc_source
  local generated_ppt wiki_ppt

  if [[ "$STAGE" != "project" ]]; then
    return 0
  fi

  delivery_status_file="$(_latest_stage_review_file "$DELIVERY_STATUS_FILENAME" "$DELIVERY_STATUS_LEGACY_FILENAMES")"
  if [[ -z "$delivery_status_file" || ! -f "$delivery_status_file" ]]; then
    echo "[stages-action] INFO: skipping post-stage PowerPoint (missing ${DELIVERY_STATUS_FILENAME})"
    return 0
  fi

  delivery_status_value="$(grep -E '^- status:' "$delivery_status_file" 2>/dev/null | head -n1 | sed -E 's/^- status:[[:space:]]*//' | tr -d '"' || true)"
  if [[ "$delivery_status_value" != "triggered" && "$delivery_status_value" != "already_dispatched" ]]; then
    echo "[stages-action] INFO: skipping post-stage PowerPoint (delivery status: ${delivery_status_value:-unknown})"
    return 0
  fi

  prompt_invoke_script="$REPO_ROOT/.github/hooks/prompt-invoke.sh"
  powerpoint_script="$REPO_ROOT/.github/skills/powerpoint/scripts/powerpoint.sh"
  stage_doc_source="$(_stage_doc_path)"
  generated_ppt="$REPO_ROOT/$(_stage_powerpoint_source_relpath "$STAGE")"
  wiki_ppt="$REPO_ROOT/$(_stage_wiki_powerpoint_relpath "$STAGE")"

  echo "[stages-action] INFO: running post-stage /powerpoint for project"
  PROMPT_INTERNAL_CALL=1 bash "$prompt_invoke_script" --prompt-name powerpoint --summary "/powerpoint (post-/project)" -- \
    env SOURCE="$stage_doc_source" LAYER="$(_active_layer_id)" bash "$powerpoint_script"

  if [[ ! -f "$generated_ppt" ]]; then
    echo "[stages-action] ERROR: generated project PowerPoint missing at ${generated_ppt#"$REPO_ROOT"/}"
    return 1
  fi

  safe_mkdir_p "$(dirname "$wiki_ppt")" "stages-action wiki powerpoint directory"
  cp "$generated_ppt" "$wiki_ppt"
  echo "[stages-action] INFO: post-stage wiki PowerPoint updated: docs/wiki/assets/Project-Summary.pptx"

  echo "[stages-action] INFO: syncing GitHub wiki with refreshed project briefing"
  _sync_project_wiki_post_gate
}

_is_stage_ready_for_planning() {
  local stage_doc
  stage_doc="$(_stage_doc_path)"
  if [[ ! -f "$stage_doc" ]]; then
    echo "[stages-action] INFO: stage gate unresolved (missing stage document: $stage_doc)"
    return 1
  fi
  if grep -qi '^ready_for_planning: true$' "$stage_doc"; then
    return 0
  fi

  gate_reason="$(grep -i '^gate_reason:' "$stage_doc" | head -n1 | sed 's/^gate_reason:[[:space:]]*//I' | tr -d '"' || true)"
  if [[ -z "$gate_reason" ]]; then
    gate_reason="stage is not marked ready_for_planning"
  fi
  echo "[stages-action] INFO: stage delivery halted - $gate_reason"
  return 1
}

if [[ "$DRY_RUN_MODE" == "1" || "$DRY_RUN_MODE" == "2" ]]; then
  echo "[stages-action] INFO: DRY_RUN=$DRY_RUN_MODE active -> resetting artifacts + board/wiki before stage execution"
  _restore_done_documents_to_input
  if [[ "$DRY_RUN_MODE" == "2" ]]; then
    _cleanup_stage_primary_system_assets
  fi
  _cleanup_stage_board_and_wiki
fi

snapshot_file_list "$BEFORE_SNAPSHOT"

echo "[progress][stages-action] step=1/6 action=ingest-input-to-data elapsed=$(_elapsed_seconds)s"
export DIGITAL_ARTIFACTS_EMIT_PIPELINE_AUDIT=0
PROMPT_INTERNAL_CALL=1 bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-input-2-data.sh"

echo "[progress][stages-action] step=2/6 action=specification-synthesis elapsed=$(_elapsed_seconds)s"
export DIGITAL_TEAM_LAYER_ID="${DIGITAL_TEAM_LAYER_ID:-python-runtime}"
bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-data-2-specification.sh"

echo "[progress][stages-action] step=3/6 action=stage-readiness-gate elapsed=$(_elapsed_seconds)s"
bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-specification-2-stage.sh" "$STAGE"
_emit_gate_observability
_render_mermaid_diagrams

echo "[progress][stages-action] step=4/6 action=planning-synchronization elapsed=$(_elapsed_seconds)s"
if [[ "$DRY_RUN_MODE" == "1" ]]; then
  export DIGITAL_STAGE_PRIMARY_SYNC=0
else
  export DIGITAL_STAGE_PRIMARY_SYNC=1
fi
bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-specification-2-planning.sh" "$STAGE"
_ensure_stage_sprint_ref

if [[ "$DRY_RUN_MODE" == "1" || "$DRY_RUN_MODE" == "2" ]]; then
  echo "[stages-action] INFO: DRY_RUN=$DRY_RUN_MODE stops after planning (delivery trigger skipped by design)"
  _write_stagnation_report
  _write_stage_completion_report
  _write_stage_handoff
  snapshot_file_list "$AFTER_SNAPSHOT"
  comm -13 "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" > "$NEW_ARTIFACTS"
  _write_audit_capture
  _print_stage_completion_brief
  if ! _enforce_workflow_code_debt_gate; then
    exit 1
  fi
  exit 0
fi

if ! _is_stage_ready_for_planning; then
  _emit_gate_observability
  _write_stagnation_report
  _write_stage_completion_report
  _write_stage_handoff
  snapshot_file_list "$AFTER_SNAPSHOT"
  comm -13 "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" > "$NEW_ARTIFACTS"
  _write_audit_capture
  _print_stage_completion_brief
  if ! _enforce_workflow_code_debt_gate; then
    exit 1
  fi
  exit 0
fi

# CRITICAL REQUIREMENT (2026-04-17):
# /project MUST trigger delivery agents AND implement bugs/tasks, not just plan them.
# Delivery agents (fullstack-engineer, data-scientist, etc.) receive work_handoff_v1.
# Agents create branches, implement code, run tests, and move board tickets to done.
# This is NOT optional. If delivery is skipped, the stage workflow is incomplete.
echo "[progress][stages-action] step=5/6 action=delivery-dispatch elapsed=$(_elapsed_seconds)s"
if bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-planning-2-delivery.sh" "$STAGE" 2>/dev/null; then
  :
else
  delivery_exit=$?
  echo "[stages-action] INFO: delivery phase skipped or not available (exit code: $delivery_exit)"
fi

if [[ -f "$CHECK_DELIVERY_WORK_SCRIPT" ]]; then
  if bash "$CHECK_DELIVERY_WORK_SCRIPT" "$STAGE"; then
    echo "[stages-action] INFO: delivery handoff check completed (no pending handoffs)"
  else
    check_delivery_exit=$?
    if [[ "$check_delivery_exit" == "3" ]]; then
      echo "[stages-action] INFO: delivery handoff check found pending work items (awaiting delivery agents)"
    else
      echo "[stages-action] WARN: delivery handoff check failed (exit code: $check_delivery_exit)"
    fi
  fi
fi

_emit_delivery_activity_snapshot
_emit_board_sync_conflict_guidance

# Write resume marker so next /project call knows pending handoff work
_pending_backlog="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/backlog" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
_pending_in_progress="$(git for-each-ref --format='%(refname:short)' "refs/board/${STAGE}/in-progress" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
_runtime_handoff_dir="$REPO_ROOT/.digital-runtime/handoffs/${STAGE}"
_handoff_files="0"
while IFS= read -r _handoff_file; do
  _handoff_status="$(awk -F': ' '$1 == "status" {print $2; exit}' "$_handoff_file" 2>/dev/null | tr -d '"' | tr -d '\r' || true)"
  if [[ "$_handoff_status" == "done" ]]; then
    continue
  fi
  _handoff_files="$((_handoff_files + 1))"
done < <(find "$_runtime_handoff_dir" -name "*-handoff.yaml" -type f 2>/dev/null)
_resume_marker="$REPO_ROOT/.digital-artifacts/50-planning/${STAGE}/RESUME_STATE.yaml"
safe_mkdir_p "$(dirname "$_resume_marker")" "stages-action resume marker directory"
cat > "$_resume_marker" <<RESUME_EOF
# Resume marker — written by stages-action after each run
# Agent reads this on next /project call to resume where work left off
generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
stage: ${STAGE}
board_backlog: ${_pending_backlog}
board_in_progress: ${_pending_in_progress}
pending_handoff_files: ${_handoff_files}
handoff_dir: .digital-runtime/handoffs/${STAGE}
loop_done: $( [[ "${_pending_backlog}" == "0" && "${_pending_in_progress}" == "0" ]] && echo "true" || echo "false" )
next_action: $( \
  if [[ "${_pending_backlog}" == "0" && "${_pending_in_progress}" == "0" ]]; then \
    echo "none - all work done"; \
  elif [[ "${_handoff_files}" != "0" ]]; then \
    echo "process pending handoff files in handoff_dir"; \
  else \
    echo "no pending handoffs; do NOT move tickets to done automatically — require PR link + human approval evidence first"; \
  fi \
)
RESUME_EOF
echo "[stages-action] INFO: resume marker -> ${_resume_marker#"$REPO_ROOT"/} (backlog=${_pending_backlog} in_progress=${_pending_in_progress} handoffs=${_handoff_files})"

echo "[progress][stages-action] step=6/6 action=review-status elapsed=$(_elapsed_seconds)s"
if bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-delivery-2-review.sh" "$STAGE" 2>/dev/null; then
  :
else
  review_exit=$?
  echo "[stages-action] INFO: review aggregation skipped or not available (exit code: $review_exit)"
fi

_validate_svg_assets

_run_project_powerpoint_post_gate

if ! _enforce_mandatory_primary_sync_gate; then
  _write_stagnation_report
  _write_stage_completion_report
  _write_stage_handoff
  snapshot_file_list "$AFTER_SNAPSHOT"
  comm -13 "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" > "$NEW_ARTIFACTS"
  _write_audit_capture
  _print_stage_completion_brief
  exit 1
fi

_close_stage_sprints_if_completed

_emit_gate_observability
_write_stagnation_report
_write_stage_completion_report
_write_stage_handoff
snapshot_file_list "$AFTER_SNAPSHOT"
comm -13 "$BEFORE_SNAPSHOT" "$AFTER_SNAPSHOT" > "$NEW_ARTIFACTS"
_write_audit_capture
_print_stage_completion_brief
if ! _enforce_workflow_code_debt_gate; then
  exit 1
fi

echo "[stages-action] INFO: delivery review status -> .digital-artifacts/60-review/*/${STAGE}/${DELIVERY_STATUS_FILENAME}"
echo "[stages-action] INFO: delivery review report -> .digital-artifacts/60-review/*/${STAGE}/${DELIVERY_REVIEW_FILENAME}"
echo "[stages-action] INFO: stage handoff -> .digital-artifacts/60-review/*/${STAGE}/${STAGE_HANDOFF_FILENAME}"
