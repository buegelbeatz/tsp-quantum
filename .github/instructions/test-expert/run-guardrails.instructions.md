---
name: "Test-expert / Test-run-guardrailss"
description: "Test-Run Guardrails"
layer: digital-generic-team
---
# Test-Run Guardrails


## Scope

Operational guardrails for test execution in all layer and app repositories.

## Mandatory rules

- **NEVER** run tests directly via `python3 -m pytest` or `python -m pytest` in the terminal.
- Always delegate test execution to the `/test` prompt, which uses `make run-tests`.
- `make run-tests` selects the correct runtime by repository type: app repositories prefer the root `.venv`, layer repositories prefer `.digital-runtime/layers/python-runtime/venv`, and only then fall back to `python3`.
- Use `runtime=container` when a standardized container runtime is required.
- Layer 1 content is public-facing by default; never embed internal URLs or stack details.
- Processed `.input` files must be archived only under repository root `.done/YYYY-MM-DD/`.
- Do not create or use `.input/processed`.
- Review artifacts under `artifacts/review/` are generated only at the final review gate.
- During preparation and implementation phases, do not run review generation.
- Test and coverage artifacts must stay under `.tests/<language>/`.
- Root-level `.pytest_cache` and root-level `.coverage` files are not allowed.
- Use standardized issue templates for Epic, Story, and Task to keep issue quality consistent.

## Test execution pattern

```bash
# Correct — always use this
DIGITAL_TEAM_TEST_TARGET=<path> make run-tests

# Forbidden — never use these directly
python3 -m pytest ...
python -m pytest ...
```

## Execution note

When these rules conflict with ad-hoc automation behavior, these guardrails take precedence and automation must be adjusted.
