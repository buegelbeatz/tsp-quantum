---
name: fullstack-engineer
description: Domain role wrapper that orchestrates generic delivery lifecycle for implementation work.
layer: digital-generic-team
---

# Skill: Fullstack Engineer

This skill orchestrates role-specific implementation flows using the generic delivery lifecycle.

## Workflow

1. Run generic-deliver prefix for ticket and branch context.
2. Execute role implementation work in repository scope.
3. Run generic-deliver postfix to finalize delivery and produce handoff metadata.

## Compliance Scope

- Implementation must honor instruction references embedded in planning artifacts.
- Delivery wording governance is centralized in `generic-deliver` to avoid duplicate policy text across role wrappers.

## Script

- `scripts/fullstack-delivery.sh`

## Dependencies

- `../generic-deliver`
- `../shared/shell`
