---
name: "Container-expert / Podmans"
description: "Enterprise Specification: Podman Container Standard"
layer: digital-generic-team
---
# Enterprise Specification: Podman Container Standard

## 1. Purpose

This document defines the enterprise standard for using Podman for local container development, local orchestration, image generation, and registry integration.

The objective is to ensure:

- Daemonless and standards-aligned container workflows
- Secure local execution patterns
- Reproducible builds and runtime behavior
- Controlled access to approved image registries
- Compatibility with Kubernetes-oriented workflows where applicable

---

## 2. Scope

This specification applies to:

- Developer workstations using Podman
- Local test and integration environments
- OCI image build workflows
- Teams requiring rootless container operation

---

## 3. Technology Standard

Podman is an approved container engine for local development and image lifecycle operations.

Approved related tooling includes:

- Podman CLI
- Podman Desktop, where approved
- Podman pods
- `podman kube play` for local Kubernetes-YAML-based execution
- Quadlet for declarative systemd-based local service orchestration

---

## 4. Local Setup Standard

### 4.1 Installation

Podman MUST be installed using approved enterprise package and workstation management processes.

### 4.2 Runtime Model

Podman SHOULD be used in rootless mode unless a documented exception exists.

### 4.3 Local Configuration

The local setup MUST include:

- Access to approved registries
- Central trust and certificate configuration
- Standard network and storage configuration
- Optional Podman Desktop where GUI support is required

---

## 5. Local Orchestration Standard

### 5.1 Approved Local Orchestration Options

Approved local orchestration options include:

- Podman pods
- `podman kube play` for structured Kubernetes-style manifests
- Quadlet for systemd-managed local container services

### 5.2 Orchestration Requirements

Local orchestration definitions MUST:

- Be stored in version control
- Use explicit image references
- Avoid embedding secrets in source-controlled files
- Separate runtime configuration from image definition

### 5.3 Service Lifecycle

Local services SHOULD support:

- Predictable startup order where required
- Simple teardown and recreation
- Persistent storage definition where applicable
- Health-aware testing patterns where practical

---

## 6. Image Generation Standard

### 6.1 Build Source

Images MUST be built from version-controlled build definitions.

### 6.2 Build Requirements

Podman-generated images MUST:

- Use approved OCI-compatible base images
- Minimize unnecessary packages and layers
- Include image metadata where required
- Be reproducible to the extent practical

### 6.3 Tagging Standard

Images MUST use enterprise tagging conventions, including:

- Semantic versions for release images
- Git-based tags for traceability
- Environment tags only where explicitly governed

---

## 7. Registry Integration Standard

### 7.1 Approved Registry Targets

Podman MAY connect to approved OCI registries such as:

- Docker Hub
- GitHub Container Registry
- Quay.io
- Internal OCI-compliant enterprise registries

### 7.2 Authentication

Authentication MUST use approved registry login methods and enterprise credential policies.

### 7.3 Transport and Trust

- TLS verification MUST remain enabled by default
- Exceptions for insecure registries MUST be centrally approved
- Registry trust configuration MUST be documented

---

## 8. Kubernetes Alignment

Where teams use Kubernetes-adjacent workflows locally, Podman SHOULD prefer:

- Kubernetes-style YAML where beneficial
- Explicit pod definitions
- Clear compatibility boundaries between local Podman execution and cluster deployment

---

## 9. Compliance Requirements

- Rootless mode SHOULD be the default
- Container definitions MUST be version controlled
- Registry usage MUST be limited to approved targets
- Image provenance MUST be traceable

---

## 10. Governance

The platform engineering function owns this standard.

Exceptions MUST be documented, justified, and approved.

---

## 11. Summary

This standard ensures secure, daemonless, and enterprise-governed Podman usage for local setup, orchestration, image generation, and registry integration.