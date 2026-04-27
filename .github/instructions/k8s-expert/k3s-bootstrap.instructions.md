---
name: "K3S Bootstrap"
description: "Bootstrap guidance for K3S clusters on Raspberry Pi and fresh AMD64 hosts."
layer: digital-generic-team
---
# K3S Bootstrap (Raspberry Pi and Fresh AMD64)

## Scope

Guidance to bootstrap a K3S cluster from scratch on Linux hosts for two primary profiles:
- Raspberry Pi edge cluster (ARM64), aligned with existing home-lab references.
- Fresh AMD64 host (16 GB RAM / 256 GB SSD baseline), suitable as single-node control plane or first server node.

## Host Profiles

### Profile A — Raspberry Pi Control Plane / Edge Node
- Architecture: ARM64 (`aarch64`)
- OS: Raspberry Pi OS 64-bit or Ubuntu Server ARM64
- Storage: SSD strongly preferred over SD card for control-plane reliability
- Recommended: disable swap, static IP, NTP enabled

### Profile B — Fresh AMD64 Host (Reference Baseline)
- Architecture: x86_64 / AMD64
- Minimum: 4 vCPU, 16 GB RAM, 256 GB SSD
- OS: Ubuntu 22.04+ / Debian 12+
- Disk layout recommendation:
  - `/var/lib/rancher/k3s` on SSD
  - Optional dedicated volume for PVs (e.g. `/data/k3s`)

## Preflight Checklist

- SSH access with sudo privileges.
- Inbound network open:
  - `6443/tcp` (Kubernetes API)
  - `8472/udp` (Flannel VXLAN, if multi-node)
  - `10250/tcp` (kubelet)
  - `30000-32767/tcp` (NodePort, if used)
- Required tools: `curl`, `iptables`, `systemd`, `bash`.
- Time sync enabled (`timedatectl status`).

## Bootstrap Flow

### 1. Install First Server (Control Plane)

```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_EXEC="server --disable traefik" \
  sh -
```

Optional hardened server flags:
- `--write-kubeconfig-mode 640`
- `--tls-san <api-fqdn-or-ip>`
- `--disable servicelb` (when external LB is used)

### 2. Capture Join Token

```bash
sudo cat /var/lib/rancher/k3s/server/token
```

### 3. Join Additional Agent Nodes

```bash
curl -sfL https://get.k3s.io | \
  K3S_URL="https://<server-ip>:6443" \
  K3S_TOKEN="<token>" \
  sh -
```

### 4. Verify Cluster

```bash
sudo kubectl get nodes -o wide
sudo kubectl get pods -A
```

## Post-Install Baseline

- Install ingress controller (if Traefik disabled):
  `ingress-nginx` or HAProxy ingress strategy.
- Install metrics stack (`metrics-server`) for `kubectl top`.
- Configure persistent storage:
  - Local path provisioner (default)
  - NFS provisioner for shared stateful workloads
- Store manifests in version control and apply declaratively.

## AMD64 Single-Node Opinionated Setup

For a fresh AMD64 machine, recommended first rollout:
1. Install K3S server with `--disable traefik`.
2. Install ingress-nginx.
3. Install metrics-server.
4. Create namespaces (`core`, `iot`, `observability`).
5. Deploy stateful workloads with explicit PVC sizing.
6. Enable periodic backup of `/var/lib/rancher/k3s/server/db`.

## Raspberry Pi Notes

- Prefer external SSD boot for better etcd/sqlite durability.
- Keep thermal throttling under control (active cooling).
- Set `vm.swappiness=1` and disable swap in production edge clusters.
- Avoid high write amplification workloads on SD cards.

## Security Baseline

- Never expose `6443` publicly without VPN or network restrictions.
- Use SSH jump-host + proxy when remote API access is required.
- Avoid `--insecure-skip-tls-verify` except temporary local diagnostics.
- Rotate join tokens if leaked.

## Validation Checklist

```text
[ ] kubectl cluster-info succeeds
[ ] all nodes Ready
[ ] kube-system pods healthy
[ ] ingress controller available
[ ] persistent volume workflow validated
[ ] backup/restore procedure documented
```
