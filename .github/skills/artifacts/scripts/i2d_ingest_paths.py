"""Shared path constants for ingest helpers."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_TOOL = Path(__file__).resolve().parent / "artifacts_tool.py"
CONTENT_TEMPLATE = (
    _REPO_ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "templates"
    / "digital-artifacts"
    / "10-data"
    / "DATA_CONTENT.template.md"
)
DONE_INVENTORY_TEMPLATE = (
    _REPO_ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "templates"
    / "digital-artifacts"
    / "20-done"
    / "INVENTORY.template.md"
)
