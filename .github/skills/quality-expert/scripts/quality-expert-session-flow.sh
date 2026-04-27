#!/usr/bin/env bash
# layer: digital-generic-team

# Purpose:
#   Provide scope selection and execution flow for quality-expert-session.
# Security:
#   Computes local targets only and executes existing validated gate functions.

configure_quality_targets() {
  QUALITY_SCOPE_MODE="${QUALITY_SCOPE_MODE:-auto}"
  QUALITY_SCOPE="layer"
  if [[ "$QUALITY_SCOPE_MODE" == "app" ]]; then
    QUALITY_SCOPE="app"
  elif [[ "$QUALITY_SCOPE_MODE" == "auto" ]]; then
    if [[ -d "$REPO_ROOT/.github" ]] && [[ -d "$REPO_ROOT/src" || -d "$REPO_ROOT/app" || -d "$REPO_ROOT/tests" ]]; then
      QUALITY_SCOPE="app"
    fi
  fi

  if [[ "$QUALITY_SCOPE" == "app" ]]; then
    TEST_TARGETS="tests"
    [[ -d "$REPO_ROOT/tests" ]] || TEST_TARGETS="."
    COVERAGE_TARGET="${QUALITY_COVERAGE_TARGET:-src}"
    [[ -d "$REPO_ROOT/$COVERAGE_TARGET" ]] || COVERAGE_TARGET="."

    NON_HIDDEN_TARGETS=""
    for entry in "$REPO_ROOT"/*; do
      [[ -e "$entry" ]] || continue
      rel="${entry#${REPO_ROOT}/}"
      NON_HIDDEN_TARGETS+=" ${rel}"
    done
    NON_HIDDEN_TARGETS="${NON_HIDDEN_TARGETS# }"
    [[ -n "$NON_HIDDEN_TARGETS" ]] || NON_HIDDEN_TARGETS="."
  else
    TEST_TARGETS=".github/skills .tests"
    COVERAGE_TARGET=".github/skills"
    NON_HIDDEN_TARGETS="."
  fi
}

initialize_quality_report() {
  {
    printf '# Quality Expert Session Report\n\n'
    printf -- '- generated_at: %s\n' "$timestamp"
    printf -- '- repo: %s\n\n' "$REPO_ROOT"
  } > "$CANONICAL_REPORT"
}

run_quality_sections() {
  # Performance: step 1 runs pytest once and writes .coverage; step 2 reads the cached
  # .coverage file via 'coverage report' — no second full test run.
  # QUALITY_SKIP_TESTS is intentionally ignored: test and coverage gates are mandatory.
  printf '[progress][quality-expert-session] phase=1/2 action=unified-tests-coverage status=start\n'
  if [[ "${QUALITY_SKIP_TESTS:-0}" == "1" ]]; then
    printf '[progress][quality-expert-session] action=warning status=ignored QUALITY_SKIP_TESTS=1 reason=mandatory-test-and-coverage-gates\n'
  fi
  append_section "Layer test suite" \
    "pytest $TEST_TARGETS -v --cov=$COVERAGE_TARGET --cov-report=term --cov-report=json:$COVERAGE_JSON_PATH" \
    1 8 sequential
  append_section "Coverage >= 80%" \
    "coverage report --fail-under=80" \
    2 8 sequential

  printf '[progress][quality-expert-session] phase=1/2 action=start-parallel-gates\n'
  append_section "Ruff lint" "ruff check $NON_HIDDEN_TARGETS" 3 8 parallel
  append_section "Mypy type check" "MYPYPATH=\"$COVERAGE_TARGET\" mypy --ignore-missing-imports --cache-dir=\".digital-runtime/layers/python-runtime/mypy-cache\" $COVERAGE_TARGET" 4 8 parallel
  append_section "Sensitive data pattern scan" "if grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=.tests --exclude-dir=node_modules --exclude-dir=.digital-runtime --exclude=\"*.lock\" -E '(AKIA[0-9A-Z]{16}|SECRET_KEY\\s*=\\s*[^[:space:]]+)' $NON_HIDDEN_TARGETS; then exit 1; fi" 5 8 parallel
  append_section "OWASP risk pattern scan" "if grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=.tests --exclude-dir=node_modules --exclude-dir=.digital-runtime --exclude=\"*.sh\" -E '(eval\\(|exec\\(|pickle\\.loads\\(|yaml\\.load\\()' $NON_HIDDEN_TARGETS; then exit 1; fi" 6 8 parallel
  append_section "Endpoint exposure scan" "if grep -RIn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=venv --exclude-dir=.tests --exclude-dir=node_modules --exclude-dir=.digital-runtime --exclude=\"*.sh\" -E '(0\\.0\\.0\\.0:|--host=0\\.0\\.0\\.0|app\\.run\\(host=\\\"0\\.0\\.0\\.0\\\")' $NON_HIDDEN_TARGETS; then exit 1; fi" 7 8 parallel
  append_section "Bandit OWASP SAST scan" "bandit -r $COVERAGE_TARGET -q -ll -ii" 8 8 parallel

  printf '[progress][quality-expert-session] phase=2/2 action=collect-parallel-results status=start\n'
  collect_parallel_sections
  printf '[progress][quality-expert-session] phase=2/2 action=collect-parallel-results status=done\n'
}