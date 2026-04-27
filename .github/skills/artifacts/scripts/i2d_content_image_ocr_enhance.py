"""Enhanced OCR pass helpers for image extraction."""

from __future__ import annotations

from typing import Any

_OCR_CONFIGS = ("--oem 3 --psm 6", "--oem 3 --psm 11", "--oem 3 --psm 11")


def _preprocess_image(
    base_img: Any,
    *,
    image_ops_module: Any,
    image_filter_module: Any,
    image_resampling_lanczos: Any,
) -> tuple[object, object]:
    """Return (denoised, upscaled) image variants from the base image."""
    gray = image_ops_module.grayscale(base_img)
    boosted = image_ops_module.autocontrast(gray)
    denoised = boosted.filter(image_filter_module.MedianFilter(size=3))
    upscaled = denoised.resize(
        (denoised.width * 2, denoised.height * 2),
        resample=image_resampling_lanczos,
    )
    return denoised, upscaled


def run_enhanced_ocr_passes(
    base_img: object,
    *,
    image_ops_module: object,
    image_filter_module: object,
    image_resampling_lanczos: object,
    ocr_call_fn,
    pytesseract_module: object,
    ocr_timeout_seconds: int,
    ocr_languages: str,
    score_candidate_fn,
) -> str:
    """Run additional OCR attempts on preprocessed image variants."""
    denoised, upscaled = _preprocess_image(
        base_img,
        image_ops_module=image_ops_module,
        image_filter_module=image_filter_module,
        image_resampling_lanczos=image_resampling_lanczos,
    )
    images = (denoised, denoised, upscaled)
    candidates = [
        ocr_call_fn(
            pytesseract_module,
            img,
            timeout=ocr_timeout_seconds,
            config=cfg,
            lang=ocr_languages,
        )
        for img, cfg in zip(images, _OCR_CONFIGS)
    ]
    return max(candidates, key=score_candidate_fn).strip()
