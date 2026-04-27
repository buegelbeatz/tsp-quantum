#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-wiki-create workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-wiki-create.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Ensure a repository exists and wiki is enabled, then initialize wiki Home.
#
# Usage:
#   gh-wiki-create.sh <owner> <repo-name>
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

owner="${1:-${GITHUB_OWNER:-}}"
repo_name="${2:-}"

if [[ -z "$owner" ]]; then
  owner="$(github_default_owner 2>/dev/null || true)"
fi
if [[ -z "$repo_name" ]]; then
  repo_name="$(github_default_repo_name 2>/dev/null || true)"
fi

[[ -n "$owner" ]] || die "Owner is required"
[[ -n "$repo_name" ]] || die "Repository name is required"

github_require_token || die "GH_TOKEN is required"

repo_slug="$owner/$repo_name"
if ! github_run_gh repo view "$repo_slug" >/dev/null 2>&1; then
  github_run_gh repo create "$repo_slug" --private --confirm >/dev/null
fi

github_run_gh api -X PATCH "repos/$repo_slug" -f has_wiki=true >/dev/null

home_created=false
home_already_present=false

if page_add_output="$($SCRIPT_DIR/gh-wiki-page-add.sh "$repo_slug" "Home" "# ${repo_name} Wiki\n\nInitialized by Agile Coach Layer 1 skill." 2>&1)"; then
  home_created=true
elif printf '%s\n' "$page_add_output" | grep -F "Wiki page already exists" >/dev/null 2>&1; then
  home_already_present=true
else
  printf '❌ Wiki auto-initialization failed for %s\n' "$repo_slug" >&2
  printf '⚠ Open https://github.com/%s/wiki in the web console, create the first page named Home, then rerun this script.\n' "$repo_slug" >&2
  printf '%s\n' "$page_add_output" >&2
  exit 1
fi

printf '%b\n' "api_version: \"v1\"\nkind: \"github_wiki_create_result\"\nrepository: \"$repo_slug\"\nwiki_enabled: true\nhome_initialized: true\nhome_created: $home_created\nhome_already_present: $home_already_present"
