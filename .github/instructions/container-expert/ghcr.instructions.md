---
name: "Container-expert / Ghcrs"
description: "Enterprise Specification: GitHub Container Registry Standard"
layer: digital-generic-team
---
# Enterprise Specification: GitHub Container Registry Standard

## 1. Purpose

This document defines the enterprise standard for using GitHub Container Registry (GHCR) for storing and distributing container images.

The objective is to ensure:

- Strong alignment with source repositories
- Controlled image permissions
- CI/CD-friendly publication workflows
- Traceable image ownership and lifecycle management

---

## 2. Scope

This specification applies to:

- Teams publishing images to GHCR
- Teams consuming images from GHCR
- GitHub-based CI/CD workflows
- Organizations requiring repository-linked container artifacts

---

## 3. Registry Role

GHCR is an approved registry for:

- OCI and Docker-compatible image storage
- Repository-associated image publication
- Private and public image distribution
- GitHub-native automation workflows

---

## 4. Repository and Package Governance

### 4.1 Ownership Model

Images MUST be associated with approved accounts or organizations.

### 4.2 Repository Association

Where applicable, container packages SHOULD be linked to the corresponding source repository for traceability.

### 4.3 Visibility and Permissions

Visibility MUST be explicitly defined.

Permissions SHOULD follow the least-privilege principle and, where beneficial, inherit from repository governance.

---

## 5. Authentication and Access Control

- Authentication MUST use approved GitHub tokens or enterprise credentials
- CI workflows SHOULD use repository- or organization-scoped automation credentials
- Package administration MUST be limited to authorized maintainers

---

## 6. Image Publication Standard

### 6.1 Source of Truth

Published images MUST originate from version-controlled repositories.

### 6.2 Build and Publish Workflow

Publication SHOULD occur through governed automation, such as CI/CD pipelines, rather than unmanaged manual pushes.

The reference implementation in this layer uses `.github/workflows/container-publish.yml` plus `.digital-team/container-publish.yaml` as the governed source of truth.

### 6.3 Tagging

Images MUST use explicit, traceable tags including version and build-identifying metadata where required.

---

## 7. Image Consumption Standard

- Consumers SHOULD reference explicit tags or digests
- Internal enterprise workloads SHOULD prefer private GHCR images where repository integration is advantageous
- Public images MUST be intentionally designated as public

---

## 8. Security Requirements

- Secrets MUST NOT be embedded in images
- Access tokens MUST be scoped appropriately
- Package visibility MUST align with data classification and release policy

---

## 9. Operational Requirements

- Package retention and cleanup policies SHOULD be defined
- Ownership transfer and archival processes MUST be documented
- Repository-package linkage SHOULD be maintained for auditability
- Where image documentation must be discoverable in the registry, teams SHOULD publish a paired OCI docs artifact such as `<image>-docs` from the same workflow run.

---

## 10. Governance

GHCR usage is governed by platform engineering in collaboration with source control administration and security governance.

Exceptions MUST be documented and approved.

---

## 11. Summary

This standard ensures secure, traceable, and repository-aligned enterprise use of GitHub Container Registry.