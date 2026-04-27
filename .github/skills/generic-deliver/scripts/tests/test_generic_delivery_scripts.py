"""Unit tests for generic delivery prefix and postfix shell scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = Path(__file__).resolve().parents[6]
PREFIX = ROOT / "scripts" / "delivery-prefix.sh"
POSTFIX = ROOT / "scripts" / "delivery-postfix.sh"
BRIDGE = ROOT / "scripts" / "delivery-language-bridge.sh"
BRIDGE_LIB = ROOT / "scripts" / "delivery-language-bridge-lib.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a delivery script with given arguments.

    Args:
        script: Path to the script to run.
        *args: Command-line arguments for the script.

    Returns:
        subprocess.CompletedProcess[str]: Result of script execution.
    """
    return subprocess.run(
        ["bash", str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_prefix_success() -> None:
    """Test that delivery-prefix.sh successfully generates feature branch name with full args."""
    result = _run(
        PREFIX,
        "--role",
        "fullstack-engineer",
        "--ticket-id",
        "DT-123",
        "--slug",
        "implement-feature",
    )
    assert result.returncode == 0
    assert 'status: "ok"' in result.stdout
    assert 'branch_name: "feature/DT-123-implement-feature"' in result.stdout


def test_prefix_missing_required_args() -> None:
    """Test that delivery-prefix.sh requires ticket-id argument."""
    result = _run(PREFIX, "--role", "fullstack-engineer")
    assert result.returncode != 0
    assert "--ticket-id is required" in result.stderr


def test_postfix_success() -> None:
    """Test that delivery-postfix.sh successfully processes delivery completion."""
    result = _run(
        POSTFIX,
        "--role",
        "fullstack-engineer",
        "--branch",
        "feature/DT-123-implement-feature",
        "--base-ref",
        "main",
        "--review-report",
        "artifacts/review/latest.md",
    )
    assert result.returncode == 0
    assert 'status: "ok"' in result.stdout
    assert "human_approval_required: true" in result.stdout


def test_postfix_requires_branch() -> None:
    """Test that delivery-postfix.sh requires branch argument."""
    result = _run(POSTFIX, "--role", "fullstack-engineer")
    assert result.returncode != 0
    assert "--branch is required" in result.stderr


def test_language_bridge_emits_contract() -> None:
    """Test language bridge emits deterministic contract payload."""
    result = _run(
        BRIDGE,
        "--mode",
        "deliver",
        "--workspace",
        str(WORKSPACE),
        "--languages",
        "python,bash",
    )
    assert result.returncode == 0
    assert 'kind: "language_expert_bridge"' in result.stdout
    assert 'mode: "deliver"' in result.stdout
    assert 'language: "python"' in result.stdout
    assert 'language: "bash"' in result.stdout
    assert "conflict_resolution:" in result.stdout


def test_prefix_and_postfix_include_language_guidance_hook() -> None:
    """Test generic delivery scripts include language guidance hook output."""
    prefix = _run(
        PREFIX,
        "--role",
        "fullstack-engineer",
        "--ticket-id",
        "DT-124",
        "--slug",
        "lang-bridge",
        "--workspace",
        str(WORKSPACE),
    )
    assert prefix.returncode == 0
    assert "language_guidance_hook:" in prefix.stdout
    assert 'kind: "language_expert_bridge"' in prefix.stdout

    postfix = _run(
        POSTFIX,
        "--role",
        "fullstack-engineer",
        "--branch",
        "feature/DT-124-lang-bridge",
        "--workspace",
        str(WORKSPACE),
    )
    assert postfix.returncode == 0
    assert "language_guidance_hook:" in postfix.stdout
    assert 'kind: "language_expert_bridge"' in postfix.stdout


def test_language_bridge_sources_helper_library() -> None:
    """Test bridge script references extracted helper module for B1 split."""
    content = BRIDGE.read_text(encoding="utf-8")
    helper_content = BRIDGE_LIB.read_text(encoding="utf-8")

    assert "delivery-language-bridge-lib.sh" in content
    assert 'source "$LIB_PATH"' in content
    assert "risk_note_for_language()" in helper_content
    assert "detect_languages_from_git()" in helper_content
