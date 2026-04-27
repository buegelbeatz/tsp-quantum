#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Provide governance permission checks and handoff schema validation helpers.
# Security:
#   Performs file-bound validation only and avoids unsafe dynamic execution.

# shellcheck shell=bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/common.sh"
# shellcheck source=/dev/null
source "${script_dir}/governance-paths.sh"
# shellcheck source=/dev/null
source "${script_dir}/governance-permissions.sh"

validate_handoff() {
  local payload_path="$1"
  local schema_path="$2"
  [[ -f "$payload_path" ]] || {
    log_error "Handoff payload not found: $payload_path"
    return 1
  }
  [[ -f "$schema_path" ]] || {
    log_error "Handoff schema not found: $schema_path"
    return 1
  }
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$payload_path" "$schema_path" <<'PY'
import sys
from pathlib import Path

payload = Path(sys.argv[1])
schema = Path(sys.argv[2])

payload_text = payload.read_text(encoding="utf-8")
schema_text = schema.read_text(encoding="utf-8")

required_markers = []
for line in schema_text.splitlines():
    stripped = line.strip()
    if stripped.startswith("required:"):
        continue
    if stripped.startswith("- "):
        required_markers.append(stripped[2:].strip())

missing = [key for key in required_markers if f"{key}:" not in payload_text]
if missing:
    print("Missing required handoff fields: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY
    return $?
  fi
  local required
  required="$(awk '/^required:/,0 { if ($1=="-") print $2 }' "$schema_path" || true)"
  local field
  while IFS= read -r field; do
    [[ -z "$field" ]] && continue
    grep -q "^${field}:" "$payload_path" || {
      log_error "Missing required handoff field: $field"
      return 1
    }
  done <<< "$required"
  return 0
}

