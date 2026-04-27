---
name: container-publish
description: Governed GHCR image publishing with documentation bundle support for delivery agents.
layer: digital-generic-team
---

# Skill: container-publish

Provide a governed implementation path for building OCI images, publishing them to GitHub Container Registry, and publishing a synchronized documentation bundle to GHCR.

## Use When

- A delivery ticket requires a repository-owned container image.
- The image must be built in GitHub Actions instead of unmanaged local pushes.
- Documentation should be published alongside the image as a registry artifact.

## Capabilities

- Respect explicit opt-in via `enabled: true` in `.digital-team/container-publish.yaml`.
- Validate `.digital-team/container-publish.yaml`.
- Resolve image build metadata for GitHub Actions matrices.
- Package configured documentation files into a deterministic tar.gz bundle.
- Support GHCR image publication and a paired `-docs` artifact repository.

## Scripts

- `scripts/container_publish.py`

## Dependencies

- `../generic-deliver`
- `../shared/shell`

## Information Flow

- Producer: `fullstack-engineer` via `generic-deliver`
- Consumer: GitHub Actions workflow `.github/workflows/container-publish.yml`
- Trigger: Delivery change introduces or updates `.digital-team/container-publish.yaml`
- Payload summary: Image refs, build context, Dockerfile path, platform list, description, docs source files