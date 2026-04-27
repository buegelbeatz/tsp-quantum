---
name: git
description: Controlled, auditable git operations with role-based permission checks.
layer: digital-generic-team
---

# Skill: Git

This skill provides controlled access to git operations for agents.

## Capabilities

- Repository status inspection (`git-status.sh`)
- Commit log inspection (`git-log.sh`)
- Diff inspection (`git-diff.sh`)
- Annotated tag creation (`git-tag-create.sh`) for allowed roles only
- Branch create and checkout (`git-branch-create.sh`) for delivery roles
- Controlled staging (`git-stage-add.sh`) for allowed delivery roles
- Controlled commit creation (`git-commit-create.sh`) for allowed delivery roles
- Controlled branch push (`git-push-branch.sh`) for allowed delivery roles

## Permission Model

Each script requires `--role` and validates the requested operation against `PERMISSIONS.csv`.
Unauthorized operations fail with structured YAML error output.

## Output Contract

- Read operations output YAML with `status: ok` and payload fields.
- Write operations output YAML with `status: ok` and operation metadata.
- Authorization failures output YAML with `status: error`.

## Dependencies

- `../shared/shell/scripts/lib/common.sh`
- local `git` binary
