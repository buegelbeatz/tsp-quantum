"""Unit tests for quality-expert-session.sh report contract and execution model."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Locate repository root by searching for .github/skills marker."""
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
    / "quality-expert"
    / "scripts"
    / "quality-expert-session.sh"
)
RUNTIME_HELPERS_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "quality-expert"
    / "scripts"
    / "quality-expert-session-runtime.sh"
)
PARALLEL_HELPERS_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "quality-expert"
    / "scripts"
    / "quality-expert-session-parallel.sh"
)
FLOW_HELPERS_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "quality-expert"
    / "scripts"
    / "quality-expert-session-flow.sh"
)


def test_quality_expert_script_declares_required_sections() -> None:
    """Ensure canonical section headings required by layer-quality parser are present."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    flow_content = FLOW_HELPERS_PATH.read_text(encoding="utf-8")

    assert "set -euo pipefail" in content
    assert 'append_section "Layer test suite"' in flow_content
    assert 'append_section "Coverage >= 80%"' in flow_content
    assert 'append_section "Ruff lint"' in flow_content
    assert 'append_section "Mypy type check"' in flow_content
    assert 'append_section "Sensitive data pattern scan"' in flow_content
    assert 'append_section "OWASP risk pattern scan"' in flow_content
    assert 'append_section "Endpoint exposure scan"' in flow_content
    assert 'append_section "Bandit OWASP SAST scan"' in flow_content
    runtime_content = RUNTIME_HELPERS_PATH.read_text(encoding="utf-8")
    assert "[progress][quality-expert-session]" in runtime_content
    assert "status=running" in runtime_content
    assert "elapsed=%ss" in runtime_content
    assert "collect-parallel-results" in flow_content


def test_quality_expert_coverage_reads_cached_file() -> None:
    """Ensure coverage check uses cached .coverage file instead of re-running tests."""
    flow_content = FLOW_HELPERS_PATH.read_text(encoding="utf-8")

    # Step 1 writes coverage; step 2 reads via 'coverage report'
    assert "coverage report --fail-under=80" in flow_content


def test_quality_expert_does_not_bypass_test_or_coverage_gates() -> None:
    """Ensure QUALITY_SKIP_TESTS cannot bypass mandatory test/coverage sections."""
    flow_content = FLOW_HELPERS_PATH.read_text(encoding="utf-8")

    assert "QUALITY_SKIP_TESTS" in flow_content
    assert "mandatory-test-and-coverage-gates" in flow_content
    assert "status=skipped QUALITY_SKIP_TESTS=1" not in flow_content


def test_quality_expert_script_no_longer_uses_legacy_runner() -> None:
    """Ensure quality-expert runs directly in current repository layout."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "LEGACY_RUNNER" not in content
    assert "fullstack-quality-session.md" not in content
    assert "run-tool.sh" in content
    assert "quality-expert-session.md" in content


def test_quality_expert_script_sources_runtime_helpers() -> None:
    """Ensure B1 decomposition keeps runtime logic in helper module."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "quality-expert-session-runtime.sh" in content
    assert "quality-expert-session-parallel.sh" in content
    assert "quality-expert-session-flow.sh" in content
    assert 'source "$SESSION_RUNTIME_HELPERS"' in content
    assert 'source "$SESSION_PARALLEL_HELPERS"' in content
    assert 'source "$SESSION_FLOW_HELPERS"' in content


def test_quality_expert_runtime_helpers_define_required_functions() -> None:
    """Ensure extracted helper exports required quality session functions."""
    content = RUNTIME_HELPERS_PATH.read_text(encoding="utf-8")

    assert "require_runtime_package()" in content
    assert "append_section()" in content


def test_quality_expert_additional_helpers_define_required_functions() -> None:
    """Ensure extracted helper modules expose required orchestration functions."""
    parallel_content = PARALLEL_HELPERS_PATH.read_text(encoding="utf-8")
    flow_content = FLOW_HELPERS_PATH.read_text(encoding="utf-8")

    assert "collect_parallel_sections()" in parallel_content
    assert "configure_quality_targets()" in flow_content
    assert "initialize_quality_report()" in flow_content
    assert "run_quality_sections()" in flow_content
