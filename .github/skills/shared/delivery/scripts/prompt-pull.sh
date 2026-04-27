#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Consolidated entrypoint for /pull delivery workflow.
# Security:
#   Executes only local git status checks and prints deterministic guidance.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

cd "$REPO_ROOT"

echo "[progress][pull] step=1/2 action=collect-git-status"
git --no-pager status --short

echo "[progress][pull] step=2/2 action=shared/delivery-entrypoint"
echo "shared/delivery: prompt-pull wrapper is active."
echo "shared/delivery: use PR automation scripts under .github/skills/shared/pr-delivery/ as they are introduced."
