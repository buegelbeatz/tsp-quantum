"""Unit tests for i2d_link — URL list detection and content fetching."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_link  # noqa: E402
from i2d_link import extract_url_list, is_url_list_file  # noqa: E402


# ---------------------------------------------------------------------------
# is_url_list_file
# ---------------------------------------------------------------------------


def test_is_url_list_file_all_urls(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_all_urls."""
    p = tmp_path / "links.txt"
    p.write_text("https://example.com\nhttps://another.org/path\n", encoding="utf-8")
    assert is_url_list_file(p) is True


def test_is_url_list_file_blank_lines_allowed(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_blank_lines_allowed."""
    p = tmp_path / "links.txt"
    p.write_text("\nhttps://example.com\n\nhttps://other.net\n", encoding="utf-8")
    assert is_url_list_file(p) is True


def test_is_url_list_file_mixed_content_returns_false(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_mixed_content_returns_false."""
    p = tmp_path / "notes.txt"
    p.write_text("https://example.com\nsome plain text here", encoding="utf-8")
    assert is_url_list_file(p) is False


def test_is_url_list_file_empty_returns_false(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_empty_returns_false."""
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    assert is_url_list_file(p) is False


def test_is_url_list_file_missing_file_returns_false(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_missing_file_returns_false."""
    p = tmp_path / "nonexistent.txt"
    assert is_url_list_file(p) is False


def test_is_url_list_file_klaxoon_url(tmp_path: Path) -> None:
    """TODO: add docstring for test_is_url_list_file_klaxoon_url."""
    p = tmp_path / "klaxoon.txt"
    p.write_text("https://app.klaxoon.com/animate/board/kmntyg4\n", encoding="utf-8")
    assert is_url_list_file(p) is True


# ---------------------------------------------------------------------------
# extract_url_list — Klaxoon credentials-missing path
# ---------------------------------------------------------------------------


def test_extract_url_list_klaxoon_no_credentials(tmp_path: Path) -> None:
    """Without credentials the extractor must return credentials-missing status without crashing."""
    p = tmp_path / "link.txt"
    p.write_text("https://app.klaxoon.com/animate/board/kmntyg4\n", encoding="utf-8")

    with patch.dict(
        "os.environ",
        {"KLAXOON_CLIENT_ID": "", "KLAXOON_CLIENT_SECRET": ""},
        clear=False,
    ):
        content, engine, status = extract_url_list(p)

    assert engine == "link-extractor"
    # No credentials → at least one section with credentials-missing, overall status is partial
    assert status == "partial"
    assert "credentials-missing" in content.lower() or "credentials" in content.lower()
    assert "## File Facts" in content


# ---------------------------------------------------------------------------
# extract_url_list — generic URL path via markitdown mock
# ---------------------------------------------------------------------------


def test_extract_url_list_generic_url_fetches_content(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_url_list_generic_url_fetches_content."""
    p = tmp_path / "links.txt"
    p.write_text("https://example.com\n", encoding="utf-8")

    with patch(
        "i2d_link._fetch_url_via_markitdown", return_value="# Example\n\nSome content."
    ) as mock_fetch:
        content, engine, status = extract_url_list(p)

    mock_fetch.assert_called_once_with("https://example.com")
    assert engine == "link-extractor"
    assert status == "ok"
    assert "## Linked Content" in content
    assert "Example" in content


def test_extract_url_list_generic_url_no_content(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_url_list_generic_url_no_content."""
    p = tmp_path / "links.txt"
    p.write_text("https://example.com\n", encoding="utf-8")

    with patch("i2d_link._fetch_url_via_markitdown", return_value=""):
        content, _engine, status = extract_url_list(p)

    assert status == "partial"
    assert "no content extracted" in content


def test_extract_url_list_klaxoon_api_error_uses_public_fallback(
    tmp_path: Path,
) -> None:
    """Klaxoon API failures should still try to extract the public board URL."""
    p = tmp_path / "link.txt"
    p.write_text("https://app.klaxoon.com/animate/board/kmntyg4\n", encoding="utf-8")

    with patch(
        "i2d_link._fetch_klaxoon_api",
        return_value=("Klaxoon board `kmntyg4` — HTTP 403: Forbidden", "error"),
    ):
        with patch(
            "i2d_link._fetch_url_via_markitdown",
            return_value="# Board Snapshot\n\nCard A\nCard B",
        ) as mock_fallback:
            content, engine, status = extract_url_list(p)

    mock_fallback.assert_called_once_with(
        "https://app.klaxoon.com/animate/board/kmntyg4"
    )
    assert engine == "link-extractor"
    assert status == "ok"
    assert "Klaxoon Fallback (public page extraction)" in content
    assert "Board Snapshot" in content


# ---------------------------------------------------------------------------
# extract_url_list — unreadable file
# ---------------------------------------------------------------------------


def test_extract_url_list_os_error_returns_error(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_url_list_os_error_returns_error."""
    p = tmp_path / "missing.txt"
    content, engine, status = extract_url_list(p)
    assert engine == "link-extractor"
    assert status == "error"
    assert "error" in content.lower()


def test_fetch_url_via_markitdown_delegates_to_fetcher_module() -> None:
    """TODO: add docstring for test_fetch_url_via_markitdown_delegates_to_fetcher_module."""
    with patch(
        "i2d_link._fetchers.fetch_url_via_markitdown",
        return_value="ok",
    ) as fetch_mock:
        result = i2d_link._fetch_url_via_markitdown("https://example.com")

    assert result == "ok"
    fetch_mock.assert_called_once_with("https://example.com")


def test_fetch_klaxoon_api_delegates_to_fetcher_module() -> None:
    """TODO: add docstring for test_fetch_klaxoon_api_delegates_to_fetcher_module."""
    with patch(
        "i2d_link._fetchers.fetch_klaxoon_api",
        return_value=("content", "ok"),
    ) as fetch_mock:
        result = i2d_link._fetch_klaxoon_api("abc123")

    assert result == ("content", "ok")
    fetch_mock.assert_called_once_with("abc123")


def test_extract_url_list_delegates_to_extract_flow_helper(tmp_path: Path) -> None:
    """Ensure extract_url_list delegates orchestration to flow helper module."""
    p = tmp_path / "links.txt"
    p.write_text("https://example.com\n", encoding="utf-8")

    with patch(
        "i2d_link._extract_flow.extract_url_list",
        return_value=("content", "link-extractor", "ok"),
    ) as flow_mock:
        result = i2d_link.extract_url_list(p)

    assert result == ("content", "link-extractor", "ok")
    args, kwargs = flow_mock.call_args
    assert args == (p,)
    assert kwargs["klaxoon_board_re"] is i2d_link._KLAXOON_BOARD_RE
    assert kwargs["fetch_klaxoon_api_fn"] is i2d_link._fetch_klaxoon_api
    assert kwargs["fetch_url_via_markitdown_fn"] is i2d_link._fetch_url_via_markitdown
    assert kwargs["file_facts_fn"] is i2d_link._file_facts
    assert kwargs["max_url_content"] == i2d_link._MAX_URL_CONTENT
