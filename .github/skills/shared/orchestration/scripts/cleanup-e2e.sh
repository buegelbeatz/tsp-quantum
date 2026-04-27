#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   End-to-end self-test for cleanup flow using an isolated temp clone under .digital-runtime.
#   Optionally creates temporary GitHub artifacts and cleans them up immediately.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

COMMON_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/common.sh"
GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
CLEANUP_SCRIPT="$REPO_ROOT/.github/skills/shared/orchestration/scripts/cleanup.sh"

# shellcheck source=/dev/null
source "$COMMON_LIB"
# shellcheck source=/dev/null
source "$GITHUB_LIB"

GITHUB_TEST=0

usage() {
  cat <<EOF
Usage: cleanup-e2e.sh [options]

Options:
  --repo-root <path>   Repository root (default: autodetect)
  --github-test <0|1>  Also run temporary GitHub artifact cycle (default: 0)
  -h, --help           Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="${2:-}"
      [[ -n "$REPO_ROOT" ]] || die "--repo-root requires a value"
      shift 2
      ;;
    --github-test)
      GITHUB_TEST="${2:-}"
      [[ "$GITHUB_TEST" == "0" || "$GITHUB_TEST" == "1" ]] || die "--github-test must be 0 or 1"
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

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
[[ -d "$REPO_ROOT/.git" ]] || die "Not a git repository: $REPO_ROOT"
[[ -f "$CLEANUP_SCRIPT" ]] || die "Missing cleanup script: $CLEANUP_SCRIPT"

create_temp_clone() {
  local runtime_root run_id temp_clone
  runtime_root="$REPO_ROOT/.digital-runtime/e2e-cleanup"
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  temp_clone="$runtime_root/$run_id/repo"
  mkdir -p "$runtime_root/$run_id"
  git clone --no-hardlinks "$REPO_ROOT" "$temp_clone" >/dev/null 2>&1
  printf '%s\n' "$temp_clone"
}

seed_local_test_data() {
  local clone_root="$1"
  mkdir -p "$clone_root/docs/wiki"
  printf '%s\n' '# temp wiki page' > "$clone_root/docs/wiki/Test.md"
  mkdir -p "$clone_root/docs/wiki/assets"
  printf '%s\n' 'temp' > "$clone_root/docs/wiki/assets/temp.txt"

  local blob
  blob="$(printf '%s\n' 'id: CLEANUP-E2E-1' 'title: temporary ticket' | git -C "$clone_root" hash-object -w --stdin)"
  git -C "$clone_root" update-ref refs/board/project/backlog/CLEANUP-E2E-1 "$blob"

  blob="$(printf '%s\n' 'id: CLEANUP-E2E-SPRINT' 'status: open' | git -C "$clone_root" hash-object -w --stdin)"
  git -C "$clone_root" update-ref refs/board/project/sprints/CLEANUP-E2E-SPRINT "$blob"
}

assert_local_cleanup_result() {
  local clone_root="$1"
  local remaining_refs
  remaining_refs="$(git -C "$clone_root" for-each-ref --format='%(refname)' refs/board/project 2>/dev/null || true)"
  [[ -z "$remaining_refs" ]] || die "E2E failed: board refs still exist in temp clone"

  if find "$clone_root/docs/wiki" -mindepth 1 -maxdepth 1 ! -name assets | grep -q .; then
    die "E2E failed: docs/wiki still contains non-assets entries"
  fi
}

run_local_e2e() {
  local clone_root
  clone_root="$(create_temp_clone)"
  log_info "cleanup-e2e: temp clone -> $clone_root"

  seed_local_test_data "$clone_root"

  bash "$CLEANUP_SCRIPT" \
    --repo-root "$clone_root" \
    --dry-run 0 \
    --confirm 1 \
    --github 0 \
    --remote 0

  assert_local_cleanup_result "$clone_root"
  log_info "cleanup-e2e: local temp clone validation passed"
}

run_github_temp_cycle() {
  if [[ "$GITHUB_TEST" != "1" ]]; then
    log_info "cleanup-e2e: GitHub test disabled (--github-test 0)"
    return 0
  fi
  if ! github_require_token; then
    log_warn "cleanup-e2e: GH_TOKEN missing, skipping GitHub test cycle"
    return 0
  fi

  local repo_slug owner run_tag issue_number milestone_number project_number
  repo_slug="$(github_repo_slug_from_git 2>/dev/null || true)"
  [[ -n "$repo_slug" ]] || { log_warn "cleanup-e2e: cannot resolve repo slug; skipping GitHub test cycle"; return 0; }
  owner="${repo_slug%%/*}"
  run_tag="cleanup-e2e-$(date -u +%Y%m%d%H%M%S)-$$"

  issue_number=""
  milestone_number=""
  project_number=""

  log_info "cleanup-e2e: creating temporary GitHub issue"
  issue_number="$(github_run_gh issue create --repo "$repo_slug" --title "[$run_tag] temp issue" --body "temporary cleanup-e2e artifact" --json number --jq '.number' 2>/dev/null || true)"

  log_info "cleanup-e2e: creating temporary GitHub milestone"
  milestone_number="$(github_run_gh api -X POST "repos/${repo_slug}/milestones" -f title="[$run_tag] temp milestone" --jq '.number' 2>/dev/null || true)"

  log_info "cleanup-e2e: creating temporary GitHub project"
  project_number="$(github_run_gh project create --owner "$owner" --title "[$run_tag] temp project" --format json --jq '.number' 2>/dev/null || true)"

  local wiki_dir wiki_remote
  ensure_github_runtime_dirs
  wiki_dir="$(github_wiki_cache_path "$repo_slug")"
  wiki_remote="https://github.com/${repo_slug}.wiki.git"
  if [[ ! -d "$wiki_dir/.git" ]]; then
    github_run_git clone "$wiki_remote" "$wiki_dir" >/dev/null 2>&1 || true
  else
    github_run_git -C "$wiki_dir" pull --rebase >/dev/null 2>&1 || true
  fi
  if [[ -d "$wiki_dir/.git" ]]; then
    printf '%s\n' '# temporary wiki page' > "$wiki_dir/${run_tag}.md"
    github_run_git -C "$wiki_dir" add "$wiki_dir/${run_tag}.md" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" commit -m "cleanup-e2e: add ${run_tag}" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" push origin HEAD >/dev/null 2>&1 || true
  fi

  log_info "cleanup-e2e: cleanup temporary GitHub artifacts"
  [[ -n "$issue_number" ]] && github_run_gh api -X PATCH "repos/${repo_slug}/issues/${issue_number}" -f state=closed >/dev/null 2>&1 || true
  [[ -n "$milestone_number" ]] && github_run_gh api -X DELETE "repos/${repo_slug}/milestones/${milestone_number}" >/dev/null 2>&1 || true
  [[ -n "$project_number" ]] && github_run_gh project delete "$project_number" --owner "$owner" --yes >/dev/null 2>&1 || true

  if [[ -d "$wiki_dir/.git" && -f "$wiki_dir/${run_tag}.md" ]]; then
    rm -f "$wiki_dir/${run_tag}.md"
    github_run_git -C "$wiki_dir" add -A >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" commit -m "cleanup-e2e: remove ${run_tag}" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" push origin HEAD >/dev/null 2>&1 || true
  fi

  log_info "cleanup-e2e: GitHub test cycle completed"
}

run_local_e2e
run_github_temp_cycle
log_info "cleanup-e2e: done"
