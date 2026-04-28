#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Cleanup local board/sprint refs, local docs/wiki content, and mandatory GitHub artifacts.
# Security:
#   Destructive actions require explicit confirmation in apply mode.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

COMMON_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/common.sh"
GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
BOARD_CONFIG="$REPO_ROOT/.github/skills/board/scripts/board_config.py"
RUN_TOOL_SH="$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh"

# shellcheck source=/dev/null
source "$COMMON_LIB"
# shellcheck source=/dev/null
source "$GITHUB_LIB"

DRY_RUN=1
CONFIRM=0
RUN_GITHUB=1
RUN_REMOTE=1
TARGET_BOARD=""

usage() {
  cat <<EOF
Usage: cleanup.sh [options]

Options:
  --repo-root <path>   Repository root (default: autodetect)
  --dry-run <0|1>      Dry run mode (default: 1)
  --confirm <0|1>      Required for destructive mode in non-interactive shells
  --github <0|1>       MUST be 1 (/cleanup requires GitHub cleanup)
  --remote <0|1>       MUST be 1 (/cleanup requires remote ref cleanup)
  --board <name>       Restrict board ref cleanup to one board
  -h, --help           Show this help

Examples:
  bash .github/skills/shared/orchestration/scripts/cleanup.sh --dry-run 1
  bash .github/skills/shared/orchestration/scripts/cleanup.sh --dry-run 0 --confirm 1
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:-}"
      [[ -n "$REPO_ROOT" ]] || die "--repo-root requires a value"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="${2:-}"
      [[ "$DRY_RUN" == "0" || "$DRY_RUN" == "1" ]] || die "--dry-run must be 0 or 1"
      shift 2
      ;;
    --confirm)
      CONFIRM="${2:-}"
      [[ "$CONFIRM" == "0" || "$CONFIRM" == "1" ]] || die "--confirm must be 0 or 1"
      shift 2
      ;;
    --github)
      RUN_GITHUB="${2:-}"
      [[ "$RUN_GITHUB" == "0" || "$RUN_GITHUB" == "1" ]] || die "--github must be 0 or 1"
      shift 2
      ;;
    --remote)
      RUN_REMOTE="${2:-}"
      [[ "$RUN_REMOTE" == "0" || "$RUN_REMOTE" == "1" ]] || die "--remote must be 0 or 1"
      shift 2
      ;;
    --board)
      TARGET_BOARD="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

TARGET_REPO_ROOT_EFFECTIVE="${TARGET_REPO_ROOT:-${DIGITAL_TARGET_REPO_ROOT:-}}"
if [[ -n "$TARGET_REPO_ROOT_EFFECTIVE" ]]; then
  TARGET_REPO_ROOT_EFFECTIVE="$(cd "$TARGET_REPO_ROOT_EFFECTIVE" && pwd)"
  if [[ "${CLEANUP_DELEGATED:-0}" != "1" && "$TARGET_REPO_ROOT_EFFECTIVE" != "$REPO_ROOT" ]]; then
    target_cleanup_script="$TARGET_REPO_ROOT_EFFECTIVE/.github/skills/shared/orchestration/scripts/cleanup.sh"
    [[ -f "$target_cleanup_script" ]] || die "Target cleanup script missing: $target_cleanup_script"
    log_info "Delegating cleanup execution to target repository: $TARGET_REPO_ROOT_EFFECTIVE"
    exec env \
      CLEANUP_DELEGATED=1 \
      TARGET_REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE" \
      DIGITAL_TARGET_REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE" \
      TARGET_REPO_SLUG="${TARGET_REPO_SLUG:-${DIGITAL_TARGET_REPO_SLUG:-}}" \
      DIGITAL_TARGET_REPO_SLUG="${DIGITAL_TARGET_REPO_SLUG:-${TARGET_REPO_SLUG:-}}" \
      bash "$target_cleanup_script" \
        --repo-root "$TARGET_REPO_ROOT_EFFECTIVE" \
        --dry-run "$DRY_RUN" \
        --confirm "$CONFIRM" \
        --github "$RUN_GITHUB" \
        --remote "$RUN_REMOTE" \
        --board "$TARGET_BOARD"
  fi
  REPO_ROOT="$TARGET_REPO_ROOT_EFFECTIVE"
fi

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
[[ -d "$REPO_ROOT/.git" ]] || die "Not a git repository: $REPO_ROOT"
COMMON_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/common.sh"
GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
BOARD_CONFIG="$REPO_ROOT/.github/skills/board/scripts/board_config.py"
RUN_TOOL_SH="$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh"
[[ -f "$COMMON_LIB" ]] || die "Missing common library: $COMMON_LIB"
[[ -f "$GITHUB_LIB" ]] || die "Missing GitHub library: $GITHUB_LIB"
# shellcheck source=/dev/null
source "$COMMON_LIB"
# shellcheck source=/dev/null
source "$GITHUB_LIB"
[[ -f "$BOARD_CONFIG" ]] || die "Missing board config helper: $BOARD_CONFIG"

# Mandatory contract for /cleanup: GitHub + remote board refs are always required.
[[ "$RUN_GITHUB" == "1" ]] || die "/cleanup requires GitHub cleanup; --github 0 is not allowed"
[[ "$RUN_REMOTE" == "1" ]] || die "/cleanup requires remote ref cleanup; --remote 0 is not allowed"

if [[ "$DRY_RUN" == "0" && "$CONFIRM" != "1" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Type DELETE to confirm full cleanup: " _confirm
    [[ "${_confirm:-}" == "DELETE" ]] || die "cleanup aborted"
  else
    die "Non-interactive destructive cleanup requires --confirm 1"
  fi
fi

act() {
  local cmd="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    log_info "[dry-run] $cmd"
  else
    eval "$cmd"
  fi
}

cleanup_run_python() {
  local script_path="$1"
  shift

  if [[ -f "$RUN_TOOL_SH" ]]; then
    local script_for_tool="$script_path"
    if [[ "$script_path" == "$REPO_ROOT"/* ]]; then
      script_for_tool="${script_path#"$REPO_ROOT"/}"
    fi
    bash "$RUN_TOOL_SH" python3 "$script_for_tool" "$@"
    return $?
  fi

  python3 "$script_path" "$@"
}

collect_board_prefixes() {
  local prefixes=()
  if [[ -n "$TARGET_BOARD" ]]; then
    local ref_prefix
    ref_prefix="$(cleanup_run_python "$BOARD_CONFIG" shell "$REPO_ROOT" "$TARGET_BOARD" | awk -F'=' '$1=="REF_PREFIX" {print $2}')"
    [[ -n "$ref_prefix" ]] || die "Unable to resolve board '$TARGET_BOARD'"
    prefixes+=("$ref_prefix")
  else
    while IFS='|' read -r _desc ref_prefix _rest; do
      [[ -n "$ref_prefix" ]] && prefixes+=("$ref_prefix")
    done < <(cleanup_run_python "$BOARD_CONFIG" list "$REPO_ROOT")
  fi
  printf '%s\n' "${prefixes[@]}"
}

cleanup_board_refs() {
  local refs=()
  local prefix
  while IFS= read -r prefix; do
    [[ -n "$prefix" ]] || continue
    while IFS= read -r ref; do
      [[ -n "$ref" ]] && refs+=("$ref")
    done < <(git -C "$REPO_ROOT" for-each-ref --format='%(refname)' "$prefix/" 2>/dev/null || true)
  done < <(collect_board_prefixes)

  if [[ ${#refs[@]} -eq 0 ]]; then
    log_info "No board/sprint refs found."
    return 0
  fi

  log_info "Selected refs for deletion: ${#refs[@]}"
  printf '  %s\n' "${refs[@]}"

  local ref
  for ref in "${refs[@]}"; do
    act "git -C \"$REPO_ROOT\" update-ref -d \"$ref\""
  done

  if git -C "$REPO_ROOT" remote get-url origin >/dev/null 2>&1; then
    for ref in "${refs[@]}"; do
      act "git -C \"$REPO_ROOT\" push origin :\"$ref\""
    done
  else
    die "Remote 'origin' not configured; cannot complete mandatory remote ref cleanup"
  fi
}

cleanup_local_wiki_docs() {
  local wiki_dir="$REPO_ROOT/docs/wiki"
  if [[ ! -d "$wiki_dir" ]]; then
    log_info "No local docs/wiki directory found."
    return 0
  fi

  act "find \"$wiki_dir\" -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
  act "mkdir -p \"$wiki_dir/assets\""
}

cleanup_generated_artifacts() {
  local cleanup_targets=(
    "$REPO_ROOT/.digital-runtime/handoffs"
    "$REPO_ROOT/.digital-artifacts/10-data"
    "$REPO_ROOT/.digital-artifacts/20-done"
    "$REPO_ROOT/.digital-artifacts/30-specification"
    "$REPO_ROOT/.digital-artifacts/40-stage"
    "$REPO_ROOT/.digital-artifacts/50-planning"
    "$REPO_ROOT/.digital-artifacts/60-review"
    "$REPO_ROOT/.digital-artifacts/70-audits"
  )
  local target

  for target in "${cleanup_targets[@]}"; do
    if [[ ! -e "$target" ]]; then
      log_info "No generated artifact path found: ${target#"$REPO_ROOT"/}"
      continue
    fi
    act "rm -rf \"$target\""
  done

  act "mkdir -p \"$REPO_ROOT/.digital-runtime/handoffs\""
}

collect_github_issues() {
  local repo_slug="$1"
  github_run_gh api --paginate "repos/${repo_slug}/issues?state=all&per_page=100" \
  --jq '.[] | select(has("pull_request") | not) | "\(.number)|\(.node_id // "")|\(.state // "")"'
}

collect_github_milestones() {
  local repo_slug="$1"
  github_run_gh api --paginate "repos/${repo_slug}/milestones?state=all&per_page=100" \
  --jq '.[] | "\(.number)|\(.title // "")"'
}

cleanup_github_issues() {
  local repo_slug="$1"
  local issue_count=0
  while IFS='|' read -r number node_id state; do
    [[ -n "$number" ]] || continue
    issue_count=$((issue_count + 1))
    if [[ "$DRY_RUN" == "1" ]]; then
      log_info "[dry-run] delete/close issue #$number ($state)"
      continue
    fi

    if [[ -n "$node_id" ]]; then
      if github_run_gh api graphql -f query='mutation($id:ID!){deleteIssue(input:{issueId:$id}){clientMutationId}}' -F id="$node_id" >/dev/null 2>&1; then
        log_info "Deleted GitHub issue #$number"
        continue
      fi
    fi

    github_run_gh api -X PATCH "repos/${repo_slug}/issues/${number}" -f state=closed >/dev/null 2>&1 \
      && log_warn "Issue #$number could not be deleted; closed instead." \
      || log_warn "Failed to delete/close issue #$number"
  done < <(collect_github_issues "$repo_slug")

  log_info "GitHub issues processed: $issue_count"
}

cleanup_github_milestones() {
  local repo_slug="$1"
  local milestone_count=0
  while IFS='|' read -r number title; do
    [[ -n "$number" ]] || continue
    milestone_count=$((milestone_count + 1))
    if [[ "$DRY_RUN" == "1" ]]; then
      log_info "[dry-run] delete milestone #$number ($title)"
      continue
    fi
    github_run_gh api -X DELETE "repos/${repo_slug}/milestones/${number}" >/dev/null 2>&1 \
      && log_info "Deleted milestone #$number ($title)" \
      || log_warn "Failed to delete milestone #$number ($title)"
  done < <(collect_github_milestones "$repo_slug")

  log_info "GitHub milestones processed: $milestone_count"
}

cleanup_github_projects() {
  local repo_slug="$1"
  local owner="${repo_slug%%/*}"
  local repo_name="${repo_slug##*/}"
  local configured_project
  local board_yaml="$REPO_ROOT/.digital-team/board.yaml"
  configured_project="$(awk -F: '
    /^[[:space:]]*project_number[[:space:]]*:/ {
      value=$2
      sub(/^[[:space:]]+/, "", value)
      sub(/[[:space:]]+$/, "", value)
      sub(/^"/, "", value)
      sub(/"$/, "", value)
      if (value != "" && value != "null" && value != "None") {
        print value
      }
      exit
    }
  ' "$board_yaml" 2>/dev/null || true)"

  if [[ -n "$configured_project" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      log_info "[dry-run] delete configured project #$configured_project"
    else
      github_run_gh project delete "$configured_project" --owner "$owner" >/dev/null 2>&1 \
        && log_info "Deleted configured project #$configured_project" \
        || log_warn "Failed to delete configured project #$configured_project"
    fi
    return 0
  fi

  log_info "No github.project_number configured; deleting owner projects that contain '$repo_name' in title."
  local repo_name_lc="$(printf '%s' "$repo_name" | tr '[:upper:]' '[:lower:]')"
  local project_rows
  if ! project_rows="$(github_run_gh project list --owner "$owner" --limit 200 --format json \
    --jq '.projects[] | select((.title // "") | ascii_downcase | contains("'"$repo_name_lc"'")) | "\(.number)|\(.title // "")"' 2>/dev/null)"; then
    log_warn "Unable to list owner projects via GitHub API; skipping project cleanup."
    return 0
  fi
  if [[ -z "$project_rows" ]]; then
    log_info "No matching owner projects found for '$repo_name'."
    return 0
  fi

  while IFS='|' read -r number title; do
    [[ -n "$number" ]] || continue
    if [[ "$DRY_RUN" == "1" ]]; then
      log_info "[dry-run] delete matching project #$number ($title)"
      continue
    fi
    github_run_gh project delete "$number" --owner "$owner" >/dev/null 2>&1 \
      && log_info "Deleted matching project #$number ($title)" \
      || log_warn "Failed to delete matching project #$number ($title)"
    done < <(printf '%s\n' "$project_rows")
}

cleanup_github_wiki() {
  local repo_slug="$1"
  local wiki_dir wiki_dir_git wiki_remote
  ensure_github_runtime_dirs
  wiki_dir="$(github_wiki_cache_path "$repo_slug")"
  wiki_dir_git="$wiki_dir"
  if [[ "$wiki_dir_git" == "$REPO_ROOT"/* ]]; then
    wiki_dir_git="${wiki_dir_git#"$REPO_ROOT"/}"
  fi
  wiki_remote="https://github.com/${repo_slug}.wiki.git"

  if [[ ! -d "$wiki_dir/.git" ]]; then
    if [[ "$DRY_RUN" == "1" ]]; then
      log_info "[dry-run] clone wiki repository: $wiki_remote"
      return 0
    fi
    github_run_git clone "$wiki_remote" "$wiki_dir_git" >/dev/null 2>&1 || {
      log_warn "Could not clone wiki. Wiki might be disabled."
      return 0
    }
  else
    [[ "$DRY_RUN" == "1" ]] || github_run_git -C "$wiki_dir_git" pull --rebase >/dev/null 2>&1 || true
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    log_info "[dry-run] clear all wiki pages in cache: $wiki_dir"
    return 0
  fi

  find "$wiki_dir" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
  if [[ -n "$(github_run_git -C "$wiki_dir_git" status --porcelain)" ]]; then
    github_run_git -C "$wiki_dir_git" add -A
    github_run_git -C "$wiki_dir_git" commit -m "cleanup: clear wiki pages" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir_git" push origin HEAD >/dev/null 2>&1 \
      && log_info "Cleared GitHub wiki pages" \
      || log_warn "Failed to push wiki cleanup"
  else
    log_info "No wiki pages to clear"
  fi
}

cleanup_github() {
  if ! github_require_token; then
    die "GH_TOKEN missing; cannot complete mandatory GitHub cleanup"
  fi

  local repo_slug
  repo_slug="${TARGET_REPO_SLUG:-${DIGITAL_TARGET_REPO_SLUG:-}}"
  if [[ -z "$repo_slug" ]]; then
    repo_slug="$(github_default_repo_slug 2>/dev/null || true)"
  fi
  if [[ -z "$repo_slug" ]]; then
    die "Unable to resolve GitHub repo slug from origin remote; cannot complete mandatory GitHub cleanup"
  fi

  # Validate GH authentication once to avoid noisy per-item warning floods.
  if ! github_run_gh api /user >/dev/null 2>&1; then
    die "gh authentication is not active (gh auth login or valid GH_TOKEN required); cannot complete mandatory GitHub cleanup"
  fi

  # Validate repository access upfront.
  if ! github_run_gh api "repos/${repo_slug}" >/dev/null 2>&1; then
    die "No API access to repo '${repo_slug}' for current GitHub identity; cannot complete mandatory GitHub cleanup"
  fi

  # Deleting/closing issues and deleting milestones require write permissions.
  local can_push
  can_push="$(github_run_gh api "repos/${repo_slug}" --jq '.permissions.push // false' 2>/dev/null || echo false)"
  if [[ "$can_push" != "true" ]]; then
    die "GitHub identity has no push/write permission on '${repo_slug}'; cannot complete mandatory GitHub cleanup"
  fi

  log_info "GitHub cleanup for repo: $repo_slug"
  cleanup_github_issues "$repo_slug"
  cleanup_github_milestones "$repo_slug"
  cleanup_github_projects "$repo_slug"
  cleanup_github_wiki "$repo_slug"
}

log_info "cleanup started (dry_run=$DRY_RUN, github=$RUN_GITHUB, remote=$RUN_REMOTE, board=${TARGET_BOARD:-all})"
cleanup_board_refs
cleanup_local_wiki_docs
cleanup_generated_artifacts
cleanup_github
log_info "cleanup finished"
