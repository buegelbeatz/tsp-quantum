"""Unit tests for centralized make targets exposed via .github/make/commands.mk."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Locate repository root by searching for .digital-team marker.

    Returns:
        Path: Absolute path to repository root.

    Raises:
        RuntimeError: If repository root cannot be found.
    """
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
COMMANDS_MK = ROOT / ".github" / "make" / "commands.mk"


def test_commands_makefile_exposes_update_target() -> None:
    """Test that commands.mk exposes update target calling update.sh."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "update:" in content
    assert "bash update.sh" in content


def test_commands_makefile_exposes_test_target() -> None:
    """Test that commands.mk exposes test target using the shared test runner."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "test:" in content
    assert "layer-venv-sync" in content
    assert "shared/local-command-orchestration/scripts/run-tests.sh" in content
    assert (
        "DIGITAL_TEAM_TEST_RUNTIME=$${DIGITAL_TEAM_TEST_RUNTIME:-container}" in content
    )
    assert (
        'DIGITAL_TEAM_TEST_TARGET="$${DIGITAL_TEAM_TEST_TARGET:-.github/skills .tests}"'
        in content
    )


def test_commands_makefile_exposes_prompt_quality_targets() -> None:
    """Test that commands.mk exposes quality and quality-fix targets."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "quality:" in content
    assert "prompt-invoke.sh" in content
    assert "quality-fix:" in content


def test_commands_makefile_exposes_prompt_powerpoint_target() -> None:
    """Test that commands.mk exposes powerpoint target with SOURCE/LAYER wiring."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "powerpoint:" in content
    assert "--prompt-name powerpoint" in content
    assert 'SOURCE="$(SOURCE)" LAYER="$(LAYER)"' in content


def test_commands_makefile_routes_internal_only_targets_through_prompt_invoke() -> None:
    """Internal-only prompt targets should be wrapped by prompt-invoke access control."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "pull:" in content
    assert "--prompt-name pull" in content
    assert "chrome:" in content
    assert "--prompt-name chrome" in content
    assert "artifacts-testdata-2-input:" in content
    assert "--prompt-name artifacts-testdata-2-input" in content


def test_commands_makefile_exposes_audit_toggle_targets() -> None:
    """Test that commands.mk exposes audit on/off targets."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "audit-on:" in content
    assert "audit-off:" in content
    assert "task-audit-toggle.sh" in content


def test_commands_makefile_exposes_help_target() -> None:
    """Test that commands.mk exposes help target for command discovery."""
    content = COMMANDS_MK.read_text(encoding="utf-8")

    assert "help:" in content
    assert "grep -hE" in content
