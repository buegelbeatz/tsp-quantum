---
name: check-delivery-work
description: "Discover and process work_handoff_v1 files in .digital-runtime/handoffs/<stage>/. Manual trigger for agents to find assigned work until automatic discovery is implemented."
---
<!-- layer: digital-generic-team -->

# Prompt: check-delivery-work

**Purpose:** Agents use this to manually discover delivery work_handoff_v1 files when automatic triggering not yet available.

**Trigger:** 
- Agent runs after /project completes
- User runs when board shows in-progress tickets
- CI/CD runs after make project before agent workflows

**What It Does:**
1. Scans `.digital-runtime/handoffs/<stage>/` for work_handoff_v1 files
2. Filters for files matching agent role/assignment
3. Returns list of work to do
4. Agent can then process each file per delivery-handoff-discovery instructions

**How Agents Use This:**
```
User: @agent check-delivery-work
Agent: 
  - Scans .digital-runtime/handoffs/<stage>/ for *.yaml
  - Finds work_handoff_v1 frontmatter with role: agent-name
  - Lists pending work items
  - Asks user: Shall I process these?
```

**How Users Use This:**
```
User: /check-delivery-work
System: Lists all pending work_handoff_v1 files
User: @fullstack-engineer process these
Agent: Starts implementation
```

**Note**: This is a temporary workaround until automatic discovery is implemented. When agents have MCP file-watch capability, this prompt will become unnecessary.

## Implementation

### File Pattern Scan
```bash
# Find all work_handoff_v1 files
find .digital-runtime/handoffs -name "*-handoff.yaml" -type f

# Expected paths:
# .digital-runtime/handoffs/{stage}/{task_id}-handoff.yaml
```

### YAML Filter
```yaml
# Example work_handoff_v1 structure to find
requester: agile-coach
receiver: fullstack-engineer   # or ux-designer, data-scientist, etc.
role: fullstack-engineer       # Match agent role
task_id: 20260417-bug-1
status: pending               # Only process pending work
```

### Discovery Output
List all pending work_handoff_v1 files matching agent role, with:
- Task ID
- Requester
- Assigned receiver 
- Brief description
- Path to handoff file
- Status (pending/started/done)

### Agent Next Steps (Per delivery-handoff-discovery.instructions.md)
1. Read work_handoff_v1 YAML
2. Extract requirements, test data, acceptance criteria
3. Implement according to spec
4. Create PR
5. Update board status
6. Mark handoff file as done

---

## Status

**Availability:** Ready for immediate use (manual trigger)

**Limitations:**
- Requires user or CI/CD to invoke (not automatic)
- Temporary workaround (replaced when MCP file-watch available)
- Must be run after /project for agents to find new work

**Next Steps:**
- Implement automatic version (MCP file-watch)
- Add this prompt to CI/CD after make project
- Document in /project workflow

**Classification:** TEMPORARY WORKAROUND - Architectural solution needed
