"""Write audit records for the artifacts-input-2-data pipeline run.

Purpose:
    Create audit trail records for ingestion pipeline executions.
    Tracks data-to-artifact transitions and validates inventory consistency.

Security:
    Writes audit records to repository-local audit paths only.
    No sensitive payload data is recorded; job outcomes and timestamps only.
"""

from __future__ import annotations

from pathlib import Path

from i2d_models import IngestResult
from i2d_audit_markdown import build_audit_markdown


def write_audit(
    audit_root: Path,
    results: list[IngestResult],
    date_key: str,
    *,
    build_markdown_fn=None,
) -> Path:
    """Append a run audit record under 70-audits/<YYYY-MM-DD>/.

    Returns the path of the written audit file.
    """
    if build_markdown_fn is None:
        build_markdown_fn = build_audit_markdown

    audit_dir = audit_root / date_key
    audit_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(
        f.name for f in audit_dir.iterdir() if f.is_file() and f.suffix == ".md"
    )
    next_seq = len(existing)
    audit_file = audit_dir / f"{next_seq:05d}-artifacts-input-2-data.md"

    lines = build_markdown_fn(results, date_key)
    audit_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit_file
