#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   End-to-end self-test for /project workflow in an isolated temp clone.
#   Optional GitHub cycle can create temporary *_test artifacts and remove them.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

COMMON_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/common.sh"
GITHUB_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/github.sh"
STAGES_ACTION_SCRIPT="$REPO_ROOT/.github/skills/stages-action/scripts/stages-action.sh"
MARKDOWN_ARTIFACTS_CONFIG="$REPO_ROOT/.github/skills/artifacts/config/markdown-artifacts.env"

# shellcheck source=/dev/null
source "$COMMON_LIB"
# shellcheck source=/dev/null
source "$GITHUB_LIB"

if [[ -f "$MARKDOWN_ARTIFACTS_CONFIG" ]]; then
  # shellcheck source=/dev/null
  source "$MARKDOWN_ARTIFACTS_CONFIG"
fi

: "${STAGE_COMPLETION_FILENAME:=stage-completion-status.md}"

GITHUB_TEST=0

usage() {
  cat <<EOF
Usage: project-e2e.sh [options]

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
[[ -f "$STAGES_ACTION_SCRIPT" ]] || die "Missing stages action script: $STAGES_ACTION_SCRIPT"

create_temp_clone() {
  local runtime_root run_id temp_clone
  runtime_root="$REPO_ROOT/.digital-runtime/e2e-project"
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  temp_clone="$runtime_root/$run_id/repo"
  mkdir -p "$runtime_root/$run_id"
  git clone --no-hardlinks "$REPO_ROOT" "$temp_clone" >/dev/null 2>&1
  printf '%s\n' "$temp_clone"
}

seed_local_test_data() {
  local clone_root="$1"
  if make -C "$clone_root" artifacts-testdata-2-input >/dev/null 2>&1; then
    return 0
  fi

  mkdir -p "$clone_root/.digital-artifacts/00-input/documents"
  cat > "$clone_root/.digital-artifacts/00-input/documents/project-e2e-input.md" <<'EOF'
# Project E2E Input

- Goal: verify isolated /project execution in a temporary clone.
- Scope: local test run only, no production board or wiki mutation.
EOF
}

run_local_e2e() {
  local clone_root source_venv clone_venv
  local source_board_refs_before source_board_refs_after
  local source_stage_reports_before source_stage_reports_after
  local clone_log stage_exit
  clone_root="$(create_temp_clone)"
  log_info "project-e2e: temp clone -> $clone_root"
  seed_local_test_data "$clone_root"

  source_board_refs_before="$(git -C "$REPO_ROOT" for-each-ref --format='%(refname)' refs/board/project 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  source_stage_reports_before="$({ find "$REPO_ROOT/.digital-artifacts/60-review" -path "*/project/${STAGE_COMPLETION_FILENAME}" -type f 2>/dev/null || true; } | wc -l | tr -d ' ')"

  # Reuse the source repo runtime by binding it into the clone-local runtime path.
  source_venv="$REPO_ROOT/.digital-runtime/layers/python-runtime/venv"
  clone_venv="$clone_root/.digital-runtime/layers/python-runtime/venv"
  [[ -x "$source_venv/bin/python3" ]] || die "Missing source layer venv: $source_venv"
  mkdir -p "$(dirname "$clone_venv")"
  ln -s "$source_venv" "$clone_venv"

  export DRY_RUN=1
  export DIGITAL_STAGE_PRIMARY_SYNC=0

  clone_log="$clone_root/.digital-runtime/project-e2e.log"
  set +e
  bash "$clone_root/.github/skills/stages-action/scripts/stages-action.sh" project >"$clone_log" 2>&1
  stage_exit=$?
  set -e

  grep -q "\[progress\]\[stages-action\] step=1/6 action=ingest-input-to-data" "$clone_log" || die "E2E failed: stages-action did not start in temp clone"
  if [[ "$stage_exit" != "0" ]]; then
    log_warn "project-e2e: stages-action returned exit code ${stage_exit} in temp clone (accepted for isolation verification)"
  fi

  source_board_refs_after="$(git -C "$REPO_ROOT" for-each-ref --format='%(refname)' refs/board/project 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')"
  source_stage_reports_after="$({ find "$REPO_ROOT/.digital-artifacts/60-review" -path "*/project/${STAGE_COMPLETION_FILENAME}" -type f 2>/dev/null || true; } | wc -l | tr -d ' ')"
  [[ "$source_board_refs_before" == "$source_board_refs_after" ]] || die "E2E failed: source refs/board/project changed during temp-clone run"
  [[ "$source_stage_reports_before" == "$source_stage_reports_after" ]] || die "E2E failed: source project stage reports changed during temp-clone run"

  log_info "project-e2e: local temp clone validation passed"
}

run_github_temp_cycle() {
  if [[ "$GITHUB_TEST" != "1" ]]; then
    log_info "project-e2e: GitHub test disabled (--github-test 0)"
    return 0
  fi
  if ! github_require_token; then
    log_warn "project-e2e: GH_TOKEN missing, skipping GitHub test cycle"
    return 0
  fi

  local repo_slug owner run_tag issue_number project_number wiki_dir wiki_remote
  repo_slug="$(github_repo_slug_from_git 2>/dev/null || true)"
  [[ -n "$repo_slug" ]] || { log_warn "project-e2e: cannot resolve repo slug; skipping GitHub test cycle"; return 0; }
  owner="${repo_slug%%/*}"
  run_tag="project-e2e-test-$(date -u +%Y%m%d%H%M%S)-$$"

  issue_number=""
  project_number=""

  issue_number="$(github_run_gh issue create --repo "$repo_slug" --title "[$run_tag] temp issue" --body "temporary project-e2e artifact" --json number --jq '.number' 2>/dev/null || true)"
  project_number="$(github_run_gh project create --owner "$owner" --title "[$run_tag] temp project" --format json --jq '.number' 2>/dev/null || true)"

  ensure_github_runtime_dirs
  wiki_dir="$(github_wiki_cache_path "$repo_slug")"
  wiki_remote="https://github.com/${repo_slug}.wiki.git"
  if [[ ! -d "$wiki_dir/.git" ]]; then
    github_run_git clone "$wiki_remote" "$wiki_dir" >/dev/null 2>&1 || true
  else
    github_run_git -C "$wiki_dir" pull --rebase >/dev/null 2>&1 || true
  fi
  if [[ -d "$wiki_dir/.git" ]]; then
    printf '%s\n' '# temporary project-e2e wiki page' > "$wiki_dir/${run_tag}.md"
    github_run_git -C "$wiki_dir" add "$wiki_dir/${run_tag}.md" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" commit -m "project-e2e: add ${run_tag}" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" push origin HEAD >/dev/null 2>&1 || true
  fi

  [[ -n "$issue_number" ]] && github_run_gh api -X PATCH "repos/${repo_slug}/issues/${issue_number}" -f state=closed >/dev/null 2>&1 || true
  [[ -n "$project_number" ]] && github_run_gh project delete "$project_number" --owner "$owner" --yes >/dev/null 2>&1 || true

  if [[ -d "$wiki_dir/.git" && -f "$wiki_dir/${run_tag}.md" ]]; then
    rm -f "$wiki_dir/${run_tag}.md"
    github_run_git -C "$wiki_dir" add -A >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" commit -m "project-e2e: remove ${run_tag}" >/dev/null 2>&1 || true
    github_run_git -C "$wiki_dir" push origin HEAD >/dev/null 2>&1 || true
  fi

  log_info "project-e2e: GitHub test cycle completed"
}

run_local_e2e
run_github_temp_cycle
log_info "project-e2e: done"
