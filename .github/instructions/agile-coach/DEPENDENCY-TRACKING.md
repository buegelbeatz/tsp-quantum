---
layer: digital-generic-team
---
# Agile Coach: Dependency Tracking & Smart Backlog Management

Enables the Agile Coach to respect task/story dependencies and suggest optimal backlog ordering.

---

## Overview

**Current**: Tickets generated from Epic/Stories/Tasks are placed in backlog with no dependency awareness.

**Goal**: Agile Coach detects dependencies and:
1. Marks blocked tasks (with `blockedBy` field)
2. Suggests backlog ordering (unblocked → ready-to-start first)
3. Prevents moving blocked tasks to in-progress
4. Highlights critical path when blocking dependencies exist

---

## Data Model

### Dependency Declaration

In Planning artifacts (stories, tasks), declare dependencies as:

```yaml
# .digital-artifacts/50-planning/[stage]/STORY_[id].md
---
id: STORY-001
title: API endpoint for user auth
depends_on:
  - TASK-001  # Must complete first
  - TASK-003
status: backlog
---
```

Fields:
- `depends_on`: List of ticket IDs this ticket depends on (blocking)
- `blocked_by`: Populated by sync (reverse relation; for UI only)

### Dependency Graph

Build during planning → specification → synchronization:

```
EPIC-001
├── STORY-001 (depends_on: [TASK-001, TASK-003])
│   ├── TASK-001 (no deps) → CAN START
│   ├── TASK-002 (depends_on: [TASK-001]) → BLOCKED
│   └── TASK-003 (no deps) → CAN START
├── STORY-002 (depends_on: [STORY-001])  → BLOCKED
└── TASK-004 (no deps) → CAN START
```

---

## Planning Integration

### Step 1: Specification → Planning (artifacts-specification-2-planning)

When generating planning artifacts:

```python
def _build_stories_with_deps(spec, stage_name):
    """Generate story/task nodes with dependency tracking."""
    stories = []
    
    for spec_entry in spec["stories"]:
        story = {
            "id": spec_entry["id"],
            "title": spec_entry["title"],
            "depends_on": [],
            "assignee": None,
            "status": "backlog",
        }
        
        # Parse dependencies from spec (if annotations exist)
        if "prerequisites" in spec_entry:
            for prereq in spec_entry["prerequisites"]:
                story["depends_on"].append(prereq)
        
        # Auto-detect implicit dependencies (e.g., migration → deploy)
        if spec_entry.get("type") == "data-migration":
            story["depends_on"].append("INFRA-SETUP")
        
        stories.append(story)
    
    return stories
```

### Step 2: Compute Dependency Status

```python
def compute_dependency_status(tickets, graph):
    """Mark tickets as can-start, blocked, or ready-for-review."""
    
    for ticket in tickets:
        ticket["_dependency_status"] = "can-start"  # Default
        
        # Check each dependency
        for dep_id in ticket.get("depends_on", []):
            dep_ticket = next((t for t in tickets if t["id"] == dep_id), None)
            
            if dep_ticket is None:
                # External dependency (not in this planning scope)
                ticket["_dependency_status"] = "external-dependency"
                break
            
            if dep_ticket["status"] not in ("done", "merged"):
                # Blocking dependency not complete
                ticket["_dependency_status"] = "blocked"
                ticket["blocked_by"] = dep_id
                break
    
    return tickets
```

### Step 3: Suggest Backlog Order

```python
def suggest_backlog_order(tickets):
    """Reorder backlog: unblocked first, then blocked."""
    
    unblocked = [
        t for t in tickets
        if t["status"] == "backlog" and t.get("_dependency_status") == "can-start"
    ]
    
    blocked = [
        t for t in tickets
        if t["status"] == "backlog" and t.get("_dependency_status") != "can-start"
    ]
    
    # Prioritize: type (Epic → Story → Task), then creation order
    unblocked.sort(key=lambda t: (t.get("type", "task"), t.get("created_at", "")))
    blocked.sort(key=lambda t: (t.get("type", "task"), t.get("created_at", "")))
    
    return unblocked + blocked
```

---

## GitHub Sync

### Issue Labels

For each synced issue, add label to reflect dependency status:

```python
def compute_issue_labels(ticket):
    """Generate labels including dependency indicators."""
    labels = ["type:" + ticket.get("type", "task")]
    
    # Dependency labels
    if ticket.get("_dependency_status") == "blocked":
        labels.append("status:blocked")
        labels.append(f"blocked-by:{ticket['blocked_by']}")
    elif ticket.get("_dependency_status") == "can-start":
        labels.append("status:ready")
    elif ticket.get("_dependency_status") == "external-dependency":
        labels.append("status:external-dep")
    
    # Assign based on dependency status
    if ticket.get("_dependency_status") in ("blocked", "external-dependency"):
        ticket["assignee"] = None  # Don't auto-assign blocked tickets
    
    return labels, ticket
```

### Board Position Rules

**Enforce during sync+board-write**:

```
BACKLOG
├── Can-start (#1, #2, #5)   → Ordered by priority
├── Blocked (#3, #4)         → Show blockers in description
IN-PROGRESS
├── Can-move-only if current blockers resolved
├── **Warn** if moving blocked ticket
BLOCKED
├── Tickets explicitly marked status:blocked
```

---

## Agile Coach Workflow

### During Planning Review

1. **Dependency analysis**:
   ```markdown
   # Planning Review: Dependency Analysis
   
   ## Critical Path
   - TASK-001 → STORY-001 → TASK-002 → STORY-002 (4 tasks)
   
   ## Unblocked Ready-to-Start
   - TASK-003 (can start immediately)
   - TASK-004 (can start immediately)
   
   ## Blocked (External)
   - TASK-005 (external: awaiting API contract)
   
   ## Recommendation
   Start with TASK-003 + TASK-004 in parallel; allow STORY-001 to progress after TASK-001.
   ```

2. **Suggest sprint breakdown**:
   - Sprint 1: Unblocked tasks + TASK-001
   - Sprint 2: Downstream tasks after Sprint 1 complete

### During Daily Standups

```bash
# Show unblocked ready-to-start tickets
agile-coach --query "backlog AND status:ready AND type:task" 

# Show actively blocked
agile-coach --query "in-progress AND status:blocked" 

# Show critical path delays
agile-coach --query "dependencies.blocked_count > 0"
```

---

## Implementation Roadmap

### Phase 1: Data Model (Week 1)
- ✅ Add `depends_on`, `blocked_by`, `_dependency_status` fields
- ✅ Extend Planning artifacts YAML schema
- ✅ Compute dependency graph during planning

### Phase 2: Backlog Ordering (Week 2)
- ✅ Implement `suggest_backlog_order()`
- ✅ Sort unblocked → blocked
- ✅ Add sort indicator to board  display

### Phase 3: GitHub Sync (Week 3)
- ✅ Persist `blocked_by` link in GitHub issue labels
- ✅ Sync `_dependency_status` → GitHub issue labels
- ✅ Update board position rules (don't sync blocked → in-progress)

### Phase 4: Agile Coach Integration (Week 4)
- ✅ Add `--dependencies` query option
- ✅ Generate critical path report
- ✅ Print recommendations during planning review
- ✅ Daily query templates for blocked/ready tickets

---

## Example Usage

### Planning Output

```markdown
## Planning: Dependency Summary

### Critical Path (4 steps)
1. TASK-001: Setup database schema
2. STORY-001: Implement user auth API
3. TASK-002: Integration tests
4. STORY-002: Deploy to staging

### Parallel Tracks
- TASK-003: Documentation (independent)
- TASK-004: Frontend scaffolding (independent)

**Recommendation**: Assign Team A to critical path, Team B to TASK-003 + TASK-004.
```

### GitHub Issue Labels

```
STORY-001
├── Labels: [epic:auth] [type:story] [status:ready]
├── Assignee: alice
└── Description:
    Implement user authentication API
    
    **Dependencies**: None (can start immediately)
    **Blocks**: TASK-002, STORY-002

TASK-002
├── Labels: [epic:auth] [type:task] [status:blocked] [blocked-by:STORY-001]
├── Assignee: (none — blocked)
└── Description:
    Write integration tests for user auth API
    
    **Depends on**: STORY-001 (in backlog)
    **Blocks**: STORY-002
```

### Query Output

```bash
$ agile-coach --dependencies --stage project

READY TO START (no blockers):
  - TASK-003 (Frontend scaffolding)
  - TASK-004 (Documentation)

BLOCKED (waiting for):
  - TASK-002 (blocked by STORY-001)
  - STORY-002 (blocked by STORY-001 + TASK-002)

CRITICAL PATH (project duration driver):
  TASK-001 → STORY-001 → TASK-002 → STORY-002 (4 steps, ~8 days est.)
```

---

## FAQ

**Q: What if dependencies span multiple projects/stages?**  
A: Mark as `external-dependency` in label. Agile Coach reports these separately with owner/status link.

**Q: Should we prevent moving blocked tickets to in-progress?**  
A: Yes. GitHub board rules or agent validation should reject moves if `status:blocked` label present. Warn user.

**Q: How do unfinished blockers affect sprint planning?**  
A: Unblocked tasks are scheduled first. Blocked tasks shown in "pending dependency relief" queue. Recommend parallel work.

**Q: Can dependencies be optional (nice-to-have before starting)?**  
A: Not in this model. Use story descriptions for "preferred sequence" guidance instead.
