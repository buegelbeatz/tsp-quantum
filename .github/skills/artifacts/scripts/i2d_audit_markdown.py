"""Build audit markdown content for ingestion pipeline runs.

Purpose:
    Format audit records as markdown, separating processed/skipped/failed results.

Security:
    No sensitive payload data is included; only job outcomes and timestamps.
"""

from __future__ import annotations

from datetime import datetime, timezone

from i2d_models import IngestResult


def _build_header_lines(
    results: list[IngestResult],
    date_key: str,
    processed_count: int,
    skipped_count: int,
    failed_count: int,
) -> list[str]:
    """Build audit header and summary lines."""
    lines = [
        "# Audit: artifacts-input-2-data",
        "",
        f"- timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "- skill: artifacts-input-2-data",
        "- triggered_by: agile-coach",
        f"- date_key: {date_key}",
        f"- processed: {processed_count}",
        f"- skipped: {skipped_count}",
        f"- failed: {failed_count}",
        "",
        "## Outcome",
    ]
    if results:
        lines.append(
            "- Input files were evaluated and the pipeline state was recorded."
        )
    else:
        lines.append(
            "- No input files were discovered. This is a no-op audit for traceability."
        )
    return lines


def _build_processed_section(processed: list[IngestResult]) -> list[str]:
    """Build processed items section."""
    lines = ["", "## Processed"]
    for r in processed:
        lines.append(
            f"- [{r.item_code}] {r.input_file.path.name} ({r.input_file.classification})"
        )
    if not processed:
        lines.append("- none")
    return lines


def _build_skipped_section(skipped: list[IngestResult]) -> list[str]:
    """Build skipped items section."""
    if not skipped:
        return []
    lines = ["", "## Skipped (already ingested)"]
    for r in skipped:
        lines.append(f"- {r.input_file.path.name}")
    return lines


def _build_failed_section(failed: list[IngestResult]) -> list[str]:
    """Build failed items section."""
    if not failed:
        return []
    lines = ["", "## Failed"]
    for r in failed:
        lines.append(f"- {r.input_file.path.name}: {r.error}")
    return lines


def _partition_results(
    results: list[IngestResult],
) -> tuple[list[IngestResult], list[IngestResult], list[IngestResult]]:
    """Partition ingest results into processed, skipped, and failed buckets."""
    processed: list[IngestResult] = []
    skipped: list[IngestResult] = []
    failed: list[IngestResult] = []
    for result in results:
        if result.error:
            failed.append(result)
            continue
        if result.skipped:
            skipped.append(result)
            continue
        processed.append(result)
    return processed, skipped, failed


def _build_all_sections(
    results: list[IngestResult],
    date_key: str,
    processed: list[IngestResult],
    skipped: list[IngestResult],
    failed: list[IngestResult],
) -> list[str]:
    """Build full markdown document sections from partitioned result buckets."""
    lines = _build_header_lines(
        results, date_key, len(processed), len(skipped), len(failed)
    )
    lines.extend(_build_processed_section(processed))
    lines.extend(_build_skipped_section(skipped))
    lines.extend(_build_failed_section(failed))
    return lines


def build_audit_markdown(results: list[IngestResult], date_key: str) -> list[str]:
    """Build audit markdown lines from ingestion results.

    Args:
        results: List of IngestResult objects from pipeline run.
        date_key: Date key (YYYY-MM-DD format) for audit record.

    Returns:
        List of markdown lines ready for writing to file.
    """
    processed, skipped, failed = _partition_results(results)
    return _build_all_sections(results, date_key, processed, skipped, failed)
