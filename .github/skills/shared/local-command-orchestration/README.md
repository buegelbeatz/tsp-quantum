---
layer: digital-generic-team
---
# shared/local-command-orchestration

Orchestrates local update and test execution with container-aware runtime selection.

## Update

Trigger the full layer update (Phase 1: `.github/` merge, Phase 2: `.claude/` adaptation):

```bash
# Primary entry point — use this in Claude Code
/update

# Via make
make update

# Direct script invocation (for CI or scripted workflows)
bash update.sh
```

The update engine reads `.digital-team/layers.yaml`, clones each parent layer, merges `.github/` content in inheritance order, and then derives `.claude/` from the result.

## Test execution

Run the full quality gate (lint → tests → coverage) via container or local venv:

```bash
make test
```

Container runtime priority: `podman` → `apptainer/singularity` → `docker` → local fallback.

The test runner uses the Python venv at `.digital-runtime/layers/<layer-id>/venv/` if present, otherwise falls back to the system `python3`.

Optional environment flags:

| Flag | Default | Description |
|------|---------|-------------|
| `DIGITAL_TEAM_TEST_RUNTIME` | auto | Force `local` or `container` |
| `DIGITAL_TEAM_TEST_ARGS` | — | Extra pytest arguments (e.g. `'-q -k sprint'`) |
| `DIGITAL_TEAM_ALLOW_LOCAL_FALLBACK` | `0` | Allow local execution when no container is available |

## Quality checks

```bash
make quality    # ruff check + mypy
```
