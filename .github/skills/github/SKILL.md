---
name: github
description: Authenticated GitHub operations with role-based permission controls.
layer: digital-generic-team
---

# Skill: GitHub

This skill provides authenticated GitHub operations for all agents.

## Capabilities

- Validate GH token and report required scopes (`gh-token-report.sh`).
- Read boards/projects in YAML (`gh-boards-list.sh`).
- Create boards/projects (`gh-board-create.sh`).
- Add issues to boards (`gh-board-items-add.sh`).
- Update board items and issue metadata (`gh-board-item-update.sh`).
- Read issues in YAML (`gh-issues-list.sh`).
- Add issue comments (`gh-issue-comment.sh`).
- Update checklist markers in issue body (`gh-issue-checklist-set.sh`).
- Read wiki pages in YAML (`gh-wiki-list-pages.sh`).
- Create/enable wiki and initialize pages (`gh-wiki-create.sh`).
- Add and edit wiki pages (`gh-wiki-page-add.sh`, `gh-wiki-page-edit.sh`).
- Create pull requests (`gh-pr-create.sh`).
- Comment on pull requests (`gh-pr-comment.sh`).

## Governance Contract

- This is the dedicated external system data-maintenance skill for GitHub.
- Skill ownership and policy governance belong to `agile-coach`.
- Execution gates for board/wiki synchronization:
	- `GH_TOKEN` is present.
	- `GH_TOKEN` is valid for required GitHub scopes.
	- `.digital-team/board.yaml` sets `primary_system: github`.
- If any gate fails, skip GitHub write sync and keep local sources (`refs/board/*`, `docs/wiki/`) authoritative.
- Generic deliver agents perform git/repository mutation workflows; `agile-coach` governs policy and flow, not raw git execution.

## Provider Pattern

- Keep a stable board/wiki exchange interface while implementing provider-specific adapters.
- Current provider is GitHub; derived layers may provide Atlassian adapters without changing the handoff contract.

## Script location

- `../shared/shell/scripts/github/`

## Output contract

Read operations output structured YAML so results can be consumed by other skills.

## Runtime and cache

All cached and report artifacts are written under `.digital-runtime/github/`.

## Permissions

Permissions are defined in `PERMISSIONS.csv` with GitHub-native operation columns.
Every caller must validate role and operation before write operations.
