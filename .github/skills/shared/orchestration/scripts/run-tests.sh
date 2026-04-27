#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
exec bash "$REPO_ROOT/.github/skills/shared/local-command-orchestration/scripts/run-tests.sh" "$@"
