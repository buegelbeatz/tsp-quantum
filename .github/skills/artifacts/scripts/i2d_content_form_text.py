"""Text-to-form markdown helper for i2d_content."""

from __future__ import annotations


_FORM_KEYWORDS = (
    "form",
    "login",
    "username",
    "password",
    "field",
    "enter",
    "submit",
)


def _has_form_keywords(normalized_text: str) -> bool:
    """Return True when text includes common form-related keywords."""
    lower = normalized_text.lower()
    return any(keyword in lower for keyword in _FORM_KEYWORDS)


def _fallback_form_fields(has_form_keywords: bool) -> list[tuple[str, str]]:
    """Return synthetic fallback fields for form-like descriptions."""
    if not has_form_keywords:
        return []
    return [("Field 1", ""), ("Field 2", ""), ("Field 3", "")]


def _build_form_rows(fields: list[tuple[str, str]]) -> list[str]:
    """Build markdown table rows for detected form fields."""
    rows = [
        "## Detected Form (from text)",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for label, value in fields[:20]:
        rows.append(f"| {label} | {value} |")
    return rows


def build_form_markdown_from_text_description(
    text: str,
    *,
    extract_form_fields_fn,
) -> str | None:
    """Create a markdown form from textual descriptions and key/value lines."""
    normalized = text.strip()
    if not normalized:
        return None

    fields = extract_form_fields_fn(normalized)
    has_form_keywords = _has_form_keywords(normalized)

    if not fields and not has_form_keywords:
        return None

    if not fields:
        fields = _fallback_form_fields(has_form_keywords)

    rows = _build_form_rows(fields)

    return "\n".join(rows)
