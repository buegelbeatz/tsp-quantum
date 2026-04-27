---
name: "Delivery Handoff Discovery"
description: "Check for pending work_handoff_v1 files and process them"
applyTo: "**"
layer: digital-generic-team
---

# Delivery Handoff Discovery

When agents see work_handoff_v1 YAML files in `.digital-runtime/handoffs/<stage>/`, they must:

1. Read the YAML file
2. Extract task_id, stage, assignee, and acceptance_criteria
3. Check `.digital-artifacts/50-planning/{stage}/{task_id}*` for source artifacts
4. Execute the work according to acceptance_criteria
5. Create PR with implementation
6. Update board status from in-progress → done

## File Pattern

Look in:
```
.digital-runtime/
  ├── handoffs/
  │   └── {stage}/
  │       └── {task_id}-handoff.yaml    ← WORK_HANDOFF_V1 FILE

.digital-artifacts/
  ├── 50-planning/
  │   └── {stage}/
  │       └── {task_id}*                ← SOURCE ARTIFACTS
```

## Trigger

Agents should check for these files when:
- User runs `/project` (step 5 creates them)
- Agent receives Context environment variable: `DELIVERY_HANDOFF_PATHS`
- Agent is invoked with task_id matching handoff file

## Implementation Checklist

- [ ] Read work_handoff_v1 YAML
- [ ] Verify all required fields present (task_id, stage, assignee, acceptance_criteria, completion_criteria)
- [ ] Locate source planning artifacts
- [ ] Implement according to acceptance_criteria
- [ ] **Create unit tests** (coverage target ≥80%)
- [ ] **CRITICAL: Do NOT update board status to done directly.** See `delivery-review-gates.instructions.md`.
- [ ] Create PR on feature branch (NOT main/master)
- [ ] Include review artifact with acceptance criteria verification
- [ ] **Wait for human reviewer approval** before merge
- [ ] **After PR is merged to main**: Delivery agent may transition board from in-progress → done
- [ ] Record human approval evidence in review artifact (timestamp, reviewer login, PR link)

## Example

```yaml
# .digital-runtime/handoffs/project/TASK-THM-05-handoff.yaml
api_version: v1
kind: work_handoff_v1
metadata:
  task_id: TASK-THM-05
  stage: project
  generated_at: 2026-04-17T12:05:46Z
spec:
  assignee: fullstack-engineer
  title: "Implement approved scope for Project Team Operating Model"
  acceptance_criteria:
    - Criterion 1
    - Criterion 2
  completion_criteria:
    - All tests pass
    - PR merged
    - Board updated
```

Agent sees this file and begins work.

## Related Requirements

**CRITICAL:** See `delivery-review-gates.instructions.md` for the mandatory human approval gate.

- Agents MUST NOT move tickets to `done` without human reviewer sign-off
- Board transition flow: `in-progress → (human review) → done`
- Every delivery artifact requires PR, human review, and documented approval
- After `/project` succeeds, wiki PowerPoint MUST be regenerated (invoke `/powerpoint` with the project stage artifacts as source)

