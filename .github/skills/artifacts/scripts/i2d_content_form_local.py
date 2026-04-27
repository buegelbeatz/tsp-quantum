"""Local form-analysis helpers for i2d_content."""

from __future__ import annotations

from pathlib import Path

import i2d_content_form_fields as _form_fields
import i2d_content_form_visual as _form_visual


def extract_form_fields_from_text(text: str) -> list[tuple[str, str]]:
    """Extract simple key/value style form fields from OCR text."""
    return _form_fields.extract_form_fields_from_text(text)


def local_visual_signals(path: Path) -> tuple[int, int]:
    """Detect likely input-box and button regions from image geometry."""
    return _form_visual.local_visual_signals(path)


def _compact_line(raw_line: str) -> str:
    """Normalize spacing in one OCR line."""
    return " ".join(raw_line.split())


def _is_candidate_shape(compact: str, word_count: int) -> bool:
    """Check length and word-count heuristic for candidate labels."""
    return 3 <= len(compact) <= 40 and 1 <= word_count <= 4


def _has_enough_alpha(compact: str) -> bool:
    """Check if OCR line has sufficient alphabetic signal."""
    alpha_count = sum(1 for ch in compact if ch.isalpha())
    return alpha_count >= 3 and alpha_count >= (len(compact) // 2)


def _is_candidate_line(compact: str) -> bool:
    """Check if compact OCR line qualifies as form-field candidate."""
    if not compact:
        return False
    words = compact.split()
    if not _is_candidate_shape(compact, len(words)):
        return False
    return _has_enough_alpha(compact)


def _filter_candidate_lines(normalized: str) -> list[str]:
    """Filter OCR lines by heuristic: short, mostly alpha, few words."""
    candidate_lines: list[str] = []
    for raw_line in normalized.splitlines():
        compact = _compact_line(raw_line)
        if _is_candidate_line(compact):
            candidate_lines.append(compact)
    return candidate_lines


def _build_fields_from_candidates(candidates: list[str]) -> list[tuple[str, str]]:
    """Convert candidate lines to fields, deduplicating by lowercase."""
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return [(item, "") for item in unique[:8]]


def _build_form_table(fields: list[tuple[str, str]]) -> str:
    """Build markdown table from form fields."""
    rows = ["| Field | Value |", "| --- | --- |"]
    if fields:
        for label, value in fields:
            rows.append(f"| {label} | {value} |")
    else:
        rows.append("| (no structured field detected) |  |")
    return "\n".join(rows)


def _normalize_ocr_text(ocr_text: str) -> str:
    """Normalize OCR text by stripping and filtering empty lines."""
    return "\n".join(line.strip() for line in ocr_text.splitlines() if line.strip())


def _extract_or_synthesize_fields(
    normalized_text: str,
    source_path: Path,
    extract_form_fields_fn,
    local_visual_signals_fn,
) -> list:
    """Extract or synthesize form fields from text and visual signals."""
    # Try direct extraction
    fields = extract_form_fields_fn(normalized_text)

    # Fallback: candidate line analysis
    if not fields:
        candidates = _filter_candidate_lines(normalized_text)
        if candidates:
            fields = _build_fields_from_candidates(candidates)

    # Fallback: synthetic fields from visual signals
    if not fields:
        input_boxes, _ = local_visual_signals_fn(source_path)
        if input_boxes > 0:
            fields = [
                (f"input_field_{idx + 1}", "") for idx in range(min(input_boxes, 12))
            ]

    return fields


def _is_form_detected(fields: list, input_boxes: int, buttons: int) -> bool:
    """Determine if form content is detected."""
    return bool(fields) or input_boxes >= 2 or (buttons >= 1 and input_boxes >= 1)


def _build_result_string(
    fields: list, ocr_status: str, input_boxes: int, buttons: int
) -> str:
    """Build final form analysis result string."""
    contains_form = _is_form_detected(fields, input_boxes, buttons)
    table = _build_form_table(fields)
    return (
        "## Local Form Analysis\n\n"
        f"- contains_form: {'true' if contains_form else 'false'}\n"
        f"- source: ocr ({ocr_status})\n"
        f"- detected_fields: {len(fields)}\n"
        f"- detected_input_boxes: {input_boxes}\n"
        f"- detected_buttons: {buttons}\n\n" + table
    )


def build_local_form_analysis(
    ocr_text: str,
    ocr_status: str,
    source_path: Path,
    *,
    extract_form_fields_fn=extract_form_fields_from_text,
    local_visual_signals_fn=local_visual_signals,
) -> str:
    """Build local form analysis when remote vision providers are unavailable."""
    # Pipeline: normalize → extract/synthesize → visual signals → classify → build result
    normalized = _normalize_ocr_text(ocr_text)
    fields = _extract_or_synthesize_fields(
        normalized, source_path, extract_form_fields_fn, local_visual_signals_fn
    )
    input_boxes, buttons = local_visual_signals_fn(source_path)

    return _build_result_string(fields, ocr_status, input_boxes, buttons)
