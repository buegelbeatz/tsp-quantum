---
kind: task
stage: "{{stage}}"
story_id: "{{story_id}}"
task_id: "{{task_id}}"
title: "{{title}}"
status: open
badge: "{{badge_color}}"
assignee_hint: "{{agent_role}}"
created: "{{date}}"
milestone_id: "{{milestone_id}}"
sprint_hint: "{{sprint_hint}}"
layer: digital-generic-team
---

# Task: {{title}}

## Description

{{description}}

## Acceptance Criteria

{{acceptance_criteria}}

## Implementation Hints

{{hints}}

## Parent Hierarchy

- Epic: {{parent_epic}}
- Story: {{parent_story}}

## Milestone Plan

- milestone_id: {{milestone_id}}
- sprint_hint: {{sprint_hint}}

## Definition of Done

- [ ] Code implemented
- [ ] Tests written
- [ ] `make test` passes
- [ ] `make quality` passes
- [ ] PR created with quality-expert review
