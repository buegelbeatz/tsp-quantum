"""URL list extraction — generic HTTP fetching and Klaxoon Board API import.

Purpose:
    Extract and fetch content from URL lists. Supports plain HTTP URLs and
    Klaxoon board share URLs with OAuth authentication. Converts fetched content to Markdown.

Security:
    HTTP requests use only HTTP/HTTPS schemes. Requires explicit OAuth credentials
    for Klaxoon access. Validates all URLs before fetching. No sensitive data in logs.
"""

from __future__ import annotations

import re
from pathlib import Path

import i2d_link_extract_flow as _extract_flow
import i2d_link_fetchers as _fetchers

_URL_LINE_RE = re.compile(r"^https?://\S+$")
_KLAXOON_BOARD_RE = re.compile(
    r"https?://app\.klaxoon\.com/animate/board/([A-Za-z0-9_-]+)"
)

# Maximum characters kept per fetched URL to avoid bloated bundles
_MAX_URL_CONTENT = 8_000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _file_facts(path: Path) -> str:
    """Return baseline file facts for the given path."""
    stat = path.stat()
    return (
        f"- file_name: {path.name}\n"
        f"- extension: {path.suffix.lower() or '(none)'}\n"
        f"- size_bytes: {stat.st_size}\n"
        f"- modified_at_epoch: {int(stat.st_mtime)}"
    )


def _fetch_url_via_markitdown(url: str) -> str:
    return _fetchers.fetch_url_via_markitdown(url)


def _fetch_klaxoon_api(board_share_code: str) -> tuple[str, str]:
    return _fetchers.fetch_klaxoon_api(board_share_code)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def is_url_list_file(path: Path) -> bool:
    """Return True if every non-blank line of ``path`` is an HTTP(S) URL."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return bool(lines) and all(_URL_LINE_RE.match(line) for line in lines)


def extract_url_list(path: Path) -> tuple[str, str, str]:
    """Extract content for a URL-list text file.

    Each non-blank line must be an HTTP(S) URL.  Klaxoon board URLs are
    resolved via the Klaxoon REST API; all other URLs are fetched via
    markitdown.

    Returns:
        ``(content, extraction_engine, extraction_status)`` where
        ``extraction_status`` is ``"ok"`` if at least one URL yielded content,
        ``"partial"`` if all fetches returned no content (e.g. auth-protected
        pages), or ``"error"`` on unrecoverable read errors.
    """
    return _extract_flow.extract_url_list(
        path,
        klaxoon_board_re=_KLAXOON_BOARD_RE,
        fetch_klaxoon_api_fn=_fetch_klaxoon_api,
        fetch_url_via_markitdown_fn=_fetch_url_via_markitdown,
        file_facts_fn=_file_facts,
        max_url_content=_MAX_URL_CONTENT,
    )
