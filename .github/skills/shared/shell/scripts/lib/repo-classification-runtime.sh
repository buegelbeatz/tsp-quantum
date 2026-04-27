#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Provide filesystem-based runtime mode helpers for app vs layer policy
#   detection, separate from git-index classification logic.
# Security:
#   Reads repository-local paths only and does not execute untrusted input.

# Return whether a repository root contains app code outside governance folders.
looks_like_app_repository_fs() {
  local repo_root="${1:-.}"
  local excluded_dirs=(
    ".github"
    ".git"
    ".tests"
    ".digital-artifacts"
    ".digital-runtime"
    ".digital-team"
    "node_modules"
    "venv"
    ".venv"
  )
  local source_pattern='\.(py|ts|tsx|js|jsx|java|go|rs|cs|rb|php)$'
  local entry=""
  local excluded="0"
  local dir_name=""

  shopt -s nullglob dotglob
  for entry in "$repo_root"/* "$repo_root"/.*; do
    [[ -e "$entry" ]] || continue
    dir_name="$(basename "$entry")"

    if [[ "$dir_name" == "." || "$dir_name" == ".." ]]; then
      continue
    fi

    excluded="0"
    for candidate in "${excluded_dirs[@]}"; do
      if [[ "$dir_name" == "$candidate" ]]; then
        excluded="1"
        break
      fi
    done
    [[ "$excluded" == "1" ]] && continue

    if [[ -f "$entry" && "$dir_name" =~ $source_pattern ]]; then
      printf '1'
      return 0
    fi

    if [[ -d "$entry" ]]; then
      if find "$entry" -type f | grep -E -q "$source_pattern"; then
        printf '1'
        return 0
      fi
    fi
  done

  printf '0'
}

# Detect runtime policy mode from filesystem layout.
detect_runtime_repo_mode() {
  local repo_root="${1:-.}"
  local override="${DIGITAL_TEAM_REPO_RUNTIME_MODE:-}"

  if [[ -n "$override" ]]; then
    printf '%s' "$override"
    return 0
  fi

  if [[ -d "$repo_root/.github" ]] && [[ "$(looks_like_app_repository_fs "$repo_root")" == "1" ]]; then
    printf 'app'
    return 0
  fi

  printf 'layer'
}