#!/usr/bin/env bash
# layer: digital-generic-team
# SSH tunnel lifecycle helpers for remote K3S kubectl access.
# Source this file from other scripts; do not run directly.
#
# Required env: SSH_KUBECTL_PROXY_HOST
# Optional env: SSH_KUBECTL_PROXY_USER, SSH_KUBECTL_PROXY_PORT,
#               SSH_KUBECTL_PROXY_LOCAL_PORT, SSH_KUBECTL_PROXY_REMOTE_ADDR,
#               SSH_KUBECTL_PROXY_REMOTE_PORT

set -euo pipefail
# Purpose:
#   Execute the k8s proxy workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

KUBECTL_PROXY_PID=""

# Resolve the cluster server from the current kubeconfig
_k8s_resolve_kubeconfig_server() {
  kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || true
}

# Resolve cluster name from kubeconfig
_k8s_resolve_kubeconfig_cluster() {
  kubectl config view --minify -o jsonpath='{.contexts[0].context.cluster}' 2>/dev/null || true
}

# Extract hostname from a server URL (strip scheme and port)
_k8s_resolve_host_from_server() {
  local server="$1"
  echo "$server" | sed -E 's#https?://##; s#:[0-9]+$##'
}

# Wait until the local tunnel port is open
_k8s_wait_for_tunnel() {
  local host="127.0.0.1"
  local port="${SSH_KUBECTL_PROXY_LOCAL_PORT:-6443}"
  local attempts=20
  local delay=0.5

  for _ in $(seq 1 "$attempts"); do
    if command -v nc >/dev/null 2>&1; then
      nc -z "$host" "$port" >/dev/null 2>&1 && return 0
    else
      (echo >/dev/tcp/${host}/"${port}") >/dev/null 2>&1 && return 0
    fi
    sleep "$delay"
  done
  return 1
}

# Rewrite kubeconfig to point to proxied server
_k8s_prepare_kubeconfig_for_proxy() {
  local cluster server
  cluster="$(_k8s_resolve_kubeconfig_cluster)"
  server="$(_k8s_resolve_kubeconfig_server)"

  if [[ -z "$cluster" || -z "$server" ]]; then
    echo "Cannot determine cluster or server from current kubeconfig." >&2
    return 1
  fi

  KUBECONFIG_PROXY_PATH="${KUBECONFIG_PROXY_PATH:-.data/kubeconfig-proxy}"
  mkdir -p "$(dirname "$KUBECONFIG_PROXY_PATH")"
  kubectl config view --minify --raw > "$KUBECONFIG_PROXY_PATH"
  kubectl --kubeconfig "$KUBECONFIG_PROXY_PATH" \
    config set-cluster "$cluster" \
    --server "${KUBECTL_SERVER:-https://127.0.0.1:${SSH_KUBECTL_PROXY_LOCAL_PORT:-6443}}" >/dev/null
  export KUBECONFIG_PROXY_PATH
}

# Start the SSH tunnel; sets KUBECTL_PROXY_PID and exports proxy vars
k8s_start_proxy() {
  if [[ -z "${SSH_KUBECTL_PROXY_HOST:-}" ]]; then
    return 0  # No proxy requested
  fi

  local remote_addr="${SSH_KUBECTL_PROXY_REMOTE_ADDR:-}"
  if [[ -z "$remote_addr" ]]; then
    local server
    server="$(_k8s_resolve_kubeconfig_server)"
    remote_addr="$(_k8s_resolve_host_from_server "$server")"
  fi

  if [[ -z "$remote_addr" ]]; then
    echo "SSH_KUBECTL_PROXY_REMOTE_ADDR is not set and cannot be resolved from kubeconfig." >&2
    return 1
  fi

  if ! command -v ssh >/dev/null 2>&1; then
    echo "ssh is not available on PATH." >&2
    return 1
  fi

  local local_port="${SSH_KUBECTL_PROXY_LOCAL_PORT:-6443}"
  local remote_port="${SSH_KUBECTL_PROXY_REMOTE_PORT:-6443}"

  export KUBECTL_SERVER="${KUBECTL_SERVER:-https://127.0.0.1:${local_port}}"
  export KUBECTL_TLS_SERVER_NAME="${KUBECTL_TLS_SERVER_NAME:-${remote_addr}}"

  local ssh_target="${SSH_KUBECTL_PROXY_HOST}"
  if [[ -n "${SSH_KUBECTL_PROXY_USER:-}" ]]; then
    ssh_target="${SSH_KUBECTL_PROXY_USER}@${SSH_KUBECTL_PROXY_HOST}"
  fi

  local -a ssh_cmd=(ssh)
  if [[ -n "${SSH_KUBECTL_PROXY_PORT:-}" ]]; then
    ssh_cmd+=("-p" "$SSH_KUBECTL_PROXY_PORT")
  fi

  echo "Starting kubectl SSH proxy: ${ssh_target} → 127.0.0.1:${local_port} → ${remote_addr}:${remote_port}"

  "${ssh_cmd[@]}" \
    -N \
    -L "${local_port}:${remote_addr}:${remote_port}" \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    "$ssh_target" &

  KUBECTL_PROXY_PID=$!
  trap 'k8s_stop_proxy' EXIT

  if ! _k8s_wait_for_tunnel; then
    echo "SSH tunnel did not become ready on 127.0.0.1:${local_port}." >&2
    return 1
  fi

  _k8s_prepare_kubeconfig_for_proxy || true
  echo "SSH tunnel ready."
}

# Stop the SSH tunnel
k8s_stop_proxy() {
  if [[ -n "${KUBECTL_PROXY_PID:-}" ]]; then
    kill "$KUBECTL_PROXY_PID" >/dev/null 2>&1 || true
    KUBECTL_PROXY_PID=""
  fi
}
