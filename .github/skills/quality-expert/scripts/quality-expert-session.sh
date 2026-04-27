#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Execute the shared quality session and publish one canonical report artifact
#   that can be consumed by layer-quality, engineering workflows, and reviewers.
# Security:
#   Delegates to the established quality runner and keeps all checks local.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"

RUN_TOOL="$REPO_ROOT/.github/skills/shared/runtime/scripts/run-tool.sh"
GATE_RUNNER="$SCRIPT_DIR/quality-gate-runner.sh"
SESSION_RUNTIME_HELPERS="$SCRIPT_DIR/quality-expert-session-runtime.sh"
SESSION_PARALLEL_HELPERS="$SCRIPT_DIR/quality-expert-session-parallel.sh"
SESSION_FLOW_HELPERS="$SCRIPT_DIR/quality-expert-session-flow.sh"
REPORT_DIR="$REPO_ROOT/.tests/python/reports"
CANONICAL_REPORT="$REPORT_DIR/quality-expert-session.md"
COVERAGE_DIR="$REPO_ROOT/.tests/python/coverage"
COVERAGE_FILE_PATH="$COVERAGE_DIR/.coverage"
COVERAGE_JSON_PATH="$REPORT_DIR/coverage.json"
RUNTIME_VENV_BIN="${DIGITAL_TEAM_SHARED_VENV_PATH:-$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin}"
RUNTIME_VENV_PYTHON="$RUNTIME_VENV_BIN/python"

mkdir -p "$REPORT_DIR"
mkdir -p "$COVERAGE_DIR"

if [[ ! -x "$RUN_TOOL" ]]; then
  echo "quality-expert: missing run-tool helper at $RUN_TOOL" >&2
  exit 1
fi

for helper in "$SESSION_RUNTIME_HELPERS" "$SESSION_PARALLEL_HELPERS" "$SESSION_FLOW_HELPERS"; do
  if [[ ! -f "$helper" ]]; then
    echo "quality-expert: missing helper at $helper" >&2
    exit 1
  fi
done

if [[ ! -x "$RUNTIME_VENV_PYTHON" ]]; then
  echo "quality-expert: missing layer runtime python at $RUNTIME_VENV_PYTHON" >&2
  echo "quality-expert: run 'make layer-venv-sync' first." >&2
  exit 1
fi

source "$SESSION_RUNTIME_HELPERS"
source "$SESSION_PARALLEL_HELPERS"
source "$SESSION_FLOW_HELPERS"

require_runtime_package "pytest"
require_runtime_package "pytest-cov"
require_runtime_package "coverage"
require_runtime_package "ruff"
require_runtime_package "mypy"
require_runtime_package "bandit"

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
declare -i overall_fail=0

QUALITY_SCOPE_MODE="${QUALITY_SCOPE_MODE:-auto}"
configure_quality_targets

# State dir for parallel gate management (no arrays needed, just files)
PARALLEL_STATE_DIR="$(mktemp -d)"
trap "rm -rf '$PARALLEL_STATE_DIR'" EXIT

initialize_quality_report
run_quality_sections

if [[ "${QUALITY_EXPERT_FAIL_ON_GATES:-0}" == "1" ]] && [[ "$overall_fail" -ne 0 ]]; then
  echo "Quality expert report written: $CANONICAL_REPORT (failing gates detected)"
  exit 1
fi

echo "Quality expert report written: $CANONICAL_REPORT"
