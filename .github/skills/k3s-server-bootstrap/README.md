---
layer: digital-generic-team
---
# k3s-server-bootstrap

Bootstrap K3S control-plane and agent nodes on Raspberry Pi or fresh AMD64 Linux hosts.

## Purpose

Provide the capabilities documented in `SKILL.md`.

## Scripts

- `k3s-install-server.sh` — installs K3S server/control-plane.
- `k3s-join-agent.sh` — joins an agent node.
- `k3s-postinstall.sh` — runs cluster validation checks.
