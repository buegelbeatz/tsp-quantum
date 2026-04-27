#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# =============================================================================
# Enterprise Shared Shell Library: containers.sh
# -----------------------------------------------------------------------------
# Purpose:
#   Provide container runtime detection and execution helpers.
#
# Mandatory Runtime Priority:
#   1) podman
#   2) singularity / apptainer
#   3) docker
#
# Security & Compliance:
#   - Never assumes privileged execution.
#   - Uses ephemeral `--rm` containers for OCI engines.
#   - Mounts repository root to `/workspace` by default when available.
# =============================================================================

# Purpose:
#   Provide container runtime detection and execution helpers.
# Security:
#   Avoids privileged assumptions, uses ephemeral runtime flags, and limits mounts.

# shellcheck shell=bash

is_engine_available() {
  local engine="$1"

  case "$engine" in
    podman)
      command -v podman >/dev/null 2>&1
      ;;
    singularity)
      command -v singularity >/dev/null 2>&1 || command -v apptainer >/dev/null 2>&1
      ;;
    docker)
      command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
      ;;
    *)
      return 1
      ;;
  esac
}

detect_container_tool() {
  if is_engine_available podman; then
    echo "podman"
    return 0
  fi
  if command -v apptainer >/dev/null 2>&1; then
    echo "apptainer"
    return 0
  fi
  if command -v singularity >/dev/null 2>&1; then
    echo "singularity"
    return 0
  fi
  if is_engine_available docker; then
    echo "docker"
    return 0
  fi
  return 1
}

_container_registry_host() {
  local image="$1"

  if [[ "$image" == *"/"* ]]; then
    local first_segment="${image%%/*}"
    if [[ "$first_segment" == *.* || "$first_segment" == *:* || "$first_segment" == "localhost" ]]; then
      printf '%s\n' "$first_segment"
      return 0
    fi
  fi

  printf '%s\n' "docker.io"
}

_ghcr_login_username() {
  if [[ -n "${GHCR_NAMESPACE:-}" && "${GHCR_NAMESPACE}" == */* ]]; then
    printf '%s\n' "${GHCR_NAMESPACE##*/}"
    return 0
  fi
  if [[ -n "${GITHUB_OWNER:-}" ]]; then
    printf '%s\n' "$GITHUB_OWNER"
    return 0
  fi
  if [[ -n "${USER:-}" ]]; then
    printf '%s\n' "$USER"
    return 0
  fi
  printf '%s\n' "github"
}

ensure_container_registry_login() {
  local engine="$1"
  local image="$2"
  local registry_host token username

  registry_host="$(_container_registry_host "$image")"
  if [[ "$registry_host" != "ghcr.io" ]]; then
    return 0
  fi

  token="${GHCR_TOKEN:-${GH_TOKEN:-}}"
  [[ -n "$token" ]] || return 0

  case "$engine" in
    podman|docker)
      username="$(_ghcr_login_username)"
      printf '%s' "$token" | "$engine" login ghcr.io -u "$username" --password-stdin >/dev/null
      ;;
  esac
}

# run_in_container <image> [cmd args...]
#
# Optional env vars controlling container behaviour:
#   CONTAINER_MOUNT_ROOT   — host path to mount as /workspace (default: repo root or $PWD)
#   CONTAINER_ENV_PASSTHROUGH — comma-separated list of env var names to forward
#                               into the container (e.g. "GH_TOKEN,GITHUB_OWNER")
#   CONTAINER_PLATFORM — optional OCI target platform (e.g. `linux/arm64`, `linux/amd64`)
run_in_container() {
  local image="$1"
  shift

  local engine
  engine="$(detect_container_tool)" || return 1

  ensure_container_registry_login "$engine" "$image"

  local mount_root
  local repo_root
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  mount_root="${CONTAINER_MOUNT_ROOT:-$repo_root}"

  local platform_args=()
  if [[ -n "${CONTAINER_PLATFORM:-}" ]]; then
    platform_args=("--platform" "$CONTAINER_PLATFORM")
  fi

  # Build --env / --env-file arguments from CONTAINER_ENV_PASSTHROUGH
  local env_args=()
  if [[ -n "${CONTAINER_ENV_PASSTHROUGH:-}" ]]; then
    local IFS_BACKUP="$IFS"
    IFS=','
    for var_name in ${CONTAINER_ENV_PASSTHROUGH}; do
      IFS="$IFS_BACKUP"
      var_name="$(printf '%s' "$var_name" | tr -d ' ')"
      [[ -z "$var_name" ]] && continue
      if [[ -n "${!var_name+x}" ]]; then
        env_args+=("--env" "${var_name}=${!var_name}")
      fi
    done
    IFS="$IFS_BACKUP"
  fi

  case "$engine" in
    docker|podman)
      "$engine" run --rm \
        "${platform_args[@]+${platform_args[@]}}" \
        -v "${mount_root}:/workspace" \
        -w /workspace \
        "${env_args[@]+${env_args[@]}}" \
        "$image" "$@"
      ;;
    singularity|apptainer)
      "$engine" exec \
        --bind "${mount_root}:/workspace" \
        --pwd /workspace \
        "${env_args[@]+${env_args[@]}}" \
        "$image" "$@"
      ;;
    *)
      return 1
      ;;
  esac
}
