#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Delete board refs under refs/board/* locally and optionally on remote.
# Security:
#   Only mutates git refs inside configured board namespaces.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
REMOTE="${BOARD_REMOTE:-origin}"
APPLY=0
PUSH_REMOTE=0
TARGET_BOARD=""
RUN_TOOL_SH="$REPO_ROOT/.github/skills/shared/shell/scripts/run-tool.sh"

usage() {
  cat <<EOF
Usage: board-cleanup.sh [--yes] [--remote] [--board <name>]

Options:
  --yes            Apply deletion (required). Without this flag: dry run.
  --remote         Also delete refs on remote (origin by default).
  --board <name>   Restrict cleanup to one configured board (e.g. project).

Environment:
  BOARD_REMOTE     Git remote for --remote mode (default: origin)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      APPLY=1
      shift
      ;;
    --remote)
      PUSH_REMOTE=1
      shift
      ;;
    --board)
      TARGET_BOARD="${2:-}"
      [[ -n "$TARGET_BOARD" ]] || { echo "board-cleanup: --board requires a value" >&2; exit 2; }
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "board-cleanup: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

helper="$SCRIPT_DIR/board_config.py"
[[ -f "$helper" ]] || { echo "board-cleanup: missing board_config.py" >&2; exit 2; }

board_cleanup_run_python() {
  local helper_path="$1"
  shift

  if [[ -f "$RUN_TOOL_SH" ]]; then
    local helper_for_tool="$helper_path"
    if [[ "$helper_path" == "$REPO_ROOT"/* ]]; then
      helper_for_tool="${helper_path#"$REPO_ROOT"/}"
    fi
    bash "$RUN_TOOL_SH" python3 "$helper_for_tool" "$@"
    return $?
  fi

  python3 "$helper_path" "$@"
}

prefixes=()
if [[ -n "$TARGET_BOARD" ]]; then
  ref_prefix="$(board_cleanup_run_python "$helper" shell "$REPO_ROOT" "$TARGET_BOARD" | awk -F'=' '$1=="REF_PREFIX" {print $2}')"
  [[ -n "$ref_prefix" ]] || { echo "board-cleanup: unable to resolve board '$TARGET_BOARD'" >&2; exit 2; }
  prefixes+=("$ref_prefix")
else
  while IFS='|' read -r _desc ref_prefix _rest; do
    [[ -n "$ref_prefix" ]] && prefixes+=("$ref_prefix")
  done < <(board_cleanup_run_python "$helper" list "$REPO_ROOT")
fi

if [[ ${#prefixes[@]} -eq 0 ]]; then
  echo "board-cleanup: no board namespaces configured"
  exit 0
fi

refs_to_delete=()
for prefix in "${prefixes[@]}"; do
  while IFS= read -r ref; do
    [[ -n "$ref" ]] && refs_to_delete+=("$ref")
  done < <(git -C "$REPO_ROOT" for-each-ref --format='%(refname)' "$prefix/" 2>/dev/null || true)
done

if [[ ${#refs_to_delete[@]} -eq 0 ]]; then
  echo "board-cleanup: no refs found"
  exit 0
fi

echo "board-cleanup: refs selected (${#refs_to_delete[@]})"
printf '  %s\n' "${refs_to_delete[@]}"

if [[ "$APPLY" -ne 1 ]]; then
  echo "board-cleanup: dry-run only (use --yes to apply)"
  exit 0
fi

for ref in "${refs_to_delete[@]}"; do
  git -C "$REPO_ROOT" update-ref -d "$ref" || true
done

echo "board-cleanup: local refs deleted"

if [[ "$PUSH_REMOTE" -eq 1 ]]; then
  for ref in "${refs_to_delete[@]}"; do
    git -C "$REPO_ROOT" push "$REMOTE" ":$ref" || true
  done
  echo "board-cleanup: remote cleanup attempted on '$REMOTE'"
fi
