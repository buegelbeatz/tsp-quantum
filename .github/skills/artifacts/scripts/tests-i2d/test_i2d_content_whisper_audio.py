"""Unit tests for i2d_content_whisper_audio command execution."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_whisper_audio as whisper_audio  # noqa: E402


def test_prepare_audio_for_whisper_uses_command_runner(tmp_path: Path) -> None:
    """Audio normalization should call ffmpeg through the shared command helper."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")

    def fake_run(
        command: list[str],
        timeout_seconds: int | None = None,
    ) -> tuple[str, str, int]:
        """TODO: add docstring for fake_run."""
        Path(command[-1]).write_bytes(b"RIFF")
        return "", "", 0

    with patch(
        "i2d_content_whisper_audio._commands.run_command_status",
        side_effect=fake_run,
    ) as command_mock:
        result = whisper_audio.prepare_audio_for_whisper(media)

    assert result is not None
    assert result.parent == tmp_path
    assert result.name.startswith(".whisper-")
    called_command = command_mock.call_args.args[0]
    assert called_command[0] == "ffmpeg"
    assert called_command[3] == str(media)
    assert called_command[-1] == str(result)


def test_prepare_audio_for_whisper_cleans_failed_temp_file(tmp_path: Path) -> None:
    """Failed audio normalization should remove the temporary output file."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")

    with patch(
        "i2d_content_whisper_audio._commands.run_command_status",
        return_value=("", "failure", 1),
    ):
        result = whisper_audio.prepare_audio_for_whisper(media)

    assert result is None
    assert list(tmp_path.glob(".whisper-*.wav")) == []
