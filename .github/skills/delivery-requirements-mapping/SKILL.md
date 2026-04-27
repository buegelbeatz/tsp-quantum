---
name: "delivery-requirements-mapping"
description: "Derive role-specific technical tasks, dependencies, and verification hooks from prose epics/stories for delivery agents."
layer: digital-generic-team
---

# Skill: Delivery Requirements Mapping

## Purpose
Provide a deterministic translation model from prose requirements to delivery-agent task sets.

## When to Use
- When agile-coach has approved epics and stories but technical tasks are still missing.
- When a delivery handoff contains primarily narrative requirements.
- When delivery agents must clarify ownership boundaries and dependency order.

## Inputs
- Epic and story statements
- Acceptance criteria
- Constraints and assumptions from expert_response_v1
- Existing architecture and platform guidance

## Output Contract
Each mapped task set should include:
- role_owner
- task_title
- technical_scope
- dependencies (internal and external)
- verification_hooks (tests, checks, evidence)
- risks_or_open_questions

## Mapping Heuristics
1. Extract explicit system components and interfaces from prose.
2. Split by delivery ownership boundary (frontend/backend/data/ux/platform).
3. Convert each boundary into an actionable technical task.
4. Attach dependency direction:
   - blocks
   - blocked_by
5. Attach verification requirements tied to acceptance criteria.
6. Flag missing implementation-critical information as open questions.

## Quality Gate
A mapped task set is complete only if:
- every acceptance criterion maps to at least one verification hook,
- each task has a clear owner role,
- cross-role dependencies are explicit,
- unresolved assumptions are listed.

## Information Flow
- producer: agile-coach or generic-deliver handoff context
- consumer: delivery agents (for example fullstack-engineer, data-scientist, ux-designer)
- trigger: post-epic/post-story decomposition step before ticket finalization
- payload summary: prose requirements plus architecture context transformed into technical, role-scoped task sets
