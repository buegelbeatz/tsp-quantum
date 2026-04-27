"""Unit tests for quality-expert-orchestrator.sh routing contract."""

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
    / "quality-expert-orchestrator.sh"
)


def test_quality_expert_orchestrator_declares_safety_headers() -> None:
    """Ensure safety headers and strict shell mode are present."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "set -euo pipefail" in content
    assert "# Purpose:" in content
    assert "# Security:" in content


def test_quality_expert_orchestrator_routes_scan_and_fix_modes() -> None:
    """Ensure orchestrator supports both scan and fix entrypoints."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'MODE="${QUALITY_EXPERT_MODE:-scan}"' in content
    assert 'case "$MODE" in' in content
    assert "scan)" in content
    assert "fix)" in content
    assert "quality-expert-session.sh" in content
    assert "layer_quality_runtime.py" in content
    assert "layer_quality_fix.sh" in content
