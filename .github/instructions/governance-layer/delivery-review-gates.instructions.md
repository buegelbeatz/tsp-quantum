---
name: "Delivery Review Gates - Mandatory Human Approval"
description: "CRITICAL: /project workflow MUST require human Review approval before tickets move to done. No tickets shall be marked done without evidence of human verification."
applyTo: "**"
priority: CRITICAL
layer: digital-generic-team
---

# Delivery Review Gates - Mandatory Human Approval

**Status:** ACTIVE | **Added:** 2026-04-18 | **Reason:** Tickets marked done without human approval violates engineering standards and delivery contract.

## The Requirement

The `/project` workflow **must NOT** transition tickets directly from `in-progress` → `done` via automation alone.

### Mandatory Review Gate Flow

```
backlog
  ↓
in-progress (automation via /project step 5)
  ↓
review (human scrutiny required)
  ↓
done (only after human approval recorded)
```

### What "Human Approval" Means

1. **Pull Request Review**: A human reviewer must read the code changes, tests, and documentation
2. **Board Transition**: Only AFTER PR merge should the board ticket transition to `done`
3. **Approval Evidence**: Review artifacts must include:
   - Reviewer name or GitHub login
   - Timestamp of approval
   - Link to PR or review artifact
   - Any conditional approvals or concerns noted

### Who Can Approve

- **Code Changes**: Any reviewer with write access matching the `receiver` role (fullstack-engineer, quality-expert, ux-designer, etc.)
- **Documentation**: Same reviewer or designated approver
- **Tests**: PR must include test coverage report; coverage target ≥80% (unless explicitly waived)

## Secondary Requirement: PowerPoint Wiki Update

After **every** successful `/project` execution:

1. **Trigger Condition**: `make project` completes with `status: triggered` > 0 or `status: already_dispatched` > 0
2. **Action Required**: Regenerate the PowerPoint deck from current artifacts by invoking `/powerpoint` with the project stage artifacts as source. Output goes to `docs/wiki/assets/Project-Summary.pptx`.
3. **Artifact Location**: Wiki PowerPoint deck at `docs/wiki/assets/Project-Summary.pptx` (or designated output)
4. **Staleness Enforcement**: If wiki PowerPoint is > 1 day old AND `/project` has been run, CI/CD or staged workflows must flag as stale with reconciliation prompt

### Implementation: Agent Invocation

After `/project` completes, invoke the `/powerpoint` prompt with the updated project artifacts as source. This triggers the PowerPoint agent to render the current stage state into a stakeholder-ready deck.

## Verification Checklist

For every `/project` execution where `triggered > 0`:

- [ ] ✅ Handoff YAML files created in `.digital-runtime/handoffs/<stage>/`
- [ ] ✅ Board tickets moved to `in-progress` by step 5
- [ ] ✅ Delivery agents notified via work_handoff_v1 discovery
- [ ] ⏳ **Agents implement code, create PR on feature branch**
- [ ] ⏳ **Human reviewer reviews PR** (no auto-merge)
- [ ] ⏳ **Human approver merges PR** (record in commit message or review artifact)
- [ ] ⏳ **Then and ONLY then**: Board ticket transitions to `done`
- [ ] ✅ PowerPoint wiki deck regenerated after `/project` completes
- [ ] ✅ PowerPoint deck timestamp is recent (≤ 1 day old)

## Failure Modes

| Scenario | Violation | Remediation |
|----------|-----------|------------|
| Ticket on `done` but no PR merged | ❌ Missing delivery evidence | Move back to `in-progress`, create PR, route to review |
| Ticket on `done` but PR has no reviewer approval | ❌ Missing human gate | Require explicit reviewer sign-off before merge |
| Wiki PowerPoint > 1 day old but `/project` ran recently | ⚠️ Stale artifact | Run `/powerpoint` with project artifacts, commit update |
| `/project` shows `triggered: 3` but PowerPoint unchanged | ⚠️ Post-execution hook missed | Run `/powerpoint` manually or re-run `/project` |

## Related Requirements

- **Copilot-Instructions** "Mandatory Delivery Gates": "Pull requests MUST include a human approval before merge"
- **Delivery-Mandatory.instructions.md**: Step 5 delivery dispatch flow
- **Handoff.instructions.md**: Review output artifacts must include recommendation + confidence

## Implementation Timeline

- **Immediate**: Document this requirement (done)
- **This week**: Add `project-post-powerpoint` target to Makefile
- **Next week**: Add CI/CD check to flag stale PowerPoint
- **Ongoing**: Enforce review gate before any board transition to `done`

---

**CRITICAL REMINDER FOR AGENTS:**

Do NOT move a ticket to `done` status on the board until:
1. Code is merged to main branch (PR approved + merged by human)
2. Human reviewer sign-off is recorded in the review artifact
3. All acceptance criteria are verified by human inspection
4. PowerPoint wiki is up-to-date

Automation creates handoffs and moves to `in-progress`. **Humans decide when work is done.**
