#!/usr/bin/env bash
# layer: digital-generic-team
# Join a Linux node to an existing K3S server as an agent.

set -euo pipefail
# Purpose:
#   Execute the k3s join agent workflow for this layer.
# Security:
#   Reads and writes only within the repository. No sensitive data processed.

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script must run on Linux." >&2
  exit 1
fi

require_cmd curl
require_cmd sudo

K3S_SERVER_URL="${K3S_SERVER_URL:-}"
K3S_TOKEN="${K3S_TOKEN:-}"
K3S_CHANNEL="${K3S_CHANNEL:-stable}"

if [[ -z "$K3S_SERVER_URL" ]]; then
  echo "K3S_SERVER_URL is required, e.g. https://10.0.0.10:6443" >&2
  exit 1
fi

if [[ -z "$K3S_TOKEN" ]]; then
  echo "K3S_TOKEN is required (from /var/lib/rancher/k3s/server/token)." >&2
  exit 1
fi

echo "Joining node to K3S cluster"
echo "  Server:  $K3S_SERVER_URL"
echo "  Channel: $K3S_CHANNEL"
echo ""

curl -sfL https://get.k3s.io | \
  sudo K3S_URL="$K3S_SERVER_URL" K3S_TOKEN="$K3S_TOKEN" INSTALL_K3S_CHANNEL="$K3S_CHANNEL" sh -

echo ""
echo "K3S agent service status:"
sudo systemctl --no-pager --full status k3s-agent | sed -n '1,20p' || true

echo ""
echo "Node join request sent. Verify from control-plane with:"
echo "  sudo kubectl get nodes -o wide"
