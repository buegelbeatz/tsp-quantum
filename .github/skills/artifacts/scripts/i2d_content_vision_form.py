"""Vision payload parsing and form normalization helpers."""

from __future__ import annotations

import json
import re

_SKIP_LABELS = {"enter", "submit", "login", "sign in"}


def _collect_json_candidates(raw: str) -> list[str]:
    """Collect JSON candidate strings from raw/fenced/loose payload variants."""
    candidates: list[str] = [raw]

    if raw.startswith("```"):
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence_match:
            candidates.append(fence_match.group(1).strip())

    loose_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if loose_match:
        candidates.append(loose_match.group(1).strip())

    return candidates


def _parse_first_dict(candidates: list[str]) -> dict[str, object] | None:
    """Parse candidates and return the first JSON object payload."""
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def extract_json_payload(text: str) -> dict[str, object] | None:
    """Best-effort parse for JSON payloads, including fenced markdown blocks."""
    raw = text.strip()
    if not raw:
        return None

    candidates = _collect_json_candidates(raw)
    return _parse_first_dict(candidates)


def _extract_detected_fields_rows(detected_fields: list) -> list[tuple[str, str, str]]:
    """Extract (label, value, confidence) from detected_fields list."""
    rows: list[tuple[str, str, str]] = []
    if not isinstance(detected_fields, list):
        return rows

    for entry in detected_fields:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        value = str(entry.get("value", "")).strip()
        confidence = str(entry.get("confidence", "")).strip().lower() or "unknown"
        if label:
            rows.append((label, value, confidence))

    return rows


def _is_valid_label_candidate(line: str) -> bool:
    """Check if line is a valid label candidate (has letters and not in skip list)."""
    if not line:
        return False
    normalized = line.lower()
    if normalized in _SKIP_LABELS:
        return False
    return re.search(r"[a-z]", normalized) is not None


def _extract_text_lines_rows(text_lines: list) -> list[tuple[str, str, str]]:
    """Extract (label, value, confidence) from detected_text_lines as fallback."""
    rows: list[tuple[str, str, str]] = []
    if not isinstance(text_lines, list):
        return rows

    for item in text_lines:
        line = str(item).strip().strip(":")
        if _is_valid_label_candidate(line):
            rows.append((line, "", "medium"))

    return rows


def _collect_field_rows(
    vision_payload: dict[str, object],
) -> list[tuple[str, str, str]]:
    """Return (label, value, confidence) triples from detected_fields or detected_text_lines."""
    detected_fields = vision_payload.get("detected_fields", [])
    rows = _extract_detected_fields_rows(detected_fields)  # type: ignore[arg-type]

    # Fallback: extract from text lines if no fields found
    if not rows:
        text_lines = vision_payload.get("detected_text_lines", [])
        rows = _extract_text_lines_rows(text_lines)  # type: ignore[arg-type]

    return rows


def _collect_action_labels(vision_payload: dict[str, object]) -> list[str]:
    """Return action button labels from detected_text_lines."""
    actions: list[str] = []
    lines = vision_payload.get("detected_text_lines", [])
    if isinstance(lines, list):
        for item in lines:
            line = str(item).strip()
            if line.lower() in _SKIP_LABELS:
                actions.append(line)
    return actions


def build_form_markdown_from_vision(vision_payload: dict[str, object]) -> str | None:
    """Build a normalized markdown form table from vision JSON output."""
    if not bool(vision_payload.get("contains_form", False)):
        return None

    field_rows = _collect_field_rows(vision_payload)
    if not field_rows:
        return None

    table = [
        "## Detected Form (normalized)",
        "",
        "| Field | Value | Confidence |",
        "| --- | --- | --- |",
    ]
    for label, value, confidence in field_rows:
        table.append(f"| {label} | {value} | {confidence} |")

    actions = _collect_action_labels(vision_payload)
    if actions:
        table.extend(["", "Actions: " + ", ".join(actions)])

    return "\n".join(table)


def _count_high_confidence_fields(detected_fields: object) -> int:
    """Count detected fields that have both label and high confidence."""
    if not isinstance(detected_fields, list):
        return 0

    high_confidence_fields = 0
    for entry in detected_fields:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        confidence = str(entry.get("confidence", "")).strip().lower()
        if label and confidence == "high":
            high_confidence_fields += 1
    return high_confidence_fields


def should_prefer_vision_form(
    vision_payload: dict[str, object],
    ocr_markdown: str,
    *,
    is_low_quality_ocr_text_fn,
) -> bool:
    """Return True when form detection is strong and OCR quality is poor."""
    if not bool(vision_payload.get("contains_form", False)):
        return False

    detected_fields = vision_payload.get("detected_fields", [])
    high_confidence_fields = _count_high_confidence_fields(detected_fields)

    return high_confidence_fields >= 1 and is_low_quality_ocr_text_fn(ocr_markdown)
