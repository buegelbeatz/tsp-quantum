#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Resolve governance-related script paths inside repository and layer layout.
# Security:
#   Restricts lookup to repository-local folders and does not execute discovered files.

# shellcheck shell=bash

resolve_script_path() {
  local script_name="$1"
  local repo_root="${2:-.}"

  if [[ -f "${repo_root}/.github/${script_name}" ]]; then
    echo "${repo_root}/.github/${script_name}"
    return 0
  fi

  if [[ -f "${repo_root}/.github/hooks/${script_name}" ]]; then
    echo "${repo_root}/.github/hooks/${script_name}"
    return 0
  fi

  local found_path
  found_path="$(find "${repo_root}/.digital-team" -type f -name "${script_name}" 2>/dev/null | head -n1 || true)"
  if [[ -n "$found_path" ]]; then
    echo "$found_path"
    return 0
  fi

  log_error "Script not found: ${script_name} (searched .github/, .github/hooks/, .digital-team/)"
  return 1
}