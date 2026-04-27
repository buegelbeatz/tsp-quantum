#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Validate generated SVG assets used by project delivery/reporting before users see broken files.
# Exit codes:
#   0 -> all discovered SVG files parse correctly
#   4 -> one or more SVG files are invalid
#   2 -> usage error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${DIGITAL_REPO_ROOT:-$(cd "$SCRIPT_DIR/../../../.." && pwd)}"

STAGE="${1:-${STAGE:-}}"
PYTHON_BIN="${2:-python3}"
if [[ -z "$STAGE" ]]; then
  echo "usage: validate-svg-assets.sh <stage> [python-bin]"
  exit 2
fi

status_dir="$REPO_ROOT/.digital-artifacts/60-review/$(date -u +%Y-%m-%d)/$STAGE"
status_file="$status_dir/SVG_ASSET_STATUS.md"
mkdir -p "$status_dir"

svg_dirs=(
  "$REPO_ROOT/docs/ux/scribbles"
  "$REPO_ROOT/docs/wiki/ux-scribbles"
  "$REPO_ROOT/docs/images/mermaid"
)

total_count=0
invalid_count=0
valid_lines=""
invalid_lines=""

for svg_dir in "${svg_dirs[@]}"; do
  [[ -d "$svg_dir" ]] || continue
  while IFS= read -r svg_file; do
    [[ -n "$svg_file" ]] || continue
    total_count=$((total_count + 1))

    rel_path="${svg_file#"$REPO_ROOT"/}"
    if "$PYTHON_BIN" - "$svg_file" <<'PY' >/dev/null 2>&1
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
root = ET.parse(path).getroot()
if not root.tag.lower().endswith("svg"):
    raise ValueError("root element is not svg")
PY
    then
      valid_lines+="- ${rel_path}"$'\n'
    else
      invalid_count=$((invalid_count + 1))
      invalid_lines+="- ${rel_path}"$'\n'
      echo "[stages-action][svg] INVALID: ${rel_path}"
    fi
  done < <(find "$svg_dir" -type f -name '*.svg' | sort)
done

{
  echo "# SVG Asset Status (${STAGE})"
  echo ""
  echo "- generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- stage: ${STAGE}"
  echo "- total_svg_files: ${total_count}"
  echo "- invalid_svg_files: ${invalid_count}"
  echo ""
  echo "## Invalid"
  echo ""
  if [[ -n "$invalid_lines" ]]; then
    printf '%s' "$invalid_lines"
  else
    echo "- none"
  fi
  echo ""
  echo "## Valid"
  echo ""
  if [[ -n "$valid_lines" ]]; then
    printf '%s' "$valid_lines"
  else
    echo "- none"
  fi
} > "$status_file"

echo "[stages-action][svg] INFO: total=${total_count} invalid=${invalid_count} -> ${status_file#"$REPO_ROOT"/}"

if [[ "$invalid_count" != "0" ]]; then
  exit 4
fi

exit 0
