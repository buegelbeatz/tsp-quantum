"""CLI fallback helpers for image OCR extraction."""

from __future__ import annotations

from pathlib import Path


def extract_image_ocr_cli(
    path: Path,
    *,
    run_command_with_timeout_fn,
    file_facts_fn,
    ocr_timeout_seconds: int,
) -> tuple[str, str, str]:
    """Extract image OCR via tesseract CLI when python OCR deps are unavailable."""
    stdout, stderr = run_command_with_timeout_fn(
        ["tesseract", str(path), "stdout"], ocr_timeout_seconds
    )
    if stdout:
        return (
            f"## File Facts\n\n{file_facts_fn(path)}\n\n## OCR Text\n\n{stdout}",
            "ocr-cli",
            "ok",
        )
    reason = (
        stderr or "OCR unavailable (install pillow + pytesseract or tesseract CLI)."
    )
    return f"## File Facts\n\n{file_facts_fn(path)}\n\n{reason}", "ocr", "unavailable"
