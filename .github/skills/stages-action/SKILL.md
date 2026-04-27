---
name: "stages-action"
description: "Orchestrates the full stage workflow: ingest → specification → stage document → planning → delivery → review cycle"
layer: digital-generic-team
---

# Skill: stages-action

## Purpose
Shared implementation behind all stage alias commands. Runs the complete agile-coach + deliver-agent lifecycle for a named stage.

## When to Use
- When `/stages-action stage="<name>"` is invoked
- When any stage alias command (`/exploration`, `/project`) is invoked

## Entry Point
```bash
make stages-action STAGE=<stage>
```

## Stage Metadata Source

Runtime command metadata is centrally defined in `.github/skills/stages-action/stages.yaml`.

- Runtime consumers (`/stages`, prompt alias generation, stage prompt pruning) MUST read this catalog.
- Governance and policy rules remain in `.github/instructions/stages/*.instructions.md`.

## DRY_RUN Modes

Optional environment variable for all stage commands (`/project`, `/exploration`, `/stages-action`):

- `DRY_RUN` unset or `0`: full stage workflow; resume/continue existing work where available.
- `DRY_RUN=1`: reset artifact workspace for re-run, clean stage board/wiki, execute until planning, disable primary-system sync, skip delivery trigger.
- `DRY_RUN=2`: same reset/cleanup as mode 1, plus best-effort cleanup of GitHub stage assets in the primary system before regeneration (stage project/board, artifact-synced issues, wiki), then execute until planning with primary-system sync enabled for verification, skip delivery trigger.

Example:

```bash
DRY_RUN=1 make project
DRY_RUN=2 make stages-action STAGE=project
```

## Phase Overview

| Phase | Trigger | Actions |
|-------|---------|---------|
| NewInputFlow | New data / new project | Ingest → Spec → Stage doc → Planning → Delivery |
| DELIVER_AGENTS | Triggered by planning | Branch → Implement → Test → PR |
| ExistingProjectFlow | Review follow-up | PR review cycle and board triage using generated status artifacts |

## Templates
All document templates in `templates/`:
- `agent-review.md` — Per-agent specification review with mandatory 1-5 scoring and recommendation
- `cumulated-review.md` — Agile-coach synthesis review with aggregated scoring
- `project.md` — Canonical stage document template rendered as `40-stage/<STAGE>.md`
- `wiki-stage-page.md` — GitHub Wiki page structure
- `epic.md`, `story.md`, `task.md`, `bug.md` — Planning item templates

## Dependencies
- `.github/skills/artifacts/` — artifact pipeline
- `.github/skills/shared/task-orchestration/` — task lifecycle
- `.github/skills/shared/shell/scripts/lib/github.sh` — board/wiki operations
- `GH_TOKEN` — required for GitHub Project board and Wiki operations

## Specification Storage Rule

- Specification artifacts are always created per bundle under `.digital-artifacts/30-specification/<date>/<item_code>/`.
- Stage readiness is tracked only in the canonical stage document (`40-stage/<STAGE>.md`) using checklist/scoring and `status: in-progress|active`.
