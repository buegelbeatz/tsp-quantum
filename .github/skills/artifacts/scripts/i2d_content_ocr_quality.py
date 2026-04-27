"""OCR text extraction and quality heuristics."""

from __future__ import annotations

import i2d_ocr_quality_helpers as _helpers


def extract_ocr_plain_text(ocr_markdown: str) -> str:
    """Extract plain OCR text body from markdown sections."""
    marker = "## OCR Text"
    if marker not in ocr_markdown:
        return ocr_markdown.strip()

    text = ocr_markdown.split(marker, 1)[1].strip()
    for section in (
        "## Raw Form Template",
        "## Local Form Analysis",
        "## Vision Analysis",
    ):
        if section in text:
            text = text.split(section, 1)[0].strip()
    return text


def _is_empty_or_undetected(text: str) -> bool:
    """Guard: Check if text is empty or has no-text marker."""
    lowered = text.lower()
    return not text or "(no text detected" in lowered


def _count_meaningful_lines(lines: list[str]) -> int:
    """Count lines with meaningful alphabetic content (>= 45% alpha ratio)."""
    meaningful = 0
    for line in lines:
        alpha = sum(1 for ch in line if ch.isalpha())
        if alpha >= 3 and alpha / float(max(1, len(line))) >= 0.45:
            meaningful += 1
    return meaningful


def _is_too_many_short_tokens(text: str) -> bool:
    """Check if text has too many short tokens (avg < 3.0 chars)."""
    return _helpers.has_low_token_quality(text)


def _normalize_nonempty_lines(text: str) -> list[str]:
    """Return normalized non-empty text lines."""
    return _helpers.normalize_text_lines(text)


def _fails_basic_quality_guards(text: str, lines: list[str]) -> bool:
    """Check guards for empty/undetected OCR and empty normalized lines."""
    return _is_empty_or_undetected(text) or not lines


def _fails_signal_quality_guards(text: str, lines: list[str]) -> bool:
    """Check heuristics for meaningful-line and token-quality signals."""
    return _helpers.has_low_meaningful_line_ratio(lines) or _is_too_many_short_tokens(
        text
    )


def is_low_quality_ocr_text(ocr_markdown: str, *, extract_plain_text_fn=None) -> bool:
    """Heuristic quality check to detect OCR letter soup/noise.

    Uses guard conditions and extracted predicates for clarity.
    """
    if extract_plain_text_fn is None:
        extract_plain_text_fn = extract_ocr_plain_text

    text = extract_plain_text_fn(ocr_markdown)
    lines = _normalize_nonempty_lines(text)
    if _fails_basic_quality_guards(text, lines):
        return True
    return _fails_signal_quality_guards(text, lines)
