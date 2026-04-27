#!/usr/bin/env bash
# layer: digital-generic-team
# Install K3S server on a fresh Linux host (ARM64 or AMD64).

set -euo pipefail
# Purpose:
#   Execute the k3s install server workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

assert_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This script must run on Linux." >&2
    exit 1
  fi
}

assert_linux
require_cmd curl
require_cmd sudo

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|aarch64) ;;
  *)
    echo "Unsupported architecture: $ARCH (expected x86_64 or aarch64)." >&2
    exit 1
    ;;
esac

K3S_CHANNEL="${K3S_CHANNEL:-stable}"
K3S_DISABLE_TRAEFIK="${K3S_DISABLE_TRAEFIK:-true}"
K3S_KUBECONFIG_MODE="${K3S_KUBECONFIG_MODE:-640}"
K3S_TLS_SAN="${K3S_TLS_SAN:-}"

INSTALL_ARGS=("server" "--write-kubeconfig-mode" "$K3S_KUBECONFIG_MODE")
if [[ "$K3S_DISABLE_TRAEFIK" == "true" ]]; then
  INSTALL_ARGS+=("--disable" "traefik")
fi
if [[ -n "$K3S_TLS_SAN" ]]; then
  INSTALL_ARGS+=("--tls-san" "$K3S_TLS_SAN")
fi

INSTALL_EXEC="${INSTALL_ARGS[*]}"

echo "Installing K3S server"
echo "  Architecture: $ARCH"
echo "  Channel:      $K3S_CHANNEL"
echo "  Traefik:      $K3S_DISABLE_TRAEFIK"
echo "  TLS SAN:      ${K3S_TLS_SAN:-<unset>}"
echo ""

curl -sfL https://get.k3s.io | \
  sudo INSTALL_K3S_CHANNEL="$K3S_CHANNEL" INSTALL_K3S_EXEC="$INSTALL_EXEC" sh -

echo ""
echo "K3S service status:"
sudo systemctl --no-pager --full status k3s | sed -n '1,20p' || true

echo ""
echo "Quick validation:"
sudo kubectl get nodes -o wide || true
sudo kubectl get pods -A || true

echo ""
echo "Join token (store securely):"
sudo cat /var/lib/rancher/k3s/server/token
