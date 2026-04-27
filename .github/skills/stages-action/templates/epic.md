---
kind: epic
stage: "{{stage}}"
epic_id: "{{epic_id}}"
title: "{{title}}"
status: open
badge: "{{badge_color}}"
assignee_hint: "{{agent_role}}"
created: "{{date}}"
milestone_id: "{{milestone_id}}"
sprint_hint: "{{sprint_hint}}"
single_point_of_truth_board: "refs/board/*"
single_point_of_truth_wiki: "docs/wiki/"
layer: digital-generic-team
---

# Epic: {{title}}

## Outcome

{{description}}

## Success Signals

{{goals}}

## Scope Boundary

- In scope: synthesis, prioritization, and governance of the linked planning stories.
- Out of scope: direct implementation and code-level verification, which remain in child tasks.

## Ownership

- Owner role: agile-coach
- Work item type: meta-planning container

## Milestone Plan

- milestone_id: {{milestone_id}}
- sprint_hint: {{sprint_hint}}

## Child Stories

{{story_links}}
