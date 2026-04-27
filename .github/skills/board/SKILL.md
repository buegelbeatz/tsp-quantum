---
name: board
description: Manages one or multiple lifecycle boards stored as git blobs in configurable refs/board/* namespaces and visualizes them. Supports distributed agent coordination via atomic ticket checkout.
user-invocable: false
layer: digital-generic-team
---

# Skill: Board

Implements a git-embedded Kanban board using one or multiple namespaces as the storage backend.

## Scripts

- `scripts/board-show.py` — reads refs and renders the board in the terminal
- `scripts/board-ticket.sh` — creates, moves, locks, and pushes tickets

## Board Storage Model

Tickets are YAML blobs stored as git objects. Legacy single-board layout:

```
refs/board/backlog/<ticket-id>
refs/board/in-progress/<ticket-id>
refs/board/blocked/<ticket-id>
refs/board/done/<ticket-id>
```

Multi-board lifecycle layout:

```
refs/board/project/backlog/<ticket-id>
refs/board/exploration/in-progress/<ticket-id>
refs/board/production/done/<ticket-id>
```

A ticket blob contains:

```yaml
id: TASK-001
title: "My task"
description: |
  Detailed description.
layer: digital-generic-team
created: 2026-04-09T10:00:00Z
assigned: null
locked_by: null
locked_at: null
labels: []
```

## Atomic Agent Checkout

Agents use `checkout` + `--force-with-lease` to lock a ticket atomically:

```bash
BOARD_AGENT=my-agent-id BOARD_PUSH=1 \
  bash .github/skills/board/scripts/board-ticket.sh checkout TASK-001
```

If another agent already moved the ticket, the push fails and the agent must retry.

## Configuration

Board behavior is controlled by `.digital-team/board.yaml`:

```yaml
primary_system: github   # github | jira | none
git_board:
  enabled: true
  ref_prefix: refs/board
  default_board: project
  boards:
    project:
      ref_prefix: refs/board/project
      columns: [backlog, in-progress, blocked, done]
    exploration:
      ref_prefix: refs/board/exploration
      columns: [backlog, in-progress, blocked, done]
```

## Usage

```bash
# Show board
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 .github/skills/board/scripts/board-show.py --all
python3 .github/skills/board/scripts/board-show.py --board project

# Manage tickets
BOARD_NAME=project bash .github/skills/board/scripts/board-ticket.sh create TASK-001 "My task"
BOARD_NAME=exploration bash .github/skills/board/scripts/board-ticket.sh list
BOARD_NAME=exploration bash .github/skills/board/scripts/board-ticket.sh checkout TASK-001
BOARD_NAME=exploration bash .github/skills/board/scripts/board-ticket.sh move TASK-001 in-progress done
bash .github/skills/board/scripts/board-ticket.sh fetch --all
bash .github/skills/board/scripts/board-ticket.sh push --all
```

## Governance Contract

- `refs/board/*` is the single point of truth for board state.
- `agile-coach` owns board policy and board-related skill governance.
- Non-agile roles must request board information/actions through `agile_info_exchange_v1` routed to `agile-coach`.
- `agile-coach` does not perform git mutation operations; generic deliver agents execute git updates against board refs.
- External project systems (GitHub/Jira) are synchronized projections controlled by policy, not replacement for local board refs.

## Information Flow

| Field    | Value |
|----------|-------|
| Producer | Agent, developer, or `/board` prompt |
| Consumer | Chat output (board-show.py) / git remote (board-ticket.sh) |
| Trigger  | User invokes `/board` or agent calls board-ticket.sh |
| Payload  | Rendered Kanban board(s) / ticket YAML blob in git refs |

## Dependencies

- `git` 2.40+
- Python 3.11+ (standard library only)
- `.digital-team/board.yaml` — configuration
