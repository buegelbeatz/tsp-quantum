#!/usr/bin/env bash
# layer: digital-generic-team
# Establish and validate kubectl connectivity to a K3S cluster.
# Supports local kubeconfig and remote SSH proxy mode.
#
# Usage:
#   # Local
#   .github/skills/k8s-expert/scripts/k8s-connect.sh
#
#   # Remote via SSH proxy
#   SSH_KUBECTL_PROXY_HOST=jump.example.com \
#   SSH_KUBECTL_PROXY_USER=pi \
#   SSH_KUBECTL_PROXY_REMOTE_ADDR=192.168.1.100 \
#     .github/skills/k8s-expert/scripts/k8s-connect.sh

set -euo pipefail
# Purpose:
#   Execute the k8s connect workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=k8s-proxy.sh
source "$SCRIPT_DIR/k8s-proxy.sh"

kubectl_cmd() {
  local -a cmd=(kubectl)
  if [[ -n "${KUBECONFIG_PROXY_PATH:-}" && -f "${KUBECONFIG_PROXY_PATH}" ]]; then
    cmd+=(--kubeconfig "$KUBECONFIG_PROXY_PATH")
  fi
  if [[ -n "${KUBECTL_SERVER:-}" ]]; then
    cmd+=(--server "$KUBECTL_SERVER")
  fi
  if [[ -n "${KUBECTL_TLS_SERVER_NAME:-}" ]]; then
    cmd+=(--tls-server-name "$KUBECTL_TLS_SERVER_NAME")
  fi
  if [[ "${KUBECTL_INSECURE_SKIP_VERIFY:-false}" == "true" ]]; then
    echo "WARNING: TLS verification is disabled (KUBECTL_INSECURE_SKIP_VERIFY=true)." >&2
    cmd+=(--insecure-skip-tls-verify)
  fi
  cmd+=("$@")
  "${cmd[@]}"
}

# Require kubectl
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is not installed or not on PATH." >&2
  exit 1
fi

# Start proxy if configured
k8s_start_proxy

echo "Active context: $(kubectl config current-context 2>/dev/null || echo 'unknown')"
echo ""

if kubectl_cmd cluster-info; then
  echo ""
  echo "Cluster is reachable."
else
  echo ""
  echo "ERROR: Could not connect to the cluster." >&2
  echo "Check kubectl config, KUBECONFIG, or SSH proxy settings." >&2
  exit 1
fi
