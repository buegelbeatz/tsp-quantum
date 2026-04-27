"""Attempt-list helpers for whisper extraction."""

from __future__ import annotations

from pathlib import Path


def build_attempts(
    path: Path,
    normalized_audio: Path | None,
) -> list[tuple[Path, bool, int, float, str]]:
    """Build the ordered list of whisper transcription attempts."""
    attempts: list[tuple[Path, bool, int, float, str]] = [
        (path, True, 5, 0.0, "default"),
        (path, False, 3, 0.2, "relaxed"),
        (path, False, 1, 0.4, "aggressive"),
    ]
    if normalized_audio is not None:
        attempts.append((normalized_audio, False, 1, 0.2, "normalized-audio"))
    return attempts
