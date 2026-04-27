#!/usr/bin/env bash
# layer: digital-generic-team
# Collect a structured cluster analysis from a K3S (or any kubectl-accessible) cluster.
# Outputs a human-readable summary of nodes, workloads, events, storage, and networking.
#
# Usage:
#   .github/skills/k8s-expert/scripts/k8s-analyze.sh
#
#   # With SSH proxy
#   SSH_KUBECTL_PROXY_HOST=jump.example.com \
#   SSH_KUBECTL_PROXY_USER=pi \
#   SSH_KUBECTL_PROXY_REMOTE_ADDR=192.168.1.100 \
#     .github/skills/k8s-expert/scripts/k8s-analyze.sh

set -euo pipefail
# Purpose:
#   Execute the k8s analyze workflow for this layer.
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

section() {
  echo ""
  echo "══════════════════════════════════════════════"
  echo "  $1"
  echo "══════════════════════════════════════════════"
}

# Require kubectl
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is not installed or not on PATH." >&2
  exit 1
fi

# Start proxy if configured
k8s_start_proxy

section "CLUSTER INFO"
kubectl_cmd cluster-info 2>/dev/null || echo "  (cluster-info unavailable)"

section "NODES"
kubectl_cmd get nodes -o wide

section "NODE RESOURCE USAGE"
kubectl_cmd top nodes 2>/dev/null || echo "  (metrics-server not available)"

section "KUBE-SYSTEM PODS"
kubectl_cmd get pods -n kube-system

section "ALL NAMESPACES — PODS"
kubectl_cmd get pods -A -o wide

section "FAILING / NON-RUNNING PODS"
kubectl_cmd get pods -A \
  --field-selector='status.phase!=Running,status.phase!=Succeeded' \
  2>/dev/null || echo "  (none found or field selector not supported)"

section "DEPLOYMENTS"
kubectl_cmd get deployments -A

section "STATEFULSETS"
kubectl_cmd get statefulsets -A 2>/dev/null || echo "  (none)"

section "DAEMONSETS"
kubectl_cmd get daemonsets -A 2>/dev/null || echo "  (none)"

section "SERVICES"
kubectl_cmd get services -A

section "INGRESS / GATEWAY"
kubectl_cmd get ingress -A 2>/dev/null || echo "  (none)"
kubectl_cmd get gateways -A 2>/dev/null || true

section "PERSISTENT VOLUMES"
kubectl_cmd get pv 2>/dev/null || echo "  (none)"

section "PERSISTENT VOLUME CLAIMS"
kubectl_cmd get pvc -A 2>/dev/null || echo "  (none)"

section "STORAGE CLASSES"
kubectl_cmd get storageclass 2>/dev/null || echo "  (none)"

section "RECENT EVENTS (last 40)"
kubectl_cmd get events -A --sort-by='.lastTimestamp' 2>/dev/null | tail -40 || echo "  (no events)"

section "TOP PODS BY MEMORY"
kubectl_cmd top pods -A --sort-by=memory 2>/dev/null || echo "  (metrics-server not available)"

section "ANALYSIS COMPLETE"
echo "  Context: $(kubectl config current-context 2>/dev/null || echo 'unknown')"
echo "  Date:    $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
