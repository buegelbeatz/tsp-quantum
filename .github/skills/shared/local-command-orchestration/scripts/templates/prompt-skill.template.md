---
name: prompt-__PROMPT_NAME__
description: "__PROMPT_PURPOSE__"
layer: digital-generic-team
---

# Skill: Prompt __PROMPT_NAME__

## Purpose

Support the `/__PROMPT_NAME__` prompt with deterministic command orchestration and governance checks.

## Outputs

- Prompt execution guidance
- Deterministic command examples
- Structured progress markers when needed

## Dependencies

- .github/skills/shared/local-command-orchestration/SKILL.md

## Information Flow

- Producer: prompt runtime and participating agents.
- Consumer: downstream role agents, reviewers, and governance/audit readers.
- Trigger: skill invocation, agent handoff boundaries, and completion handoff.
- Payload summary: normalized inputs, execution decisions, status updates, and output artifact references.
