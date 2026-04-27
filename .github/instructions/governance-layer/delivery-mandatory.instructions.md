---
name: "Delivery Phase - Mandatory Implementation Requirement"
description: "CRITICAL: /project workflow MUST trigger delivery agents during step 5. Planning without implementation is incomplete work. This is non-negotiable."
applyTo: "**"
priority: CRITICAL
layer: digital-generic-team
---

# Delivery Phase - Mandatory Implementation Requirement

**Status:** BLOCKING | **Added:** 2026-04-17 | **Reason:** Week-long escalation - /project must implement bugs, not just plan them

## The Requirement

The `/project` workflow has 6 critical steps:

1. Ingest (Input → Data)
2. Specification Synthesis
3. Readiness Gate
4. Planning Synchronization
5. **Delivery Dispatch** ← MANDATORY PHASE
6. Review Status

**Step 5 is MANDATORY and NON-NEGOTIABLE.**

If step 5 does not trigger delivery agents and move board tickets from backlog→in-progress, the workflow is broken.

## Why This Matters

- Pure planning without implementation leaves bugs in backlog forever
- Board transitions MUST happen DURING workflow execution, not after
- Agents must be triggered with work_handoff_v1 payload
- This requirement has been requested 10+ times and is now critical path

## Implementation Reality

**CORRECTION (2026-04-17 - realized after implementation):**

Agents run in VS Code. `make project` runs in CLI. They are separate processes.

**DO NOT attempt subprocess calls to runSubagent from Python** - it's a VS Code tool, not a CLI command.

**Correct pattern:**
1. `make project` step 5 creates work_handoff_v1 YAML files
2. Agents monitor `.digital-runtime/handoffs/*/` directories  
3. When agents see work_handoff_v1 files, they pick them up independently
4. Agents then create PRs/commits in their own process

**The actual implementation:**
```python
def _mark_delivery_ready(repo_root, assignee, task_id, handoff_path, source_path) -> bool:
    # Just verify the file exists. Agents will discover it.
    return handoff_path.exists()
```

This is NOT "triggering" agents. This is "preparing work for agents to discover."

## Current Status (Honest Assessment)

- ✅ Work_handoff_v1 files are created during `make project`
- ✅ Board moves backlog→in-progress during delivery step
- ⏳ Agents must pick up work independently (this requires agent-side monitoring, not CLI triggering)
- ❌ `make project` alone cannot implement bugs - it only prepares the work
- ❌ Agents must be running in VS Code to discover and process handoffs

## Verification Checklist

Every time `.github/skills/artifacts/scripts/artifacts_flow.py` is modified:

- [ ] Line 468: `_trigger_delivery_agent()` call is present
- [ ] Function `_trigger_delivery_agent()` exists (Line 340+)
- [ ] CRITICAL comment exists documenting requirement
- [ ] Unit tests pass: `test_run_planning_to_delivery_moves_board_ticket_*`
- [ ] Integration test: `make project` shows `triggered: 2` or more in step 5 output
- [ ] Board transitions happen during step 5, not after
- [ ] Agents receive work_handoff_v1 YAML with task context

If ANY of these fail, the workflow is broken and must be fixed immediately.

## Related Files

- `.github/skills/stages-action/scripts/stages-action.sh` (Line 437 - deployment point)
- `.github/prompts/project.prompt.md` section "Delivery bootstrap rule"
- `.github/skills/prompt-project/SKILL.md` (Delivery phase contract)

## Historical Context

- **Week 1:** Users asked for delivery implementation
- **Week 2:** Users asked again - bugs still in backlog
- **Today:** User escalated: "Ich werde jetzt solange diese Anforderung prompten, bis Du Dir es endlich hinter die Ohren schreibst" (I will keep prompting until you write it behind your ears)
- **Decision:** Make requirement permanent and non-negotiable in code

## Test Case

```bash
# This should show "triggered": 2 or more during step 5
make project

# Expected output in step 5 (delivery-dispatch):
# "triggered": 2,
# "ready": 2,
# "dispatch_traces": 2,

# Expected board state DURING execution:
# git for-each-ref refs/board/project | grep in-progress
# PRO-THM-04-TASK in-progress (was backlog)
# PRO-THM-05-TASK in-progress (was backlog)
```

## Non-Compliance Consequences

- Any PR that removes agent triggering from step 5 will be blocked
- Any modification to `run_planning_to_delivery()` without agent awareness will fail review
- Workflow is considered incomplete if work_handoff_v1 files are not created

## 🚨 CRITICAL ARCHITECTURAL GAP (2026-04-17)

**Status:** DISCOVERED - Agents cannot be triggered from CLI

The current implementation has a fundamental architectural gap:
- CLI process (`make project`) and VS Code agent process are separate
- Agents have NO mechanism to discover work_handoff_v1 files
- Agents are never notified work is ready

**This means:**
- ✅ `make project` works and creates handoff files
- ❌ Agents do NOT pick up the work automatically
- ❌ User must manually provide handoff file to agents
- ❌ Board stays "in-progress" indefinitely

**Solution:** 
Agents need an instruction/prompt to check `.digital-runtime/handoffs/*/` for work_handoff_v1 files and process them. Currently missing. See `.digital-artifacts/70-audits/2026-04-17/DELIVERY_AGENT_DISCOVERY_GAP.md`

---

**This is not a suggestion. This is a requirement. But it's currently incomplete.**
