#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# =============================================================================
# Enterprise Shared Local Orchestration: refactor-discovery.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Deterministically discover tracked .sh/.py files for /refactor reviews,
#   compute line-count candidates, and surface high-signal file subsets.
#
# Inputs:
#   $1 / DIGITAL_TEAM_REFACTOR_PATH       Review root path (default: .digital-team)
#   $2 / DIGITAL_TEAM_REFACTOR_MAX_LINES  Refactor threshold (default: 100)
#   DIGITAL_TEAM_REFACTOR_RELEVANT_LIMIT  Max emitted relevant files (default: 20)
#
# Security:
#   Uses git-tracked discovery only, avoids ad-hoc execution, and cleans temp files.
#
# Output contract:
#   Prints stable section markers for downstream parsing:
#   - ===TRACKED_COUNT===
#   - ===RELEVANT_COUNT===
#   - ===REMAINING_COUNT===
#   - ===RELEVANT_FILES===
#   - ===OVER_THRESHOLD===
#   - ===LINE_COUNTS===
#
# Security & Compliance:
#   - Uses git-tracked discovery only (no untracked/generated artifacts).
#   - Avoids ad-hoc heredoc execution paths.
#   - Cleans all temporary files via trap.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

TARGET_PATH="${1:-${DIGITAL_TEAM_REFACTOR_PATH:-.digital-team}}"
MAX_LINES="${2:-${DIGITAL_TEAM_REFACTOR_MAX_LINES:-100}}"
RELEVANT_LIMIT="${DIGITAL_TEAM_REFACTOR_RELEVANT_LIMIT:-20}"

tracked_file_list="$(mktemp)"
line_counts="$(mktemp)"
over_threshold="$(mktemp)"
security_relevant="$(mktemp)"
shell_safety_relevant="$(mktemp)"
relevant_union="$(mktemp)"

cleanup() {
  rm -f "$tracked_file_list" "$line_counts" "$over_threshold" "$security_relevant" "$shell_safety_relevant" "$relevant_union"
}
trap cleanup EXIT

git -C "$REPO_ROOT" ls-files -- \
  "${TARGET_PATH}/*.sh" \
  "${TARGET_PATH}/**/*.sh" \
  "${TARGET_PATH}/*.py" \
  "${TARGET_PATH}/**/*.py" | sort -u > "$tracked_file_list"

tracked_count="$(wc -l < "$tracked_file_list" | tr -d ' ')"

while IFS= read -r rel_path; do
  [[ -n "$rel_path" ]] || continue
  [[ -f "$REPO_ROOT/$rel_path" ]] || continue
  printf '%s\t%s\n' "$rel_path" "$(wc -l < "$REPO_ROOT/$rel_path" | tr -d ' ')"
done < "$tracked_file_list" > "$line_counts"

sort -t $'\t' -k2,2nr -k1,1 "$line_counts" -o "$line_counts"
awk -F $'\t' -v max="$MAX_LINES" '$2 > max { print }' "$line_counts" > "$over_threshold"

while IFS= read -r rel_path; do
  [[ -n "$rel_path" ]] || continue
  abs_path="$REPO_ROOT/$rel_path"
  case "$rel_path" in
    *.sh)
      if grep -Eq '(^|[^A-Za-z0-9_])eval[[:space:]]+|curl[^|]*\|[[:space:]]*(bash|sh)\b' "$abs_path"; then
        printf '%s\n' "$rel_path" >> "$security_relevant"
      fi
      if ! grep -q 'set -euo pipefail' "$abs_path"; then
        printf '%s\n' "$rel_path" >> "$shell_safety_relevant"
      fi
      ;;
    *.py)
      if grep -Eq 'subprocess\.(run|Popen)\([^\n]*shell[[:space:]]*=[[:space:]]*True|os\.system\(|\beval\(' "$abs_path"; then
        printf '%s\n' "$rel_path" >> "$security_relevant"
      fi
      ;;
  esac
done < "$tracked_file_list"

{
  awk -F $'\t' '{ print $1 }' "$over_threshold"
  cat "$security_relevant"
  cat "$shell_safety_relevant"
} | awk 'NF' | sort -u > "$relevant_union"

relevant_count="$(wc -l < "$relevant_union" | tr -d ' ')"
remaining_count="$((tracked_count - relevant_count))"
if (( remaining_count < 0 )); then
  remaining_count=0
fi

printf '[refactor-discovery] repo_root=%s\n' "$REPO_ROOT"
printf '[refactor-discovery] path=%s max_lines=%s relevant_limit=%s\n' "$TARGET_PATH" "$MAX_LINES" "$RELEVANT_LIMIT"
printf '[refactor-discovery] tracked_count=%s relevant_count=%s remaining_count=%s\n' "$tracked_count" "$relevant_count" "$remaining_count"

printf '===TRACKED_COUNT===\n%s\n' "$tracked_count"
printf '===RELEVANT_COUNT===\n%s\n' "$relevant_count"
printf '===REMAINING_COUNT===\n%s\n' "$remaining_count"

printf '===RELEVANT_FILES===\n'
head -n "$RELEVANT_LIMIT" "$relevant_union"

printf '===OVER_THRESHOLD===\n'
cat "$over_threshold"

printf '===LINE_COUNTS===\n'
cat "$line_counts"
