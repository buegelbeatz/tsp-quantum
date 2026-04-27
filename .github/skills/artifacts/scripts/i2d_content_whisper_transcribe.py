"""Low-level faster-whisper transcription helpers."""

from __future__ import annotations

from pathlib import Path


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
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]
    except ImportError:
        return "", "", "Transcription unavailable (install faster-whisper)."

    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(media_path),
            beam_size=beam_size,
            vad_filter=vad_filter,
            condition_on_previous_text=False,
            temperature=temperature,
            no_speech_threshold=no_speech_threshold,
            log_prob_threshold=log_prob_threshold,
        )
        transcript = "\n".join(
            segment.text.strip() for segment in segments if segment.text.strip()
        ).strip()
        return transcript, str(getattr(info, "language", "unknown")), ""
    except (OSError, RuntimeError, ValueError) as exc:
        return "", "", str(exc)
