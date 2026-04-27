---
name: "Agile-coach / Project-managements"
description: "Configuration and best practices"
layer: digital-generic-team
---

# Agile Coach Project Management

## Scope

Define governance boundaries for board/wiki information flow and external system synchronization.

## Coordination Protocol

- `agile-coach` is the coordination gateway for board/wiki requests across roles.
- Any non-agile role requiring board/wiki information or updates must submit an `agile_info_exchange_v1` handoff.
- Response payloads from `agile-coach` must include explicit artifacts and completion evidence.

## Milestone and Sprint Preparation

- Planning outputs must carry milestone metadata for each epic/story/task (`milestone_id`, `sprint_hint`).
- Milestone metadata must be deterministic and traceable to stage and theme identifiers.
- Sprint planning can refine milestones later, but project planning must pre-structure this data.

## Source-of-Truth Rules

- Board source-of-truth: `refs/board/*`.
- Wiki source-of-truth: `docs/wiki/`.
- External systems (GitHub, later Atlassian) are synchronization targets, not primary local source unless configured as primary system policy.

## Git and Delivery Boundary

- `agile-coach` defines policy and acceptance for board/wiki orchestration.
- Generic deliver agents execute git mutations and implementation-level repository operations.

## Provider Abstraction Requirement

- Project management workflows must use a provider abstraction so backend platforms can vary per layer.
- Keep command and handoff semantics stable while swapping implementations (GitHub, Atlassian, others).

## Role-Specific Requirement Contracts

Planning outputs must include role-specific requirement contracts before tickets can be synchronized to board/issues.

### Engineer Task Contract

- Functional requirements: explicit behavior, input/output, error handling.
- Non-functional requirements: security, performance, observability.
- Acceptance criteria: business outcome, failure handling, regression protection.
- Verification evidence: automated tests mapped to acceptance criteria.

### UX Designer Task Contract

- User outcome: target segment/persona and journey scenario.
- Interaction requirements: wireframe/prototype scope and navigation assumptions.
- Accessibility requirements: WCAG 2.2 AA checks for relevant interactions.
- Validation plan: method, sample size, completion metric, handoff evidence.

### Agile-Coach Meta Contract (Epic/Story)

- Scope boundaries, ownership, and readiness signals are explicit.
- No implementation-only Definition-of-Done checklist in meta artifacts.
- Downstream executable tasks and decision evidence are linked.

## Normative Standards Baseline

- Scrum Guide (latest): artifact purpose, accountabilities, and increment focus.
- ISO/IEC 25010: non-functional quality model for software requirements.
- WCAG 2.2 AA: accessibility acceptance baseline for UX/UI work.
- OWASP ASVS / OWASP Top 10: security requirement baseline.
- Team governance: stage gates and delivery evidence in `.digital-artifacts`.
