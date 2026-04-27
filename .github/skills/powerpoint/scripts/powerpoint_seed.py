"""Deterministic seed helpers for PowerPoint generation."""

from __future__ import annotations

import hashlib
from pathlib import Path


def build_seed(repo_name: str, layer: str) -> int:
    """Return a stable integer seed from repository and layer identifiers."""
    digest = hashlib.sha256(f"{repo_name}:{layer}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def source_slug(source: Path) -> str:
    """Return a predictable filename slug derived from a source path."""
    clean = "".join(ch if ch.isalnum() else "-" for ch in source.stem.lower())
    compact = "-".join(part for part in clean.split("-") if part)
    return compact or "deck"
