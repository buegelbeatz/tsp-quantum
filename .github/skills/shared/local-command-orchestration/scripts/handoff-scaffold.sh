#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Create a governed handoff schema scaffold with standard required fields.
# Security:
#   Validates target names and writes only inside the repository .github source path.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
HANDOFFS_DIR="$REPO_ROOT/.github/handoffs"
HANDOFF_NAME="${HANDOFF_NAME:-}"
HANDOFF_SCHEMA="${HANDOFF_SCHEMA:-}"

progress() {
  printf '[progress][handoff-scaffold] %s\n' "$1"
}

if [[ -z "$HANDOFF_NAME" || -z "$HANDOFF_SCHEMA" ]]; then
  echo "[ERROR] HANDOFF_NAME and HANDOFF_SCHEMA are required (example: make scaffold-handoff HANDOFF_NAME=MY_HANDOFF HANDOFF_SCHEMA=my_handoff_v1)" >&2
  exit 1
fi

if [[ ! "$HANDOFF_NAME" =~ ^[A-Z_]+$ ]]; then
  echo "[ERROR] HANDOFF_NAME must match ^[A-Z_]+$" >&2
  exit 1
fi

if [[ ! "$HANDOFF_SCHEMA" =~ ^[a-z0-9]+(_[a-z0-9]+)*_v[0-9]+$ ]]; then
  echo "[ERROR] HANDOFF_SCHEMA must match ^[a-z0-9]+(_[a-z0-9]+)*_v[0-9]+$" >&2
  exit 1
fi

TARGET_FILE="$HANDOFFS_DIR/$HANDOFF_NAME.schema.yaml"
if [[ -e "$TARGET_FILE" ]]; then
  echo "[ERROR] Handoff schema already exists: ${TARGET_FILE#$REPO_ROOT/}" >&2
  echo "[ERROR] Refusing to override existing handoff scaffolding automatically." >&2
  exit 1
fi

progress 'step=1/2 action=create-handoff-schema'
mkdir -p "$HANDOFFS_DIR"
cat > "$TARGET_FILE" <<EOF
schema: $HANDOFF_SCHEMA
type: object
required:
  - kind
  - from
  - to
  - summary
  - assumptions
  - open_questions
  - artifacts
properties:
  kind:
    type: string
  from:
    type: string
  to:
    type: string
  summary:
    type: string
  assumptions:
    type: array
    items:
      type: string
  open_questions:
    type: array
    items:
      type: string
  artifacts:
    type: array
    items:
      type: object
EOF

progress 'step=2/2 action=complete'
printf 'handoff-scaffold: created %s\n' "${TARGET_FILE#$REPO_ROOT/}"