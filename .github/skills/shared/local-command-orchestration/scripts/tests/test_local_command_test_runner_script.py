from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "run-tests.sh"
)


def test_run_tests_script_supports_runtime_and_container_modes() -> None:
    """TODO: add docstring for test_run_tests_script_supports_runtime_and_container_modes."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'TEST_RUNTIME="${DIGITAL_TEAM_TEST_RUNTIME:-container}"' in content
    assert 'TEST_TARGET="${DIGITAL_TEAM_TEST_TARGET:-.github/skills}"' in content
    assert 'ALLOW_LOCAL_FALLBACK="${DIGITAL_TEAM_ALLOW_LOCAL_FALLBACK:-0}"' in content
    assert 'FAIL_FAST="${DIGITAL_TEAM_TEST_FAIL_FAST:-1}"' in content
    assert 'SHOW_PROGRESS="${DIGITAL_TEAM_TEST_SHOW_PROGRESS:-0}"' in content
    assert (
        'REPORT_DIR_REL="${DIGITAL_TEAM_TEST_REPORT_DIR_REL:-.tests/python/reports}"'
        in content
    )
    assert (
        'REPORT_DIR="${DIGITAL_TEAM_TEST_REPORT_DIR:-$REPO_ROOT/$REPORT_DIR_REL}"'
        in content
    )
    assert (
        'PYTEST_JUNIT_REL="${DIGITAL_TEAM_PYTEST_JUNIT_REL:-$REPORT_DIR_REL/pytest-junit.xml}"'
        in content
    )
    assert (
        'CONTAINER_IMAGE="${DIGITAL_TEAM_TEST_CONTAINER_IMAGE:-python:3.12-slim}"'
        in content
    )
    assert 'CONTAINER_ENGINE="${DIGITAL_TEAM_TEST_CONTAINER_ENGINE:-}"' in content
    assert (
        'REPO_CLASSIFICATION_LIB="$REPO_ROOT/.github/skills/shared/shell/scripts/lib/repo-classification.sh"'
        in content
    )
    assert 'source "$REPO_CLASSIFICATION_LIB"' in content
    assert "resolve_effective_runtime()" in content
    assert "run_gate_stages" in content
    assert 'python_exec="python"' in content


def test_run_tests_script_prefers_repo_specific_python_envs() -> None:
    """App repos should prefer root .venv, while layer repos should prefer python-runtime."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'repo_runtime_mode="$(detect_runtime_repo_mode "$REPO_ROOT")"' in content
    assert 'if [[ "$repo_runtime_mode" == "app" ]]; then' in content
    assert '"$REPO_ROOT/.venv/bin/python"' in content
    assert (
        '"$REPO_ROOT/.digital-runtime/layers/python-runtime/venv/bin/python"' in content
    )


def test_run_tests_script_resolves_repo_specific_container_requirements() -> None:
    """Containerized runs should install app or layer requirements before test tools."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'CONTAINER_REQUIREMENTS="${DIGITAL_TEAM_TEST_REQUIREMENTS:-}"' in content
    assert "resolve_container_requirements()" in content
    assert ".digital-runtime/layers/python-runtime/requirements.merged.txt" in content
    assert (
        'container_requirements_file="$(resolve_container_requirements "$repo_runtime_mode")"'
        in content
    )


def test_run_tests_script_supports_optional_progress_markers() -> None:
    """TODO: add docstring for test_run_tests_script_supports_optional_progress_markers."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[progress][test]" in content
    assert '[[ "$SHOW_PROGRESS" == "1" ]] || return 0' in content
    assert 'progress "stage=$stage_name action=start"' in content
    assert 'progress "stage=$stage_name action=complete status=pass"' in content
    assert 'progress "stage=$stage_name action=complete status=fail"' in content
    assert "command_status=0" in content
    assert 'return "$command_status"' in content
    assert "print_stage_header()" in content
    assert "print_status_line()" in content
    assert "[summary][test]" in content
    assert "overall_status=" in content
    assert "complete status=ok" in content


def test_run_tests_script_routes_coverage_into_tests_folder() -> None:
    """TODO: add docstring for test_run_tests_script_routes_coverage_into_tests_folder."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert (
        'COVERAGE_FILE_PATH="${DIGITAL_TEAM_COVERAGE_FILE:-$REPO_ROOT/.tests/python/coverage/.coverage}"'
        in content
    )
    assert (
        'CONTAINER_COVERAGE_FILE="${DIGITAL_TEAM_CONTAINER_COVERAGE_FILE:-/workspace/.tests/python/coverage/.coverage}"'
        in content
    )
    assert (
        'COVERAGE_JSON_PATH="${DIGITAL_TEAM_COVERAGE_JSON:-$REPO_ROOT/$COVERAGE_JSON_REL}"'
        in content
    )
    assert (
        'COVERAGE_JSON_REL="${DIGITAL_TEAM_COVERAGE_JSON_REL:-$REPORT_DIR_REL/coverage.json}"'
        in content
    )
    assert (
        'COVERAGE_OMIT_PATTERNS="${DIGITAL_TEAM_COVERAGE_OMIT:-*/tests/*,*/test_*.py,*/conftest.py}"'
        in content
    )
    assert 'COVERAGE_THRESHOLD="${DIGITAL_TEAM_COVERAGE_THRESHOLD:-80}"' in content
    assert 'mkdir -p "$(dirname "$COVERAGE_FILE_PATH")"' in content
    assert 'COVERAGE_FILE="$COVERAGE_FILE_PATH"' in content
    assert "coverage json --pretty-print" in content
    assert '"$SCRIPT_DIR/render_coverage_summary.py"' in content


def test_run_tests_script_suppresses_container_runtime_noise() -> None:
    """TODO: add docstring for test_run_tests_script_suppresses_container_runtime_noise."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "PIP_ROOT_USER_ACTION=ignore" in content
    assert "PIP_DISABLE_PIP_VERSION_CHECK=1" in content
    assert "DEBIAN_FRONTEND=noninteractive" in content
    assert "mkdir -p '.tests/python/coverage' '.tests/python/reports'" in content
    assert "ln -sf /usr/local/bin/python /usr/local/bin/python3" in content


def test_run_tests_script_supports_multiple_test_targets() -> None:
    """TODO: add docstring for test_run_tests_script_supports_multiple_test_targets."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'read -r -a test_targets <<<"$TEST_TARGET"' in content
    assert 'command+=("${test_targets[@]}")' in content


def test_run_tests_script_outputs_verbose_colored_results() -> None:
    """TODO: add docstring for test_run_tests_script_outputs_verbose_colored_results."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'TEST_ARGS_RAW="${DIGITAL_TEAM_TEST_ARGS:--q --color=yes}"' in content
    assert "FORCE_COLOR=1" in content
    assert '"$SCRIPT_DIR/render_pytest_summary.py"' in content
    assert '"$SCRIPT_DIR/render_coverage_summary.py"' in content
