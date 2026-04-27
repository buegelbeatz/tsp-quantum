"""Runtime helpers for managed artifact bundle allocation and snapshots."""

from __future__ import annotations

from artifact_inventory import InventoryEntry, append_inventory_entry
from dataclasses import dataclass
from pathlib import Path
import shutil

from artifact_bundle_allocator import next_bundle_code


@dataclass(frozen=True)
class DataBundle:
    """Allocated data bundle paths for a single artifact item."""

    date_key: str
    item_code: str
    item_root: Path
    markdown_path: Path
    metadata_path: Path
    reviews_dir: Path


def create_data_bundle(data_root: Path, date_key: str) -> DataBundle:
    """Create the next numbered bundle and ensure canonical 60-review directory exists."""
    day_root = data_root / date_key
    day_root.mkdir(parents=True, exist_ok=True)
    item_code = next_bundle_code(day_root)
    item_root = day_root / item_code
    item_root.mkdir(parents=True, exist_ok=True)
    reviews_root = data_root.parent / "60-review"
    reviews_dir = reviews_root / date_key / item_code
    reviews_dir.mkdir(parents=True, exist_ok=True)
    return DataBundle(
        date_key=date_key,
        item_code=item_code,
        item_root=item_root,
        markdown_path=item_root / f"{item_code}.md",
        metadata_path=item_root / f"{item_code}.yaml",
        reviews_dir=reviews_dir,
    )


def write_latest_snapshot(latest_path: Path, source_path: Path) -> None:
    """Copy the latest artifact content into the managed LATEST.md file."""
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, latest_path)


__all__ = [
    "DataBundle",
    "InventoryEntry",
    "append_inventory_entry",
    "create_data_bundle",
    "next_bundle_code",
    "write_latest_snapshot",
]
