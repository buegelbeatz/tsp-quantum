---
kind: bug
stage: "{{stage}}"
bug_id: "{{bug_id}}"
title: "{{title}}"
status: open
badge: "{{badge_color}}"
assignee_hint: "{{agent_role}}"
created: "{{date}}"
milestone_id: "{{milestone_id}}"
sprint_hint: "{{sprint_hint}}"
parent_epic: "{{parent_epic}}"
parent_story: "{{parent_story}}"
layer: digital-generic-team
---

# Bug: {{title}}

## Description

{{description}}

## Acceptance Criteria

{{acceptance_criteria}}

## Parent Hierarchy

- Epic: {{parent_epic}}
- Story: {{parent_story}}

## Implementation Hints

{{hints}}

## Milestone Plan

- milestone_id: {{milestone_id}}
- sprint_hint: {{sprint_hint}}

## Definition of Done

- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Regression tests added
- [ ] `make test` passes
- [ ] Documentation updated if behavior changed