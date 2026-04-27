#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute gh-wiki-list-pages workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# =============================================================================
# Enterprise Script: gh-wiki-list-pages.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Retrieve wiki pages as structured YAML for reuse in other skills.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(cd "$SCRIPT_DIR/../lib" && pwd)"

# shellcheck source=/dev/null
source "$LIB_DIR/common.sh"
# shellcheck source=/dev/null
source "$LIB_DIR/github.sh"

repo_slug="${1:-}"
if [[ -z "$repo_slug" ]]; then
  repo_slug="$(github_default_repo_slug 2>/dev/null || true)"
fi
[[ -n "$repo_slug" ]] || die "Usage: gh-wiki-list-pages.sh <owner/repo>"

github_require_token || die "GH_TOKEN is required"
ensure_github_runtime_dirs

wiki_dir="$(github_wiki_cache_path "$repo_slug")"
wiki_remote="https://github.com/${repo_slug}.wiki.git"

if [[ ! -d "$wiki_dir/.git" ]]; then
  github_run_git clone "$wiki_remote" "$wiki_dir" >/dev/null 2>&1 || die "Wiki clone failed. Ensure wiki is enabled and repository is accessible."
else
  github_run_git -C "$wiki_dir" pull --rebase >/dev/null 2>&1 \
    || die "Wiki sync failed from remote. Cached data may be stale."
fi

pages_json="$(python3 - <<'PY' "$wiki_dir" "$repo_slug"
import json
import os
import sys

wiki_dir = sys.argv[1]
repo = sys.argv[2]
pages = []
for root, _, files in os.walk(wiki_dir):
    for file_name in files:
        if file_name.endswith(".md"):
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, wiki_dir)
            slug = rel_path[:-3]
            title = slug.replace("-", " ")
            pages.append({"slug": slug, "title": title, "path": rel_path})

pages.sort(key=lambda item: item["slug"].lower())
print(json.dumps({
    "api_version": "v1",
    "kind": "github_wiki_page_list",
    "repository": repo,
    "pages": pages,
}))
PY
)"

printf '%s\n' "$pages_json" | github_json_to_yaml
