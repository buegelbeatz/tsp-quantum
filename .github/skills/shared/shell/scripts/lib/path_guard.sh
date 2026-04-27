#!/usr/bin/env bash
# layer: digital-generic-team

# shellcheck shell=bash

_path_guard_repo_root() {
  local detected
  detected="${REPO_ROOT:-}"
  if [[ -z "$detected" ]]; then
    detected="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || true)"
  fi
  printf '%s' "$detected"
}

_path_guard_realpath() {
  local target="$1"
  bash "$(dirname "${BASH_SOURCE[0]}")/../run-tool.sh" python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$target"
}

assert_path_within_repo() {
  local target="$1"
  local purpose="${2:-path operation}"
  local repo_root
  repo_root="$(_path_guard_repo_root)"
  [[ -n "$repo_root" ]] || {
    echo "[path-guard] ERROR: cannot resolve repository root for ${purpose}" >&2
    return 1
  }

  local absolute_target
  if [[ "$target" = /* ]]; then
    absolute_target="$target"
  else
    absolute_target="$(pwd)/$target"
  fi

  local normalized_repo normalized_target
  normalized_repo="$(_path_guard_realpath "$repo_root")"
  normalized_target="$(_path_guard_realpath "$absolute_target")"

  case "$normalized_target" in
    "$normalized_repo"|"$normalized_repo"/*)
      return 0
      ;;
    *)
      echo "[path-guard] ERROR: ${purpose} outside repository is forbidden: ${target}" >&2
      return 1
      ;;
  esac
}

safe_mkdir_p() {
  local target="$1"
  local purpose="${2:-mkdir}"
  assert_path_within_repo "$target" "$purpose"
  mkdir -p "$target"
}
