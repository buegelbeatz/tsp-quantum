"""Formatted OCR result builders for i2d_content_image_ocr."""

from __future__ import annotations


def build_ok_response(file_facts: str, text: str) -> tuple[str, str, str]:
    """Build a successful OCR extraction response."""
    return (
        f"## File Facts\n\n{file_facts}\n\n## OCR Text\n\n{text}",
        "ocr",
        "ok",
    )


def build_empty_response(file_facts: str, *, timed_out: bool) -> tuple[str, str, str]:
    """Build an empty OCR response, optionally marked as timeout-related."""
    timeout_suffix = " - OCR timeout" if timed_out else ""
    extra_field = "| Field 4 |  |\n" if timed_out else ""
    return (
        f"## File Facts\n\n{file_facts}\n\n"
        f"## OCR Text\n\n(no text detected{timeout_suffix})\n\n"
        "## Raw Form Template\n\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Field 1 |  |\n"
        "| Field 2 |  |\n"
        "| Field 3 |  |\n"
        f"{extra_field}",
        "ocr",
        "empty",
    )


def build_error_response(file_facts: str, message: str) -> tuple[str, str, str]:
    """Build an OCR failure response."""
    return (f"## File Facts\n\n{file_facts}\n\nOCR failed: {message}", "ocr", "error")
