#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute layer-venv-sync workflow command.
# Security:
#   Uses strict shell mode and validated runtime inputs.

# Purpose:
#   Build and synchronize a layer-scoped Python virtual environment from merged requirements.
# Security|Compliance:
#   Constrains environments to layer runtime paths and removes unsupported root-level virtualenvs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_SHELL_SCRIPTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="${DIGITAL_TEAM_REPO_ROOT:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)}"
REPO_CLASSIFICATION_LIB="$SHARED_SHELL_SCRIPTS_DIR/lib/repo-classification.sh"

# shellcheck source=/dev/null
source "$REPO_CLASSIFICATION_LIB"

root_venv_path="$REPO_ROOT/.venv"
root_venv_alt_path="$REPO_ROOT/venv"
repo_runtime_mode="$(detect_runtime_repo_mode "$REPO_ROOT")"

# Hard guard: layer repositories must never keep root-level virtual environments.
if [[ "$repo_runtime_mode" == "layer" ]]; then
  if [[ -d "$root_venv_path" ]]; then
    echo "[ERROR] Forbidden root virtual environment detected: $root_venv_path" >&2
    echo "[ERROR] Layer repos must only use .digital-runtime/layers/* virtual environments." >&2
    echo "[ERROR] Remove $root_venv_path and rerun make layer-venv-sync." >&2
    exit 2
  fi

  if [[ -d "$root_venv_alt_path" ]]; then
    echo "[ERROR] Forbidden root virtual environment detected: $root_venv_alt_path" >&2
    echo "[ERROR] Layer repos must only use .digital-runtime/layers/* virtual environments." >&2
    echo "[ERROR] Remove $root_venv_alt_path and rerun make layer-venv-sync." >&2
    exit 2
  fi
fi

layer_dir="${1:-}"
[[ -n "$layer_dir" ]] || { echo "Usage: layer-venv-sync.sh <layer-dir>" >&2; exit 1; }

shared_layer_id="${DIGITAL_TEAM_SHARED_LAYER_ID:-python-runtime}"
layer_id="${DIGITAL_TEAM_LAYER_ID:-$(basename "$layer_dir")}"
runtime_root="${DIGITAL_TEAM_RUNTIME_ROOT:-$REPO_ROOT/.digital-runtime}"
layer_runtime_dir="$runtime_root/layers/$layer_id"
venv_path="${DIGITAL_TEAM_SHARED_VENV_PATH:-$runtime_root/layers/$shared_layer_id/venv}"
merged_requirements="$layer_runtime_dir/requirements.merged.txt"
current_hash_file="$layer_runtime_dir/requirements.sha256"

if [[ "$repo_runtime_mode" == "layer" ]]; then
  case "$venv_path" in
    "$REPO_ROOT/.venv"|"$REPO_ROOT/.venv/"*|"$REPO_ROOT/venv"|"$REPO_ROOT/venv/"*)
      echo "[ERROR] Invalid DIGITAL_TEAM_SHARED_VENV_PATH for layer repo: $venv_path" >&2
      echo "[ERROR] Root-level venv paths are forbidden in layer repositories." >&2
      exit 2
      ;;
    "$runtime_root/layers/"*)
      ;;
    *)
      echo "[ERROR] Invalid shared venv location for layer repo: $venv_path" >&2
      echo "[ERROR] Expected path under: $runtime_root/layers/" >&2
      exit 2
      ;;
  esac
fi

cleanup_stray_layer_venvs() {
  local shared_venv_dir="$1"
  local layers_root="$runtime_root/layers"
  local stray_venv=""

  [[ -d "$layers_root" ]] || return 0

  while IFS= read -r stray_venv; do
    [[ -n "$stray_venv" ]] || continue
    if [[ "$stray_venv" != "$shared_venv_dir" ]]; then
      echo "[WARN] Removing unexpected layer virtual environment: $stray_venv" >&2
      echo "[WARN] Reusing shared layer runtime venv: $shared_venv_dir" >&2
      rm -rf "$stray_venv"
    fi
  done < <(find "$layers_root" -mindepth 2 -maxdepth 2 -type d -name venv | sort)
}

mkdir -p "$layer_runtime_dir"
cleanup_stray_layer_venvs "$venv_path"

requirement_files=()
while IFS= read -r requirement_file; do
  requirement_files+=("$requirement_file")
done < <(find "$layer_dir" -type f \( -name 'requirements.txt' -o -name 'requirements-*.txt' -o -name '*requirements.txt' \) | sort)

python3 "$SCRIPT_DIR/layer-requirements-merge.py" --output "$merged_requirements" "${requirement_files[@]}"

requirements_hash="$(if command -v sha256sum &>/dev/null; then sha256sum "$merged_requirements"; else shasum -a 256 "$merged_requirements"; fi | awk '{print $1}')"
previous_hash=""
if [[ -f "$current_hash_file" ]]; then
  previous_hash="$(cat "$current_hash_file")"
fi

venv_newly_created=false
if [[ ! -d "$venv_path" ]]; then
  if [[ "${DIGITAL_TEAM_ALLOW_VENV_CREATE:-0}" == "1" ]]; then
    python3 -m venv "$venv_path"
    venv_newly_created=true
  else
    echo "[ERROR] Shared venv not found: $venv_path" >&2
    echo "[ERROR] Creation is disabled by default (DIGITAL_TEAM_ALLOW_VENV_CREATE=0)." >&2
    echo "[ERROR] Reuse the shared python-runtime venv or set DIGITAL_TEAM_SHARED_VENV_PATH explicitly." >&2
    exit 1
  fi
fi

requirements_changed=false
if [[ "$requirements_hash" != "$previous_hash" ]]; then
  requirements_changed=true
fi

if [[ "$venv_newly_created" == "true" || "$requirements_changed" == "true" ]]; then
  if [[ "${DIGITAL_TEAM_SKIP_PIP_INSTALL:-0}" != "1" ]]; then
    "$venv_path/bin/python" -m pip install --upgrade pip >/dev/null
    if [[ -s "$merged_requirements" ]]; then
      "$venv_path/bin/pip" install -r "$merged_requirements" >/dev/null
    fi
  fi
  printf '%s\n' "$requirements_hash" > "$current_hash_file"
fi

venv_exists=false
[[ -d "$venv_path" ]] && venv_exists=true

if [[ "${DIGITAL_TEAM_VENV_SYNC_HIDE_CONTEXT:-1}" == "1" ]]; then
  printf '%b\n' "api_version: \"v1\"\nkind: \"venv_requirements_sync_result\"\nvenv_exists: $venv_exists\nvenv_newly_created: $venv_newly_created\nrequirements_changed: $requirements_changed"
else
  printf '%b\n' "api_version: \"v1\"\nkind: \"venv_requirements_sync_result\"\nrequirements_scope_id: \"$layer_id\"\nrequirements_scope_dir: \"$layer_dir\"\nvenv_path: \"$venv_path\"\nrequirements_file: \"$merged_requirements\"\nrequirements_hash: \"$requirements_hash\"\nvenv_exists: $venv_exists\nvenv_newly_created: $venv_newly_created\nrequirements_changed: $requirements_changed"
fi
