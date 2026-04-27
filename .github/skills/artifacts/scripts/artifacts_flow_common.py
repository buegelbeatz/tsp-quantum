"""Shared helpers for artifacts flow orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BundleRef:
    """Reference to one numbered data bundle."""

    date_key: str
    item_code: str
    item_root: Path
    markdown_path: Path
    metadata_path: Path


def timestamp() -> str:
    """Return ISO-8601 timestamp in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_valid_item_code(code: str) -> bool:
    """Check if item code is valid: 5 digits."""
    return len(code) == 5 and code.isdigit()


def _is_valid_bundle_files(item_root: Path, item_code: str) -> tuple[bool, Path, Path]:
    """Check if bundle has required files and return their paths."""
    markdown_path = item_root / f"{item_code}.md"
    metadata_path = item_root / f"{item_code}.yaml"
    return (
        markdown_path.exists() and metadata_path.exists(),
        markdown_path,
        metadata_path,
    )


def _create_bundle_ref(
    day_root: Path,
    item_root: Path,
    item_code: str,
    markdown_path: Path,
    metadata_path: Path,
) -> BundleRef:
    """Create a BundleRef from validated bundle components."""
    return BundleRef(
        date_key=day_root.name,
        item_code=item_code,
        item_root=item_root,
        markdown_path=markdown_path,
        metadata_path=metadata_path,
    )


def _iter_sorted_dirs(root: Path) -> Iterable[Path]:
    """Yield child directories sorted by directory name."""
    return sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)


def _build_bundle_ref_if_valid(day_root: Path, item_root: Path) -> BundleRef | None:
    """Build BundleRef for valid bundle folders, else return None."""
    item_code = item_root.name
    if not _is_valid_item_code(item_code):
        return None
    is_valid, markdown_path, metadata_path = _is_valid_bundle_files(
        item_root, item_code
    )
    if not is_valid:
        return None
    return _create_bundle_ref(
        day_root, item_root, item_code, markdown_path, metadata_path
    )


def iter_data_bundles(data_root: Path) -> Iterable[BundleRef]:
    """Yield valid 10-data bundles in sorted order."""
    if not data_root.exists():
        return
    for day_root in _iter_sorted_dirs(data_root):
        for item_root in _iter_sorted_dirs(day_root):
            bundle_ref = _build_bundle_ref_if_valid(day_root, item_root)
            if bundle_ref:
                yield bundle_ref


def ensure_text(path: Path, content: str) -> None:
    """Write UTF-8 content after ensuring directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def stage_readiness(spec_text: str) -> tuple[bool, list[str]]:
    """Evaluate whether specification contains minimum planning signals."""
    lowered = spec_text.lower()
    missing: list[str] = []

    has_problem = (
        "## problem" in lowered or "## synthesized problem statement" in lowered
    )
    if not has_problem:
        missing.append("problem statement section is missing")

    if "## scope" not in lowered:
        missing.append("scope section is missing")

    if "## acceptance criteria" not in lowered:
        missing.append("acceptance criteria section is missing")

    return len(missing) == 0, missing


def bundle_id(bundle: BundleRef) -> str:
    """Build stable item identifier for inventory entries."""
    return f"{bundle.date_key}/{bundle.item_code}"


def sha256_text(content: str) -> str:
    """Return deterministic SHA-256 hex digest for text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def score_badge(score: int) -> str:
    """Map a 1-5 score to a markdown-friendly color badge emoji."""
    if score >= 4:
        return "🟢"
    if score >= 3:
        return "🟡"
    return "🔴"
