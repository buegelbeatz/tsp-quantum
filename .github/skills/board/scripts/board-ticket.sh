#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Manage board tickets stored as YAML blobs in one configured board namespace.
#   Supports creating, moving (checkout/complete/block), and listing tickets.
#   Provides atomic ticket locking for distributed agent coordination via
#   git hash-object + update-ref + push --force-with-lease.
# Security:
#   Reads and writes only to the local git object store and configured remote.
#   No eval, no dynamic code execution. Ticket content is plain YAML text.
#   LOCKED_BY values are taken from environment; never sourced from ticket content.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
SHARED_GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
RUN_TOOL_SH="$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh"

if [[ -f "$SHARED_GITHUB_LIB" ]]; then
  # shellcheck source=/dev/null
  source "$SHARED_GITHUB_LIB"
fi

REMOTE="${BOARD_REMOTE:-origin}"
BOARD_NAME="${BOARD_NAME:-}"
REF_PREFIX=""
VALID_COLUMNS=()

# ── helpers ─────────────────────────────────────────────────────────────────

die()  { echo "board-ticket: ERROR: $*" >&2; exit 1; }
info() { echo "board-ticket: $*"; }
warn() { echo "board-ticket: WARNING: $*" >&2; }

board_run_gh() {
  if declare -F github_run_gh >/dev/null 2>&1; then
    github_run_gh "$@"
    return $?
  fi
  if [[ -x "$RUN_TOOL_SH" || -f "$RUN_TOOL_SH" ]]; then
    GH_TOKEN="${GH_TOKEN:-}" GITHUB_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}" bash "$RUN_TOOL_SH" gh "$@"
    return $?
  fi
  return 127
}

board_run_python() {
  local helper="$1"
  shift

  if [[ -x "$RUN_TOOL_SH" || -f "$RUN_TOOL_SH" ]]; then
    local helper_for_tool="$helper"
    if [[ "$helper" == "$REPO_ROOT"/* ]]; then
      helper_for_tool="${helper#"$REPO_ROOT"/}"
    fi
    bash "$RUN_TOOL_SH" python3 "$helper_for_tool" "$@"
    return $?
  fi

  python3 "$helper" "$@"
}

board_can_use_github() {
  if declare -F github_require_token >/dev/null 2>&1; then
    github_require_token || true
  fi
  board_run_gh api /user >/dev/null 2>&1
}

sync_issue_status_for_ticket() {
  [[ "${BOARD_SYNC_GITHUB_STATUS:-1}" == "1" ]] || return 0
  board_can_use_github || {
    warn "GitHub status sync failed: runtime/auth unavailable"
    return 1
  }

  local ticket_id="$1"
  local to_col="$2"
  local repo_slug
  repo_slug="$(resolve_github_repo_slug)"
  [[ -n "$repo_slug" ]] || {
    warn "GitHub status sync failed: cannot resolve repository slug"
    return 1
  }

  local target_status
  target_status="$(project_status_name_for_column "$to_col")"
  [[ -n "$target_status" ]] || {
    warn "GitHub status sync failed: unsupported board column '$to_col'"
    return 1
  }

  local issue_number
  issue_number="$(board_run_gh issue list --repo "$repo_slug" --search "\"${ticket_id}\" in:title state:open" --json number --jq '.[0].number // empty' 2>/dev/null || true)"
  [[ -n "$issue_number" ]] || {
    warn "GitHub status sync failed: no issue found for ticket '${ticket_id}'"
    return 1
  }

  # Prefer real GitHub Project status transitions over label coloring.
  if ! sync_project_item_status_for_issue "$repo_slug" "$issue_number" "$to_col"; then
    warn "GitHub status sync failed: cannot set project status '$to_col' for issue #${issue_number}"
    return 1
  fi

  return 0
}

resolve_project_owner() {
  local repo_slug="$1"
  if [[ -n "${GITHUB_OWNER:-}" ]]; then
    printf '%s' "$GITHUB_OWNER"
    return 0
  fi
  printf '%s' "${repo_slug%%/*}"
}

resolve_project_number() {
  local stage_lower="${BOARD_NAME:-}"
  local stage_upper
  stage_upper="$(printf '%s' "$stage_lower" | tr '[:lower:]' '[:upper:]')"
  local stage_doc="$REPO_ROOT/.digital-artifacts/40-stage/${stage_upper}.md"

  if [[ -n "${BOARD_GITHUB_PROJECT_NUMBER:-}" ]]; then
    printf '%s' "$BOARD_GITHUB_PROJECT_NUMBER"
    return 0
  fi
  if [[ -n "${GITHUB_PROJECT_NUMBER:-}" ]]; then
    printf '%s' "$GITHUB_PROJECT_NUMBER"
    return 0
  fi
  if [[ -f "$stage_doc" ]]; then
    local board_id
    board_id="$(grep -E '^board_id:' "$stage_doc" 2>/dev/null | head -n1 | sed -E 's/^board_id:[[:space:]]*"?([0-9]+)"?.*$/\1/' || true)"
    if [[ "$board_id" =~ ^[0-9]+$ ]]; then
      printf '%s' "$board_id"
      return 0
    fi
  fi
  printf ''
}

project_status_name_for_column() {
  local column="$1"
  case "$column" in
    backlog) printf '%s' "Backlog" ;;
    in-progress) printf '%s' "In Progress" ;;
    blocked) printf '%s' "Blocked" ;;
    done) printf '%s' "Done" ;;
    *) printf '%s' "" ;;
  esac
}

sync_project_item_status_for_issue() {
  local repo_slug="$1"
  local issue_number="$2"
  local to_col="$3"

  local owner project_number status_name
  owner="$(resolve_project_owner "$repo_slug")"
  project_number="$(resolve_project_number)"
  status_name="$(project_status_name_for_column "$to_col")"

  [[ -n "$owner" && -n "$project_number" && -n "$status_name" ]] || return 1

  local project_id field_id option_id item_id
  project_id="$(board_run_gh project view "$project_number" --owner "$owner" --format json --jq '.id // empty' 2>/dev/null || true)"
  [[ -n "$project_id" ]] || return 1

  field_id="$(board_run_gh project field-list "$project_number" --owner "$owner" --format json --jq '.fields[] | select(.name == "Status") | .id' 2>/dev/null | head -n1 || true)"
  [[ -n "$field_id" ]] || return 1

  option_id="$(board_run_gh project field-list "$project_number" --owner "$owner" --format json --jq ".fields[] | select(.name == \"Status\") | .options[] | select(.name == \"${status_name}\") | .id" 2>/dev/null | head -n1 || true)"
  [[ -n "$option_id" ]] || return 1

  item_id="$(board_run_gh project item-list "$project_number" --owner "$owner" --format json --jq ".items[] | select((.content.number // 0) == ${issue_number}) | .id" 2>/dev/null | head -n1 || true)"
  [[ -n "$item_id" ]] || return 1

  board_run_gh project item-edit \
    --id "$item_id" \
    --project-id "$project_id" \
    --field-id "$field_id" \
    --single-select-option-id "$option_id" >/dev/null 2>&1
}

resolve_github_repo_slug() {
  local remote_url
  remote_url="$(git -C "$REPO_ROOT" remote get-url "$REMOTE" 2>/dev/null || true)"
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

find_milestone_number() {
  local repo_slug="$1"
  local title="$2"
  board_run_gh api "repos/${repo_slug}/milestones?state=all&per_page=100" --jq '.[] | [.number,.title] | @tsv' 2>/dev/null \
    | while IFS=$'\t' read -r number milestone_title; do
        [[ "$milestone_title" == "$title" ]] || continue
        printf '%s\n' "$number"
        break
      done
}

sync_milestone_on_create() {
  [[ "${BOARD_SYNC_MILESTONES:-1}" == "1" ]] || return 0
  board_can_use_github || { warn "Skipping milestone sync (GitHub runtime/auth unavailable)."; return 0; }

  local sprint_id="$1"
  local goal="$2"
  local repo_slug
  repo_slug="$(resolve_github_repo_slug)"
  [[ -n "$repo_slug" ]] || { warn "Skipping milestone sync (remote is not github.com)."; return 0; }

  local existing_number
  existing_number="$(find_milestone_number "$repo_slug" "$sprint_id" || true)"
  if [[ -n "$existing_number" ]]; then
    info "Milestone '${sprint_id}' already exists (#${existing_number})."
    return 0
  fi

  if board_run_gh api -X POST "repos/${repo_slug}/milestones" -f title="$sprint_id" -f description="$goal" >/dev/null 2>&1; then
    info "Milestone '${sprint_id}' created on GitHub."
  else
    warn "Failed to create milestone '${sprint_id}' on GitHub."
  fi
}

sync_milestone_on_close() {
  [[ "${BOARD_SYNC_MILESTONES:-1}" == "1" ]] || return 0
  board_can_use_github || { warn "Skipping milestone sync (GitHub runtime/auth unavailable)."; return 0; }

  local sprint_id="$1"
  local repo_slug
  repo_slug="$(resolve_github_repo_slug)"
  [[ -n "$repo_slug" ]] || { warn "Skipping milestone sync (remote is not github.com)."; return 0; }

  local milestone_number
  milestone_number="$(find_milestone_number "$repo_slug" "$sprint_id" || true)"
  if [[ -z "$milestone_number" ]]; then
    warn "No GitHub milestone found for sprint '${sprint_id}'."
    return 0
  fi

  if board_run_gh api -X PATCH "repos/${repo_slug}/milestones/${milestone_number}" -f state=closed >/dev/null 2>&1; then
    info "Milestone '${sprint_id}' closed on GitHub."
  else
    warn "Failed to close milestone '${sprint_id}' on GitHub."
  fi
}

require_done_pr_gate() {
  local ticket_id="$1"
  [[ "${BOARD_SKIP_PR_GATE:-0}" == "1" ]] && return 0

  board_can_use_github || die "GitHub runtime/auth is required for done transition gate (or set BOARD_SKIP_PR_GATE=1)"

  local pr_numbers
  pr_numbers="$(board_run_gh pr list --search "\"${ticket_id}\" is:merged" --json number --jq '.[].number' 2>/dev/null || true)"
  [[ -n "$pr_numbers" ]] || die "No merged PR found referencing ticket ${ticket_id}. Merge a PR before moving to done."

  local approved=0
  local pr_number review_decision
  while IFS= read -r pr_number; do
    [[ -z "$pr_number" ]] && continue
    review_decision="$(board_run_gh pr view "$pr_number" --json reviewDecision --jq '.reviewDecision // ""' 2>/dev/null || true)"
    if [[ "$review_decision" == "APPROVED" ]]; then
      approved=1

      # Require visible review/quality evidence in PR body or comments.
      # This enforces governance requirement 5d from the architecture KISS plan.
      if [[ "${BOARD_SKIP_REVIEW_EVIDENCE_GATE:-0}" != "1" ]]; then
        local evidence_text
        evidence_text="$(board_run_gh pr view "$pr_number" --json body,comments --jq '[.body // "", (.comments[]?.body // "")] | join("\n")' 2>/dev/null || true)"
        local has_review_keywords=0
        local has_test_keywords=0
        if printf '%s' "$evidence_text" | grep -Eiq 'review|quality|qa'; then
          has_review_keywords=1
        fi
        if printf '%s' "$evidence_text" | grep -Eiq 'test|coverage|pytest|unit[[:space:]]+test'; then
          has_test_keywords=1
        fi
        if [[ "$has_review_keywords" != "1" || "$has_test_keywords" != "1" ]]; then
          die "Merged+approved PR found for ${ticket_id}, but review evidence is missing. Add visible quality/review and test/coverage proof in PR description or comments."
        fi
      fi

      break
    fi
  done <<< "$pr_numbers"

  [[ "$approved" == "1" ]] || die "Merged PR found for ${ticket_id}, but no human approval detected (reviewDecision=APPROVED)."
}

resolve_board_settings() {
  local target_board="${1:-$BOARD_NAME}"
  local helper="$SCRIPT_DIR/board_config.py"
  [[ -f "$helper" ]] || die "Missing board config helper: $helper"

  local config_lines=()
  local line
  while IFS= read -r line; do
    config_lines+=("$line")
  done < <(
    if [[ -n "$target_board" ]]; then
      board_run_python "$helper" shell "$REPO_ROOT" "$target_board"
    else
      board_run_python "$helper" shell "$REPO_ROOT"
    fi
  )

  local columns_csv=""
  local key value
  for line in "${config_lines[@]}"; do
    key="${line%%=*}"
    value="${line#*=}"
    case "$key" in
      BOARD_NAME) BOARD_NAME="$value" ;;
      REF_PREFIX) REF_PREFIX="$value" ;;
      COLUMNS) columns_csv="$value" ;;
      *) ;;
    esac
  done

  IFS=',' read -r -a VALID_COLUMNS <<< "$columns_csv"
  [[ -n "$REF_PREFIX" ]] || die "Unable to resolve board ref prefix"
  [[ ${#VALID_COLUMNS[@]} -gt 0 ]] || die "Unable to resolve board columns"
}

cmd_sprint_create() {
  local sprint_id="${1:-}"
  local goal="${2:-}"
  [[ -n "$sprint_id" ]] || die "Usage: sprint-create <sprint-id> <goal>"
  [[ -n "$goal" ]]      || die "Usage: sprint-create <sprint-id> <goal>"

  resolve_board_settings
  local sprint_ref="${REF_PREFIX}/sprints/${sprint_id}"
  local creator="${BOARD_AGENT:-${USER:-unknown-agent}}"

  if git -C "$REPO_ROOT" rev-parse --verify "$sprint_ref" &>/dev/null; then
    die "Sprint '${sprint_id}' already exists."
  fi

  local blob
  blob=$(git -C "$REPO_ROOT" hash-object -w --stdin <<EOF
id: ${sprint_id}
goal: "${goal}"
status: open
created_by: ${creator}
created_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
closed_at: null
tickets: []
EOF
)
  git -C "$REPO_ROOT" update-ref "${sprint_ref}" "${blob}"
  info "Sprint '${sprint_id}' created (goal: ${goal})."
  sync_milestone_on_create "$sprint_id" "$goal"
  [[ "${BOARD_PUSH:-0}" == "1" ]] && \
    git -C "$REPO_ROOT" push "$REMOTE" "+${sprint_ref}:${sprint_ref}" && \
    info "Sprint ref pushed."
  return 0
}

cmd_sprint_close() {
  local sprint_id="${1:-}"
  [[ -n "$sprint_id" ]] || die "Usage: sprint-close <sprint-id>"

  resolve_board_settings
  local sprint_ref="${REF_PREFIX}/sprints/${sprint_id}"

  git -C "$REPO_ROOT" rev-parse --verify "$sprint_ref" &>/dev/null \
    || die "Sprint '${sprint_id}' not found."

  local current
  current=$(git -C "$REPO_ROOT" cat-file -p "${sprint_ref}")
  local goal created_by created_at tickets
  goal=$(echo "$current" | grep '^goal:' | sed 's/^goal: //')
  created_by=$(echo "$current" | grep '^created_by:' | sed 's/^created_by: //')
  created_at=$(echo "$current" | grep '^created_at:' | sed 's/^created_at: //')
  tickets=$(echo "$current" | grep '^tickets:' | sed 's/^tickets: //')

  local sprint_id_val
  sprint_id_val=$(echo "$current" | grep '^id:' | sed 's/^id: //')

  local blob
  blob=$(git -C "$REPO_ROOT" hash-object -w --stdin <<EOF
id: ${sprint_id_val}
goal: ${goal}
status: closed
created_by: ${created_by}
created_at: ${created_at}
closed_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
tickets: ${tickets}
EOF
)
  git -C "$REPO_ROOT" update-ref "${sprint_ref}" "${blob}"
  info "Sprint '${sprint_id}' closed."
  sync_milestone_on_close "$sprint_id"
  [[ "${BOARD_PUSH:-0}" == "1" ]] && \
    git -C "$REPO_ROOT" push "$REMOTE" "+${sprint_ref}:${sprint_ref}" && \
    info "Sprint ref pushed."
  return 0
}

cmd_sprint_list() {
  resolve_board_settings
  local sprint_prefix="${REF_PREFIX}/sprints"
  local found=0
  local has_open=0
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    found=1
    local sprint_id status goal
    sprint_id="${ref##*/}"
    local content
    content=$(git -C "$REPO_ROOT" cat-file -p "$ref" 2>/dev/null || echo "")
    status=$(echo "$content" | grep '^status:' | sed 's/^status: //')
    goal=$(echo "$content" | grep '^goal:' | sed 's/^goal: //')
    if [[ "${status}" == "open" ]]; then
      has_open=1
    fi
    printf "  %-24s  %-8s  %s\n" "$sprint_id" "${status:-?}" "${goal:-}"
  done < <(git -C "$REPO_ROOT" for-each-ref --format='%(refname)' "${sprint_prefix}/" 2>/dev/null)

  local in_progress_count=0
  local title_samples=""
  local ticket_id ticket_title
  while IFS= read -r ticket_id; do
    [[ -n "$ticket_id" ]] || continue
    in_progress_count=$((in_progress_count + 1))
    if [[ "$in_progress_count" -le 3 ]]; then
      ticket_title="$(read_ticket "${REF_PREFIX}/in-progress/${ticket_id}" | grep '^title:' | sed 's/title: *//' | tr -d '"')"
      if [[ -n "$ticket_title" ]]; then
        if [[ -z "$title_samples" ]]; then
          title_samples="$ticket_title"
        else
          title_samples+="; $ticket_title"
        fi
      fi
    fi
  done < <(list_column "in-progress")

  if [[ "$in_progress_count" -gt 0 && "$has_open" == "0" ]]; then
    local synthetic_sprint_id="auto-${BOARD_NAME}-current"
    local synthetic_goal="Derived from in-progress tickets"
    if [[ -n "$title_samples" ]]; then
      synthetic_goal="Complete current in-progress work: ${title_samples}"
    fi
    printf "  %-24s  %-8s  %s\n" "$synthetic_sprint_id" "open" "$synthetic_goal"
  elif [[ "$found" == "0" ]]; then
    info "No sprints found for board ${BOARD_NAME}."
  fi
  return 0
}

cmd_sprint_show() {
  local sprint_id="${1:-}"
  [[ -n "$sprint_id" ]] || die "Usage: sprint-show <sprint-id>"

  resolve_board_settings
  local sprint_ref="${REF_PREFIX}/sprints/${sprint_id}"
  git -C "$REPO_ROOT" rev-parse --verify "$sprint_ref" &>/dev/null \
    || die "Sprint '${sprint_id}' not found."

  local content
  content="$(git -C "$REPO_ROOT" cat-file -p "$sprint_ref")"
  printf '%s\n' "$content"
  return 0
}

list_all_board_prefixes() {
  local helper="$SCRIPT_DIR/board_config.py"
  board_run_python "$helper" list "$REPO_ROOT" | while IFS='|' read -r descriptor ref_prefix _rest; do
    [[ -n "$descriptor" && -n "$ref_prefix" ]] || continue
    printf '%s\n' "$ref_prefix"
  done
}

column_valid() {
  local col="$1"
  for c in "${VALID_COLUMNS[@]}"; do [[ "$c" == "$col" ]] && return 0; done
  return 1
}

# Store a YAML string as a git blob, return its hash
store_blob() {
  printf '%s' "$1" | git -C "$REPO_ROOT" hash-object --stdin -w
}

# Read a ticket blob from a ref
read_ticket() {
  local ref="$1"
  git -C "$REPO_ROOT" cat-file blob "$ref" 2>/dev/null || echo ""
}

# Write a ref pointing to a blob hash
write_ref() {
  local ref="$1" hash="$2"
  git -C "$REPO_ROOT" update-ref "$ref" "$hash"
}

# Delete a ref
delete_ref() {
  local ref="$1"
  git -C "$REPO_ROOT" update-ref -d "$ref" 2>/dev/null || true
}

# List all ticket IDs in a column
list_column() {
  local col="$1"
  git -C "$REPO_ROOT" for-each-ref --format="%(refname)" "${REF_PREFIX}/${col}/" 2>/dev/null \
    | sed "s|${REF_PREFIX}/${col}/||"
}

# ── commands ─────────────────────────────────────────────────────────────────

cmd_create() {
  resolve_board_settings
  local id="$1" title="$2" description="${3:-}"
  local acceptance_criteria_raw="${BOARD_ACCEPTANCE_CRITERIA:-}"
  local definition_of_done_raw="${BOARD_DEFINITION_OF_DONE:-}"
  local strict_create="${BOARD_STRICT_CREATE:-0}"
  local assigned_raw="${BOARD_ASSIGNED:-}"
  local sprint_raw="${BOARD_SPRINT:-}"
  local ensure_sprint="${BOARD_ENSURE_SPRINT:-0}"
  local sprint_goal="${BOARD_SPRINT_GOAL:-Auto-created sprint for board ${BOARD_NAME}}"
  local column="backlog"
  local layer
  # Detect current layer from git config or .digital-team
  layer="$(awk '/^\[remote "origin"\]/{found=1; next} found && /url/{sub(/.*url[ \t]*=[ \t]*/,""); sub(/\.git$/,""); sub(/.*\//,""); print; found=0} found && /^\[/{found=0}' \
    "$REPO_ROOT/.git/config" 2>/dev/null | tr -d '[:space:]' || echo "unknown")"

  local created_at
  created_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  local assigned
  assigned="${assigned_raw:-null}"
  local sprint
  sprint="${sprint_raw:-null}"
  if [[ "$strict_create" == "1" ]]; then
    [[ -n "$assigned_raw" && "$assigned_raw" != "null" ]] || die "Strict create requires BOARD_ASSIGNED"
    [[ -n "$sprint_raw" && "$sprint_raw" != "null" ]] || die "Strict create requires BOARD_SPRINT"
    assigned="$assigned_raw"
    sprint="$sprint_raw"
  fi

  if [[ "$ensure_sprint" == "1" && "$sprint" != "null" ]]; then
    local sprint_ref="${REF_PREFIX}/sprints/${sprint}"
    if ! git -C "$REPO_ROOT" rev-parse --verify "$sprint_ref" &>/dev/null; then
      cmd_sprint_create "$sprint" "$sprint_goal"
    fi
  fi

  local description_block=""
  local line
  while IFS= read -r line; do
    description_block+="  ${line}"$'\n'
  done <<< "${description:-No description provided.}"
  description_block="${description_block%$'\n'}"

  local acceptance_block="acceptance_criteria: []"
  if [[ -n "$acceptance_criteria_raw" ]]; then
    acceptance_block="acceptance_criteria:"
    local old_ifs="$IFS"
    IFS=$'\n'
    for line in $acceptance_criteria_raw; do
      [[ -z "$line" ]] && continue
      local escaped="${line//\"/\\\"}"
      acceptance_block+=$'\n'"  - \"${escaped}\""
    done
    IFS="$old_ifs"
  fi

  local dod_block="definition_of_done: []"
  if [[ -n "$definition_of_done_raw" ]]; then
    dod_block="definition_of_done:"
    local old_ifs_dod="$IFS"
    IFS=$'\n'
    for line in $definition_of_done_raw; do
      [[ -z "$line" ]] && continue
      local escaped="${line//\"/\\\"}"
      dod_block+=$'\n'"  - \"${escaped}\""
    done
    IFS="$old_ifs_dod"
  fi

  local yaml
  yaml=$(cat <<YAML
id: ${id}
title: "${title}"
description: |
${description_block}
layer: ${layer}
created: ${created_at}
assigned: ${assigned}
locked_by: null
locked_at: null
labels: []
${acceptance_block}
${dod_block}
sprint: ${sprint}
YAML
)

  local hash
  hash="$(store_blob "$yaml")"
  local ref="${REF_PREFIX}/${column}/${id}"
  write_ref "$ref" "$hash"
  info "Created ticket ${id} in ${column} on board ${BOARD_NAME}: $title"
  if [[ "${BOARD_PUSH:-0}" == "1" ]]; then
    git -C "$REPO_ROOT" push "$REMOTE" "$ref"
  fi
}

cmd_move() {
  resolve_board_settings
  local id="$1" from_col="$2" to_col="$3"
  column_valid "$from_col" || die "Invalid source column: $from_col"
  column_valid "$to_col"   || die "Invalid target column: $to_col"

  local from_ref="${REF_PREFIX}/${from_col}/${id}"
  local to_ref="${REF_PREFIX}/${to_col}/${id}"

  local content
  content="$(read_ticket "$from_ref")"
  [[ -z "$content" ]] && die "Ticket $id not found in $from_col"

  # Enforce lifecycle order: only in-progress tickets may transition to done.
  if [[ "$to_col" == "done" && "$from_col" != "in-progress" ]]; then
    die "Invalid transition ${from_col} -> done for ${id}. Move ticket to in-progress first."
  fi

  # PR-gate: require a merged PR and human approval before moving to done
  if [[ "$to_col" == "done" ]]; then
    require_done_pr_gate "$id"
  fi

  local hash
  hash="$(store_blob "$content")"
  write_ref "$to_ref" "$hash"
  delete_ref "$from_ref"
  info "Moved $id on board ${BOARD_NAME}: $from_col → $to_col"

  if [[ "${BOARD_PUSH:-0}" == "1" ]]; then
    git -C "$REPO_ROOT" push "$REMOTE" "$to_ref" || true
    git -C "$REPO_ROOT" push "$REMOTE" ":${from_ref}" 2>/dev/null || true
  fi

  sync_issue_status_for_ticket "$id" "$to_col"
}

cmd_checkout() {
  resolve_board_settings
  # Atomically lock a backlog ticket to this agent
  local id="$1"
  local agent="${BOARD_AGENT:-${USER:-unknown-agent}}"
  local locked_at
  locked_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  local from_ref="${REF_PREFIX}/backlog/${id}"
  local to_ref="${REF_PREFIX}/in-progress/${id}"

  local content
  content="$(read_ticket "$from_ref")"
  [[ -z "$content" ]] && die "Ticket $id not found in backlog"

  # Set locking fields
  content="$(printf '%s' "$content" \
    | sed "s|locked_by: .*|locked_by: ${agent}|" \
    | sed "s|locked_at: .*|locked_at: ${locked_at}|")"
  content="$(printf '%s' "$content" | sed "s|assigned: .*|assigned: ${agent}|")"

  local hash
  hash="$(store_blob "$content")"
  write_ref "$to_ref" "$hash"
  delete_ref "$from_ref"
  info "Checked out $id on board ${BOARD_NAME} → in-progress (locked by $agent)"

  if [[ "${BOARD_PUSH:-0}" == "1" ]]; then
    git -C "$REPO_ROOT" push --force-with-lease "$REMOTE" "$to_ref" || \
      die "Push failed — ticket may be locked by another agent. Fetch and retry."
    git -C "$REPO_ROOT" push "$REMOTE" ":${REF_PREFIX}/backlog/${id}" 2>/dev/null || true
  fi

  sync_issue_status_for_ticket "$id" "in-progress"
}

cmd_list() {
  resolve_board_settings
  local col="${1:-}"
  if [[ -n "$col" ]]; then
    column_valid "$col" || die "Invalid column: $col"
    echo "=== ${BOARD_NAME}: $col ==="
    while IFS= read -r id; do
      [[ -z "$id" ]] && continue
      local title
      title="$(read_ticket "${REF_PREFIX}/${col}/${id}" | grep '^title:' | sed 's/title: *//' | tr -d '"')"
      printf "  %-20s  %s\n" "$id" "$title"
    done < <(list_column "$col")
  else
    for c in "${VALID_COLUMNS[@]}"; do
      echo "=== ${BOARD_NAME}: $c ==="
      while IFS= read -r id; do
        [[ -z "$id" ]] && continue
        local title
        title="$(read_ticket "${REF_PREFIX}/${c}/${id}" | grep '^title:' | sed 's/title: *//' | tr -d '"')"
        printf "  %-20s  %s\n" "$id" "$title"
      done < <(list_column "$c")
    done
  fi
}

cmd_fetch() {
  local mode="${1:-}"
  if [[ "$mode" == "--all" ]]; then
    local fetched_any=0
    local ref_prefix
    while IFS= read -r ref_prefix; do
      [[ -z "$ref_prefix" ]] && continue
      info "Fetching board refs from $REMOTE for namespace $ref_prefix..."
      if git -C "$REPO_ROOT" fetch "$REMOTE" "+${ref_prefix}/*:${ref_prefix}/*" 2>/dev/null; then
        fetched_any=1
      fi
    done < <(list_all_board_prefixes)
    if [[ "$fetched_any" == "1" ]]; then
      info "Board refs updated."
    else
      info "No board refs found on remote (first push pending)."
    fi
    return
  fi

  resolve_board_settings
  info "Fetching board refs from $REMOTE for board ${BOARD_NAME}..."
  git -C "$REPO_ROOT" fetch "$REMOTE" "+${REF_PREFIX}/*:${REF_PREFIX}/*" 2>/dev/null \
    && info "Board refs updated." \
    || info "No board refs found on remote (first push pending)."
}

cmd_push() {
  local mode="${1:-}"
  if [[ "$mode" == "--all" ]]; then
    local pushed_any=0
    local ref_prefix
    while IFS= read -r ref_prefix; do
      [[ -z "$ref_prefix" ]] && continue
      info "Pushing board refs to $REMOTE for namespace $ref_prefix..."
      if git -C "$REPO_ROOT" push "$REMOTE" "+${ref_prefix}/*:${ref_prefix}/*"; then
        pushed_any=1
      fi
    done < <(list_all_board_prefixes)
    [[ "$pushed_any" == "1" ]] && info "Board refs pushed." || die "Push failed."
    return
  fi

  resolve_board_settings
  info "Pushing board refs to $REMOTE for board ${BOARD_NAME}..."
  git -C "$REPO_ROOT" push "$REMOTE" "+${REF_PREFIX}/*:${REF_PREFIX}/*" \
    && info "Board refs pushed." \
    || die "Push failed."
}

# ── entry point ──────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: board-ticket.sh <command> [args]

Commands:
  create <id> <title> [description]   Create a new ticket in backlog
  move   <id> <from> <to>             Move ticket between columns
  checkout <id>                        Lock and move ticket to in-progress
  list   [column]                      List tickets (all or one column)
  sprint-create <sprint-id> <goal>     Create a new sprint blob
  sprint-close  <sprint-id>            Mark sprint as closed
  sprint-list                          List all sprints
  sprint-show  <sprint-id>             Show one sprint payload
  fetch  [--all]                       Fetch board refs from remote
  push   [--all]                       Push board refs to remote

Columns: backlog | in-progress | blocked | done

Environment:
  BOARD_PUSH=1     Automatically push after create/move/checkout
  BOARD_REMOTE     Git remote to use (default: origin)
  BOARD_NAME       Board key from .digital-team/board.yaml (default: configured default_board)
  BOARD_AGENT      Agent identifier for locking (default: \$USER)
  BOARD_SKIP_PR_GATE=1               Skip merged-PR + approval done gate (local/dev only)
  BOARD_SKIP_REVIEW_EVIDENCE_GATE=1  Skip visible review-evidence check (local/dev only)
EOF
  exit 1
}

CMD="${1:-}"
shift || true

case "$CMD" in
  create)   cmd_create "$@" ;;
  move)     cmd_move "$@" ;;
  checkout) cmd_checkout "$@" ;;
  list)     cmd_list "$@" ;;
  sprint-create) cmd_sprint_create "$@" ;;
  sprint-close)  cmd_sprint_close "$@" ;;
  sprint-list)   cmd_sprint_list "$@" ;;
  sprint-show) cmd_sprint_show "$@" ;;
  fetch)    cmd_fetch "$@" ;;
  push)     cmd_push "$@" ;;
  *)        usage ;;
esac
