"""Dynamic exception discovery for markitdown integration."""

from __future__ import annotations


def collect_markitdown_errors() -> list[type[BaseException]]:
    """Collect known markitdown exception classes from available modules."""
    markitdown_errors: list[type[BaseException]] = [OSError, RuntimeError, ValueError]
    exception_sources: tuple[tuple[str, tuple[str, ...]], ...] = (
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
    for module_name, exception_names in exception_sources:
        try:
            module = __import__(module_name, fromlist=list(exception_names))
        except ImportError:
            continue
        for exception_name in exception_names:
            exception_type = getattr(module, exception_name, None)
            if (
                isinstance(exception_type, type)
                and issubclass(exception_type, BaseException)
                and exception_type not in markitdown_errors
            ):
                markitdown_errors.append(exception_type)
    return markitdown_errors
