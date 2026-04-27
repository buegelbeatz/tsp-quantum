---
name: "handoff"
description: "Standardize all agent-to-agent handoffs: work transfers (work_handoff_v1) and expert consultations (expert_request_v1 / expert_response_v1)."
layer: digital-generic-team
---

# Skill: Agent Handoff

## Purpose
Standardize all agent-to-agent communication: work transfers and expert consultations.

## When to Use

### Work Handoff (work_handoff_v1)
- When transferring work between delivery agents
- When context, artifacts, and next steps must be communicated
- When results from one phase feed into the next

### Expert Consultation (expert_request_v1 / expert_response_v1)
- When specialized knowledge is required
- When uncertainty prevents a decision
- When analysis is needed without implementation

## Work Handoff Steps
1. Summarize goal and current state
2. List relevant artifacts
3. Separate facts from assumptions
4. List open questions explicitly
5. Define expected output
6. Generate `work_handoff_v1` using the template in `templates/work_handoff_v1.template.yaml`

## Expert Consultation Rules
- Experts provide analysis only — no file modifications, no workflow continuation
- Always include confidence level (1–5 scale)
- Separate factual findings from inferred recommendations

## Quality Criteria
- Actionable without follow-up questions
- No hidden assumptions
- Clear artifact references
- Explicit definition of done
- Handoff payload content written in English unless an explicit policy states otherwise

## Canonical Schema Source
- Canonical schema contracts remain in `.github/handoffs/*.schema.yaml`.
- Skill templates in `templates/` are authoring helpers and must stay aligned with canonical schemas.

## Scripts
- `scripts/handoff-runtime-sync.sh` — sync canonical handoff schemas into `.digital-runtime/layers/<layer>/handoffs`, clean stale runtime entries, and generate an index.
