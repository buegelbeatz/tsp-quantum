---
name: k3s-server-bootstrap
description: Bootstrap K3S control-plane and agent nodes on Raspberry Pi or fresh AMD64 Linux hosts.
layer: digital-generic-team
---

# Skill: K3S Server Bootstrap

## Purpose

Provide deterministic shell helpers to install and validate a K3S cluster on Linux hosts, including:
- Raspberry Pi (ARM64) edge nodes.
- Fresh AMD64 machine profile (16 GB RAM / 256 GB SSD baseline).

## When to Use

- New host requires first-time K3S installation.
- Building a new single-node K3S server on AMD64.
- Expanding an existing cluster with additional agent nodes.

## Capabilities

- `scripts/k3s-install-server.sh` — install and validate first server/control-plane node.
- `scripts/k3s-join-agent.sh` — join additional agents to existing server.
- `scripts/k3s-postinstall.sh` — post-install sanity checks and baseline diagnostics.

## Environment Variables

| Variable            | Default                    | Description |
|---------------------|----------------------------|-------------|
| `K3S_CHANNEL`       | `stable`                   | K3S release channel |
| `K3S_DISABLE_TRAEFIK` | `true`                   | Disable bundled Traefik |
| `K3S_TLS_SAN`       | *(unset)*                  | API TLS SAN host/IP |
| `K3S_SERVER_URL`    | *(required for join)*      | API URL, e.g. `https://10.0.0.10:6443` |
| `K3S_TOKEN`         | *(required for join)*      | Node join token |
| `K3S_KUBECONFIG_MODE` | `640`                    | kubeconfig mode |

## Usage Examples

```bash
# Install server on fresh machine
.github/skills/k3s-server-bootstrap/scripts/k3s-install-server.sh

# Join worker/agent node
K3S_SERVER_URL="https://10.0.0.10:6443" \
K3S_TOKEN="<token>" \
  .github/skills/k3s-server-bootstrap/scripts/k3s-join-agent.sh

# Run post-install checks
.github/skills/k3s-server-bootstrap/scripts/k3s-postinstall.sh
```
