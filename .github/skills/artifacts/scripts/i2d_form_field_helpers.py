"""Shared form field extraction utilities.

Purpose:
    Centralized form field collection and analysis to reduce duplication across
    i2d_content_form_local and i2d_content_form_visual modules.

Security:
    Pure functions with no mutable state or side effects.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FormField:
    """Extracted form field with confidence score."""

    value: str
    field_type: str
    confidence: float


def filter_high_confidence_fields(
    fields: list[FormField], min_confidence: float = 0.85
) -> list[FormField]:
    """Filter form fields to only those meeting confidence threshold.

    Args:
        fields: List of form fields to filter.
        min_confidence: Minimum confidence score (default 0.85).

    Returns:
        List of fields with confidence >= min_confidence.
    """
    return [f for f in fields if f.confidence >= min_confidence]


def filter_by_field_type(fields: list[FormField], field_type: str) -> list[FormField]:
    """Filter form fields by type.

    Args:
        fields: List of form fields to filter.
        field_type: Target field type (e.g., 'text', 'checkbox', 'dropdown').

    Returns:
        List of fields matching the specified type.
    """
    return [f for f in fields if f.field_type == field_type]


def collect_field_values(
    fields: list[FormField], field_type: str | None = None
) -> list[str]:
    """Collect field values, optionally filtered by type.

    Args:
        fields: List of form fields.
        field_type: Optional field type filter. If None, collects all values.

    Returns:
        List of field values.
    """
    filtered = (
        fields if field_type is None else filter_by_field_type(fields, field_type)
    )
    return [f.value for f in filtered if f.value.strip()]


def calculate_average_confidence(fields: list[FormField]) -> float:
    """Calculate average confidence score for a set of fields.

    Args:
        fields: List of form fields.

    Returns:
        Average confidence score (0.0 if no fields).
    """
    if not fields:
        return 0.0
    return sum(f.confidence for f in fields) / len(fields)
