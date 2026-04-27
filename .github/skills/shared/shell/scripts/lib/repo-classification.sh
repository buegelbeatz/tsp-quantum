#!/usr/bin/env bash
# layer: digital-generic-team

# =============================================================================
# Enterprise Shared Shell Library: repo-classification.sh
# =============================================================================
# Purpose:
#   Deterministic repository classification (Layer 0, Layer N>0, or App)
#   using git-tracked-state inspection.
#
# Security:
#   Reads and writes only within the repository. No sensitive data processed.
# Scope:
#   - Classify repository by `.digital-team/` structure and `.github` tracking
#   - Return machine-readable classification
#   - Provide diagnostics for ambiguous states (hard-fail)
#
# Classification Rules:
#   Layer 0:
#     - `.digital-team/00-*` exists and IS tracked
#     - `.github` exists but is NOT tracked
#   Layer N (N > 0):
#     - `.digital-team/(01-99)-*` exists and IS tracked
#     - `.github` exists but is NOT tracked
#   App:
#     - `.digital-team/*` exists but is NOT tracked
#     - `.github` exists and IS tracked
#
# Security & Compliance:
#   - Uses git ls-files for authoritative tracked-state truth
#   - No secrets are logged
#   - Ambiguous states produce actionable diagnostics
#
# Usage:
#   source "<path>/repo-classification.sh"
#   classify_repo "$REPO_ROOT"   # Returns: "layer-0" | "layer-n" | "app" | exit 1 on error
#   get_repo_classification_mode "$REPO_ROOT"  # Alias
#
# Return codes:
#   0: classification successful
#   1: ambiguous or invalid state
# =============================================================================

# shellcheck shell=bash
# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/repo-classification-runtime.sh"

# Detect if a path is tracked in git index
_is_git_tracked() {
  local pattern="$1"
  local repo_root="${2:-.}"
  
  git -C "$repo_root" ls-files --error-unmatch "$pattern" >/dev/null 2>&1
}

# Count tracked files matching a glob pattern
_count_git_tracked() {
  local pattern="$1"
  local repo_root="${2:-.}"
  
  git -C "$repo_root" ls-files "$pattern" 2>/dev/null | wc -l | awk '{print $1}'
}

# List tracked directories matching a glob pattern
_list_git_tracked_dirs() {
  local pattern="$1"
  local repo_root="${2:-.}"
  
  git -C "$repo_root" ls-files "$pattern" 2>/dev/null | cut -d/ -f1 | sort -u
}

# Emit structured diagnostic message for ambiguous state
_emit_ambiguity_diagnostic() {
  local repo_root="$1"
  local github_tracked="$2"
  local layer0_tracked="$3"
  local layer_n_tracked="$4"
  local digital_team_tracked="$5"
  
  printf '[ERROR] Ambiguous repository state - cannot classify\n' >&2
  printf '[ERROR] repo_root: %s\n' "$repo_root" >&2
  printf '[ERROR] .github is tracked: %s\n' "$github_tracked" >&2
  printf '[ERROR] .digital-team/00-* is tracked: %s\n' "$layer0_tracked" >&2
  printf '[ERROR] .digital-team/(01-99)-* is tracked: %s\n' "$layer_n_tracked" >&2
  printf '[ERROR] any .digital-team/* is tracked: %s\n' "$digital_team_tracked" >&2
  printf '[ERROR] Please review repository structure and git index status\n' >&2
  printf '[ERROR] Use: git ls-files --debug .digital-team/.github for details\n' >&2
}

# Main classification function
classify_repo() {
  local repo_root="${1:-.}"
  
  # Verify git repo
  if ! git -C "$repo_root" rev-parse --git-dir >/dev/null 2>&1; then
    printf '[ERROR] Not a git repository: %s\n' "$repo_root" >&2
    return 1
  fi
  
  # Check .github tracked status
  local github_tracked=0
  if _is_git_tracked ".github/*" "$repo_root"; then
    github_tracked=1
  fi
  
  # Check .digital-team layers tracked status
  local layer0_tracked=0
  if _count_git_tracked ".digital-team/00-*" "$repo_root" | grep -q -E "[1-9]"; then
    layer0_tracked=1
  fi
  
  local layer_n_tracked=0
  if _count_git_tracked ".digital-team/0[1-9]-*" "$repo_root" | grep -q -E "[1-9]"; then
    layer_n_tracked=1
  fi
  
  local digital_team_any_tracked=0
  if _count_git_tracked ".digital-team/*" "$repo_root" | grep -q -E "[1-9]"; then
    digital_team_any_tracked=1
  fi
  
  # Classification logic
  if [[ "$github_tracked" -eq 0 ]] && [[ "$layer0_tracked" -eq 1 ]] && [[ "$layer_n_tracked" -eq 0 ]]; then
    printf 'layer-0'
    return 0
  fi
  
  if [[ "$github_tracked" -eq 0 ]] && [[ "$layer0_tracked" -eq 0 ]] && [[ "$layer_n_tracked" -eq 1 ]]; then
    printf 'layer-n'
    return 0
  fi
  
  if [[ "$github_tracked" -eq 1 ]] && [[ "$digital_team_any_tracked" -eq 0 ]]; then
    printf 'app'
    return 0
  fi
  
  # Ambiguous state: hard-fail with diagnostics
  _emit_ambiguity_diagnostic "$repo_root" "$github_tracked" "$layer0_tracked" "$layer_n_tracked" "$digital_team_any_tracked"
  return 1
}

# Alias for readability
get_repo_classification_mode() {
  classify_repo "$@"
}

