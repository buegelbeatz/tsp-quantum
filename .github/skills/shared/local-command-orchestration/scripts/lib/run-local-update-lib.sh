#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Provide helper functions for deterministic local update orchestration.
# Security:
#   Uses explicit git/path handling and dry-run aware command execution only.

# shellcheck shell=bash

collect_update_scope_status() {
  git -C "$REPO_ROOT" status --porcelain --untracked-files=all -- .github .digital-team .vscode/mcp.json 2>/dev/null || true
}


print_summary_table() {
  printf '\n'
  printf '| Step | Action | Status | Detail | Files |\n'
  printf '|---|---|---|---|---|\n'
  printf '| 1/3 | %s | %s | %s | %s |\n' "$REPORT_ACTION_UPDATE" "$REPORT_STATUS_UPDATE" "$REPORT_DETAIL_UPDATE" "$REPORT_FILES_UPDATE"
  printf '| 2/3 | %s | %s | %s | %s |\n' "$REPORT_ACTION_SYNC" "$REPORT_STATUS_SYNC" "$REPORT_DETAIL_SYNC" "$REPORT_FILES_SYNC"
  printf '| 3/3 | %s | %s | %s | %s |\n\n' "$REPORT_ACTION_VERIFY" "$REPORT_STATUS_VERIFY" "$REPORT_DETAIL_VERIFY" "$REPORT_FILES_VERIFY"
}


compact_file_delta() {
  local status_before="$1"
  local status_after="$2"
  local delta_lines="$(comm -3 <(printf '%s\n' "$status_before" | sed '/^$/d' | sort -u) <(printf '%s\n' "$status_after" | sed '/^$/d' | sort -u) || true)"
  local delta_paths count top3

  [[ -n "$delta_lines" ]] || { printf '%s\n' '-'; return; }
  delta_paths="$(printf '%s\n' "$delta_lines" | sed 's/^\t//' | cut -c4- | sed '/^$/d' | sort -u)"
  [[ -n "$delta_paths" ]] || { printf '%s\n' '-'; return; }

  count="$(printf '%s\n' "$delta_paths" | wc -l | tr -d ' ')"
  top3="$(printf '%s\n' "$delta_paths" | head -n 3 | paste -sd ', ' -)"
  [[ "$count" -le 3 ]] && printf '%s\n' "$top3" || printf '%s\n' "$count files (%s, ...)" "$top3"
}


status_entry_count() {
  local status_content="$1"
  printf '%s\n' "$status_content" | sed '/^$/d' | wc -l | tr -d ' '
}


detect_bootstrap_mode() {
  local metadata_file="$REPO_ROOT/.digital-team/template-source.env"
  local mode=""

  if [[ -f "$metadata_file" ]]; then
    mode="$(sed -n 's/^DIGITAL_BOOTSTRAP_MODE="\([^"]*\)"$/\1/p' "$metadata_file" | tail -n 1)"
    [[ -n "$mode" ]] && { printf '%s\n' "$mode"; return; }
  fi
  if [[ -d "$REPO_ROOT/.digital-team" ]]; then
    [[ -d "$REPO_ROOT/.github" ]] && { printf '%s\n' 'layer0'; return; }
    printf '%s\n' 'layer_n'
    return
  fi
  printf '%s\n' 'app'
}


verification_expr_for_mode() {
  local bootstrap_mode="$1"
  case "$bootstrap_mode" in
    layer0) printf '%s\n' 'update_creates_backup_restores_readme_and_removes_install_link or update_writes_root_install_wrapper_for_layer0_mode or update_stops_parent_refresh_for_self_referencing_layer0_source or layer0_install_wrapper_fails_without_explicit_template_source' ;;
    layer_n) printf '%s\n' 'update_skips_backup_for_layer1_repo or update_refreshes_direct_parent_and_recursively_loads_ancestors or update_generates_merged_instruction_index_for_layered_fullstack_folder or update_fails_when_duplicate_instruction_ids_exist or update_merges_layer_readmes_into_github_targets or update_backup_excludes_root_readme' ;;
    app) printf '%s\n' 'update_backup_excludes_root_readme or update_merges_layer_readmes_into_github_targets or update_app_refreshes_direct_parent_and_recursively_loads_ancestors' ;;
    *) printf '%s\n' '' ;;
  esac
}


progress() {
  printf '[progress][update] %s\n' "$1"
}


run_cmd() {
  local command="$1"
  shift
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] %s\n' "$command"
    return 0
  fi
  "$@"
}