#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Create a governed agent scaffold with canonical frontmatter and sections.
# Security:
#   Validates target names and writes only inside the repository .github source path.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
AGENTS_DIR="$REPO_ROOT/.github/agents"
AGENT_NAME="${AGENT_NAME:-}"
AGENT_PURPOSE="${AGENT_PURPOSE:-use when this agent role is needed}"
CURRENT_LAYER="$(basename "$REPO_ROOT")"

progress() {
  printf '[progress][agent-scaffold] %s\n' "$1"
}

if [[ -z "$AGENT_NAME" ]]; then
  echo "[ERROR] AGENT_NAME is required (example: make scaffold-agent AGENT_NAME=my-agent AGENT_PURPOSE='use when ...')" >&2
  exit 1
fi

if [[ ! "$AGENT_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[ERROR] AGENT_NAME must match ^[a-z0-9]+(-[a-z0-9]+)*$" >&2
  exit 1
fi

TARGET_FILE="$AGENTS_DIR/$AGENT_NAME.agent.md"
if [[ -e "$TARGET_FILE" ]]; then
  echo "[ERROR] Agent file already exists: ${TARGET_FILE#$REPO_ROOT/}" >&2
  echo "[ERROR] Refusing to override existing agent scaffolding automatically." >&2
  exit 1
fi

progress 'step=1/2 action=create-agent-file'
mkdir -p "$AGENTS_DIR"
cat > "$TARGET_FILE" <<EOF
---
name: $AGENT_NAME
description: "Use when: $AGENT_PURPOSE"
layer: $CURRENT_LAYER
user-invocable: false
tools: []
handoffs:
  - work_handoff_v1
---

## Mission

$AGENT_PURPOSE.

## Responsibilities

- Define the agent scope in concrete operational terms.
- Document the handoff expectations before first use.
- Reference the skills this agent is expected to invoke.

## Handoff Rules

- Use only governed handoff schemas.
- Keep assumptions and open questions explicit.

## Preferred Skills

- .github/skills/shared/task-orchestration/SKILL.md

## Not Responsible For

- Work outside the defined role boundary.
- Silent continuation when a governed handoff is required.
EOF

progress 'step=2/2 action=complete'
printf 'agent-scaffold: created %s\n' "${TARGET_FILE#$REPO_ROOT/}"