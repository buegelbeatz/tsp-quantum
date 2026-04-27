"""GitHub API response payload normalization and extraction.

Purpose:
    Normalize GitHub API JSON responses into consistent dict/list structures.
    Provide safe extraction helpers to avoid type errors.

Security:
    Type-safe extraction; returns None or empty list on type mismatch.
    No external I/O or shell execution.
"""

from __future__ import annotations


def filter_dict_items(values: object) -> list[dict[str, object]]:
    """Return only dictionary entries from a list-like value.

    Args:
        values: Potentially list-like object.

    Returns:
        List of dicts found; empty list if values is not a list.
    """
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def extract_container_values(payload: object, key: str) -> object:
    """Extract container payload by key when payload is dict; else passthrough.

    Args:
        payload: Potentially dict object.
        key: Dictionary key to extract.

    Returns:
        Value at payload[key] if payload is dict; otherwise payload itself.
    """
    if isinstance(payload, dict):
        return payload.get(key)
    return payload


def extract_dict_list(payload: object, key: str) -> list[dict[str, object]]:
    """Normalize payload to a list of dictionaries for a given top-level key.

    Args:
        payload: JSON payload (dict or other).
        key: Top-level key to extract.

    Returns:
        List of dicts extracted from payload[key]; empty list on error.
    """
    values = extract_container_values(payload, key)
    return filter_dict_items(values)


def extract_project_items(payload: object) -> list[dict[str, object]]:
    """Normalize gh project item-list payload to a list of items."""
    return extract_dict_list(payload, "items")


def extract_projects(payload: object) -> list[dict[str, object]]:
    """Normalize gh project list payload to a list of project dicts."""
    return extract_dict_list(payload, "projects")


def extract_issues(payload: object) -> list[dict[str, object]]:
    """Normalize gh issue list payload to a list of issues."""
    return extract_dict_list(payload, "issues")
