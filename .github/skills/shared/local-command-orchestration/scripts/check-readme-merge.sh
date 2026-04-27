#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Run focused README-merge regression checks for layered update behavior.
# Security:
#   Executes a constrained local pytest command without external mutations.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
TEST_RUNNER_SH="$REPO_ROOT/.github/skills/shared/local-command-orchestration/scripts/run-tests.sh"
PYTHON_VENV_BIN=""
TEST_EXPR="${DIGITAL_TEAM_README_MERGE_TEST_EXPR:-merges_layer_readmes_into_github_targets or backup_excludes_root_readme}"

progress() {
  local step="$1"
  printf '[progress][check-readme-merge] %s\n' "$step"
}

for candidate in "$REPO_ROOT"/.digital-runtime/layers/*/venv/bin/python; do
  if [[ -x "$candidate" ]]; then
    PYTHON_VENV_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_VENV_BIN" ]]; then
  echo "Missing test python environment: $PYTHON_VENV_BIN" >&2
  echo "Run: make layer-venv-sync" >&2
  exit 1
fi

progress "step=1/2 action=run_focused_readme_merge_tests"
DIGITAL_TEAM_TEST_COMMAND="$PYTHON_VENV_BIN -m pytest -q .digital-team/scripts/tests/test_root_bootstrap_scripts.py -k '$TEST_EXPR'" \
  bash "$TEST_RUNNER_SH"

progress "step=2/2 action=complete"
echo "check-readme-merge: completed"
