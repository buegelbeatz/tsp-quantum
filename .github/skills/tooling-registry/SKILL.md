---
name: tooling-registry
description: Manage artifact versioning, release tracking, and reproducible build outputs.
layer: digital-generic-team
---

# Skill: Tooling Registry

This skill provides version-controlled artifact management for releases and build outputs.

Scope clarification:

- `tooling-registry` manages metadata and release registration for generated skill/tool artifacts.
- `artifacts` manages the `.digital-artifacts/` workspace structure and operational content lifecycle.

## Registry Model

- **Metadata CSV** — Registry of authored artifacts with version, format, and location.
- **Release Scripts** — Tag, version, and publish artifacts to approved registries.
- **Verification** — Validate artifact integrity and reproducibility.

## Scripts

- `scripts/artifact-register.sh`
- `scripts/artifact-verify.sh`
- `scripts/artifact-release.sh`

## Metadata

Registry file: `metadata/artifacts.csv`

Format:
```
artifact_name,artifact_type,version,location,format,created_at,verified
skill-generic-deliver,shell,1.0.0,.../generic-deliver/scripts,sh,2026-03-25T00:00:00Z,yes
```
