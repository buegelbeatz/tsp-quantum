---
name: "k3s (Lightweight Kubernetes)"
description: "Lightweight Kubernetes baseline for edge and IoT clusters with clear role separation and operational safety controls."
layer: digital-generic-team
---
# k3s (Lightweight Kubernetes)

## Scope
Lightweight Kubernetes baseline for edge and IoT clusters with clear role separation and operational safety controls.

## Golden Cluster Template
```text
control-plane nodes: 1-3
worker nodes: N
stateful workloads: SSD-backed workers only
critical addons: ingress, cert-manager, metrics-server, backup job
```

## Standard Extensions / Add-ons
- `cert-manager` for certificate lifecycle
- `ingress-nginx` or HAProxy ingress
- `longhorn` or NFS-backed PV solution (environment dependent)
- `metrics-server` + Prometheus stack

## Kubernetes Integration Pattern
- Use GitOps (ArgoCD) for all workloads and cluster add-ons.
- Place IoT stateful services (MQTT/InfluxDB) with node affinity and anti-affinity rules.
- Enforce network policies between ingestion, processing, and visualization namespaces.

## References
- k3s docs: https://docs.k3s.io/
- Kubernetes docs: https://kubernetes.io/docs/home/
- cert-manager docs: https://cert-manager.io/docs/