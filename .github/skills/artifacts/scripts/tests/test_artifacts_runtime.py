"""Unit tests for artifact runtime helper behavior and inventory updates."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_DIR = ROOT / ".github" / "skills" / "artifacts" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

artifact_runtime = import_module("artifact_runtime")
InventoryEntry = artifact_runtime.InventoryEntry
append_inventory_entry = artifact_runtime.append_inventory_entry
create_data_bundle = artifact_runtime.create_data_bundle
next_bundle_code = artifact_runtime.next_bundle_code
write_latest_snapshot = artifact_runtime.write_latest_snapshot


def _inventory_entry(summary: str, status: str, created_at: str) -> InventoryEntry:  # type: ignore[valid-type]
    """Build deterministic inventory entry for update/upsert tests."""
    return InventoryEntry(
        item_id="00000",
        created_at=created_at,
        fields={
            "classification": "feature",
            "summary": summary,
            "status": status,
            "paths": ["10-data/2026-03-24/00000/00000.md"],
        },
    )


def test_next_bundle_code_uses_five_digits_and_ignores_other_dirs(
    tmp_path: Path,
) -> None:
    """Test that bundle code generation uses 5 digits and ignores non-numeric directories."""
    (tmp_path / "00000").mkdir()
    (tmp_path / "00009").mkdir()
    (tmp_path / "notes").mkdir()
    assert next_bundle_code(tmp_path) == "00010"


def test_create_data_bundle_creates_item_paths_and_reviews_dir(tmp_path: Path) -> None:
    """Test that create_data_bundle creates required directories and metadata files."""
    bundle = create_data_bundle(tmp_path, "2026-03-24")
    assert bundle.item_code == "00000"
    assert bundle.item_root.exists()
    assert bundle.markdown_path.name == "00000.md"
    assert bundle.metadata_path.name == "00000.yaml"
    assert bundle.reviews_dir.exists()


def test_append_inventory_entry_initializes_from_template_and_upserts(
    tmp_path: Path,
) -> None:
    """Test that append_inventory_entry initializes from template and upserts entries correctly."""
    inventory_path = tmp_path / "INVENTORY.md"
    template_path = tmp_path / "INVENTORY.template.md"
    template_path.write_text(
        "# DATA INVENTORY\n\n## Purpose\nTracks managed artifact entries.\n",
        encoding="utf-8",
    )

    append_inventory_entry(
        inventory_path,
        _inventory_entry("Initial import", "new", "2026-03-24T10:00:00Z"),
        template_path,
    )
    append_inventory_entry(
        inventory_path,
        _inventory_entry("Updated import", "reviewed", "2026-03-24T10:05:00Z"),
        template_path,
    )

    content = inventory_path.read_text(encoding="utf-8")
    assert content.count("## Entry: 00000") == 1
    assert "Updated import" in content
    assert "Initial import" not in content
    assert "Tracks managed artifact entries." in content


def test_write_latest_snapshot_copies_source_content(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_latest_snapshot_copies_source_content."""
    source_path = tmp_path / "source.md"
    latest_path = tmp_path / "LATEST.md"
    source_path.write_text("# Review\n\nReady", encoding="utf-8")
    write_latest_snapshot(latest_path, source_path)
    assert latest_path.read_text(encoding="utf-8") == "# Review\n\nReady"
