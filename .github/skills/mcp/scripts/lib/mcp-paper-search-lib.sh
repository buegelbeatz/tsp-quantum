#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Provide bootstrap and runtime helpers for the paper-search MCP wrapper.
# Security:
#   Keeps mutable runtime state under .digital-runtime and uses bounded container execution.

# shellcheck shell=bash

log() {
  printf '[mcp-paper-search] %s\n' "$*" >&2
}


run_with_timeout() {
  local timeout_seconds="$1"
  shift
  "$@" &
  local command_pid=$!
  local elapsed=0

  while kill -0 "$command_pid" 2>/dev/null; do
    if (( elapsed > 0 && elapsed % 10 == 0 )); then
      log "bootstrap still running (${elapsed}s elapsed)..."
    fi
    if (( elapsed >= timeout_seconds )); then
      log "bootstrap timeout reached after ${timeout_seconds}s"
      kill "$command_pid" 2>/dev/null || true
      wait "$command_pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  wait "$command_pid"
}


run_local_venv() {
  if [[ ! -x "$HOST_LAYER_VENV/bin/python" ]]; then
    echo "Missing local layer venv python: $HOST_LAYER_VENV/bin/python" >&2
    echo "Run: make layer-venv-sync" >&2
    return 1
  fi
  exec "$HOST_LAYER_VENV/bin/python" -m paper_search_mcp.server "$@"
}


run_container_venv() {
  mkdir -p "$HOST_LAYER_RUNTIME_DIR"

  local bootstrap_timeout_seconds="${DIGITAL_MCP_BOOTSTRAP_TIMEOUT_SECONDS:-120}"
  local pip_timeout_seconds="${DIGITAL_MCP_PIP_TIMEOUT_SECONDS:-20}"
  local pip_retries="${DIGITAL_MCP_PIP_RETRIES:-1}"
  local bootstrap_verbose="${DIGITAL_MCP_VERBOSE:-$BOOTSTRAP_VERBOSE}"
  local container_runtime_dir="/workspace/.digital-runtime/layers/$LAYER_ID"
  local container_venv="$container_runtime_dir/venv-container-paper-search"
  local container_requirements="$container_runtime_dir/requirements.merged.txt"
  local bootstrap_state_file="$container_runtime_dir/paper-search-bootstrap.sha256"

  log "container-first bootstrap started (timeout=${bootstrap_timeout_seconds}s, pip_timeout=${pip_timeout_seconds}s, pip_retries=${pip_retries}, verbose=${bootstrap_verbose})"
  if ! CONTAINER_MOUNT_ROOT="$REPO_ROOT" run_with_timeout "$bootstrap_timeout_seconds" run_in_container "python:3.12-slim" \
    bash -lc '
      set -euo pipefail

      runtime_dir="$1"
      venv_path="$2"
      requirements_file="$3"
      state_file="$4"
      pip_timeout="$5"
      pip_retries="$6"
      bootstrap_verbose="$7"

      bootstrap_version="paper-search-mcp-bootstrap-v2"
      requirements_hash="none"
      if [[ -s "$requirements_file" ]]; then
        requirements_hash="$(sha256sum "$requirements_file" | awk "{print \$1}")"
      fi
      desired_hash="$(printf "%s|%s\n" "$bootstrap_version" "$requirements_hash" | sha256sum | awk "{print \$1}")"
      current_hash="$(cat "$state_file" 2>/dev/null || true)"

      mkdir -p "$runtime_dir"
      if [[ ! -x "$venv_path/bin/python" ]]; then
        echo "[mcp-paper-search][container] creating venv at $venv_path" >&2
        python -m venv "$venv_path"
        current_hash=""
      fi
      if [[ "$desired_hash" != "$current_hash" ]]; then
        echo "[mcp-paper-search][container] synchronizing dependencies" >&2
        pip_flags=("--timeout" "$pip_timeout" "--retries" "$pip_retries")
        if [[ "$bootstrap_verbose" != "1" ]]; then
          pip_flags+=("--quiet")
        else
          echo "[mcp-paper-search][container] verbose bootstrap output enabled" >&2
        fi
        "$venv_path/bin/python" -m pip install --upgrade pip "${pip_flags[@]}"
        if [[ -s "$requirements_file" ]]; then
          "$venv_path/bin/pip" install -r "$requirements_file" "${pip_flags[@]}"
        fi
        "$venv_path/bin/pip" install paper-search-mcp "${pip_flags[@]}"
        printf "%s\n" "$desired_hash" > "$state_file"
      else
        echo "[mcp-paper-search][container] dependency cache is up to date" >&2
      fi
    ' _ "$container_runtime_dir" "$container_venv" "$container_requirements" "$bootstrap_state_file" "$pip_timeout_seconds" "$pip_retries" "$bootstrap_verbose"; then
    log "bootstrap failed or timed out"
    log "hint: set DIGITAL_MCP_BOOTSTRAP_TIMEOUT_SECONDS to a higher value for first-run installs"
    log "hint: local defender/proxy rules may block outbound URLs (for example chatgpt.com or package mirrors)"
    return 1
  fi

  log "starting paper-search MCP server from mounted container venv"
  CONTAINER_MOUNT_ROOT="$REPO_ROOT" run_in_container "python:3.12-slim" "$container_venv/bin/python" -m paper_search_mcp.server "$@"
}