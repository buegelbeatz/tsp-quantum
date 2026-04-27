"""Unit tests for artifacts_tool.py CLI commands and output format validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
TOOL_PATH = ROOT / ".github" / "skills" / "artifacts" / "scripts" / "artifacts_tool.py"


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    """Run artifacts_tool.py with given arguments and return the result.

    Args:
        *args: Command-line arguments to pass to artifacts_tool.py.

    Returns:
        subprocess.CompletedProcess[str]: Result of the tool execution.
    """
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_bundle_command_allocates_five_digit_bundle(tmp_path: Path) -> None:
    """Test that bundle command successfully allocates a new 5-digit bundle entry."""
    data_root = tmp_path / "10-data"
    result = _run_tool("bundle", "--data-root", str(data_root), "--date", "2026-03-24")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["item_code"] == "00000"
    assert Path(payload["reviews_dir"]).exists()


def test_inventory_command_upserts_template_backed_entry(tmp_path: Path) -> None:
    """Test that inventory command upserts entries with template initialization and overwrite."""
    inventory_path = tmp_path / "INVENTORY.md"
    template_path = tmp_path / "INVENTORY.template.md"
    template_path.write_text("# HEADER\n", encoding="utf-8")

    result = _run_tool(
        "inventory",
        "--inventory-path",
        str(inventory_path),
        "--template-path",
        str(template_path),
        "--item-id",
        "00001",
        "--created-at",
        "2026-03-24T11:00:00Z",
        "--fields-json",
        json.dumps({"status": "new", "paths": ["a.md"]}),
    )

    assert result.returncode == 0, result.stderr
    content = inventory_path.read_text(encoding="utf-8")
    assert "## Entry: 00001" in content
    assert "# HEADER" in content


def test_latest_command_copies_markdown_snapshot(tmp_path: Path) -> None:
    """TODO: add docstring for test_latest_command_copies_markdown_snapshot."""
    source_path = tmp_path / "review.md"
    latest_path = tmp_path / "LATEST.md"
    source_path.write_text("hello\n", encoding="utf-8")

    result = _run_tool(
        "latest", "--latest-path", str(latest_path), "--source-path", str(source_path)
    )

    assert result.returncode == 0, result.stderr
    assert latest_path.read_text(encoding="utf-8") == "hello\n"
