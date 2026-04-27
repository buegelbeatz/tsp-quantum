"""Content extraction and markdown rendering for 10-data bundles."""

from __future__ import annotations

from functools import partial
from pathlib import Path

import i2d_content_extract_flow as _extract_flow
import i2d_content_form_local as _form_local
import i2d_content_form_text as _form_text
import i2d_content_helpers as _helpers
import i2d_content_image_ocr as _image_ocr
import i2d_content_markitdown_email as _markitdown_email
import i2d_content_render as _render
import i2d_content_whisper as _whisper

_DEFAULT_TEMPLATE = _render.DEFAULT_TEMPLATE

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
_EML_SUFFIXES = {".eml"}

# MarkItDown may return synthetic transcript failure text while still reporting
# content; treat these placeholders as extraction errors so media files can
# fall back to Whisper.
_MARKITDOWN_TRANSCRIPT_ERROR_SNIPPETS = (
    "could not transcribe this audio",
    "could not transcribe this video",
)


_extract_json_payload = _helpers._extract_json_payload
_extract_ocr_plain_text = _helpers._extract_ocr_plain_text
_is_low_quality_ocr_text = _helpers._is_low_quality_ocr_text
_build_form_markdown_from_vision = _helpers._build_form_markdown_from_vision
_should_prefer_vision_form = _helpers._should_prefer_vision_form


def _build_form_markdown_from_text_description(text: str) -> str | None:
    return _form_text.build_form_markdown_from_text_description(
        text,
        extract_form_fields_fn=_extract_form_fields_from_text,
    )


_file_facts = _helpers._file_facts
_run_command = _helpers._run_command
_run_command_with_timeout = _helpers._run_command_with_timeout
_env_int = _helpers._env_int
compute_sha256 = _helpers.compute_sha256
_extract_with_markitdown = partial(
    _markitdown_email.extract_with_markitdown,
    file_facts_fn=_file_facts,
)
_markitdown_contains_transcript_error = partial(
    _markitdown_email.markitdown_contains_transcript_error,
    snippets=_MARKITDOWN_TRANSCRIPT_ERROR_SNIPPETS,
)
_cleanup_epub_markitdown_content = _markitdown_email.cleanup_epub_markitdown_content
_extract_eml = partial(_markitdown_email.extract_eml, file_facts_fn=_file_facts)


def _extract_image_ocr(path: Path) -> tuple[str, str, str]:
    return _image_ocr.extract_image_ocr(
        path,
        env_int_fn=_env_int,
        file_facts_fn=_file_facts,
        run_command_with_timeout_fn=_run_command_with_timeout,
    )


_extract_form_fields_from_text = _form_local.extract_form_fields_from_text
_local_visual_signals = _form_local.local_visual_signals


def _build_local_form_analysis(
    ocr_text: str, ocr_status: str, source_path: Path
) -> str:
    return _form_local.build_local_form_analysis(
        ocr_text,
        ocr_status,
        source_path,
        extract_form_fields_fn=_extract_form_fields_from_text,
        local_visual_signals_fn=_local_visual_signals,
    )


_run_faster_whisper_transcribe = _whisper.run_faster_whisper_transcribe
_prepare_audio_for_whisper = _whisper.prepare_audio_for_whisper
_extract_whisper = partial(
    _whisper.extract_whisper,
    file_facts_fn=_file_facts,
    run_command_fn=_run_command,
    prepare_audio_fn=_prepare_audio_for_whisper,
    transcribe_fn=_run_faster_whisper_transcribe,
)


def extract_content(path: Path) -> tuple[str, str, str]:
    """Extract normalized markdown-ready text from a source file.

    Returns: (content, extraction_engine, extraction_status)
    """
    return _extract_flow.extract_content(
        path,
        file_facts_fn=_file_facts,
        extract_eml_fn=_extract_eml,
        extract_with_markitdown_fn=_extract_with_markitdown,
        cleanup_epub_markitdown_content_fn=_cleanup_epub_markitdown_content,
        markitdown_contains_transcript_error_fn=_markitdown_contains_transcript_error,
        extract_image_ocr_fn=_extract_image_ocr,
        extract_json_payload_fn=_extract_json_payload,
        build_form_markdown_from_vision_fn=_build_form_markdown_from_vision,
        should_prefer_vision_form_fn=_should_prefer_vision_form,
        build_local_form_analysis_fn=_build_local_form_analysis,
        extract_whisper_fn=_extract_whisper,
        build_form_markdown_from_text_description_fn=_build_form_markdown_from_text_description,
        image_suffixes=_IMAGE_SUFFIXES,
        audio_suffixes=_AUDIO_SUFFIXES,
        video_suffixes=_VIDEO_SUFFIXES,
        eml_suffixes=_EML_SUFFIXES,
    )


def render_bundle_markdown(template_path: Path | None, fields: dict[str, str]) -> str:
    """Render data bundle markdown from template and fields."""
    return _render.render_bundle_markdown(
        template_path,
        fields,
        default_template=_DEFAULT_TEMPLATE,
    )
