"""Archival helpers for moving ingested source files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


def _strip_bundle_prefixes(filename: str) -> str:
    """Remove repeated ingest bundle prefixes like 00000__ from a filename."""
    cleaned = re.sub(r"^(?:\d{5}__)+", "", filename)
    return cleaned or filename


def move_source_to_done(
    source_path: Path,
    done_root: Path,
    classification: str,
    date_key: str,
    item_code: str,
) -> Path:
    """Move one processed source file from input to 20-done and return destination path."""
    done_dir = done_root / classification / date_key
    done_dir.mkdir(parents=True, exist_ok=True)
    normalized_name = _strip_bundle_prefixes(source_path.name)
    destination = done_dir / f"{item_code}__{normalized_name}"
    shutil.move(str(source_path), str(destination))
    return destination
