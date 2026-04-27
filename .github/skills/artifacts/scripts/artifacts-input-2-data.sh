#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail
# Purpose:
#   Execute the artifacts input 2 data workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

# Prompt entrypoint: /artifacts-input-2-data
# Skill owner: agile-coach
# Canonical language rule:
#   All normalized content written to .digital-artifacts/10-data must be English.
#   Source-language text may be retained for provenance only, never as the primary normalized payload.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SHARED_RUNTIME_SYNC="$REPO_ROOT/.github/skills/shared/shell/scripts/runtime/layer-venv-sync.sh"
ARTIFACTS_LAYER_DIR="$REPO_ROOT/.github/skills/artifacts"
INPUT_ROOT="$REPO_ROOT/.digital-artifacts/00-input"
INPUT_DOCUMENTS="$INPUT_ROOT/documents"
INPUT_FEATURES="$INPUT_ROOT/features"
INPUT_BUGS="$INPUT_ROOT/bugs"

resolve_venv_path() {
  local sync_output venv_path layer_id
  sync_output="$(DIGITAL_TEAM_VENV_SYNC_HIDE_CONTEXT=0 bash "$SHARED_RUNTIME_SYNC" "$ARTIFACTS_LAYER_DIR")"
  venv_path="$(printf '%s\n' "$sync_output" | awk -F': ' '$1=="venv_path" {gsub(/\"/, "", $2); print $2}')"
  if [[ -z "$venv_path" ]]; then
    layer_id="${DIGITAL_TEAM_SHARED_LAYER_ID:-python-runtime}"
    venv_path="$REPO_ROOT/.digital-runtime/layers/$layer_id/venv"
  fi
  if [[ -z "$venv_path" || ! -x "$venv_path/bin/python" ]]; then
    echo "[artifacts-input-2-data] ERROR: could not resolve synced layer venv python"
    exit 1
  fi
  printf '%s\n' "$venv_path"
}

# Ensure stage workflows always have the input structure available.
mkdir -p "$INPUT_ROOT" "$INPUT_DOCUMENTS" "$INPUT_FEATURES" "$INPUT_BUGS"

# Nothing to ingest: still emit a no-op audit entry, but skip credential validation.
if ! find "$INPUT_ROOT" -type f -print -quit | grep -q .; then
  echo "[artifacts-input-2-data] no input files found — nothing to process"
  export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
  VENV_PATH="$(resolve_venv_path)"
  "$VENV_PATH/bin/python" "$SCRIPT_DIR/artifacts_input_2_data.py" --repo-root "$REPO_ROOT" "$@"
  exit $?
fi

# Load environment
ENV_FILE="$REPO_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# Validate credentials
MISSING=()
for var in DIGITAL_TEAM_VISION_API_URL DIGITAL_TEAM_VISION_API_KEY DIGITAL_TEAM_VISION_MODEL; do
  [[ -z "${!var:-}" ]] && MISSING+=("$var")
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "[artifacts-input-2-data] ERROR: missing required env vars: ${MISSING[*]}"
  exit 1
fi

# Set PYTHONPATH for local imports
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Sync layer venv
VENV_PATH="$(resolve_venv_path)"

echo "[artifacts-input-2-data] starting pipeline (repo=$REPO_ROOT)"
echo "[artifacts-input-2-data] canonical-language=english"
"$VENV_PATH/bin/python" "$SCRIPT_DIR/artifacts_input_2_data.py" --repo-root "$REPO_ROOT" "$@"
