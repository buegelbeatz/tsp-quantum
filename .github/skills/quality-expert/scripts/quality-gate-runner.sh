#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute quality gate commands in standardized python:3.14-slim containers
#   from tools.csv, with RW access to repo for cache/coverage files.
# Security:
#   Uses standard public container images only. No custom builds.
#   Mounts are RW because we trust the repo and need artifact write-back.

GATE_NAME="${1:-unknown}"
GATE_COMMAND="${2:-echo 'no-op'}"
REPO_ROOT="${3:-.}"
COVERAGE_FILE="${4:-}"

detect_container_runtime() {
  if command -v podman &>/dev/null; then
    echo "podman"
    return 0
  elif command -v docker &>/dev/null; then
    echo "docker"
    return 0
  fi
  echo "none"
  return 1
}

run_in_container() {
  local runtime="$1"
  local gate_name="$2"
  local gate_command="$3"
  local repo_root="$4"
  local coverage_file="$5"

  local image="python:3.14-slim"
  local work_dir="/workspace"
  local sanitized_gate="${gate_name//[^a-zA-Z0-9_.-]/-}"
  local container_name="dt-${sanitized_gate}-$$-$(date +%s)"
  local container_coverage_file=""
  
  printf '[gate-runner] runtime=%s image=%s gate=%s coverage=%s\n' "$runtime" "$image" "$gate_name" "${coverage_file:-(none)}" >&2

  local container_opts=(
    "--rm"
    "--name" "$container_name"
    "-w" "$work_dir"
    "-v" "$repo_root:$work_dir:rw"  # RW mount for caching, .coverage, and artifact output
    "-e" "PYTHONDONTWRITEBYTECODE=1"
    "-e" "CI=true"
  )

  if [[ -n "$coverage_file" ]]; then
    # Ensure .tests directories exist
    mkdir -p "${coverage_file%/*}" "$repo_root/.tests/python/reports"
    container_coverage_file="${coverage_file/#$repo_root/$work_dir}"
    container_opts+=("-e" "COVERAGE_FILE=$container_coverage_file")
  fi

  # Install system dependencies (git for tests, perl for task-audit-log)
  # then install all quality tools + any merged requirements from layer venv
  local install_cmd="apt-get update -qq && apt-get install -y --no-install-recommends git perl && pip install -q --no-cache-dir pytest pytest-cov coverage ruff mypy bandit"
  
  # If merged-requirements exists, install those too (all layer dependencies)
  if [[ -f "$repo_root/.digital-runtime/layers/python-runtime/requirements.merged.txt" ]]; then
    install_cmd+=" && pip install -q --no-cache-dir -r .digital-runtime/layers/python-runtime/requirements.merged.txt"
  fi

  local full_command="$install_cmd && $gate_command"

  "$runtime" run "${container_opts[@]}" "$image" bash -c "$full_command"
}

run_locally() {
  local gate_name="$1"
  local gate_command="$2"
  local repo_root="$3"
  local coverage_file="$4"

  if [[ "${QUALITY_GATE_FORCE_LOCAL:-0}" == "1" ]]; then
    printf '[gate-runner] mode=local gate=%s (forced by QUALITY_GATE_FORCE_LOCAL=1)\n' "$gate_name" >&2
  else
    printf '[gate-runner] mode=local gate=%s (container runtime unavailable)\n' "$gate_name" >&2
  fi

  local venv_path="$repo_root/.digital-runtime/layers/python-runtime/venv"
  if [[ ! -d "$venv_path" ]]; then
    printf '[gate-runner] ERROR: Layer venv not found at %s\n' "$venv_path" >&2
    printf '[gate-runner] Install with: make layer-venv-sync\n' >&2
    return 1
  fi

  if [[ -n "$coverage_file" ]]; then
    export COVERAGE_FILE="$coverage_file"
  fi
  export PYTHONDONTWRITEBYTECODE=1
  export PATH="$venv_path/bin:$PATH"

  (
    cd "$repo_root"
    bash -c "$gate_command"
  )
}

# Main: try container first, fall back to local venv
runtime=$(detect_container_runtime)
force_local="${QUALITY_GATE_FORCE_LOCAL:-0}"

if [[ "$force_local" == "1" ]]; then
  run_locally "$GATE_NAME" "$GATE_COMMAND" "$REPO_ROOT" "$COVERAGE_FILE"
elif [[ "$runtime" != "none" ]]; then
  run_in_container "$runtime" "$GATE_NAME" "$GATE_COMMAND" "$REPO_ROOT" "$COVERAGE_FILE"
else
  run_locally "$GATE_NAME" "$GATE_COMMAND" "$REPO_ROOT" "$COVERAGE_FILE"
fi
