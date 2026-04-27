"""Regression tests for root Makefile include structure."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Locate repository root by searching for root Makefile and .github folder."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "Makefile").exists() and (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
ROOT_MAKEFILE = ROOT / "Makefile"
ROOT_CONFIG_MAKEFILE = ROOT / ".github" / "root-config" / "Makefile"


def test_root_makefile_includes_central_commands_mk() -> None:
    """Ensure the repository root Makefile includes centralized command targets."""
    content = ROOT_MAKEFILE.read_text(encoding="utf-8")

    assert (
        "# All project make targets are centralized in .github/make/commands.mk."
        in content
    )
    assert "include .github/make/commands.mk" in content


def test_root_config_makefile_includes_central_commands_mk() -> None:
    """Ensure root-config Makefile template uses centralized command targets."""
    content = ROOT_CONFIG_MAKEFILE.read_text(encoding="utf-8")

    assert (
        "# All project make targets are centralized in .github/make/commands.mk."
        in content
    )
    assert "include .github/make/commands.mk" in content
