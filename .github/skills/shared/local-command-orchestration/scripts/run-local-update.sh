#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Orchestrate one deterministic local update cycle with optional focused
#   verification based on detected bootstrap mode.
# Security:
#   Uses explicit command construction and dry-run support for safer execution.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
RUN_LOCAL_UPDATE_LIB="$SCRIPT_DIR/lib/run-local-update-lib.sh"
DRY_RUN="${DIGITAL_TEAM_DRY_RUN:-0}"
RUN_VERIFY="${DIGITAL_TEAM_RUN_VERIFY:-1}"
VERIFY_IF_NO_CHANGES="${DIGITAL_TEAM_VERIFY_IF_NO_CHANGES:-0}"
TEST_RUNNER_SH="$REPO_ROOT/.github/skills/shared/local-command-orchestration/scripts/run-tests.sh"

# shellcheck source=/dev/null
source "$RUN_LOCAL_UPDATE_LIB"

REPORT_ACTION_UPDATE='execute_update_script'
REPORT_STATUS_UPDATE='ok'
REPORT_DETAIL_UPDATE='update.sh executed'
REPORT_FILES_UPDATE='n/a'
REPORT_ACTION_SYNC='sync_payload'
REPORT_STATUS_SYNC='unknown'
REPORT_DETAIL_SYNC='sync state not evaluated'
REPORT_FILES_SYNC='n/a'
REPORT_ACTION_VERIFY='verify_update'
REPORT_STATUS_VERIFY='n/a'
REPORT_DETAIL_VERIFY='verification not requested'
REPORT_FILES_VERIFY='n/a'

STATUS_BEFORE=""
PREEXISTING_CHANGE_COUNT='0'
if [[ "$DRY_RUN" != "1" ]]; then
  STATUS_BEFORE="$(collect_update_scope_status)"
  PREEXISTING_CHANGE_COUNT="$(status_entry_count "$STATUS_BEFORE")"
fi

printf 'run-local-update: repo_root=%s dry_run=%s verify=%s verify_if_no_changes=%s\n' "$REPO_ROOT" "$DRY_RUN" "$RUN_VERIFY" "$VERIFY_IF_NO_CHANGES"
progress 'step=1/3 action=execute_update_script'
run_cmd "bash \"$REPO_ROOT/.digital-team/scripts/update.sh\"" bash "$REPO_ROOT/.digital-team/scripts/update.sh"

if [[ "$DRY_RUN" == "1" ]]; then
  REPORT_STATUS_SYNC='dry-run'
  REPORT_DETAIL_SYNC='no filesystem changes applied'
  REPORT_FILES_SYNC='-'
  HAS_UPDATE_CHANGES='unknown'
else
  STATUS_AFTER="$(collect_update_scope_status)"
  REPORT_FILES_SYNC="$(compact_file_delta "$STATUS_BEFORE" "$STATUS_AFTER")"
  if [[ "$STATUS_BEFORE" == "$STATUS_AFTER" ]]; then
    REPORT_STATUS_SYNC='current'
    if [[ "$PREEXISTING_CHANGE_COUNT" != "0" ]]; then
      REPORT_DETAIL_SYNC="no new update-scope changes introduced by this run; ${PREEXISTING_CHANGE_COUNT} pre-existing change entries remained unchanged"
    else
      REPORT_DETAIL_SYNC='no update-scope changes introduced by this run (.github, .digital-team, .vscode/mcp.json)'
    fi
    HAS_UPDATE_CHANGES='0'
  else
    REPORT_STATUS_SYNC='updated'
    REPORT_DETAIL_SYNC='changes detected in update scope (.github, .digital-team, .vscode/mcp.json)'
    HAS_UPDATE_CHANGES='1'
  fi
fi

if [[ "$RUN_VERIFY" == "1" ]]; then
  if [[ "${HAS_UPDATE_CHANGES:-1}" == "0" && "$VERIFY_IF_NO_CHANGES" != "1" ]]; then
    progress 'step=2/3 action=skip-verification'
    printf '[info][update] verification skipped: this update run produced no new changes in the update scope. Set DIGITAL_TEAM_VERIFY_IF_NO_CHANGES=1 to force verification.\n'
    REPORT_STATUS_VERIFY='skipped'
    REPORT_DETAIL_VERIFY='verification skipped: this run produced no new update-scope changes (set DIGITAL_TEAM_VERIFY_IF_NO_CHANGES=1 to force)'
    REPORT_FILES_VERIFY='-'
  else
    BOOTSTRAP_MODE="$(detect_bootstrap_mode)"
    TEST_EXPR="$(verification_expr_for_mode "$BOOTSTRAP_MODE")"
    progress 'step=2/3 action=verify_update'
    run_cmd "DIGITAL_TEAM_TEST_TARGET=.digital-team/scripts/tests/test_root_bootstrap_scripts.py DIGITAL_TEAM_TEST_ARGS='-q' DIGITAL_TEAM_TEST_EXPR='$TEST_EXPR' bash \"$TEST_RUNNER_SH\"" \
      env \
      DIGITAL_TEAM_TEST_TARGET=.digital-team/scripts/tests/test_root_bootstrap_scripts.py \
      DIGITAL_TEAM_TEST_ARGS=-q \
      DIGITAL_TEAM_TEST_EXPR="$TEST_EXPR" \
      bash "$TEST_RUNNER_SH"
    REPORT_STATUS_VERIFY='ok'
    REPORT_DETAIL_VERIFY='focused verification passed'
    REPORT_FILES_VERIFY='.digital-team/scripts/tests/test_root_bootstrap_scripts.py'
  fi
fi

progress 'step=3/3 action=complete'
print_summary_table
printf 'run-local-update: completed\n'
