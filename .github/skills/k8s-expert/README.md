---
layer: digital-generic-team
---
# k8s-expert

Analyze a local or remote K3S Kubernetes cluster via kubectl, with optional SSH proxy tunnel support.

## Purpose

Provide the capabilities documented in `SKILL.md`.

## Usage

```bash
# Check connectivity (local)
.github/skills/k8s-expert/scripts/k8s-connect.sh

# Check connectivity (remote SSH proxy)
SSH_KUBECTL_PROXY_HOST=jump.host \
SSH_KUBECTL_PROXY_USER=pi \
SSH_KUBECTL_PROXY_REMOTE_ADDR=192.168.1.100 \
  .github/skills/k8s-expert/scripts/k8s-connect.sh

# Run cluster analysis
.github/skills/k8s-expert/scripts/k8s-analyze.sh
```

## Scripts

- `k8s-connect.sh` — validate cluster connectivity.
- `k8s-analyze.sh` — collect cluster status summary.
- `k8s-proxy.sh` — SSH tunnel lifecycle helpers.
