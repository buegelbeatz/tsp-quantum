---
layer: digital-generic-team
---
# GitHub Shared Scripts

## Purpose

Reusable GitHub automation scripts for all Layer 1 agents.

## Structured read outputs

The following scripts emit structured YAML for downstream skills:

- `gh-token-report.sh`
- `gh-boards-list.sh`
- `gh-issues-list.sh`
- `gh-wiki-list-pages.sh`

## Write operations

- `gh-board-create.sh`
- `gh-board-items-add.sh`
- `gh-board-item-update.sh`
- `gh-issue-comment.sh`
- `gh-issue-checklist-set.sh`
- `gh-wiki-create.sh`
- `gh-wiki-page-add.sh`
- `gh-wiki-page-edit.sh`

## Runtime cache layout

- `.digital-runtime/github/reports/`
- `.digital-runtime/github/cache/`
- `.digital-runtime/github/wiki-cache/`
