#!/usr/bin/env bash
# layer: digital-generic-team
# Purpose:
#   Shared helper functions for git skill operations: output formatting,
#   YAML result encoding, and role-based permission checking via PERMISSIONS.csv.
# Security:
#   Reads PERMISSIONS.csv to enforce allowed operations per role.
#   No external network calls; all operations are local git and CSV reads.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SHARED_LIB_DIR="$(cd "$SKILL_DIR/../shared/shell/scripts/lib" && pwd)"

# shellcheck source=/dev/null
source "$SHARED_LIB_DIR/common.sh"

PERMISSIONS_CSV="$SKILL_DIR/PERMISSIONS.csv"

git_yaml_error() {
  local message="$1"
  printf 'kind: "git_operation"\n'
  printf 'status: "error"\n'
  printf 'message: "%s"\n' "$message"
}

git_yaml_ok() {
  local operation="$1"
  printf 'kind: "git_operation"\n'
  printf 'status: "ok"\n'
  printf 'operation: "%s"\n' "$operation"
}

require_permission() {
  local role="$1"
  local operation="$2"

  if [[ -z "$role" ]]; then
    git_yaml_error "--role is required"
    exit 2
  fi

  if [[ ! -f "$PERMISSIONS_CSV" ]]; then
    git_yaml_error "Permissions file not found: $PERMISSIONS_CSV"
    exit 2
  fi

  local decision
  decision="$(python3 - <<'PY' "$PERMISSIONS_CSV" "$role" "$operation"
import csv
import sys

path, role, operation = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter=";")
    for row in reader:
        if row.get("role") == role:
            print(row.get(operation, "").strip().lower())
            break
    else:
        print("")
PY
)"

  if [[ "$decision" != "yes" ]]; then
    git_yaml_error "Role '$role' is not permitted for operation '$operation'"
    exit 3
  fi
}
