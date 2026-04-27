"""Helper functions extracted from i2d_content for B1 decomposition."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import i2d_content_commands as _commands
import i2d_content_ocr_quality as _ocr_quality
import i2d_content_vision_form as _vision_form


def _extract_json_payload(text: str) -> dict[str, object] | None:
    """Best-effort parse for JSON payloads, including fenced markdown blocks."""
    return _vision_form.extract_json_payload(text)


def _extract_ocr_plain_text(ocr_markdown: str) -> str:
    """Extract plain OCR text body from markdown sections."""
    return _ocr_quality.extract_ocr_plain_text(ocr_markdown)


def _is_low_quality_ocr_text(ocr_markdown: str) -> bool:
    """Heuristic quality check to detect OCR letter soup/noise."""
    return _ocr_quality.is_low_quality_ocr_text(
        ocr_markdown,
        extract_plain_text_fn=_extract_ocr_plain_text,
    )


def _build_form_markdown_from_vision(vision_payload: dict[str, object]) -> str | None:
    """Build a normalized markdown form table from vision JSON output."""
    return _vision_form.build_form_markdown_from_vision(vision_payload)


def _should_prefer_vision_form(
    vision_payload: dict[str, object], ocr_markdown: str
) -> bool:
    """Return True when form detection is strong and OCR quality is poor."""
    return _vision_form.should_prefer_vision_form(
        vision_payload,
        ocr_markdown,
        is_low_quality_ocr_text_fn=_is_low_quality_ocr_text,
    )


def _file_facts(path: Path) -> str:
    """Return baseline file facts that are always available."""
    stat = path.stat()
    return (
        f"- file_name: {path.name}\n"
        f"- extension: {path.suffix.lower() or '(none)'}\n"
        f"- size_bytes: {stat.st_size}\n"
        f"- modified_at_epoch: {int(stat.st_mtime)}"
    )


def _run_command(command: list[str]) -> tuple[str, str]:
    """Run a command and return (stdout, stderr) as text."""
    return _commands.run_command(command)


def _run_command_with_timeout(
    command: list[str], timeout_seconds: int
) -> tuple[str, str]:
    """Run a command with timeout and return (stdout, stderr) as text."""
    return _commands.run_command_with_timeout(command, timeout_seconds)


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read bounded int from environment with a safe default fallback."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
