---
name: artifacts
description: Governs the .digital-artifacts folder structure, template scaffolding, inventory maintenance, LATEST.md updates, and role-based artifact access.
layer: digital-generic-team
---

# Skill: Artifacts

This skill governs the entire `.digital-artifacts/` workspace structure.
It is the shared foundation for all other skills and agents that read or write
artifact content.

## Capabilities

- Ensure the `.digital-artifacts/` scaffold exists from skill-local templates.
- Create missing directory and template files idempotently before write operations.
- Maintain append-only `INVENTORY.md` files for managed artifact folders.
- Maintain `LATEST.md` snapshots for stage and review outputs.
- Enforce role-based access rules via `PERMISSIONS.csv`.
- Embed deterministic SHA-256 source/synthesis fingerprints in generated specifications and stage documents.
- Keep local source-of-truth continuity: if `.digital-artifacts/` is missing, rebuild from `refs/board/*` and `docs/wiki/` references.
- Preserve `00-input` subfolder classification (`features`, `bugs`, `documents`) in downstream data metadata.
- Standardize `10-data` bundle numbering with five-digit zero-padded identifiers.
- Provide template-first artifact creation so generated outputs stay consistent.
- Store expert review question/gap/finding language in templates (not inline script constants).
- Route unhandled file formats to the richer extraction pipeline used by `agile-coach-intake-normalizer`.
- Govern canonical prompt entrypoints owned by `agile-coach`:
  - `/artifacts-testdata-2-input`
  - `/artifacts-input-2-data`
  - `/artifacts-data-2-specification`
  - `/artifacts-specification-2-stage stage="<stage>"`
  - `/artifacts-specification-2-planning stage="<stage>"`
- Support transparent, stakeholder-readable companion documentation in `docs/wiki/` when planning artifacts are synthesized from specifications.

## Composition Model

- `artifacts` is the foundation skill for structure, templates, inventory, and numbering.
- Prompt orchestration is centralized under `skills/artifacts/scripts/`.
- `artifacts-input-2-data` remains a runtime ingest dependency, while prompt ownership and entry contracts are governed by this skill.

## Managed Structure

```text
.digital-artifacts/
├── 00-input/
├── 10-data/
├── 20-done/
├── 30-specification/
├── 40-stage/
├── 50-planning/
└── 60-review/
```

## Managed Files

### INVENTORY.md

This skill maintains append-only inventory files in:

- `10-data/INVENTORY.md`
- `20-done/INVENTORY.md`
- `30-specification/INVENTORY.md`
- `40-stage/INVENTORY.md`
- `50-planning/INVENTORY.md`

Each new entry must include:

- item ID
- date
- source classification
- brief summary
- status

### LATEST.md

This skill maintains latest-item snapshots in:

- `40-stage/LATEST.md`
- `60-review/LATEST.md`

## Numbering and Classification

- Items under `10-data/YYYY-MM-DD/` use five-digit IDs: `00000` to `99999`.
- The sequence is per-date and increments from the highest existing bundle ID.
- Source classification is derived from the `00-input` subfolder name and stored in metadata.

## Entry Script

- `scripts/artifacts-bootstrap.sh`
- `scripts/artifacts_tool.py`

These scripts must be called before write-heavy artifact workflows.
The bootstrap script reads the template tree and creates missing folders and managed files without overwriting existing user content.

The Python utility provides operational subcommands for:

- bundle allocation under `10-data`
- inventory entry upsert
- `LATEST.md` snapshot updates

### Prompt Entry Scripts (Owner: agile-coach)

- `/artifacts-testdata-2-input` → `scripts/artifacts-testdata-2-input.sh`
  - Bootstraps `.digital-artifacts/`, refills fixtures into `00-input/documents`, then triggers `input -> data`.
- `/artifacts-input-2-data` → `scripts/artifacts-input-2-data.sh`
  - Runs normalized ingest (`00-input -> 10-data`), English-focused `.txt` interpretation, inventory/audit updates, and source archive move to `20-done`.
- `/artifacts-data-2-specification` → `scripts/artifacts-data-2-specification.sh`
  - Always generates or updates `30-specification/<date>/<item>/<item>-specification.md` for every normalized data bundle; incompleteness is reflected via checklist/scoring.
- `/artifacts-specification-2-stage stage="<stage>"` → `scripts/artifacts-specification-2-stage.sh`
  - Evaluates stage readiness from specification completeness and creates/updates only the canonical stage document in `40-stage/<STAGE>.md` using `status: in-progress|active`.
- `/artifacts-specification-2-planning stage="<stage>"` → `scripts/artifacts-specification-2-planning.sh`
  - Activates only when the canonical stage document exists, prepares template-based planning artifacts in `50-planning/<stage>/`, enriches planning with parallel stakeholder-readable `docs/wiki/` explanation pages and linked visuals where useful, enforces anti-placeholder content quality, injects milestone metadata for sprint preparation, checks or creates stage-scoped GitHub projects when possible, and records generic-deliver trigger preparation.

### Specification Completeness Model

- Canonical specification path per bundle: `.digital-artifacts/30-specification/<date>/<item_code>/<item_code>-specification.md`
- Specification generation is mandatory for every bundle.
- Missing information is expressed through checklist items and low readiness scores, not by skipping specification creation.

### Transition Orchestrator

- `scripts/artifacts_flow.py`
  - `data-to-specification`
  - `specification-to-stage --stage <stage>`
  - `specification-to-planning --stage <stage>`

### Planning Assessment Contract

- The planning transition emits a stage-scoped assessment artifact:
  - `.digital-artifacts/50-planning/<stage>/project-assessment.md`
- The same path is returned in the command result payload as `assessment_path`.
- This file is a first-class planning artifact and must remain stable unless an explicit migration updates:
  - producer code (`artifacts_flow_planning.py`),
  - consumer expectations (if any),
  - skill/process documentation.

### Expert Review Language Contract

- Source of truth for role-specific review wording:
  - `templates/digital-artifacts/30-specification/REVIEW_QUESTION_BANK.yaml`
- Scripts in `artifacts_flow_data_to_spec.py` must consume this template data.
- Hardcoded question banks in Python are allowed only as runtime fallback when template loading fails.

## Dependencies

- `../shared/shell/scripts/lib/common.sh`
- `markitdown` for primary document conversion flows
- fallback extraction logic from `agile-coach-intake-normalizer` for unsupported formats

## Permissions

The normative access matrix is stored in `templates/digital-artifacts/PERMISSIONS.csv`.
Agents must not perform operations outside their declared permissions.
