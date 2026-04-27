---
name: shared/runtime
description: Consolidated runtime facade in shared namespace.
layer: digital-generic-team
---

# Skill: shared/runtime

## Purpose
Canonical shared namespace entrypoint for .

## Information Flow
- producer: prompts, scripts, hooks, or make targets
- consumer: shared/runtime wrappers
- trigger: shared capability invocation
- payload summary: delegated command execution to legacy implementation

## Delegation
This skill delegates to the temporary compatibility alias:
- ".github/skills/shared/runtime/"

## Migration Note
This wrapper exists for Phase 2 namespace convergence. Legacy aliases stay
available until all direct callers are migrated.
