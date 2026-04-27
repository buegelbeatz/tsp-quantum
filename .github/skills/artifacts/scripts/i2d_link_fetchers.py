"""Fetcher helpers for i2d_link URL extraction."""

from __future__ import annotations

import urllib.error

import i2d_link_klaxoon_api as _klaxoon_api

_MARKITDOWN_EXCEPTION_SPECS = (
    (
        "markitdown._exceptions",
        ("FileConversionException", "MissingDependencyException"),
    ),
    (
        "markitdown._markitdown",
        (
            "FileConversionException",
            "MissingDependencyException",
            "UnsupportedFormatException",
        ),
    ),
)


def _collect_markitdown_exception_types() -> tuple[type[BaseException], ...]:
    base: list[type[BaseException]] = [
        OSError,
        RuntimeError,
        ValueError,
        urllib.error.URLError,
    ]
    for module_name, names in _MARKITDOWN_EXCEPTION_SPECS:
        try:
            module = __import__(module_name, fromlist=list(names))
        except ImportError:
            continue
        for name in names:
            exc = getattr(module, name, None)
            if (
                isinstance(exc, type)
                and issubclass(exc, BaseException)
                and exc not in base
            ):
                base.append(exc)
    return tuple(base)


def fetch_url_via_markitdown(url: str) -> str:
    """Fetch URL and return markdown content, or empty string on failure."""
    try:
        from markitdown import MarkItDown  # type: ignore[import-untyped]  # pyright: ignore[reportMissingImports]

        # Dynamically discover MarkItDown-specific exceptions across versions.
        md_exceptions = _collect_markitdown_exception_types()

        converter = MarkItDown()
        result = converter.convert(url)
        text = getattr(result, "text_content", "") or ""
        return text.strip()
    except (ImportError, OSError, RuntimeError, ValueError, urllib.error.URLError):
        return ""
    except md_exceptions:  # type: ignore[misc]  # dynamic tuple
        return ""


def fetch_klaxoon_api(board_share_code: str) -> tuple[str, str]:
    """Fetch Klaxoon board content via REST API."""
    return _klaxoon_api.fetch_klaxoon_api(board_share_code)
