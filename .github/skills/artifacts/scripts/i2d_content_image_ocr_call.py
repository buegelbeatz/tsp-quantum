"""Low-level OCR call helpers for i2d_content_image_ocr."""

from __future__ import annotations

from typing import Any


def call_ocr(
    pytesseract_module: Any,
    image_obj: object,
    *,
    timeout: int,
    config: str | None = None,
    lang: str | None = None,
) -> str:
    """Call pytesseract with optional config and tolerate simple test doubles."""
    kwargs: dict[str, object] = {"timeout": timeout}
    if config:
        kwargs["config"] = config
    if lang:
        kwargs["lang"] = lang
    try:
        return str(pytesseract_module.image_to_string(image_obj, **kwargs)).strip()  # type: ignore[attr-defined]
    except TypeError:
        return str(
            pytesseract_module.image_to_string(image_obj, timeout=timeout)
        ).strip()  # type: ignore[attr-defined]
