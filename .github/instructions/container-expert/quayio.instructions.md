---
name: "Container-expert / Quayios"
description: "Enterprise Specification: Quay.io Registry Standard"
layer: digital-generic-team
---
# Enterprise Specification: Quay.io Registry Standard

## 1. Purpose

This document defines the enterprise standard for using Quay.io as a hosted container and OCI artifact registry.

The objective is to ensure:

- Controlled publication and distribution of images
- Strong repository and namespace governance
- Secure push and pull workflows
- Support for enterprise and multi-team registry operations

---

## 2. Scope

This specification applies to:

- Teams publishing images to Quay.io
- Teams consuming images from Quay.io
- CI/CD systems using Quay-based artifact workflows
- Projects using Quay.io for OCI distribution

---

## 3. Registry Role

Quay.io is an approved registry for:

- Hosting container images
- Storing OCI artifacts
- Team-oriented namespace and repository management
- External and internal distribution where approved

---

## 4. Repository Governance

### 4.1 Namespace Standard

Repositories MUST be created under approved user or organizational namespaces.

### 4.2 Ownership

Each repository MUST have an accountable owner and defined maintainers.

### 4.3 Access Model

Read and write permissions MUST be role-based and aligned with the principle of least privilege.

---

## 5. Authentication and Access Control

- Authentication MUST use approved credentials, tokens, or robot/service accounts where supported
- CI/CD pipelines SHOULD use non-human credentials
- Push rights MUST be restricted to authorized publishers

---

## 6. Image Publication Standard

### 6.1 Push Requirements

Published artifacts MUST:

- Use explicit tags
- Be traceable to version-controlled source
- Follow enterprise naming conventions
- Comply with image signing and scanning policies where mandated

### 6.2 Tagging

Tags MUST follow enterprise release and traceability standards.

### 6.3 Repository Structure

Repositories SHOULD reflect product, service, or platform ownership boundaries.

---

## 7. Image Consumption Standard

- Consumers SHOULD pin versions or digests
- Public consumption MUST be intentionally approved
- Pull access for private repositories MUST be centrally governed

---

## 8. Security Requirements

- Secrets MUST NOT be embedded in images
- Permissions MUST be periodically reviewed
- Registry usage MUST align with data classification and supply chain policy

---

## 9. Operational Requirements

- Repository lifecycle policies SHOULD be defined
- Deprecated tags SHOULD be cleaned up or clearly marked
- Automation hooks and build integrations MUST be documented where used

---

## 10. Governance

Quay.io usage is governed by platform engineering and security governance.

Exceptions MUST be documented and approved.

---

## 11. Summary

This standard ensures secure, governed, and enterprise-scalable use of Quay.io for container and OCI artifact distribution.