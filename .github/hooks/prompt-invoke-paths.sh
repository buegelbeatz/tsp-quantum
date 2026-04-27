#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Resolve prompt hook script locations inside repository structure.
# Security:
#   Restricts lookup to repository-local .github and .digital-team paths.

resolve_prompt_hook_path() {
  local script_name="$1"

  if [[ -f "$repo_root/.github/${script_name}" ]]; then
    printf '%s\n' "$repo_root/.github/${script_name}"
    return 0
  fi
  if [[ -f "$repo_root/.github/hooks/${script_name}" ]]; then
    printf '%s\n' "$repo_root/.github/hooks/${script_name}"
    return 0
  fi

  local found_path=""
  found_path="$(find "$repo_root/.digital-team" -type f -name "$script_name" 2>/dev/null | head -n1 || true)"
  if [[ -n "$found_path" ]]; then
    printf '%s\n' "$found_path"
    return 0
  fi

  return 1
}
