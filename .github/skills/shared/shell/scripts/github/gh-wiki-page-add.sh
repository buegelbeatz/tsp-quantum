#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-wiki-page-add workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-wiki-page-add.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Add a new wiki page and push changes.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
page_title="${2:-}"
page_content="${3:-}"

[[ -n "$repo_slug" ]] || die "Usage: gh-wiki-page-add.sh <owner/repo> <title> <content>"
[[ -n "$page_title" ]] || die "Page title is required"
[[ -n "$page_content" ]] || die "Page content is required"

github_require_token || die "GH_TOKEN is required"
ensure_github_runtime_dirs

wiki_dir="$(github_wiki_cache_path "$repo_slug")"
wiki_remote="https://github.com/${repo_slug}.wiki.git"

_is_fresh_wiki=false

if [[ ! -d "$wiki_dir/.git" ]]; then
  if github_run_git clone "$wiki_remote" "$wiki_dir" >/dev/null 2>&1; then
    : # clone succeeded — existing wiki
  else
    # Fresh wiki: no git repo exists yet. Initialize locally and push first page.
    log_info "Wiki git repo not found — initializing fresh wiki for $repo_slug"
    mkdir -p "$wiki_dir"
    github_run_git -C "$wiki_dir" init -b main >/dev/null 2>&1 \
      || github_run_git -C "$wiki_dir" init >/dev/null 2>&1
    github_run_git -C "$wiki_dir" remote add origin "$wiki_remote" >/dev/null 2>&1
    _is_fresh_wiki=true
  fi
else
  github_run_git -C "$wiki_dir" pull --rebase >/dev/null 2>&1 || true
fi

page_slug="$(printf '%s' "$page_title" | tr ' ' '-' | tr -cd '[:alnum:]-_')"
[[ -n "$page_slug" ]] || die "Unable to derive wiki page slug from title"
page_file="$wiki_dir/${page_slug}.md"
if [[ "$_is_fresh_wiki" == "false" ]]; then
  [[ ! -f "$page_file" ]] || die "Wiki page already exists: ${page_slug}.md"
fi

printf '%b\n' "$page_content" > "$page_file"
github_run_git -C "$wiki_dir" add "${page_slug}.md"

if [[ -z "$(github_run_git -C "$wiki_dir" config --get user.name 2>/dev/null || true)" ]]; then
  github_run_git -C "$wiki_dir" config user.name "agile-coach-bot" >/dev/null
fi
if [[ -z "$(github_run_git -C "$wiki_dir" config --get user.email 2>/dev/null || true)" ]]; then
  github_run_git -C "$wiki_dir" config user.email "agile-coach-bot@users.noreply.github.com" >/dev/null
fi

github_run_git -C "$wiki_dir" commit -m "Add wiki page: $page_title" >/dev/null \
  || die "Git commit failed while creating wiki page"

if [[ "$_is_fresh_wiki" == "true" ]]; then
  github_run_git -C "$wiki_dir" push --set-upstream origin main >/dev/null 2>&1 \
    || github_run_git -C "$wiki_dir" push --set-upstream origin master >/dev/null \
    || die "Wiki push failed for fresh wiki"
else
  github_run_git -C "$wiki_dir" push >/dev/null || die "Wiki push failed"
fi

printf '%b\n' "api_version: \"v1\"\nkind: \"github_wiki_page_add_result\"\nrepository: \"$repo_slug\"\npage_title: \"$page_title\"\npage_slug: \"$page_slug\"\ncreated: true"
