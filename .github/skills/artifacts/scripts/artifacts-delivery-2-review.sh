#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the artifacts delivery 2 review workflow for this layer.
#   Aggregates review handoffs from delivery agents and generates cumulated review.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Prompt entrypoint: /artifacts-delivery-2-review stage="<stage>"
# Skill owner: agile-coach

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SHARED_RUNTIME_SYNC="$REPO_ROOT/.github/skills/shared/shell/scripts/runtime/layer-venv-sync.sh"
ARTIFACTS_LAYER_DIR="$REPO_ROOT/.github/skills/artifacts"

STAGE="${1:-}"
if [[ -z "$STAGE" ]]; then
  echo "usage: artifacts-delivery-2-review.sh <stage>"
  exit 2
fi

SYNC_OUTPUT="$(bash "$SHARED_RUNTIME_SYNC" "$ARTIFACTS_LAYER_DIR")"
VENV_PATH="$(printf '%s\n' "$SYNC_OUTPUT" | awk -F': ' '$1=="venv_path" {gsub(/\"/, "", $2); print $2}')"
if [[ -z "$VENV_PATH" ]]; then
  LAYER_ID="${DIGITAL_TEAM_LAYER_ID:-python-runtime}"
  VENV_PATH="$REPO_ROOT/.digital-runtime/layers/$LAYER_ID/venv"
fi
if [[ -z "$VENV_PATH" || ! -x "$VENV_PATH/bin/python" ]]; then
  echo "[artifacts-delivery-2-review] ERROR: could not resolve synced layer venv python"
  exit 1
fi

export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
"$VENV_PATH/bin/python" "$SCRIPT_DIR/artifacts_flow.py" --repo-root "$REPO_ROOT" delivery-to-review --stage "$STAGE"
