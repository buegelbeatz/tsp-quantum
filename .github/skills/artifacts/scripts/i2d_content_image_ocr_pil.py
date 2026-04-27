"""Pillow-backed OCR helpers for image extraction."""

from __future__ import annotations

from pathlib import Path

from typing import Any

import i2d_content_image_ocr_enhance as _ocr_enhance


def _attempt_heif_registration() -> None:
    """Attempt to register HEIF opener if pillow_heif is available."""
    try:
        from pillow_heif import register_heif_opener  # type: ignore[import-untyped]

        register_heif_opener()
    except ImportError:
        pass


def _scale_image_if_needed(img: Any, image_module: Any) -> Any:
    """Downscale image if larger than 2200 pixels."""
    base_width = getattr(img, "width", None)
    base_height = getattr(img, "height", None)
    if isinstance(base_width, int) and isinstance(base_height, int):
        max_dim = max(base_width, base_height)
        if max_dim > 2200 and hasattr(img, "resize"):
            scale = 2200.0 / float(max_dim)
            img = img.resize(
                (int(base_width * scale), int(base_height * scale)),
                resample=image_module.Resampling.LANCZOS,
            )
    return img


def _try_run_ocr(
    base_img: Any,
    image_module: Any,
    pytesseract_module: Any,
    ocr_call_fn,
    ocr_timeout_seconds: int,
    ocr_languages: str,
    score_candidate_fn,
) -> str:
    """Run OCR with optional enhanced passes if initial attempt is empty."""
    text = ocr_call_fn(
        pytesseract_module,
        base_img,
        timeout=ocr_timeout_seconds,
        lang=ocr_languages,
    )
    if not text:
        try:
            from PIL import ImageFilter, ImageOps  # type: ignore[import-untyped]

            text = _ocr_enhance.run_enhanced_ocr_passes(
                base_img,
                image_ops_module=ImageOps,
                image_filter_module=ImageFilter,
                image_resampling_lanczos=image_module.Resampling.LANCZOS,
                ocr_call_fn=ocr_call_fn,
                pytesseract_module=pytesseract_module,
                ocr_timeout_seconds=ocr_timeout_seconds,
                ocr_languages=ocr_languages,
                score_candidate_fn=score_candidate_fn,
            )
        except (
            ImportError,
            AttributeError,
            AssertionError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            pass
    return text


def extract_image_ocr_with_pil(
    path: Path,
    *,
    image_module: Any,
    pytesseract_module: Any,
    file_facts_fn,
    ocr_call_fn,
    ocr_timeout_seconds: int,
    ocr_languages: str,
    score_candidate_fn,
    build_ok_response_fn,
    build_empty_response_fn,
    build_error_response_fn,
) -> tuple[str, str, str]:
    """Run OCR using Pillow and pytesseract with enhanced fallback passes."""
    try:
        _attempt_heif_registration()
        with image_module.open(path) as img:
            base_img = _scale_image_if_needed(img.convert("RGB"), image_module)
            text = _try_run_ocr(
                base_img,
                image_module,
                pytesseract_module,
                ocr_call_fn,
                ocr_timeout_seconds,
                ocr_languages,
                score_candidate_fn,
            )
        if text:
            return build_ok_response_fn(file_facts_fn(path), text)
        return build_empty_response_fn(file_facts=file_facts_fn(path), timed_out=False)
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        message = str(exc)
        if "timeout" in message.lower():
            return build_empty_response_fn(
                file_facts=file_facts_fn(path), timed_out=True
            )
        return build_error_response_fn(file_facts_fn(path), message)
