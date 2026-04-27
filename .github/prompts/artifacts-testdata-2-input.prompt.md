<!-- layer: digital-generic-team -->
# /artifacts-testdata-2-input Prompt

Run one deterministic flow from template fixtures to normalized data bundles.

## Default command

```bash
make artifacts-testdata-2-input
```

## Execution contract

- Bootstrap `.digital-artifacts/` from governed templates.
- Copy all files from `99-testdata/` to `.digital-artifacts/00-input/documents/`.
- Report credential readiness for vision and Klaxoon integrations.
- Do **NOT** trigger `artifacts-input-2-data` — that is a separate explicit prompt.

## Documentation contract

- This prompt is test-context only.
- Never creates or updates boards, tickets, or wiki pages.
- Writes only local artifacts under `.digital-artifacts/`.

## Verification

- Progress markers are emitted as:
  `[progress][artifacts-testdata-2-input] step=<x/y> action=<name>`
- Required milestones: `bootstrap`, `fixture-refill`, `environment-summary`, `completion`.
