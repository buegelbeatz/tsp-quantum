---
name: shared/local-command-orchestration
description: Local command orchestration backend in shared namespace.
layer: digital-generic-team
---

# Skill: shared/local-command-orchestration

## Purpose
Canonical shared namespace entrypoint for .

## Information Flow
- producer: prompts, scripts, hooks, or make targets
- consumer: shared/local-command-orchestration wrappers
- trigger: shared capability invocation
- payload summary: delegated command execution to legacy implementation

## Delegation
This skill delegates to the temporary compatibility alias:
- ".github/skills/shared/local-command-orchestration/"

## Migration Note
This wrapper exists for Phase 2 namespace convergence. Legacy aliases stay
available until all direct callers are migrated.
