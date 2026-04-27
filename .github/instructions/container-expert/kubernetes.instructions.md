---
name: "Container-expert / Kubernetess"
description: "Enterprise Specification: Kubernetes Platform Standard"
layer: digital-generic-team
---
# Enterprise Specification: Kubernetes Platform Standard

## 1. Purpose

This document defines the enterprise standard for Kubernetes infrastructure, manifest specifications, command-line operations, and workload governance.

The objective is to ensure:

- Standardized cluster and workload design
- Consistent use of Kubernetes YAML manifests
- Secure and governed platform operations
- Predictable deployment and runtime behavior
- Alignment between development, platform engineering, and operations

---

## 2. Scope

This specification applies to:

- All enterprise Kubernetes clusters
- Platform engineering teams
- Application teams deploying to Kubernetes
- CI/CD pipelines managing Kubernetes workloads
- Operators using `kubectl` and Kubernetes manifests

---

## 3. Platform Standard

Kubernetes is the approved enterprise orchestration platform for containerized workloads requiring clustered deployment, scaling, service abstraction, and declarative operations.

---

## 4. Infrastructure Standard

### 4.1 Cluster Ownership

Each cluster MUST have:

- A defined owner
- An operational support model
- A lifecycle policy
- Environment classification, such as development, staging, or production

### 4.2 Environment Segmentation

Workloads MUST be segmented by environment using approved isolation patterns, such as:

- Separate clusters
- Separate namespaces
- Separate network and policy boundaries

### 4.3 Node and Runtime Baseline

Cluster nodes MUST use approved operating system and runtime baselines maintained by platform engineering.

---

## 5. Kubernetes Object Standard

### 5.1 Declarative Resource Model

Kubernetes resources MUST be managed declaratively wherever practical.

### 5.2 Approved Core Objects

Common approved objects include:

- Namespace
- Deployment
- StatefulSet
- DaemonSet
- Service
- Ingress or Gateway resources
- ConfigMap
- Secret
- Job
- CronJob
- PersistentVolumeClaim

### 5.3 Namespace Governance

Namespaces MUST be used to establish logical ownership, policy boundaries, and workload grouping.

---

## 6. YAML Manifest Standard

### 6.1 Source Control

All Kubernetes YAML manifests MUST be stored in version control.

### 6.2 Manifest Requirements

Each manifest MUST define:

- `apiVersion`
- `kind`
- `metadata`
- `spec`

Labels and annotations SHOULD be applied consistently for ownership, traceability, and automation.

### 6.3 Configuration Standards

Manifests MUST:

- Avoid hardcoded secrets
- Externalize configuration into appropriate resources
- Use explicit image references
- Include resource requests and limits where mandated
- Define probes where workload behavior requires them

### 6.4 Reusability

Manifest reuse SHOULD be implemented via approved templating or packaging approaches, such as:

- Kustomize
- Helm
- Platform-approved internal generators

---

## 7. kubectl Standard

### 7.1 Approved CLI Usage

`kubectl` is the standard command-line tool for interacting with Kubernetes clusters.

### 7.2 Operational Controls

Use of `kubectl` in production MUST be governed by:

- Role-based access control
- Approved kubeconfig handling
- Audit and accountability requirements
- Change management expectations where applicable

### 7.3 Usage Expectations

Operators SHOULD prefer:

- Declarative apply-based workflows
- Least-privilege contexts
- Read-only inspection for routine diagnostics where possible

Imperative ad hoc changes in controlled environments SHOULD be minimized.

---

## 8. Workload Deployment Standard

### 8.1 Stateless Workloads

Stateless services SHOULD use Deployment-based patterns unless another controller is clearly required.

### 8.2 Stateful Workloads

Stateful workloads MUST use appropriate state-aware Kubernetes resources and approved storage classes.

### 8.3 Batch Workloads

One-time and scheduled batch workloads SHOULD use Job and CronJob resources.

---

## 9. Networking Standard

### 9.1 Service Exposure

Workloads MUST use approved service exposure patterns, such as:

- Cluster-internal Services
- Ingress or Gateway-based north-south access
- Controlled load balancer usage where approved

### 9.2 Network Policy

Sensitive namespaces and workloads SHOULD use network policy controls to restrict traffic.

---

## 10. Configuration and Secrets Standard

### 10.1 ConfigMap Usage

Non-sensitive runtime configuration SHOULD be stored in ConfigMaps.

### 10.2 Secret Usage

Sensitive values MUST be stored using approved secret mechanisms and MUST NOT be committed to source control in plaintext.

### 10.3 External Secret Integration

Where enterprise secret platforms exist, Kubernetes integrations SHOULD be preferred over static secret definitions.

---

## 11. Image Standard

### 11.1 Registry Usage

Workloads MUST pull images from approved registries only.

### 11.2 Image Referencing

Images SHOULD be pinned to explicit versions and MAY be pinned by digest in higher-control environments.

### 11.3 Provenance

Image provenance and ownership MUST be traceable.

---

## 12. Observability Standard

### 12.1 Logging

Applications SHOULD write logs to standard output streams unless a documented exception exists.

### 12.2 Metrics

Critical workloads SHOULD expose metrics compatible with the enterprise observability platform.

### 12.3 Health Signals

Readiness and liveness mechanisms SHOULD be used where they improve resilience and operational clarity.

---

## 13. Security Standard

### 13.1 Access Control

Cluster access MUST use role-based access control and enterprise identity integration where available.

### 13.2 Pod Security

Workloads MUST comply with enterprise pod security requirements.

### 13.3 Supply Chain Controls

Images, manifests, and deployment pipelines MUST comply with enterprise software supply chain controls.

---

## 14. CI/CD and Change Management

### 14.1 Deployment Automation

Cluster changes SHOULD be applied through approved automation pipelines wherever practical.

### 14.2 Drift Control

Manual changes to controlled environments SHOULD be minimized and reconciled back to source definitions.

### 14.3 Promotion

Promotion across environments MUST follow approved release and approval processes.

---

## 15. Compliance Requirements

- Kubernetes resources MUST be version controlled
- Production access MUST be governed
- Secrets MUST be handled through approved mechanisms
- Approved registries and namespaces MUST be used
- Platform standards MUST be enforced through review and automation

---

## 16. Governance

This standard is owned by platform engineering, with security, operations, and architecture governance participation.

Exceptions MUST be documented, risk-assessed, and approved.

---

## 17. Summary

This standard ensures consistent, secure, and scalable enterprise use of Kubernetes across infrastructure, YAML specifications, `kubectl` operations, and workload lifecycle management.