"""Shared OCR quality assessment utilities.

Purpose:
    Centralized OCR quality predicates to reduce duplication across
    i2d_content_ocr_quality and i2d_content_image_ocr_enhance modules.

Security:
    Pure functions with no mutable state or side effects.
"""

from __future__ import annotations


def is_confidence_threshold_met(confidence: float, threshold: float = 0.85) -> bool:
    """Check if OCR confidence score meets or exceeds threshold.

    Args:
        confidence: OCR confidence score (typically 0.0-1.0).
        threshold: Minimum acceptable confidence (default 0.85).

    Returns:
        True if confidence >= threshold, otherwise False.
    """
    return confidence >= threshold


def is_text_region_meaningful(text: str, min_length: int = 3) -> bool:
    """Check if OCR text region has meaningful content.

    Args:
        text: Extracted OCR text.
        min_length: Minimum character count for meaningful text (default 3).

    Returns:
        True if text length >= min_length after stripping, else False.
    """
    return len(text.strip()) >= min_length


def has_low_token_quality(
    text: str, min_avg_token_len: float = 3.0, min_tokens: int = 20
) -> bool:
    """Check if text has suspiciously short tokens (noise signal).

    Args:
        text: Text to assess.
        min_avg_token_len: Threshold for average token length (default 3.0).
        min_tokens: Minimum token count to trigger heuristic (default 20).

    Returns:
        True if average token length < min_avg_token_len and token count >= min_tokens.
    """
    import re

    tokens = re.findall(r"[A-Za-z]{2,}", text)
    if len(tokens) < min_tokens:
        return False
    avg_len = sum(len(t) for t in tokens) / float(len(tokens))
    return avg_len < min_avg_token_len


def has_low_meaningful_line_ratio(lines: list[str], min_ratio: float = 0.2) -> bool:
    """Check if meaningful line count is suspiciously low for line count.

    Args:
        lines: Normalized (stripped) text lines.
        min_ratio: Minimum ratio of meaningful lines (default 0.2 = 20%).

    Returns:
        True if meaningful line count < (total lines * min_ratio).
    """

    def count_meaningful_lines() -> int:
        """TODO: add docstring for count_meaningful_lines."""
        meaningful = 0
        for line in lines:
            alpha_count = sum(1 for ch in line if ch.isalpha())
            if alpha_count >= 3 and alpha_count / float(max(1, len(line))) >= 0.45:
                meaningful += 1
        return meaningful

    if len(lines) < 6:
        return count_meaningful_lines() <= 1
    if len(lines) < 15:
        return count_meaningful_lines() <= max(3, int(len(lines) * min_ratio))
    return False


def normalize_text_lines(text: str) -> list[str]:
    """Return normalized non-empty text lines.

    Args:
        text: Input text.

    Returns:
        List of stripped, non-empty lines.
    """
    return [line.strip() for line in text.splitlines() if line.strip()]
