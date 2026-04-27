---
name: shared/pr-delivery
description: PR delivery backend in shared namespace.
layer: digital-generic-team
---

# Skill: shared/pr-delivery

## Purpose
Canonical shared namespace entrypoint for .

## Information Flow
- producer: prompts, scripts, hooks, or make targets
- consumer: shared/pr-delivery wrappers
- trigger: shared capability invocation
- payload summary: delegated command execution to legacy implementation

## Delegation
This skill delegates to the temporary compatibility alias:
- ".github/skills/shared/pr-delivery/"

## Migration Note
This wrapper exists for Phase 2 namespace convergence. Legacy aliases stay
available until all direct callers are migrated.
