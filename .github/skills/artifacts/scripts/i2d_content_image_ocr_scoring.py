"""Scoring helper for OCR text candidates."""

from __future__ import annotations


def score_ocr_candidate(text: str) -> tuple[int, int]:
    """Score OCR candidate text by alpha and alnum density."""
    alnum_chars = sum(1 for ch in text if ch.isalnum())
    alpha_chars = sum(1 for ch in text if ch.isalpha())
    return alpha_chars, alnum_chars
