---
name: "Stages / 05-projects"
description: "Enterprise Specification: Project Stage"
layer: digital-generic-team
---
# Enterprise Specification: Project Stage

## 1. Purpose

Defines the formal state machine governing the Project layer.

The goal is to:

- Transform a validated exploration candidate into a registered project
- Establish project infrastructure (board, team, wiki)
- Define initial scope, ownership, and constraints
- Unlock the project for downstream delivery layers

This stage is the **activation gate** between exploration and delivery.

---

## 2. Scope

Applies to:

- Exploration candidates in state `STATE_3_PROJECT_CANDIDATE`
- New projects that have not yet received a formal project charter
- Re-activations of previously paused projects

---

## 3. Required Inputs

- Validated exploration output (exploration candidate document or equivalent)
- Initial problem statement and hypothesis
- Identified project owner / responsible stakeholder
- High-level scope boundaries (what is in and out of scope)

---

## 4. Activities

- Register the project formally (`PROJECT.md` canonical document)
- Create the GitHub Project board and initial wiki page
- Identify team members and assign roles
- Define initial scope boundaries and constraints
- Record open questions and missing information explicitly

---

## 5. Output Artifacts

- `PROJECT.md` — canonical stage document (created from template)
- GitHub Project board with initial columns
- Wiki page for this project
- Identified stakeholder list

## 5a. Canonical Language Requirement

- All normalized intake artifacts consumed by this stage must be in English.
- All stage outputs created from normalized intake artifacts must be written in English.
- Original non-English source material may be retained only for provenance and must not replace the English canonical stage content.

---

## 6. Readiness Criteria (Exit Gate — "Freischaltung")

ALL must be true for the stage to be considered `active` (unlocked):

- `PROJECT.md` exists and `status: active` is set in frontmatter
- GitHub Project board exists and is accessible
- Project owner is identified and confirmed
- Scope boundaries are explicit (at least one in-scope and one out-of-scope item)
- No open blocking questions remain (or they are documented with owners)

---

## 7. Non-Readiness Indicators (Stage remains `in-progress`)

- No confirmed project owner
- Scope completely undefined or contradictory
- Blocking open questions with no assigned owner
- Exploration candidate not in `STATE_3_PROJECT_CANDIDATE` state

---

## 8. Agent Responsibilities

Primary: agile-coach

- Create `PROJECT.md` from template on first invocation
- Validate all readiness criteria before setting `status: active`
- Identify and list all missing information in `PROJECT.md` → "Missing Information / Failure List"
- Reject or re-normalize non-English upstream bundles before continuing stage work

Support: platform-architect (on request)

- Review scope definition and architectural constraints
- Provide `expert_response_v1` with readiness score

---

## 9. Handoff Mapping

- Output → `expert_request_v1` → platform-architect (scope review)
- Or → `expert_request_v1` → agile-coach (if clarification needed)
- On exit → handoff to downstream layer stage flow (for example `digital-iot-team`)

---

## 10. Transition

Project → downstream layer stage flow ONLY if:

- `PROJECT.md` exists with `status: active`
- Project owner is confirmed
- Initial scope is defined
- Board is operational

---

## 11. Summary

The Project stage registers the project formally and sets up all infrastructure needed for downstream delivery layers. Only a fully unlocked (`status: active`) project may transition beyond this layer.