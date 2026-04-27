---
stage: "{{stage}}"
stage_id: "{{stage_id}}"
created: "{{date}}"
board_type: github
board_id: ""
board_url: ""
wiki_url: ""
single_point_of_truth_board: "refs/board/*"
single_point_of_truth_wiki: "docs/wiki/"
external_system_provider: "github"
status: in-progress
history: []
layer: digital-generic-team
---

# {{stage_title}} Project

> Canonical language rule: keep all stage content in English. Use non-English source material only as provenance, never as the primary project text.

## Governance Header

- single_point_of_truth_board: refs/board/*
- single_point_of_truth_wiki: docs/wiki/
- primary_external_sync: github (optional in derived layers)
- **SoT Version**: Canonical version is in `.digital-artifacts/40-stage/{{stage}}.md` – this is NOT a cached copy

## Vision

Deliver a concrete {{stage_title}} stage that turns intake and expert findings into auditable delivery outcomes with clear ownership, review evidence, and deterministic synchronization to board and wiki systems.

## Goals

- Establish one canonical scope statement for this stage in `.digital-artifacts/40-stage/{{stage}}.md`.
- Keep board and wiki links synchronized so reviewers can verify progress without local context.
- Ensure every delivery item has acceptance criteria and a human-review gate before done transition.

## Constraints

- All stage content must remain in English and be understandable for non-technical approvers.
- Board transitions to `done` require merged and human-approved PR evidence.
- Runtime/tooling actions must stay inside repository governance paths and approved wrappers.

## Stage Readiness Assessment

> **Who scores?** Expert Agents report readiness in their specification handoffs. Agile-Coach aggregates scores and consensus.
> **When?** After all expert reviews are collected (typically at end of specification phase).

| Criterion | Status | Score | Evidence | Expert | Sign-Off |
|-----------|--------|-------|----------|--------|----------|
| Vision concrete & evidence-backed | ⏳ pending | / | "Awaiting platform-architect review" | platform-architect | pending |
| Goals measurable & testable | ⏳ pending | / | "Awaiting agile-coach assessment" | agile-coach | pending |
| Constraints explicit & bounded | ⏳ pending | / | "Awaiting security-expert constraints" | security-expert | pending |
| Stakeholders & owners clear | ⏳ pending | / | "Awaiting org chart alignment" | agile-coach | pending |
| Open questions actionable | ⏳ pending | / | "TODO: gather unknowns" | agile-coach | pending |

**Score Legend**: 
- 1 = Incomplete or blocked
- 2 = Minimal evidence, many gaps
- 3 = Adequate with caveats
- 4 = Strong, minor gaps
- 5 = Complete, high confidence

**Status**: ✅ done | ⚠️ in-progress | ⏳ pending | ❌ blocked

## Missing Information / Open Questions

- [ ] Missing acceptance criteria – **Owner**: ? | **Target Resolution**: ?
- [ ] Missing owner or assignee – **Owner**: ? | **Target Resolution**: ?

**Note**: This readiness checklist is filled iteratively as specifications from expert agents arrive. Agile-Coach consolidates final scores once all experts have reported.
- [ ] Missing technical constraints
- [ ] Risk not assessed

## Stage Quality Notes

- Vision quality: evidence-backed and stakeholder-readable.
- Scope quality: measurable boundaries (in / out) are explicit.
- Delivery quality: work can be delegated without hidden local context.
- Risk quality: constraints, dependencies, and unknowns are listed.
- Overall confidence: derive from concrete content, not fixed placeholder scores.

## Stakeholders

| Role | Name/Team | Contact |
|------|-----------|---------|

## Definition of Done

- Stage scope is explicit, measurable, and linked to actionable delivery tasks.
- Review gate evidence (PR, approval, tests/quality) is documented and verifiable.
- Board, wiki, and stage document reflect the same final state without manual reconciliation.

## History

| Date | Change | Author |
|------|--------|--------|
