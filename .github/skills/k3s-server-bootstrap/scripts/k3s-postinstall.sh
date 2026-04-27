#!/usr/bin/env bash
# layer: digital-generic-team
# Run post-install checks for K3S cluster readiness.

set -euo pipefail
# Purpose:
#   Execute the k3s postinstall workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

kubectl_cmd() {
  if command -v sudo >/dev/null 2>&1; then
    sudo kubectl "$@"
  else
    kubectl "$@"
  fi
}

if ! command -v kubectl >/dev/null 2>&1 && ! command -v sudo >/dev/null 2>&1; then
  echo "kubectl is required." >&2
  exit 1
fi

echo "=== K3S Post-install Check ==="
echo "Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

echo "[1/6] Cluster info"
kubectl_cmd cluster-info || true

echo ""
echo "[2/6] Nodes"
kubectl_cmd get nodes -o wide || true

echo ""
echo "[3/6] kube-system pods"
kubectl_cmd get pods -n kube-system || true

echo ""
echo "[4/6] All namespaces workloads"
kubectl_cmd get deployments -A || true


echo ""
echo "[5/6] Services and ingress"
kubectl_cmd get svc -A || true
kubectl_cmd get ingress -A || true

echo ""
echo "[6/6] Recent events"
kubectl_cmd get events -A --sort-by='.lastTimestamp' | tail -30 || true

echo ""
echo "Post-install check completed."
