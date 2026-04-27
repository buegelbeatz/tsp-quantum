"""Image extraction flow helpers for i2d_content extraction orchestration."""

from __future__ import annotations

from pathlib import Path

_VISION_OCR_NOTE = (
    "Note: Vision output can be uncertain; prefer OCR text where available."
)
_OCR_OMIT_NOTE = (
    "Note: OCR output omitted because detected form confidence is high "
    "while OCR text quality is low."
)


def _build_combined_output(
    ocr_text: str,
    ocr_engine: str,
    vision_text: str,
    vision_engine: str,
    form_markdown: str | None,
    path: Path,
    *,
    file_facts_fn,
    should_prefer_vision_form_fn,
    vision_payload: object,
) -> tuple[str, str, str]:
    """Merge OCR + vision results into the best combined output for ok+ok case."""
    if isinstance(vision_payload, dict) and should_prefer_vision_form_fn(
        vision_payload, ocr_text
    ):
        preferred = (
            f"## File Facts\n\n{file_facts_fn(path)}\n\n"
            f"## Vision Analysis ({vision_engine})\n\n{vision_text}"
        )
        if form_markdown:
            preferred += f"\n\n{form_markdown}"
        preferred += f"\n\n{_OCR_OMIT_NOTE}"
        return preferred, vision_engine, "ok"

    combined = (
        f"{ocr_text}\n\n"
        f"## Vision Analysis ({vision_engine})\n\n{vision_text}\n\n"
        f"{_VISION_OCR_NOTE}"
    )
    if form_markdown:
        combined = f"{combined}\n\n{form_markdown}"
    return combined, f"{ocr_engine}+{vision_engine}", "ok"


def extract_image_content(
    path: Path,
    *,
    file_facts_fn,
    extract_image_ocr_fn,
    extract_json_payload_fn,
    build_form_markdown_from_vision_fn,
    should_prefer_vision_form_fn,
    build_local_form_analysis_fn,
) -> tuple[str, str, str]:
    """Run OCR and vision analysis for image inputs and choose the best result."""
    from i2d_vision import classify_image

    ocr_text, ocr_engine, ocr_status = extract_image_ocr_fn(path)
    vision_text, vision_engine, vision_status = classify_image(path)
    vision_payload = (
        extract_json_payload_fn(vision_text) if vision_status == "ok" else None
    )
    form_markdown = (
        build_form_markdown_from_vision_fn(vision_payload)
        if isinstance(vision_payload, dict)
        else None
    )

    if vision_status == "ok" and ocr_status == "ok":
        return _build_combined_output(
            ocr_text,
            ocr_engine,
            vision_text,
            vision_engine,
            form_markdown,
            path,
            file_facts_fn=file_facts_fn,
            should_prefer_vision_form_fn=should_prefer_vision_form_fn,
            vision_payload=vision_payload,
        )

    if vision_status == "ok":
        content = (
            f"## File Facts\n\n{file_facts_fn(path)}\n\n"
            f"## Vision Analysis ({vision_engine})\n\n{vision_text}\n\n"
            f"## OCR Status\n\nengine={ocr_engine}, status={ocr_status}"
        )
        if form_markdown:
            content = f"{content}\n\n{form_markdown}"
        return content, vision_engine, "ok"

    local_form = build_local_form_analysis_fn(ocr_text, ocr_status, path)
    return f"{ocr_text}\n\n{local_form}", f"{ocr_engine}+form-local", ocr_status
