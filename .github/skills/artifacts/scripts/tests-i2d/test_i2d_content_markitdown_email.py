"""Unit tests for i2d_content_markitdown_email utility delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_markitdown_email as md_email  # noqa: E402


def test_markitdown_contains_transcript_error_delegates_to_utils() -> None:
    """Ensure transcript-error check delegates to markitdown utils module."""
    snippets = ("err",)
    with patch(
        "i2d_content_markitdown_email._md_utils.markitdown_contains_transcript_error",
        return_value=True,
    ) as util_mock:
        result = md_email.markitdown_contains_transcript_error("x", snippets)

    assert result is True
    util_mock.assert_called_once_with("x", snippets)


def test_cleanup_epub_markitdown_content_delegates_to_utils() -> None:
    """Ensure EPUB cleanup delegates to markitdown utils module."""
    with patch(
        "i2d_content_markitdown_email._md_utils.cleanup_epub_markitdown_content",
        return_value="clean",
    ) as util_mock:
        result = md_email.cleanup_epub_markitdown_content("raw")

    assert result == "clean"
    util_mock.assert_called_once_with("raw")


def test_extract_with_markitdown_uses_exception_helper(tmp_path: Path) -> None:
    """extract_with_markitdown should collect exception types via helper module."""
    file_path = tmp_path / "doc.pdf"
    file_path.write_bytes(b"%PDF")

    class _MarkItDown:
        def convert(self, _path: str) -> object:
            """TODO: add docstring for convert."""

            class _Result:
                text_content = "hello"

            return _Result()

    with patch(
        "i2d_content_markitdown_email._md_exceptions.collect_markitdown_errors",
        return_value=[OSError, RuntimeError, ValueError],
    ) as exc_mock:
        with patch.dict(
            sys.modules,
            {"markitdown": type("M", (), {"MarkItDown": _MarkItDown})},
        ):
            content, engine, status = md_email.extract_with_markitdown(
                file_path,
                file_facts_fn=lambda _p: "facts",
            )

    exc_mock.assert_called_once_with()
    assert engine == "markitdown"
    assert status == "ok"
    assert "hello" in content


def test_extract_eml_delegates_to_eml_helper(tmp_path: Path) -> None:
    """extract_eml should delegate to the dedicated EML helper module."""
    path = tmp_path / "message.eml"
    path.write_bytes(b"From: sender@example.com\n")

    with patch(
        "i2d_content_markitdown_email._md_eml.extract_eml",
        return_value=("content", "eml-parser", "ok"),
    ) as helper_mock:
        result = md_email.extract_eml(path, file_facts_fn=lambda _path: "facts")

    assert result == ("content", "eml-parser", "ok")
    helper_mock.assert_called_once()
    call_args = helper_mock.call_args
    assert call_args.args == (path,)
    assert call_args.kwargs["file_facts_fn"](path) == "facts"
