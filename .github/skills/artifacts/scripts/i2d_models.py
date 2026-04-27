"""Data models for the artifacts-input-2-data ingest pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# Input classifications derived from 00-input subfolder name
CLASSIFICATION_MAP: dict[str, str] = {
    "documents": "document",
    "features": "feature",
    "bugs": "bug",
}


@dataclass(frozen=True)
class InputFile:
    """A single file discovered in 00-input/ with its resolved classification."""

    path: Path
    classification: str  # document | feature | bug
    context_candidates: tuple[str, ...] = ()


@dataclass
class BundleMetadata:
    """Metadata written to <code>.yaml inside a 10-data bundle."""

    item_code: str
    date_key: str
    source_file: str
    source_input_file: str
    source_fingerprint_sha256: str
    classification: str
    file_format: str
    processed_at: str
    extraction_engine: str = ""
    extraction_status: str = ""
    txt_translation: str = ""
    txt_inferred_type: str = ""
    txt_research_hints: list[str] = field(default_factory=list)
    language_gate_status: str = ""
    language_gate_note: str = ""
    review_note: str = ""


@dataclass(frozen=True)
class IngestResult:
    """Result of processing one input file."""

    input_file: InputFile
    item_code: str
    bundle_root: Path
    skipped: bool = False
    error: str = ""
