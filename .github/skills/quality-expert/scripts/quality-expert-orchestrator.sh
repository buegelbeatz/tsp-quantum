#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Orchestrate canonical quality workflows through one quality-expert entrypoint:
#   read-only overview via /quality and report-driven remediation via /quality-fix.
# Security:
#   Executes only repository-local quality scripts and avoids eval/dynamic execution.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
RUN_TOOL="$REPO_ROOT/.github/skills/shared/runtime/scripts/run-tool.sh"
QUALITY_EXPERT_SESSION_SCRIPT="$REPO_ROOT/.github/skills/quality-expert/scripts/quality-expert-session.sh"
LAYER_QUALITY_RUNTIME_SCRIPT="$REPO_ROOT/.github/skills/shared/orchestration/scripts/layer_quality_runtime.py"
LAYER_QUALITY_FIX_SCRIPT="$REPO_ROOT/.github/skills/shared/orchestration/scripts/layer_quality_fix.sh"
MODE="${QUALITY_EXPERT_MODE:-scan}"

if [[ ! -x "$RUN_TOOL" ]]; then
  echo "quality-expert-orchestrator: missing run-tool helper at $RUN_TOOL" >&2
  exit 1
fi

case "$MODE" in
  scan)
    if [[ ! -f "$QUALITY_EXPERT_SESSION_SCRIPT" ]]; then
      echo "quality-expert-orchestrator: missing quality session script at $QUALITY_EXPERT_SESSION_SCRIPT" >&2
      exit 1
    fi
    echo "[progress][quality-expert-orchestrator] step=1/2 action=run-quality-expert-session"
    RUN_TOOL_PREFER_CONTAINER=1 bash "$QUALITY_EXPERT_SESSION_SCRIPT"
    echo "[progress][quality-expert-orchestrator] step=2/2 action=run-quality-runtime"
    LAYER_QUALITY_SCRIPTS_DIR="$(dirname "$LAYER_QUALITY_RUNTIME_SCRIPT")"
    RUNTIME_VENV_BIN="$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin"
    if [[ -x "$RUNTIME_VENV_BIN/python3" ]]; then
      PYTHONPATH="$LAYER_QUALITY_SCRIPTS_DIR" "$RUNTIME_VENV_BIN/python3" "$LAYER_QUALITY_RUNTIME_SCRIPT"
    else
      LAYER_QUALITY_REL="${LAYER_QUALITY_RUNTIME_SCRIPT#${REPO_ROOT}/}"
      bash "$RUN_TOOL" python3 "/workspace/${LAYER_QUALITY_REL}"
    fi
    ;;
  fix)
    if [[ ! -f "$LAYER_QUALITY_FIX_SCRIPT" ]]; then
      echo "quality-expert-orchestrator: missing quality-fix script at $LAYER_QUALITY_FIX_SCRIPT" >&2
      exit 1
    fi
    echo "[progress][quality-expert-orchestrator] step=1/1 action=run-quality-fix"
    bash "$LAYER_QUALITY_FIX_SCRIPT"
    ;;
  *)
    echo "quality-expert-orchestrator: unsupported QUALITY_EXPERT_MODE='$MODE' (expected: scan|fix)" >&2
    exit 2
    ;;
esac
