---
name: "Stages / 00-explorations"
description: "Enterprise Specification: Exploration State Machine"
layer: digital-generic-team
---
# Enterprise Specification: Exploration State Machine

## 1. Purpose

Defines the formal state machine governing the Exploration layer.

The goal is to:

- Structure progression from idea to project candidate
- Enable controlled execution (including engineering and data science work)
- Prevent premature transition into full delivery

---

## 2. Core Principle

Exploration is a **controlled learning system**.

It allows:

- Hypothesis validation
- Technical probing
- Early experimentation

But it MUST NOT become:

- Full implementation
- Production delivery
- Detailed execution planning

---

## 3. States

Exploration is divided into four discrete states:

```
STATE_0_RAW_IDEA
STATE_1_PROBLEM_FRAMED
STATE_2_VALIDATED_UNDERSTANDING
STATE_3_PROJECT_CANDIDATE
```

---

## 4. State Definitions

### 4.1 STATE_0_RAW_IDEA

Description:
- Unstructured idea or observation

Characteristics:
- Problem unclear
- No validated value
- No defined stakeholders

Allowed Activities:
- Initial framing
- Expert consultation

Allowed Agents:
- agile-coach
- generic-expert

---

### 4.2 STATE_1_PROBLEM_FRAMED

Description:
- Problem is described but not validated

Characteristics:
- Stakeholders roughly identified
- Initial hypotheses exist

Allowed Activities:
- Problem refinement
- Early architecture sketches
- UX exploration

Allowed Agents:
- agile-coach
- generic-expert
- platform-architect
- ux-designer

---

### 4.3 STATE_2_VALIDATED_UNDERSTANDING

Description:
- Problem validated and solution direction emerging

Characteristics:
- Value hypothesis plausible
- Constraints partially known

Allowed Activities (IMPORTANT):

- Architecture exploration
- Technical spikes (engineering)
- Data exploration / prototyping (data science)
- Feasibility validation

Allowed Agents:

- platform-architect (dual expert+review role)
- generic-deliver (engineers doing spikes)
- generic-expert
- ux-designer

Constraint:

- Work MUST remain experimental
- No production-grade implementation

---

### 4.4 STATE_3_PROJECT_CANDIDATE

Description:
- Ready for formal project initiation

Characteristics:
- Problem clearly defined
- Stakeholders known
- Value justified
- Scope bounded

Allowed Activities:
- Final validation
- Consolidation

Allowed Agents:
- agile-coach

---

## 5. State Transitions

### 5.1 Transition Rules

Transitions are only allowed if criteria are met.

---

### STATE_0 → STATE_1

Requires:

- Problem articulated
- Stakeholders identified (at least roughly)

---

### STATE_1 → STATE_2

Requires:

- Hypotheses defined
- Initial validation performed
- Solution direction exists

---

### STATE_2 → STATE_3

Requires:

- Problem validated
- Value plausible
- Feasibility demonstrated (via spikes or experiments)
- Scope bounded

---

### STATE_* → TERMINATED

If:

- No value identified
- Problem invalid
- Not strategically relevant

---

## 6. Handoff Integration

### Expert Pattern

```
any → expert_request_v1 → generic-expert
generic-expert → expert_response_v1 → requester
```

---

### Architecture Exploration

```
agile-coach → expert_request_v1 → platform-architect
platform-architect → expert_response_v1 → agile-coach
```

---

### Engineering / Data Exploration (NEW)

```
agile-coach → work_handoff_v1 → generic-deliver
generic-deliver → work_handoff_v1 → agile-coach
```

Purpose:

- Build prototypes
- Run experiments
- Validate feasibility

---

### UX Exploration

```
agile-coach → work_handoff_v1 → ux-designer
ux-designer → work_handoff_v1 → agile-coach
```

---

## 7. Output Per State

| State | Output |
|------|--------|
| STATE_0 | Raw idea |
| STATE_1 | Problem definition |
| STATE_2 | Validated hypotheses + experiments |
| STATE_3 | Project-ready definition |

---

## 8. Exit Contract (Project Initiation Input)

STATE_3 MUST produce:

```
{
  "problem": "...",
  "stakeholders": [...],
  "impact": "...",
  "value": "...",
  "constraints": [...],
  "evidence": [
    "user validation",
    "technical spike results",
    "data experiments"
  ],
  "open_questions": [...]
}
```

---

## 9. Anti-Patterns

- Skipping states
- Moving to delivery too early
- Over-engineering prototypes
- Treating spikes as production work
- Missing validation before transition

---

## 10. Governance

- State transitions MUST be explicit
- Each transition SHOULD be documented
- Evidence MUST be attached for STATE_2 → STATE_3

---

## 11. Summary

This state machine enables:

- Structured exploration
- Controlled experimentation
- Clear transition into project initiation

It ensures that engineering and data science can contribute early without breaking process integrity.