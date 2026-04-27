#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-wiki-page-edit workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-wiki-page-edit.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Edit an existing wiki page and push the update.
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

[[ -n "$repo_slug" ]] || die "Usage: gh-wiki-page-edit.sh <owner/repo> <title> <content>"
[[ -n "$page_title" ]] || die "Page title is required"
[[ -n "$page_content" ]] || die "Page content is required"

github_require_token || die "GH_TOKEN is required"
ensure_github_runtime_dirs

wiki_dir="$(github_wiki_cache_path "$repo_slug")"
wiki_remote="https://github.com/${repo_slug}.wiki.git"

if [[ ! -d "$wiki_dir/.git" ]]; then
  github_run_git clone "$wiki_remote" "$wiki_dir" >/dev/null 2>&1 || die "Wiki clone failed. Ensure wiki is enabled and repository is accessible."
else
  github_run_git -C "$wiki_dir" pull --rebase >/dev/null 2>&1 || true
fi

page_slug="$(printf '%s' "$page_title" | tr ' ' '-' | tr -cd '[:alnum:]-_')"
[[ -n "$page_slug" ]] || die "Unable to derive wiki page slug from title"
page_file="$wiki_dir/${page_slug}.md"
[[ -f "$page_file" ]] || die "Wiki page does not exist: ${page_slug}.md"

printf '%b\n' "$page_content" > "$page_file"
github_run_git -C "$wiki_dir" add "${page_slug}.md"
github_run_git -C "$wiki_dir" commit -m "Edit wiki page: $page_title" >/dev/null || true
github_run_git -C "$wiki_dir" push >/dev/null

printf '%b\n' "api_version: \"v1\"\nkind: \"github_wiki_page_edit_result\"\nrepository: \"$repo_slug\"\npage_title: \"$page_title\"\npage_slug: \"$page_slug\"\nupdated: true"
