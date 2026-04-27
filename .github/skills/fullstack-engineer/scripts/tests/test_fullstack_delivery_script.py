"""Unit tests for fullstack-delivery.sh script behavior and output format."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "fullstack-delivery.sh"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run fullstack-delivery.sh with given arguments and return the result.

    Args:
        *args: Command-line arguments to pass to the script.

    Returns:
        subprocess.CompletedProcess[str]: Result of the script execution.
    """
    return subprocess.run(
        [str(SCRIPT), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_fullstack_delivery_success() -> None:
    """Test that fullstack-delivery.sh successfully generates branch name and expects approval."""
    result = _run(
        "--ticket-id",
        "DT-456",
        "--slug",
        "add-dashboard-api",
        "--base-ref",
        "main",
        "--review-report",
        "artifacts/review/latest.md",
    )
    assert result.returncode == 0
    assert 'kind: "fullstack_delivery"' in result.stdout
    assert 'branch_name: "feature/DT-456-add-dashboard-api"' in result.stdout
    assert "human_approval_required: true" in result.stdout


def test_fullstack_delivery_requires_ticket_id() -> None:
    """TODO: add docstring for test_fullstack_delivery_requires_ticket_id."""
    result = _run("--slug", "foo")
    assert result.returncode != 0
    assert "--ticket-id is required" in result.stderr
