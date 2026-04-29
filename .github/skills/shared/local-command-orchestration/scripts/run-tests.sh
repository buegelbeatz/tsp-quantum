#!/usr/bin/env bash
# layer: digital-generic-team
set -euo pipefail

# Purpose:
#   Run standardized test sessions in local or container runtime with stable
#   progress markers and configurable test selection.
# Security:
#   Uses explicit runtime/tool resolution and bounded command execution paths.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || pwd)"
REPO_CLASSIFICATION_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/repo-classification.sh"

# shellcheck source=/dev/null
source "$REPO_CLASSIFICATION_LIB"

TEST_RUNTIME="${DIGITAL_TEAM_TEST_RUNTIME:-container}"
TEST_TARGET="${DIGITAL_TEAM_TEST_TARGET:-.github/skills}"
TEST_ARGS_RAW="${DIGITAL_TEAM_TEST_ARGS:--q --color=yes}"
TEST_EXPR="${DIGITAL_TEAM_TEST_EXPR:-}"
TEST_COMMAND="${DIGITAL_TEAM_TEST_COMMAND:-}"
LINT_COMMAND="${DIGITAL_TEAM_LINT_COMMAND:-}"
ALLOW_LOCAL_FALLBACK="${DIGITAL_TEAM_ALLOW_LOCAL_FALLBACK:-0}"
FAIL_FAST="${DIGITAL_TEAM_TEST_FAIL_FAST:-1}"
COVERAGE_THRESHOLD="${DIGITAL_TEAM_COVERAGE_THRESHOLD:-80}"
SHOW_PROGRESS="${DIGITAL_TEAM_TEST_SHOW_PROGRESS:-0}"
COVERAGE_FILE_PATH="${DIGITAL_TEAM_COVERAGE_FILE:-$REPO_ROOT/.tests/python/coverage/.coverage}"
REPORT_DIR_REL="${DIGITAL_TEAM_TEST_REPORT_DIR_REL:-.tests/python/reports}"
REPORT_DIR="${DIGITAL_TEAM_TEST_REPORT_DIR:-$REPO_ROOT/$REPORT_DIR_REL}"
PYTEST_JUNIT_REL="${DIGITAL_TEAM_PYTEST_JUNIT_REL:-$REPORT_DIR_REL/pytest-junit.xml}"
PYTEST_RAW_LOG_REL="${DIGITAL_TEAM_PYTEST_LOG_REL:-$REPORT_DIR_REL/pytest.log}"
LINT_RAW_LOG_REL="${DIGITAL_TEAM_LINT_LOG_REL:-$REPORT_DIR_REL/lint.log}"
COVERAGE_JSON_REL="${DIGITAL_TEAM_COVERAGE_JSON_REL:-$REPORT_DIR_REL/coverage.json}"
COVERAGE_RAW_LOG_REL="${DIGITAL_TEAM_COVERAGE_LOG_REL:-$REPORT_DIR_REL/coverage.log}"
PYTEST_JUNIT_PATH="${DIGITAL_TEAM_PYTEST_JUNIT:-$REPO_ROOT/$PYTEST_JUNIT_REL}"
PYTEST_RAW_LOG_PATH="${DIGITAL_TEAM_PYTEST_LOG:-$REPO_ROOT/$PYTEST_RAW_LOG_REL}"
LINT_RAW_LOG_PATH="${DIGITAL_TEAM_LINT_LOG:-$REPO_ROOT/$LINT_RAW_LOG_REL}"
COVERAGE_JSON_PATH="${DIGITAL_TEAM_COVERAGE_JSON:-$REPO_ROOT/$COVERAGE_JSON_REL}"
COVERAGE_RAW_LOG_PATH="${DIGITAL_TEAM_COVERAGE_LOG:-$REPO_ROOT/$COVERAGE_RAW_LOG_REL}"
COVERAGE_OMIT_PATTERNS="${DIGITAL_TEAM_COVERAGE_OMIT:-*/tests/*,*/test_*.py,*/conftest.py}"
CONTAINER_IMAGE="${DIGITAL_TEAM_TEST_CONTAINER_IMAGE:-python:3.12-slim}"
CONTAINER_ENGINE="${DIGITAL_TEAM_TEST_CONTAINER_ENGINE:-}"
CONTAINER_REQUIREMENTS="${DIGITAL_TEAM_TEST_REQUIREMENTS:-}"
CONTAINER_COVERAGE_FILE="${DIGITAL_TEAM_CONTAINER_COVERAGE_FILE:-/workspace/.tests/python/coverage/.coverage}"
CONTAINER_DEPS="${DIGITAL_TEAM_TEST_CONTAINER_DEPS:-pytest pytest-cov coverage ruff}"

[[ -z "${DIGITAL_TEAM_COVERAGE_THRESHOLD+x}" && ( -n "$TEST_COMMAND" || -n "${DIGITAL_TEAM_TEST_TARGET+x}" || -n "$TEST_EXPR" ) ]] && COVERAGE_THRESHOLD="0"

mkdir -p "$(dirname "$COVERAGE_FILE_PATH")"
mkdir -p "$REPORT_DIR"

progress() {
  [[ "$SHOW_PROGRESS" == "1" ]] || return 0
  printf '[progress][test] %s\n' "$1"
}

summary() {
  [[ "$SHOW_PROGRESS" == "1" ]] || return 0
  printf '[summary][test] %s\n' "$1"
}

resolve_python_exec() {
  local candidate
  local repo_runtime_mode
  repo_runtime_mode="$(detect_runtime_repo_mode "$REPO_ROOT")"

  if [[ "$repo_runtime_mode" == "app" ]]; then
    for candidate in \
      "$REPO_ROOT/.venv/bin/python" \
      "$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python" \
      "$REPO_ROOT"/.digital-runtime/layers/*/venv/bin/python; do
      [[ -x "$candidate" ]] && { printf '%s\n' "$candidate"; return; }
    done
  else
    for candidate in \
      "$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python" \
      "$REPO_ROOT"/.digital-runtime/layers/*/venv/bin/python; do
      [[ -x "$candidate" ]] && { printf '%s\n' "$candidate"; return; }
    done
  fi

  command -v python3 >/dev/null 2>&1 && { command -v python3; return; }
  echo "python3 executable not found" >&2
  exit 1
}

resolve_container_engine() {
  local candidate
  [[ -n "$CONTAINER_ENGINE" ]] && { printf '%s\n' "$CONTAINER_ENGINE"; return; }
  for candidate in docker podman; do
    command -v "$candidate" >/dev/null 2>&1 && { printf '%s\n' "$candidate"; return; }
  done
  echo "No container engine found (docker/podman)" >&2
  exit 1
}

resolve_container_requirements() {
  local repo_runtime_mode="$1"

  if [[ -n "$CONTAINER_REQUIREMENTS" ]]; then
    printf '%s\n' "$CONTAINER_REQUIREMENTS"
    return
  fi

  if [[ "$repo_runtime_mode" == "app" ]]; then
    if [[ -f "$REPO_ROOT/requirements-dev.txt" ]]; then
      printf '%s\n' "requirements-dev.txt"
      return
    fi
    if [[ -f "$REPO_ROOT/requirements.txt" ]]; then
      printf '%s\n' "requirements.txt"
      return
    fi
  fi

  if [[ -f "$REPO_ROOT/.digital-runtime/layers/python-runtime/requirements.merged.txt" ]]; then
    printf '%s\n' ".digital-runtime/layers/python-runtime/requirements.merged.txt"
    return
  fi

  printf '\n'
}

shell_lint_command() {
  cat <<'EOF'
if command -v git >/dev/null 2>&1; then
  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    bash -n "$file"
  done < <(git ls-files '*.sh')
fi
EOF
}

build_lint_command() {
  if [[ -n "$LINT_COMMAND" ]]; then
    printf '%s\n' "$LINT_COMMAND"
    return
  fi
  local python_exec="$1"
  printf '%s\n%s\n' "$python_exec -m ruff check ." "$(shell_lint_command)"
}

build_pytest_command() {
  local python_exec="$1"
  read -r -a test_args <<<"$TEST_ARGS_RAW"
  read -r -a test_targets <<<"$TEST_TARGET"
  local command=("$python_exec" -m pytest "${test_args[@]}" --junitxml "$PYTEST_JUNIT_REL" --cov=. --cov-report=)
  [[ -n "$TEST_EXPR" ]] && command+=(-k "$TEST_EXPR")
  command+=("${test_targets[@]}")
  printf '%q ' "${command[@]}"
}

build_coverage_command() {
  local python_exec="$1"
  printf '%s\n' "$python_exec -m coverage json --pretty-print -o '$COVERAGE_JSON_REL' --omit '$COVERAGE_OMIT_PATTERNS'"
}

print_stage_header() {
  printf '\n%s\n' "$1"
}

print_status_line() {
  local status="$1"
  local message="$2"
  local color="32"
  case "$status" in
    PASSED) color="32" ;;
    FAILED) color="31" ;;
    SKIPPED) color="33" ;;
    INFO) color="36" ;;
  esac
  printf '  \033[%sm%-7s\033[0m %s\n' "$color" "$status" "$message"
}

count_git_files() {
  local pattern="$1"
  git -C "$REPO_ROOT" ls-files "$pattern" | wc -l | awk '{print $1}'
}

render_lint_summary() {
  local status="$1"
  local python_count
  local shell_count

  python_count="$(count_git_files '*.py')"
  shell_count="$(count_git_files '*.sh')"

  print_stage_header 'Lint Checks'
  if [[ "$status" -eq 0 ]]; then
    print_status_line PASSED "ruff check on repository (${python_count} Python files)"
    print_status_line PASSED "bash -n syntax validation (${shell_count} shell scripts)"
    return 0
  fi

  print_status_line FAILED 'lint stage failed'
  [[ -f "$LINT_RAW_LOG_PATH" ]] && cat "$LINT_RAW_LOG_PATH"
  return 1
}

render_pytest_summary() {
  local python_exec="$1"
  local status="$2"
  "$python_exec" "$SCRIPT_DIR/render_pytest_summary.py" "$PYTEST_JUNIT_PATH" "$PYTEST_RAW_LOG_PATH" "$status"
}

render_coverage_summary() {
  local python_exec="$1"
  "$python_exec" "$SCRIPT_DIR/render_coverage_summary.py" "$COVERAGE_JSON_PATH" "$COVERAGE_THRESHOLD" "$REPO_ROOT"
}

run_lint_stage() {
  local runtime="$1"
  local engine="$2"
  local lint_cmd="$3"
  local requirements_file="${4:-}"

  if execute_stage lint "$runtime" "( $lint_cmd ) > '$LINT_RAW_LOG_REL' 2>&1" "$engine" "$requirements_file"; then
    render_lint_summary 0
    return 0
  fi

  render_lint_summary 1
  return 1
}

run_tests_stage() {
  local runtime="$1"
  local engine="$2"
  local tests_cmd="$3"
  local python_exec="$4"
  local requirements_file="${5:-}"

  rm -f "$PYTEST_JUNIT_PATH" "$PYTEST_RAW_LOG_PATH"
  local stage_status=0
  execute_stage tests "$runtime" "( $tests_cmd ) > '$PYTEST_RAW_LOG_REL' 2>&1" "$engine" "$requirements_file" || stage_status=$?
  render_pytest_summary "$python_exec" "$stage_status"
}

run_coverage_stage() {
  local runtime="$1"
  local engine="$2"
  local coverage_cmd="$3"
  local python_exec="$4"
  local requirements_file="${5:-}"

  rm -f "$COVERAGE_JSON_PATH" "$COVERAGE_RAW_LOG_PATH"
  if execute_stage coverage "$runtime" "( $coverage_cmd ) > '$COVERAGE_RAW_LOG_REL' 2>&1" "$engine" "$requirements_file"; then
    render_coverage_summary "$python_exec"
    return $?
  fi

  print_stage_header 'Coverage Summary'
  print_status_line FAILED 'coverage stage failed'
  [[ -f "$COVERAGE_RAW_LOG_PATH" ]] && cat "$COVERAGE_RAW_LOG_PATH"
  return 1
}

resolve_effective_runtime() {
  case "$TEST_RUNTIME" in
  local)
    printf '%s\n' local
    ;;
  container)
    if command -v docker >/dev/null 2>&1 || command -v podman >/dev/null 2>&1 || [[ -n "$CONTAINER_ENGINE" ]]; then
      printf '%s\n' container
      return
    fi
    if [[ "$ALLOW_LOCAL_FALLBACK" == "1" ]]; then
      progress "runtime=container action=fallback-to-local reason=no-container-engine"
      printf '%s\n' local
      return
    fi
    echo "No container engine found and DIGITAL_TEAM_ALLOW_LOCAL_FALLBACK is disabled" >&2
    exit 1
    ;;
  *)
    echo "Unsupported DIGITAL_TEAM_TEST_RUNTIME: $TEST_RUNTIME" >&2
    exit 1
    ;;
  esac
}

run_local_command() {
  local command="$1"
  (cd "$REPO_ROOT" && FORCE_COLOR=1 COVERAGE_FILE="$COVERAGE_FILE_PATH" bash -lc "set -euo pipefail; $command")
}

run_container_command() {
  local engine="$1"
  local command="$2"
  local requirements_file="${3:-}"
  "$engine" run --rm \
    -v "$REPO_ROOT:/workspace" \
    -w /workspace \
    "$CONTAINER_IMAGE" \
    bash -lc "set -euo pipefail; export DEBIAN_FRONTEND=noninteractive PIP_ROOT_USER_ACTION=ignore PIP_DISABLE_PIP_VERSION_CHECK=1 FORCE_COLOR=1 COVERAGE_FILE='$CONTAINER_COVERAGE_FILE'; mkdir -p '.tests/python/coverage' '.tests/python/reports'; if ! command -v python3 >/dev/null 2>&1; then ln -sf /usr/local/bin/python /usr/local/bin/python3; fi; if ! command -v git >/dev/null 2>&1; then if command -v apt-get >/dev/null 2>&1; then apt-get update -qq >/dev/null 2>&1 || true; apt-get install -y -qq --no-install-recommends git >/dev/null 2>&1 || true; fi; fi; python -m pip install --quiet --upgrade pip; if [[ -n '$requirements_file' && -f '$requirements_file' ]]; then python -m pip install --quiet -r '$requirements_file'; fi; python -m pip install --quiet $CONTAINER_DEPS; $command"
}

declare -a STAGE_NAMES=()
declare -a STAGE_STATUSES=()

execute_stage() {
  local stage_name="$1"
  local runtime="$2"
  local command="$3"
  local engine="${4:-}"
  local requirements_file="${5:-}"
  local command_status=0

  progress "stage=$stage_name action=start"
  if [[ "$runtime" == "container" ]]; then
    run_container_command "$engine" "$command" "$requirements_file" || command_status=$?
  else
    run_local_command "$command" || command_status=$?
  fi
  if [[ "$command_status" -eq 0 ]]; then
    progress "stage=$stage_name action=complete status=pass"
    return 0
  fi

  progress "stage=$stage_name action=complete status=fail"
  return "$command_status"
}

record_stage_pass() {
  local stage_name="$1"
  STAGE_NAMES+=("$stage_name")
  STAGE_STATUSES+=("pass")
}

record_stage_fail() {
  local stage_name="$1"
  STAGE_NAMES+=("$stage_name")
  STAGE_STATUSES+=("fail")
}

print_summary() {
  local idx
  local failed_count=0
  for idx in "${!STAGE_NAMES[@]}"; do
    summary "stage=${STAGE_NAMES[$idx]} status=${STAGE_STATUSES[$idx]}"
    [[ "${STAGE_STATUSES[$idx]}" == "fail" ]] && failed_count=$((failed_count + 1))
  done
  summary "overall_status=$([[ "$failed_count" -eq 0 ]] && echo pass || echo fail) failed_stages=$failed_count total_stages=${#STAGE_NAMES[@]}"
  [[ "$failed_count" -eq 0 ]]
}

run_gate_stages() {
  local runtime="$1"
  local python_exec="$2"
  local engine="${3:-}"
  local requirements_file="${4:-}"

  local lint_cmd
  lint_cmd="$(build_lint_command "$python_exec")"
  local tests_cmd
  if [[ -n "$TEST_COMMAND" ]]; then
    tests_cmd="$TEST_COMMAND"
  else
    tests_cmd="$(build_pytest_command "$python_exec")"
  fi
  local coverage_cmd
  coverage_cmd="$(build_coverage_command "$python_exec")"

  if run_lint_stage "$runtime" "$engine" "$lint_cmd" "$requirements_file"; then
    record_stage_pass lint
  else
    record_stage_fail lint
    [[ "$FAIL_FAST" == "1" ]] && return
  fi

  if run_tests_stage "$runtime" "$engine" "$tests_cmd" "$python_exec" "$requirements_file"; then
    record_stage_pass tests
  else
    record_stage_fail tests
    [[ "$FAIL_FAST" == "1" ]] && return
  fi

  if run_coverage_stage "$runtime" "$engine" "$coverage_cmd" "$python_exec" "$requirements_file"; then
    record_stage_pass coverage
  else
    record_stage_fail coverage
    [[ "$FAIL_FAST" == "1" ]] && return
  fi
}

progress "start requested_runtime=$TEST_RUNTIME"
effective_runtime="$(resolve_effective_runtime)"
python_exec="python"
container_engine=""
repo_runtime_mode="$(detect_runtime_repo_mode "$REPO_ROOT")"
container_requirements_file="$(resolve_container_requirements "$repo_runtime_mode")"

if [[ "$effective_runtime" == "container" ]]; then
  container_engine="$(resolve_container_engine)"
  progress "runtime=container engine=$container_engine image=$CONTAINER_IMAGE target=$TEST_TARGET"
else
  python_exec="$(resolve_python_exec)"
  progress "runtime=local python=$python_exec target=$TEST_TARGET coverage=$COVERAGE_FILE_PATH"
fi

run_gate_stages "$effective_runtime" "$python_exec" "$container_engine" "$container_requirements_file"

if print_summary; then
  progress 'complete status=ok'
  exit 0
fi

progress 'complete status=failed'
exit 1