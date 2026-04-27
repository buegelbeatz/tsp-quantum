"""MarkItDown and EML extractor helpers for i2d_content."""

from __future__ import annotations

from pathlib import Path

import i2d_content_markitdown_eml as _md_eml
import i2d_content_markitdown_exceptions as _md_exceptions
import i2d_content_markitdown_utils as _md_utils


def extract_with_markitdown(path: Path, *, file_facts_fn) -> tuple[str, str, str]:
    """Extract text via markitdown and normalize to tuple contract."""
    try:
        from markitdown import MarkItDown  # type: ignore[import-untyped]
    except ImportError:
        return "", "", ""

    markitdown_errors = _md_exceptions.collect_markitdown_errors()

    try:
        converter = MarkItDown()
        result = converter.convert(str(path))
        text = (getattr(result, "text_content", "") or "").strip()
        if text:
            return (
                f"## File Facts\n\n{file_facts_fn(path)}\n\n## Extracted Text\n\n{text}",
                "markitdown",
                "ok",
            )
    except tuple(markitdown_errors) as exc:
        return (
            f"## File Facts\n\n{file_facts_fn(path)}\n\nExtraction failed via markitdown: {exc}",
            "markitdown",
            "error",
        )
    return "", "", ""


def markitdown_contains_transcript_error(
    content: str, snippets: tuple[str, ...]
) -> bool:
    """Detect synthetic transcript error placeholders in markitdown output."""
    return _md_utils.markitdown_contains_transcript_error(content, snippets)


def cleanup_epub_markitdown_content(content: str) -> str:
    """Remove EPUB archive noise (for example CSS blobs) from markitdown output."""
    return _md_utils.cleanup_epub_markitdown_content(content)


def extract_eml(path: Path, *, file_facts_fn) -> tuple[str, str, str]:
    """Extract email headers, body, and attachment metadata from an EML file."""
    return _md_eml.extract_eml(path, file_facts_fn=file_facts_fn)
