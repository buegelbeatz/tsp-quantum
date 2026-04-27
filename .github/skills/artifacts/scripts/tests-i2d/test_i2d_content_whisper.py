"""Unit tests for i2d_content_whisper delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_whisper as whisper  # noqa: E402


def test_run_faster_whisper_transcribe_delegates_to_helper(tmp_path: Path) -> None:
    """Low-level whisper transcription should delegate to dedicated helper module."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")

    with patch(
        "i2d_content_whisper._whisper_transcribe.run_faster_whisper_transcribe",
        return_value=("hello", "en", ""),
    ) as helper_mock:
        result = whisper.run_faster_whisper_transcribe(
            media,
            "tiny",
            vad_filter=True,
            beam_size=5,
            temperature=0.0,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
        )

    assert result == ("hello", "en", "")
    helper_mock.assert_called_once_with(
        media,
        "tiny",
        vad_filter=True,
        beam_size=5,
        temperature=0.0,
        no_speech_threshold=0.6,
        log_prob_threshold=-1.0,
    )


def test_extract_whisper_uses_configured_model_list_helper(tmp_path: Path) -> None:
    """extract_whisper should resolve models through config helper module."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")

    with patch(
        "i2d_content_whisper._whisper_config.get_model_names",
        return_value=["tiny"],
    ) as model_mock:
        content, engine, status = whisper.extract_whisper(
            media,
            file_facts_fn=lambda _p: "facts",
            run_command_fn=lambda _cmd: ("{}", ""),
            prepare_audio_fn=lambda _p: None,
            transcribe_fn=lambda *_args, **_kwargs: ("", "", ""),
        )

    model_mock.assert_called_once_with()
    assert engine == "whisper"
    assert status == "empty"
    assert "models=tiny" in content


def test_extract_whisper_delegates_attempt_list_to_helper(tmp_path: Path) -> None:
    """extract_whisper should build attempt lists through the dedicated helper."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")

    with patch(
        "i2d_content_whisper._whisper_config.get_model_names",
        return_value=["tiny"],
    ):
        with patch(
            "i2d_content_whisper._whisper_attempts.build_attempts",
            return_value=[(media, True, 5, 0.0, "default")],
        ) as attempts_mock:
            content, engine, status = whisper.extract_whisper(
                media,
                file_facts_fn=lambda _p: "facts",
                run_command_fn=lambda _cmd: ("{}", ""),
                prepare_audio_fn=lambda _p: None,
                transcribe_fn=lambda *_args, **_kwargs: ("", "", ""),
            )

    attempts_mock.assert_called_once_with(media, None)
    assert engine == "whisper"
    assert status == "empty"
    assert "facts" in content


def test_prepare_audio_for_whisper_delegates_to_audio_helper(tmp_path: Path) -> None:
    """prepare_audio_for_whisper should delegate to dedicated audio helper."""
    media = tmp_path / "sample.mp3"
    media.write_bytes(b"ID3")
    expected = tmp_path / "normalized.wav"

    with patch(
        "i2d_content_whisper._whisper_audio.prepare_audio_for_whisper",
        return_value=expected,
    ) as audio_mock:
        result = whisper.prepare_audio_for_whisper(media)

    assert result == expected
    audio_mock.assert_called_once_with(media)
