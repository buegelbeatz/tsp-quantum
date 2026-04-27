"""Extraction flow orchestration helper for i2d_content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import i2d_content_extract_image_flow as _image_flow
import i2d_content_text_flow as _text_flow


@dataclass
class ExtractDeps:
    """Bundled dependency-injection bag for extract_content."""

    file_facts_fn: Any
    extract_eml_fn: Any
    extract_with_markitdown_fn: Any
    cleanup_epub_markitdown_content_fn: Any
    markitdown_contains_transcript_error_fn: Any
    extract_image_ocr_fn: Any
    extract_json_payload_fn: Any
    build_form_markdown_from_vision_fn: Any
    should_prefer_vision_form_fn: Any
    build_local_form_analysis_fn: Any
    extract_whisper_fn: Any
    build_form_markdown_from_text_description_fn: Any
    image_suffixes: set[str]
    audio_suffixes: set[str]
    video_suffixes: set[str]
    eml_suffixes: set[str]


def _is_successful_markitdown(engine: str, status: str) -> bool:
    """Return True when markitdown extraction succeeded."""
    return engine == "markitdown" and status == "ok"


def _should_cleanup_epub_result(engine: str, status: str, suffix: str) -> bool:
    """Return True when EPUB post-processing should run."""
    return _is_successful_markitdown(engine, status) and suffix == ".epub"


def _should_reclassify_transcript_error(
    text: str,
    engine: str,
    status: str,
    suffix: str,
    *,
    deps: ExtractDeps,
) -> bool:
    """Return True when transcript extraction error should become status=error."""
    if not _is_successful_markitdown(engine, status):
        return False
    if suffix not in deps.audio_suffixes and suffix not in deps.video_suffixes:
        return False
    return deps.markitdown_contains_transcript_error_fn(text)


def _normalize_markitdown_result(
    text: str,
    engine: str,
    status: str,
    suffix: str,
    *,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Apply post-processing and error reclassification to a markitdown result."""
    if _should_cleanup_epub_result(engine, status, suffix):
        text = deps.cleanup_epub_markitdown_content_fn(text)

    if _should_reclassify_transcript_error(text, engine, status, suffix, deps=deps):
        status = "error"

    return text, engine, status


def _extract_text_file(
    path: Path,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Extract text file content via text flow."""
    from i2d_link import extract_url_list, is_url_list_file

    return _text_flow.extract_text_content(
        path,
        file_facts_fn=deps.file_facts_fn,
        build_form_markdown_from_text_description_fn=deps.build_form_markdown_from_text_description_fn,
        is_url_list_file_fn=is_url_list_file,
        extract_url_list_fn=extract_url_list,
    )


def _extract_eml_file(
    path: Path,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Extract EML file content."""
    return deps.extract_eml_fn(path)


def _extract_image_file(
    path: Path,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Extract image file content via vision flow."""
    return _image_flow.extract_image_content(
        path,
        file_facts_fn=deps.file_facts_fn,
        extract_image_ocr_fn=deps.extract_image_ocr_fn,
        extract_json_payload_fn=deps.extract_json_payload_fn,
        build_form_markdown_from_vision_fn=deps.build_form_markdown_from_vision_fn,
        should_prefer_vision_form_fn=deps.should_prefer_vision_form_fn,
        build_local_form_analysis_fn=deps.build_local_form_analysis_fn,
    )


def _extract_audio_video_file(
    path: Path,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Extract audio/video file content via whisper."""
    return deps.extract_whisper_fn(path)


def _try_markitdown_with_fallbacks(
    path: Path,
    suffix: str,
    text: str,
    engine: str,
    status: str,
    deps: ExtractDeps,
) -> tuple[str, str, str]:
    """Try markitdown extraction with fallback to image/audio/video handlers."""
    # If markitdown succeeded, return it
    if engine and status != "error":
        return text, engine, status

    # Try image extraction if available
    if suffix in deps.image_suffixes:
        return _extract_image_file(path, deps)

    # Try audio/video extraction if available
    if suffix in deps.audio_suffixes or suffix in deps.video_suffixes:
        return _extract_audio_video_file(path, deps)

    # If markitdown produced any result, return it
    if engine:
        return text, engine, status

    # Last resort fallback
    return (
        f"## File Facts\n\n{deps.file_facts_fn(path)}\n\n"
        f"Extraction unavailable for '{path.name}'. Install markitdown (or OCR/Whisper deps) for richer content.",
        "fallback",
        "unavailable",
    )


def extract_content_impl(path: Path, deps: ExtractDeps) -> tuple[str, str, str]:
    """Extract normalized markdown-ready text from a source file (implementation)."""
    suffix = path.suffix.lower()

    # Try text file extraction
    if suffix == ".txt":
        return _extract_text_file(path, deps)

    # Try EML file extraction
    if suffix in deps.eml_suffixes:
        return _extract_eml_file(path, deps)

    # Try markitdown extraction first, then fallbacks
    text, engine, status = deps.extract_with_markitdown_fn(path)
    text, engine, status = _normalize_markitdown_result(
        text, engine, status, suffix, deps=deps
    )

    return _try_markitdown_with_fallbacks(path, suffix, text, engine, status, deps)


def extract_content(
    path: Path,
    *,
    file_facts_fn,
    extract_eml_fn,
    extract_with_markitdown_fn,
    cleanup_epub_markitdown_content_fn,
    markitdown_contains_transcript_error_fn,
    extract_image_ocr_fn,
    extract_json_payload_fn,
    build_form_markdown_from_vision_fn,
    should_prefer_vision_form_fn,
    build_local_form_analysis_fn,
    extract_whisper_fn,
    build_form_markdown_from_text_description_fn,
    image_suffixes: set[str],
    audio_suffixes: set[str],
    video_suffixes: set[str],
    eml_suffixes: set[str],
) -> tuple[str, str, str]:
    """Extract normalized markdown-ready text from a source file."""
    deps = ExtractDeps(
        file_facts_fn=file_facts_fn,
        extract_eml_fn=extract_eml_fn,
        extract_with_markitdown_fn=extract_with_markitdown_fn,
        cleanup_epub_markitdown_content_fn=cleanup_epub_markitdown_content_fn,
        markitdown_contains_transcript_error_fn=markitdown_contains_transcript_error_fn,
        extract_image_ocr_fn=extract_image_ocr_fn,
        extract_json_payload_fn=extract_json_payload_fn,
        build_form_markdown_from_vision_fn=build_form_markdown_from_vision_fn,
        should_prefer_vision_form_fn=should_prefer_vision_form_fn,
        build_local_form_analysis_fn=build_local_form_analysis_fn,
        extract_whisper_fn=extract_whisper_fn,
        build_form_markdown_from_text_description_fn=build_form_markdown_from_text_description_fn,
        image_suffixes=image_suffixes,
        audio_suffixes=audio_suffixes,
        video_suffixes=video_suffixes,
        eml_suffixes=eml_suffixes,
    )
    return extract_content_impl(path, deps)
