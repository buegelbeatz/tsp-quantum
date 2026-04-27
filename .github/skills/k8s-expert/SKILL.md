---
name: k8s-expert
description: Analyze a local or remote K3S Kubernetes cluster via kubectl, with optional SSH proxy tunnel support.
layer: digital-generic-team
---

# Skill: K8S Expert

## Purpose

Provide reusable shell helpers to connect to, inspect, and analyze K3S Kubernetes clusters — both locally via kubeconfig and remotely via an SSH port-forward tunnel.

## When to Use

- When a user needs to analyze a K3S cluster health, workloads, storage, or networking.
- When the cluster API is accessible only through an SSH jump host.
- When wrapping kubectl commands that need consistent proxy/server overrides.

## Capabilities

- `scripts/k8s-connect.sh` — establish connectivity (local or SSH proxy) and validate `cluster-info`.
- `scripts/k8s-analyze.sh` — collect structured cluster status (nodes, pods, events, PVCs, services).
- `scripts/k8s-proxy.sh` — start and stop an SSH tunnel to a remote K3S API server.

## Environment Variables

| Variable                        | Default                  | Description                                          |
|---------------------------------|--------------------------|------------------------------------------------------|
| `KUBECONFIG`                    | `~/.kube/config`         | Path to kubeconfig file(s)                           |
| `KUBECONFIG_PROXY_PATH`         | `.data/kubeconfig-proxy` | Rewritten kubeconfig for proxy mode                  |
| `KUBECTL_SERVER`                | *(unset)*                | Override kubectl `--server` flag                     |
| `KUBECTL_TLS_SERVER_NAME`       | *(unset)*                | TLS SNI override to match cluster cert               |
| `KUBECTL_INSECURE_SKIP_VERIFY`  | `false`                  | Skip TLS verify — local debug only, never in CI      |
| `SSH_KUBECTL_PROXY_HOST`        | *(required for proxy)*   | Jump host FQDN or IP                                 |
| `SSH_KUBECTL_PROXY_USER`        | *(optional)*             | SSH username on jump host                            |
| `SSH_KUBECTL_PROXY_PORT`        | `22`                     | SSH port                                             |
| `SSH_KUBECTL_PROXY_LOCAL_PORT`  | `6443`                   | Local tunnel port                                    |
| `SSH_KUBECTL_PROXY_REMOTE_ADDR` | *(auto-resolved)*        | K3S API address reachable from jump host             |
| `SSH_KUBECTL_PROXY_REMOTE_PORT` | `6443`                   | K3S API port on the remote side                      |

## Scripts

- `scripts/k8s-connect.sh` — validate cluster connectivity with optional proxy start.
- `scripts/k8s-analyze.sh` — run structured analysis queries and emit YAML summary.
- `scripts/k8s-proxy.sh` — SSH tunnel lifecycle management (start/stop/wait).

## Usage Examples

```bash
# Local cluster connectivity check
.github/skills/k8s-expert/scripts/k8s-connect.sh

# Remote cluster via SSH proxy
SSH_KUBECTL_PROXY_HOST=jump.example.com \
SSH_KUBECTL_PROXY_USER=pi \
SSH_KUBECTL_PROXY_REMOTE_ADDR=192.168.1.100 \
  .github/skills/k8s-expert/scripts/k8s-connect.sh

# Full cluster analysis
.github/skills/k8s-expert/scripts/k8s-analyze.sh
```
