---
name: "user-review"
description: >
  Provides the user-standard agent with structured UX review capabilities.
  Parses SVG scribbles and screenshot sets from a non-technical user perspective,
  applies the 5-criteria 1–5 rating system, and writes user-review artifacts to
  .digital-artifacts/60-review/<stage>/<date>/user-review-*.md.
layer: digital-generic-team
---

# Skill: user-review

## Purpose

Give the `user-standard` agent a consistent, structured method for reviewing UX scribbles
and app screenshots as a non-technical mobile user would experience them.

---

## Input

Accepted via `work_handoff_v1` from `ux-designer`:

| Field | Description |
|-------|-------------|
| `design_artifact` | Path to SVG scribble or screenshot set |
| `task_performed` | One sentence: what the user should accomplish |
| `iteration` | Round number (r1, r2, ...) |
| `context` | Minimal onboarding context (app category only, no internals) |

---

## Output

### Review File

```
.digital-artifacts/60-review/<stage>/<YYYY-MM-DD>/user-review-<YYYYMMDD>-<feature-slug>-r<n>.md
```

File uses template: `templates/user-review.md`
Question catalog template: `templates/interview-questionnaire.md`

### Handoff

`user_review_v1` payload sent back to `ux-designer`.

---

## Rating Criteria

Five criteria, each scored 1–5. See full definitions in
`.specifications/user-standard/rating-criteria.md`.

| Criterion | Key Question |
|-----------|--------------|
| Discoverability | Can the user find what they need without guidance? |
| Clarity | Are labels, icons, and CTAs self-explanatory? |
| Navigation | Is the flow predictable and consistent with mobile conventions? |
| Error Recovery | Can the user recover from mistakes without help? |
| Mobile Familiarity | Does it feel like an app the user already knows? |

### Composite Score

```
composite = (discoverability + clarity + navigation + error_recovery + mobile_familiarity) / 5
```

### Recommendation Thresholds

| Composite | Action |
|-----------|--------|
| ≥ 4.0 and no blockers | `proceed` |
| 2.0 – 3.9 or blockers present | `revise` |
| < 2.0 | `redesign` |

---

## Instructions

### SVG Interpretation

1. Parse visible elements: buttons, inputs, labels, icons, text, annotations.
2. Identify interactive elements by visual convention (borders, underlines, colored fills).
3. Map layout regions: header, content area, footer, navigation bar.
4. Note any annotated states (error state, empty state, loading state).
5. Ignore element IDs, CSS classes, or internal SVG metadata — treat as pure visual.

### Task Simulation

Starting from the first visible screen:
1. Identify the element the user would interact with first.
2. Follow the likely user path step-by-step.
3. Document each step in the review walkthrough table.
4. Mark where friction, confusion, or dead-ends occur.
5. Complete the template-based interview questionnaire section in the review artifact.

### Finding Classification

**Positive finding:** Something the user can do naturally, without hesitation.  
**Confusion finding:** An element that causes hesitation, misunderstanding, or friction.  
**Blocking issue:** Prevents task completion entirely — dead-end, missing action, crash.

All findings must be written in **plain user language** — never technical terms.

---

## Output Path Scaffolding

Before writing:
1. Determine the current active stage (from `40-stage/LATEST.md` or fallback to `general`).
2. Construct path: `.digital-artifacts/60-review/<stage>/<YYYY-MM-DD>/`
3. Create directory if it does not exist (idempotent).
4. Construct filename: `user-review-<YYYYMMDD>-<feature-slug>-r<n>.md`
   - `feature-slug`: derived from design_artifact filename, lowercase, hyphens.

---

## Dependencies

- `artifacts` skill (path scaffolding)
- `USER_REVIEW.schema.yaml` (handoff schema validation)
