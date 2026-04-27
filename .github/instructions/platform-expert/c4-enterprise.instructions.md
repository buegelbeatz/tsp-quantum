---
name: "Platform-architect / C4-enterprises"
description: "C4 Enterprise Architecture Instructions"
layer: digital-generic-team
---
# C4 Enterprise Architecture Instructions


Use this instruction when creating enterprise-ready C4 documentation aligned with operational and governance needs.

## Scope

Produce and maintain C4 levels in `docs/uml/c4/`:

- `system-context.puml` (L1)
- `container.puml` (L2)
- `component-<service>.puml` (L3)
- `code-<domain>.puml` (L4, optional for complex domains)
- `enterprise-landscape.puml` (cross-system enterprise context)

## Mandatory Enterprise Additions

In addition to classic C4 levels, include:

1. Trust boundaries
2. Identity providers and auth domains
3. Data classification boundaries
4. Critical external dependencies
5. Ownership mapping per container/component
6. Deployment footprint reference to runtime topology

## File and Naming Rules

- Keep one concern per file.
- Use stable names to avoid unnecessary documentation churn.
- Store source diagrams only (`.puml`) under `docs/uml/c4/`.
- Rendered files are generated SVG files under `docs/images/uml/c4/`.

## Diagram Quality Rules

- Keep relationships directional and named.
- Use consistent tags for actors, systems, containers, and components.
- Avoid duplicating full details between levels.
- L2 must be a refinement of L1; L3 of L2.

## Security and Compliance View

For enterprise systems, every L2+ diagram must document:

- authentication path
- authorization enforcement points
- sensitive data flows
- logging/audit sinks
- internet-facing surfaces

## Update Policy

Refresh C4 diagrams when:

- adding/removing services
- changing major interfaces
- changing trust boundaries
- introducing new external dependencies

## Automation Policy

- Diagram rendering is automated via make targets.
- Never commit manually exported images.
- Use hash-based incremental rendering to avoid full redraws.

## Review Checklist

Before merge, confirm:

- all references still exist in code/spec docs
- ownership and responsibilities are current
- security boundaries are visible
- diagrams render successfully to SVG
