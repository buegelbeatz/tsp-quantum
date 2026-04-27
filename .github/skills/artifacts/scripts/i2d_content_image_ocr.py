"""Image OCR extraction helper for i2d_content."""

from __future__ import annotations

import os
from pathlib import Path

import i2d_content_image_ocr_call as _ocr_call_helper
import i2d_content_image_ocr_cli as _ocr_cli
import i2d_content_image_ocr_output as _ocr_output
import i2d_content_image_ocr_pil as _ocr_pil
import i2d_content_image_ocr_scoring as _ocr_scoring


def _ocr_call(
    pytesseract_module: object,
    image_obj: object,
    *,
    timeout: int,
    config: str | None = None,
    lang: str | None = None,
) -> str:
    """Call the dedicated OCR helper for the low-level pytesseract invocation."""
    return _ocr_call_helper.call_ocr(
        pytesseract_module,
        image_obj,
        timeout=timeout,
        config=config,
        lang=lang,
    )


def _build_ok_response(file_facts: str, text: str) -> tuple[str, str, str]:
    """Delegate success response rendering to the output helper module."""
    return _ocr_output.build_ok_response(file_facts, text)


def _build_empty_response(*, file_facts: str, timed_out: bool) -> tuple[str, str, str]:
    """Delegate empty response rendering to the output helper module."""
    return _ocr_output.build_empty_response(file_facts, timed_out=timed_out)


def _build_error_response(file_facts: str, message: str) -> tuple[str, str, str]:
    """Delegate error response rendering to the output helper module."""
    return _ocr_output.build_error_response(file_facts, message)


def extract_image_ocr(
    path: Path,
    *,
    env_int_fn,
    file_facts_fn,
    run_command_with_timeout_fn,
) -> tuple[str, str, str]:
    """Extract text from image files via pytesseract or tesseract CLI."""
    ocr_timeout_seconds = env_int_fn(
        "I2D_OCR_TIMEOUT_SECONDS", default=45, minimum=1, maximum=300
    )
    ocr_languages = os.getenv("I2D_OCR_LANG", "eng+deu").strip() or "eng+deu"

    def _score_ocr_candidate(text: str) -> tuple[int, int]:
        return _ocr_scoring.score_ocr_candidate(text)

    try:
        from PIL import Image  # type: ignore[import-untyped]
        import pytesseract  # type: ignore[import-untyped]
    except ImportError:
        return _ocr_cli.extract_image_ocr_cli(
            path,
            run_command_with_timeout_fn=run_command_with_timeout_fn,
            file_facts_fn=file_facts_fn,
            ocr_timeout_seconds=ocr_timeout_seconds,
        )

    return _ocr_pil.extract_image_ocr_with_pil(
        path,
        image_module=Image,
        pytesseract_module=pytesseract,
        file_facts_fn=file_facts_fn,
        ocr_call_fn=_ocr_call,
        ocr_timeout_seconds=ocr_timeout_seconds,
        ocr_languages=ocr_languages,
        score_candidate_fn=_score_ocr_candidate,
        build_ok_response_fn=_build_ok_response,
        build_empty_response_fn=_build_empty_response,
        build_error_response_fn=_build_error_response,
    )
