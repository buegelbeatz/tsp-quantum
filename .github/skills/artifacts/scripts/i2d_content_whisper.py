"""Whisper media transcription helpers for i2d_content."""

from __future__ import annotations

from pathlib import Path

import i2d_content_whisper_audio as _whisper_audio
import i2d_content_whisper_attempts as _whisper_attempts
import i2d_content_whisper_config as _whisper_config
import i2d_content_whisper_transcribe as _whisper_transcribe


def run_faster_whisper_transcribe(
    media_path: Path,
    model_name: str,
    *,
    vad_filter: bool,
    beam_size: int,
    temperature: float,
    no_speech_threshold: float,
    log_prob_threshold: float,
) -> tuple[str, str, str]:
    """Run one faster-whisper transcription attempt."""
    return _whisper_transcribe.run_faster_whisper_transcribe(
        media_path,
        model_name,
        vad_filter=vad_filter,
        beam_size=beam_size,
        temperature=temperature,
        no_speech_threshold=no_speech_threshold,
        log_prob_threshold=log_prob_threshold,
    )


def prepare_audio_for_whisper(path: Path) -> Path | None:
    """Create a normalized mono WAV file for more robust speech detection."""
    return _whisper_audio.prepare_audio_for_whisper(path)


_FFPROBE_CMD = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration,bit_rate",
    "-show_streams",
    "-of",
    "json",
]


def _run_model_attempts(
    path: Path,
    model_names: list[str],
    normalized_audio: Path | None,
    *,
    prepare_audio_fn,
    transcribe_fn,
) -> tuple[str | None, str | None, str | None, list[str], Path | None]:
    """Iterate over models and attempts; return first successful transcript or errors."""
    attempt_errors: list[str] = []
    for model_name in model_names:
        normalized_audio = prepare_audio_fn(path)
        attempts = _whisper_attempts.build_attempts(path, normalized_audio)
        for media_path, vad_filter, beam_size, temperature, label in attempts:
            no_speech_threshold = 0.6 if label == "default" else 1.0
            log_prob_threshold = -1.0 if label == "default" else -3.0
            transcript, language, error = transcribe_fn(
                media_path,
                model_name,
                vad_filter=vad_filter,
                beam_size=beam_size,
                temperature=temperature,
                no_speech_threshold=no_speech_threshold,
                log_prob_threshold=log_prob_threshold,
            )
            if transcript:
                return (
                    transcript,
                    language,
                    model_name,
                    attempt_errors,
                    normalized_audio,
                )
            if error:
                attempt_errors.append(f"{model_name}/{label}: {error}")
    return None, None, None, attempt_errors, normalized_audio


def _build_transcript_output(
    header: str,
    transcript: str,
    language: str,
    model_name: str,
) -> tuple[str, str, str]:
    """Format successful transcript output."""
    return (
        f"{header}## Transcript (language={language}, model={model_name}, attempt=default)\n\n{transcript}",
        "whisper",
        "ok",
    )


def _build_unavailable_output(header: str) -> tuple[str, str, str]:
    """Format unavailable output when faster-whisper not installed."""
    return (
        header + "Transcription unavailable (install faster-whisper).",
        "whisper",
        "unavailable",
    )


def _build_empty_output(header: str, model_names: list[str]) -> tuple[str, str, str]:
    """Format empty output when no transcript was extracted."""
    model_list = ",".join(model_names)
    return (
        f"{header}Whisper returned no transcript (models={model_list}). "
        "Likely causes: no speech, low audio quality, or very short speech segments.",
        "whisper",
        "empty",
    )


def _build_whisper_header(path: Path, file_facts_fn, media_probe: str) -> str:
    """Build shared whisper output header with file facts and probe details."""
    return (
        f"## File Facts\n\n{file_facts_fn(path)}\n\n## Media Probe\n\n{media_probe}\n\n"
    )


def _is_missing_whisper_dependency(attempt_errors: list[str]) -> bool:
    """Return True when all attempt errors indicate missing faster-whisper dependency."""
    return bool(attempt_errors) and all(
        "install faster-whisper" in error.lower() for error in attempt_errors
    )


def _select_whisper_result(
    header: str,
    transcript: str | None,
    language: str | None,
    model_name: str | None,
    attempt_errors: list[str],
    model_names: list[str],
) -> tuple[str, str, str]:
    """Select final whisper output tuple based on attempt outcome."""
    if transcript:
        return _build_transcript_output(
            header, transcript, language or "unknown", model_name or "unknown"
        )
    if _is_missing_whisper_dependency(attempt_errors):
        return _build_unavailable_output(header)
    return _build_empty_output(header, model_names)


def extract_whisper(
    path: Path,
    *,
    file_facts_fn,
    run_command_fn,
    prepare_audio_fn=prepare_audio_for_whisper,
    transcribe_fn=run_faster_whisper_transcribe,
) -> tuple[str, str, str]:
    """Extract transcript text from audio/video using faster-whisper."""
    ffprobe_stdout, ffprobe_stderr = run_command_fn(_FFPROBE_CMD + [str(path)])
    media_probe = ffprobe_stdout or ffprobe_stderr or "ffprobe unavailable"
    model_names = _whisper_config.get_model_names()
    normalized_audio: Path | None = None

    try:
        transcript, language, model_name, attempt_errors, normalized_audio = (
            _run_model_attempts(
                path,
                model_names,
                normalized_audio,
                prepare_audio_fn=prepare_audio_fn,
                transcribe_fn=transcribe_fn,
            )
        )
        header = _build_whisper_header(path, file_facts_fn, media_probe)
        return _select_whisper_result(
            header,
            transcript,
            language,
            model_name,
            attempt_errors,
            model_names,
        )
    finally:
        if normalized_audio is not None:
            normalized_audio.unlink(missing_ok=True)
