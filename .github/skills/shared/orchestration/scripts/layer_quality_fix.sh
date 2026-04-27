#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Apply quality-fix remediation workflow and refresh canonical layer-quality report.
# Security:
#   Executes only repository-local quality scripts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
SESSION_SCRIPT="$REPO_ROOT/.github/skills/quality-expert/scripts/quality-expert-session.sh"
RUNTIME_SCRIPT="$SCRIPT_DIR/layer_quality_runtime.py"
REPORT_DIR="$REPO_ROOT/.tests/python/reports"
FIX_LOG="$REPORT_DIR/quality-fix-run.log"

mkdir -p "$REPORT_DIR"

if [[ ! -f "$SESSION_SCRIPT" ]]; then
  echo "layer-quality-fix: missing session script at $SESSION_SCRIPT" >&2
  exit 1
fi

if [[ ! -f "$RUNTIME_SCRIPT" ]]; then
  echo "layer-quality-fix: missing runtime script at $RUNTIME_SCRIPT" >&2
  exit 1
fi

echo "[progress][quality-fix] step=1/2 action=run-quality-expert-session"
if ! RUN_TOOL_PREFER_CONTAINER=1 bash "$SESSION_SCRIPT" >"$FIX_LOG" 2>&1; then
  echo "layer-quality-fix: quality session failed; see $FIX_LOG" >&2
  cat "$FIX_LOG" >&2
  exit 1
fi

echo "[progress][quality-fix] step=2/2 action=refresh-layer-quality-report"
python_cmd="python3"
if [[ -x "$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python3" ]]; then
  python_cmd="$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python3"
fi
"$python_cmd" "$RUNTIME_SCRIPT"

echo "layer-quality-fix: completed; report=$REPORT_DIR/layer-quality-current.md"
