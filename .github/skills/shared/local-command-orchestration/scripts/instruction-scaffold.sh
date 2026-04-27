#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Create a governed instruction scaffold for domain or stage instructions.
# Security:
#   Validates target names and writes only inside the repository .github source path.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
INSTRUCTIONS_DIR="$REPO_ROOT/.github/instructions"
INSTRUCTION_CATEGORY="${INSTRUCTION_CATEGORY:-}"
INSTRUCTION_NAME="${INSTRUCTION_NAME:-}"
INSTRUCTION_PURPOSE="${INSTRUCTION_PURPOSE:-describe the instruction purpose}"
CURRENT_LAYER="$(basename "$REPO_ROOT")"

progress() {
  printf '[progress][instruction-scaffold] %s\n' "$1"
}

if [[ -z "$INSTRUCTION_CATEGORY" || -z "$INSTRUCTION_NAME" ]]; then
  echo "[ERROR] INSTRUCTION_CATEGORY and INSTRUCTION_NAME are required (example: make scaffold-instruction INSTRUCTION_CATEGORY=stages INSTRUCTION_NAME=40-mvp INSTRUCTION_PURPOSE='stage guidance')" >&2
  exit 1
fi

if [[ ! "$INSTRUCTION_CATEGORY" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[ERROR] INSTRUCTION_CATEGORY must match ^[a-z0-9]+(-[a-z0-9]+)*$" >&2
  exit 1
fi

if [[ ! "$INSTRUCTION_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "[ERROR] INSTRUCTION_NAME must match ^[a-z0-9]+(-[a-z0-9]+)*$" >&2
  exit 1
fi

TARGET_DIR="$INSTRUCTIONS_DIR/$INSTRUCTION_CATEGORY"
TARGET_FILE="$TARGET_DIR/$INSTRUCTION_NAME.instructions.md"
if [[ -e "$TARGET_FILE" ]]; then
  echo "[ERROR] Instruction file already exists: ${TARGET_FILE#$REPO_ROOT/}" >&2
  echo "[ERROR] Refusing to override existing instruction scaffolding automatically." >&2
  exit 1
fi

progress 'step=1/2 action=create-instruction-file'
mkdir -p "$TARGET_DIR"
cat > "$TARGET_FILE" <<EOF
---
name: "$INSTRUCTION_CATEGORY / $INSTRUCTION_NAME"
description: "$INSTRUCTION_PURPOSE"
layer: $CURRENT_LAYER
---

# $INSTRUCTION_NAME

## Scope

- Applies to: describe the target audience.
- When to use: describe the execution context.

## Standards

- Keep the guidance deterministic and auditable.
- Link to related instructions when overlap exists.

## Process

1. Define the intended workflow.
2. Document required checks and exit criteria.
3. Reference downstream artifacts or handoffs when relevant.

## References

- Related instruction paths.
- External standards or platform references.
EOF

progress 'step=2/2 action=complete'
printf 'instruction-scaffold: created %s\n' "${TARGET_FILE#$REPO_ROOT/}"