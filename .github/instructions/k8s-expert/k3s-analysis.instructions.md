---
name: "K3S Cluster Analysis"
description: "Operational guidance for analyzing a K3S Kubernetes cluster via kubectl — both locally and tunneled through an SSH proxy."
layer: digital-generic-team
---
# K3S Cluster Analysis — Local and Remote (SSH Proxy)

## Scope

Operational guidance for analyzing a K3S Kubernetes cluster via `kubectl` — both locally and tunneled through an SSH proxy. Covers cluster health inspection, workload analysis, namespace review, resource constraints, and diagnostics.

## Prerequisites

- `kubectl` installed and on `PATH`.
- Either:
  - Local kubeconfig (`~/.kube/config` or `KUBECONFIG` env var) pointing to the K3S API server, **or**
  - SSH access to a jump host with a port-forwarding tunnel to the K3S API (see SSH Proxy section below).

## Local Connection

### Check Active Context

```bash
kubectl config current-context
kubectl config get-contexts
kubectl cluster-info
```

### Environment Variables (Local)

| Variable     | Example          | Description                            |
|--------------|------------------|----------------------------------------|
| `KUBECONFIG` | `~/.kube/config` | Path to kubeconfig; supports colon-separated list |

---

## Remote Connection via SSH Proxy

K3S clusters on private networks (e.g. Raspberry Pi clusters, home-lab, remote edge nodes) are typically not directly reachable. Use an SSH port-forward to create a local tunnel.

### Setup Pattern

```bash
# Start SSH tunnel in background
ssh -N \
  -L "${LOCAL_PORT}:${K3S_API_HOST}:${K3S_API_PORT}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  "${SSH_USER}@${SSH_JUMP_HOST}" &
TUNNEL_PID=$!
trap 'kill $TUNNEL_PID 2>/dev/null || true' EXIT

# Wait for tunnel to be ready
for _ in $(seq 1 20); do
  nc -z 127.0.0.1 "$LOCAL_PORT" 2>/dev/null && break
  sleep 0.5
done

# Use kubectl with overridden server
kubectl \
  --server "https://127.0.0.1:${LOCAL_PORT}" \
  --tls-server-name "${K3S_API_HOST}" \
  cluster-info
```

### Environment Variables (SSH Proxy)

| Variable                        | Example              | Description                                     |
|---------------------------------|----------------------|-------------------------------------------------|
| `SSH_KUBECTL_PROXY_HOST`        | `jump.example.com`   | Jump-host FQDN or IP                           |
| `SSH_KUBECTL_PROXY_USER`        | `pi`                 | SSH username on jump host                      |
| `SSH_KUBECTL_PROXY_PORT`        | `22`                 | SSH port (default 22)                          |
| `SSH_KUBECTL_PROXY_LOCAL_PORT`  | `6443`               | Local TCP port for the tunnel                  |
| `SSH_KUBECTL_PROXY_REMOTE_ADDR` | `192.168.1.100`      | K3S API server address (from jump host's POV)  |
| `SSH_KUBECTL_PROXY_REMOTE_PORT` | `6443`               | K3S API server port                            |
| `KUBECTL_SERVER`                | `https://127.0.0.1:6443` | Override for `--server` flag                |
| `KUBECTL_TLS_SERVER_NAME`       | `192.168.1.100`      | TLS SNI override to match cluster certificate  |
| `KUBECTL_INSECURE_SKIP_VERIFY`  | `false`              | Set `true` only for temporary local-only debugging; never in CI |
| `KUBECONFIG_PROXY_PATH`         | `.data/kubeconfig-proxy` | Rewritten kubeconfig with proxied server URL |

> **Security note:** `KUBECTL_INSECURE_SKIP_VERIFY=true` disables TLS verification and must never be used in production or CI pipelines. Prefer `KUBECTL_TLS_SERVER_NAME` with a valid certificate instead.

---

## Cluster Health Analysis

### Node Status

```bash
kubectl get nodes -o wide
kubectl describe nodes
```

### Component Status

```bash
kubectl get componentstatuses 2>/dev/null || kubectl get --raw /healthz
kubectl get pods -n kube-system
```

### Resource Pressure

```bash
kubectl top nodes
kubectl top pods -A --sort-by=memory
```

### Events (Cluster-wide)

```bash
kubectl get events -A --sort-by='.lastTimestamp' | tail -40
```

---

## Workload Analysis

### Overview

```bash
kubectl get all -A
kubectl get deployments -A
kubectl get statefulsets -A
kubectl get daemonsets -A
```

### Failing Pods

```bash
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
kubectl get pods -A | grep -v Running | grep -v Completed
```

### Pod Logs

```bash
kubectl logs -n <namespace> <pod> --tail=100
kubectl logs -n <namespace> <pod> --previous   # crashed container
```

---

## Storage Analysis

```bash
kubectl get pv
kubectl get pvc -A
kubectl get storageclass
```

---

## Network Analysis

```bash
kubectl get services -A
kubectl get ingress -A
kubectl get endpoints -A
```

---

## K3S-Specific Considerations

- K3S uses a single-binary architecture; the API server, scheduler, controller-manager, and kubelet are embedded.
- Default kubeconfig is at `/etc/rancher/k3s/k3s.yaml` (root-owned on the K3S node).
- K3S uses `containerd` (not Docker) as container runtime.
- Built-in Traefik ingress controller in default K3S installs (check `helm list -n kube-system`).
- Local path provisioner is the default storage class.
- For multi-node K3S clusters, check agent connectivity: `kubectl get nodes`.

---

## Decision Flow

```text
Connect to cluster?
  ├─> Local kubeconfig available?
  │     └─> kubectl cluster-info                  → proceed with analysis
  └─> Remote / private network?
        └─> SSH tunnel available?
              ├─> Yes → start SSH proxy → kubectl --server https://127.0.0.1:LOCAL_PORT
              └─> No  → request SSH credentials or VPN access from operator
```
