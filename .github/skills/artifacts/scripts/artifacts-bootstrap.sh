#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Bootstrap .digital-artifacts directory structure from governed templates.
# Security:
#   Copies known template files only and avoids dynamic command evaluation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_ROOT="$SKILL_DIR/templates/digital-artifacts"
TARGET_ROOT="${1:-.digital-artifacts}"

copy_if_missing() {
  local source_path="$1"
  local target_path="$2"

  if [[ -e "$target_path" ]]; then
    return 0
  fi

  mkdir -p "$(dirname "$target_path")"
  cp "$source_path" "$target_path"
}

mkdir -p "$TARGET_ROOT"

# Runtime directory scaffold only (no template fixture trees in runtime state)
for relative_dir in \
  "00-input/documents" \
  "00-input/features" \
  "00-input/bugs" \
  "10-data" \
  "20-done" \
  "30-specification" \
  "40-stage" \
  "50-planning" \
  "60-review" \
  "70-audits"
do
  mkdir -p "$TARGET_ROOT/$relative_dir"
done

# Managed files materialized from templates
copy_if_missing "$TEMPLATE_ROOT/10-data/INVENTORY.template.md" "$TARGET_ROOT/10-data/INVENTORY.md"
copy_if_missing "$TEMPLATE_ROOT/20-done/INVENTORY.template.md" "$TARGET_ROOT/20-done/INVENTORY.md"
copy_if_missing "$TEMPLATE_ROOT/30-specification/INVENTORY.template.md" "$TARGET_ROOT/30-specification/INVENTORY.md"
copy_if_missing "$TEMPLATE_ROOT/40-stage/INVENTORY.template.md" "$TARGET_ROOT/40-stage/INVENTORY.md"
copy_if_missing "$TEMPLATE_ROOT/40-stage/LATEST.template.md" "$TARGET_ROOT/40-stage/LATEST.md"
copy_if_missing "$TEMPLATE_ROOT/50-planning/INVENTORY.template.md" "$TARGET_ROOT/50-planning/INVENTORY.md"
copy_if_missing "$TEMPLATE_ROOT/60-review/LATEST.template.md" "$TARGET_ROOT/60-review/LATEST.md"

# Cleanup of previously leaked template-only runtime artifacts
rm -rf "$TARGET_ROOT/99-testdata" "$TARGET_ROOT/Users"
rm -f "$TARGET_ROOT/10-data/DATA_CONTENT.md" "$TARGET_ROOT/PERMISSIONS.csv"

printf 'status: ok\nroot: %s\n' "$TARGET_ROOT"
