"""Process input files through the ingest pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

from i2d_ingest import ingest_file
from i2d_models import IngestResult, InputFile


def _ingest_with_fallback(
    input_file: InputFile,
    data_root: Path,
    date_key: str,
    inventory_path: Path,
    template_path: Path | None,
) -> IngestResult:
    """Try to ingest file, return error result on failure."""
    try:
        return ingest_file(
            input_file=input_file,
            data_root=data_root,
            date_key=date_key,
            inventory_path=inventory_path,
            template_path=template_path,
        )
    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
        ImportError,
        ModuleNotFoundError,
    ) as exc:
        return IngestResult(
            input_file=input_file,
            item_code="",
            bundle_root=data_root,
            error=str(exc),
        )


def _report_processing_step(result: IngestResult) -> None:
    """Report the processing status for a single file."""
    if result.skipped:
        print("[artifacts-input-2-data]   skipped (already ingested)")
    elif result.error:
        print(f"[artifacts-input-2-data]   error: {result.error}")
    else:
        print(f"[artifacts-input-2-data]   bundle: {result.item_code}")


def process_input_files(
    input_files: list[InputFile],
    data_root: Path,
    date_key: str,
    inventory_path: Path,
    template_path: Path | None,
) -> list[IngestResult]:
    """Process each input file through the ingest pipeline.

    Returns list of IngestResult objects.
    """
    results: list[IngestResult] = []
    for input_file in input_files:
        print(
            f"[artifacts-input-2-data] processing: {input_file.path.name} ({input_file.classification})"
        )
        if input_file.classification == "bug" and input_file.context_candidates:
            print(
                "[artifacts-input-2-data]   context-check: possible related files -> "
                + ", ".join(input_file.context_candidates)
            )
        result = _ingest_with_fallback(
            input_file=input_file,
            data_root=data_root,
            date_key=date_key,
            inventory_path=inventory_path,
            template_path=template_path,
        )
        _report_processing_step(result)
        results.append(result)
    return results
