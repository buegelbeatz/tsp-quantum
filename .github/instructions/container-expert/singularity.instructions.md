---
name: "Container-expert / Singularitys"
description: "Enterprise Specification: Singularity / Apptainer Container Standard"
layer: digital-generic-team
---
# Enterprise Specification: Singularity / Apptainer Container Standard

## 1. Purpose

This document defines the enterprise standard for using Singularity / Apptainer for local container execution, local orchestration patterns, image generation, and registry integration.

The objective is to ensure:

- Controlled use of HPC- and research-oriented containers
- Reproducible scientific and technical workloads
- Standardized image generation and transport
- Secure integration with approved registries and remote endpoints
- Governance for hybrid OCI and SIF-based workflows

---

## 2. Scope

This specification applies to:

- Workstations using Singularity / Apptainer
- Research and compute-heavy developer environments
- HPC-adjacent container workflows
- Teams requiring SIF-based runtime artifacts

---

## 3. Technology Standard

Singularity / Apptainer is an approved container technology for specialized workloads, especially where SIF-based packaging, reproducibility, or HPC execution models are required.

---

## 4. Local Setup Standard

### 4.1 Installation

Apptainer MUST be installed using approved enterprise package sources and documented installation methods.

### 4.2 Local Configuration

The local setup MUST include:

- Approved remote endpoint configuration where required
- Registry and key trust settings where applicable
- Standardized cache and storage configuration
- Clear user guidance for OCI versus SIF workflows

### 4.3 Security Baseline

- Remote credentials MUST be stored using approved methods
- Sensitive keys and tokens MUST NOT be embedded in definition files
- Trusted sources MUST be used for all imported base artifacts

---

## 5. Local Orchestration Standard

### 5.1 Orchestration Model

Singularity / Apptainer is not the primary enterprise tool for general-purpose multi-service local orchestration.

### 5.2 Approved Local Patterns

Approved local execution patterns include:

- Single-container execution for scientific or batch workloads
- Scripted multi-container coordination where required
- Integration with scheduler or workflow tooling in specialized environments
- Controlled composition with external local tooling when necessary

### 5.3 Usage Boundary

For general-purpose microservice orchestration, Docker or Podman SHOULD be preferred unless a documented exception exists.

---

## 6. Image Generation Standard

### 6.1 Build Source

Images MUST be generated from version-controlled definition files or approved build sources.

### 6.2 Build Requirements

Apptainer images MUST:

- Be traceable to source definitions
- Use approved upstream bases
- Prefer reproducible build inputs
- Distinguish clearly between OCI source images and final SIF deliverables

### 6.3 Artifact Format

Teams MUST define whether the authoritative artifact is:

- A SIF image
- An OCI image reference
- Both, for interoperability workflows

### 6.4 Tagging and Naming

Artifacts MUST follow standardized naming and versioning conventions consistent with enterprise release governance.

---

## 7. Registry and Remote Endpoint Integration Standard

### 7.1 Approved Integration Targets

Apptainer MAY integrate with:

- OCI registries
- Approved library endpoints
- Enterprise-approved image distribution services
- Keyserver and signature infrastructure where applicable

### 7.2 Authentication

Authentication MUST use approved credential storage and token handling practices.

### 7.3 Provenance

Imported base images and produced runtime artifacts MUST be traceable to their source and version.

---

## 8. Operational Standards

### 8.1 Reproducibility

Build definitions, source references, and output artifact versions MUST be preserved.

### 8.2 Portability

Workloads SHOULD be portable across approved environments where technically feasible.

### 8.3 Documentation

Each project using Singularity / Apptainer MUST document:

- Image source
- Build process
- Runtime assumptions
- Registry or library dependencies

---

## 9. Compliance Requirements

- Definition files MUST be version controlled
- Approved sources MUST be used
- Artifact provenance MUST be recorded
- Security and signing requirements MUST be followed where mandated

---

## 10. Governance

This standard is owned by platform engineering in collaboration with research or compute platform stakeholders.

Exceptions MUST be documented and approved.

---

## 11. Summary

This standard ensures governed use of Singularity / Apptainer for reproducible, specialized, and HPC-oriented container workflows, including local setup, image generation, and registry integration.