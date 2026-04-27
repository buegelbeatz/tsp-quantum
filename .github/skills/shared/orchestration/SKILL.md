---
name: shared/orchestration
description: Consolidated orchestration facade in shared namespace.
layer: digital-generic-team
---

# Skill: shared/orchestration

## Purpose
Canonical shared namespace entrypoint for .

## Information Flow
- producer: prompts, scripts, hooks, or make targets
- consumer: shared/orchestration wrappers
- trigger: shared capability invocation
- payload summary: delegated command execution to legacy implementation

## Delegation
This skill delegates to the temporary compatibility alias:
- ".github/skills/shared/orchestration/"

## Migration Note
This wrapper exists for Phase 2 namespace convergence. Legacy aliases stay
available until all direct callers are migrated.
