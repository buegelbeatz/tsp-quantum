"""Form field extraction helpers for local OCR-driven form analysis."""

from __future__ import annotations

import re

_FORM_FIELD_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9 /().,_-]{1,60})\s*[:=-]\s*(.{0,160})$"
)


def _is_candidate_field_label(text: str) -> bool:
    """Return True when text resembles a short field label candidate."""
    compact = " ".join(text.split())
    words = compact.split()
    alpha_count = sum(1 for ch in compact if ch.isalpha())
    return (
        3 <= len(compact) <= 40
        and 1 <= len(words) <= 4
        and alpha_count >= 3
        and alpha_count >= (len(compact) // 2)
    )


def extract_form_fields_from_text(text: str) -> list[tuple[str, str]]:
    """Extract simple key/value style form fields from OCR text."""
    fields: list[tuple[str, str]] = []
    seen_labels: set[str] = set()

    def _append(label: str, value: str) -> None:
        key = label.strip().lower()
        if not key or key in seen_labels:
            return
        alpha_count = sum(1 for ch in key if ch.isalpha())
        if alpha_count < 2:
            return
        symbol_count = sum(1 for ch in key if not ch.isalnum() and not ch.isspace())
        if symbol_count > max(3, len(key) // 3):
            return
        seen_labels.add(key)
        fields.append((label.strip(), value.strip()))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or len(line) > 180:
            continue
        match = _FORM_FIELD_PATTERN.match(line)
        if not match:
            if _is_candidate_field_label(line):
                _append(" ".join(line.split()), "")
            continue
        label = match.group(1).strip()
        value = match.group(2).strip()
        if len(label.split()) > 8:
            continue
        _append(label, value)
    return fields[:20]
