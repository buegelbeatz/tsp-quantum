---
layer: digital-generic-team
---
# Deprecation Map (old -> new)

Status: active
Layer: digital-generic-team

This map documents deprecated skill entrypoints and their canonical replacements.
Each mapping includes a planned removal date to keep migration deterministic.

| Legacy entrypoint | Replacement entrypoint | Scope | Deprecation date | Planned removal date | Notes |
|---|---|---|---|---|---|
| skills/prompt-update/ | skills/shared-runtime/ | Runtime refresh/update orchestration | 2026-04-20 | 2026-06-30 | Runtime behavior moved to shared runtime wrapper scripts. |
| skills/prompt-pull/ | skills/shared-delivery/ | Delivery publication / PR flow | 2026-04-20 | 2026-06-30 | Pull publication flow unified with delivery wrappers. |
| skills/prompt-layer-quality-fix/ | skills/shared-orchestration/ + skills/quality-expert/ | Layer quality remediation orchestration | 2026-04-20 | 2026-06-30 | Fix orchestration moved to shared orchestrators + quality gates. |
| skills/prompt-test-import-data/ | skills/artifacts/ + scripts/artifacts-testdata-2-input.sh | Test fixture import into artifacts pipeline | 2026-04-20 | 2026-06-30 | Prompt wrapper removed; canonical artifacts entrypoint retained. |
| skills/shared-shell/ | skills/shared/shell/ | Shared shell helper backend | 2026-04-21 | 2026-07-31 | Keep wrapper as temporary compatibility shim during namespace convergence. |
| skills/shared-runtime/ | skills/shared/runtime/ | Canonical runtime facade | 2026-04-21 | 2026-07-31 | New references should prefer the nested shared namespace path. |
| skills/shared-orchestration/ | skills/shared/orchestration/ | Canonical orchestration facade | 2026-04-21 | 2026-07-31 | Canonical public orchestration surface moves under shared/. |
| skills/shared-delivery/ | skills/shared/delivery/ | Canonical delivery facade | 2026-04-21 | 2026-07-31 | Delivery publication and PR flows converge under shared/. |
| skills/shared-pr-delivery/ | skills/shared/pr-delivery/ | PR delivery backend wrapper | 2026-04-21 | 2026-07-31 | Keep as shim until all direct references are migrated. |
| skills/shared-task-orchestration/ | skills/shared/task-orchestration/ | Task orchestration backend wrapper | 2026-04-21 | 2026-07-31 | Public docs should no longer teach this as a top-level peer. |
| skills/shared-local-command-orchestration/ | skills/shared/local-command-orchestration/ | Local command orchestration backend wrapper | 2026-04-21 | 2026-07-31 | Preserve only as migration alias. |

## Governance

- New migrations into `shared-*` MUST be appended here in the same PR.
- New references should target canonical nested entrypoints (`skills/shared/...`) where available.
- If a legacy alias stays beyond its planned removal date, add a dated exception note.
- Do not delete legacy entrypoints without a replacement path in this file.

## Shared Namespace Migration Rules

- The long-term canonical model is one visible shared namespace: `skills/shared/...`.
- Top-level `shared-*` directories are transitional aliases, not the target structure.
- Public documentation must describe nested `shared/` entrypoints first and mention top-level aliases only as migration shims.

## Execution Note (2026-04-21)

- Shared namespace migration reached alias-retirement state in this repository.
- Top-level `shared-*` skill directories were removed after caller migration.
- Canonical path model is now exclusively `skills/shared/...`.
