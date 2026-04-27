#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Create a governed skill scaffold with canonical SKILL.md sections and layout.
# Security:
#   Validates target names and writes only inside the repository .github source path.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
SKILLS_DIR="$REPO_ROOT/.github/skills"
SKILL_NAME="${SKILL_NAME:-}"
SKILL_PURPOSE="${SKILL_PURPOSE:-use when this workflow is needed}"
CURRENT_LAYER="$(basename "$REPO_ROOT")"

progress() {
  printf '[progress][skill-scaffold] %s\n' "$1"
}

if [[ -z "$SKILL_NAME" ]]; then
  echo "[ERROR] SKILL_NAME is required (example: make scaffold-skill SKILL_NAME=my-skill SKILL_PURPOSE='use when ...')" >&2
  exit 1
fi

if [[ ! "$SKILL_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[ERROR] SKILL_NAME must match ^[a-z0-9]+(-[a-z0-9]+)*$" >&2
  exit 1
fi

SKILL_DIR="$SKILLS_DIR/$SKILL_NAME"
SKILL_FILE="$SKILL_DIR/SKILL.md"
if [[ -e "$SKILL_FILE" || -d "$SKILL_DIR" ]]; then
  echo "[ERROR] Skill already exists: ${SKILL_DIR#$REPO_ROOT/}" >&2
  echo "[ERROR] Refusing to override existing skill scaffolding automatically." >&2
  exit 1
fi

progress 'step=1/3 action=create-skill-layout'
mkdir -p "$SKILL_DIR/scripts/tests" "$SKILL_DIR/templates"
touch "$SKILL_DIR/requirements.txt"

progress 'step=2/3 action=create-skill-file'
cat > "$SKILL_FILE" <<EOF
---
name: $SKILL_NAME
description: "$SKILL_PURPOSE"
layer: $CURRENT_LAYER
---

# Skill: $SKILL_NAME

## Purpose

$SKILL_PURPOSE.

## Outputs

- Deterministic runtime behavior
- Documented entry points and outputs

## Dependencies

- .github/skills/shared/shell/SKILL.md

## Information Flow

- Producer: the invoking prompt, agent, or workflow.
- Consumer: downstream agents, reviewers, or generated artifacts.
- Trigger: explicit invocation of this skill.
- Payload summary: normalized inputs, execution steps, and resulting outputs.
EOF

progress 'step=3/3 action=complete'
printf 'skill-scaffold: created %s\n' "${SKILL_DIR#$REPO_ROOT/}"