"""Audio preparation helpers for whisper transcription."""

from __future__ import annotations

import tempfile
from pathlib import Path

import i2d_content_commands as _commands


def prepare_audio_for_whisper(path: Path) -> Path | None:
    """Create a normalized mono WAV file for more robust speech detection."""
    try:
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            prefix=".whisper-",
            suffix=".wav",
            dir=path.parent,
        )
    except OSError:
        return None
    tmp_path = Path(tmp.name)
    tmp.close()
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(tmp_path),
    ]
    _stdout, _stderr, returncode = _commands.run_command_status(command)
    if returncode != 0:
        tmp_path.unlink(missing_ok=True)
        return None
    return tmp_path
