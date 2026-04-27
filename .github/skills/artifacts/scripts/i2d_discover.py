"""Discover input files from .digital-artifacts/00-input/ subfolders."""

from __future__ import annotations

from pathlib import Path

from i2d_models import CLASSIFICATION_MAP, InputFile

_SKIP_NAMES = {".gitkeep", ".DS_Store"}


def _discover_folder_files(folder: Path) -> list[Path]:
    """Return processable files for one input subfolder in stable order."""
    files: list[Path] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.name in _SKIP_NAMES:
            continue
        if path.stat().st_size == 0:
            print(
                f"[i2d-discover] WARNING: skipping empty (0-byte) file: {path.name}"
            )
            continue
        files.append(path)
    return files


def _build_input_records(paths: list[Path], classification: str) -> list[InputFile]:
    """Build InputFile records and attach context candidates for bug batches."""
    if classification != "bug" or len(paths) <= 1:
        return [InputFile(path=path, classification=classification) for path in paths]

    return [
        InputFile(
            path=path,
            classification=classification,
            context_candidates=tuple(other.name for other in paths if other != path),
        )
        for path in paths
    ]


def _fingerprint_markers(source_fingerprint_sha256: str) -> tuple[str, str] | None:
    """Return plain and quoted fingerprint markers when fingerprint is provided."""
    if not source_fingerprint_sha256:
        return None
    return (
        f"source_fingerprint_sha256: {source_fingerprint_sha256}",
        f'source_fingerprint_sha256: "{source_fingerprint_sha256}"',
    )


def _matches_ingest_reference(
    content: str,
    source_rel: str,
    source_fingerprint_sha256: str,
) -> bool:
    """Check whether metadata content references source path or fingerprint."""
    if f"source_file: {source_rel}" in content:
        return True
    if f"source_input_file: {source_rel}" in content:
        return True

    markers = _fingerprint_markers(source_fingerprint_sha256)
    if not markers:
        return False
    plain_marker, quoted_marker = markers
    return plain_marker in content or quoted_marker in content


def discover_input_files(input_root: Path) -> list[InputFile]:
    """Return all processable files from documents/, features/, and bugs/.

    Files named .gitkeep or .DS_Store are excluded. Empty (0-byte) files are
    skipped with a warning to prevent noise bundles in the downstream pipeline.
    Order is stable (subfolder order from CLASSIFICATION_MAP, then filename
    alphabetically).
    """
    result: list[InputFile] = []
    for subfolder, classification in CLASSIFICATION_MAP.items():
        folder = input_root / subfolder
        if not folder.is_dir():
            continue
        paths = _discover_folder_files(folder)
        result.extend(_build_input_records(paths, classification))
    return result


def already_ingested(
    source_path: Path, data_root: Path, source_fingerprint_sha256: str = ""
) -> bool:
    """Return True if a bundle metadata file referencing this source already exists.

    Scans all <code>.yaml files under 10-data/ for a matching source_file entry.
    """
    source_rel = str(source_path)
    for yaml_file in data_root.rglob("*.yaml"):
        try:
            content = yaml_file.read_text(encoding="utf-8")
            if _matches_ingest_reference(
                content, source_rel, source_fingerprint_sha256
            ):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False
