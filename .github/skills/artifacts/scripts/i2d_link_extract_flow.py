"""Flow helper for URL list extraction orchestration."""

from __future__ import annotations

import re
from pathlib import Path

_KLAXOON_FALLBACK_HEADER = "#### Klaxoon Fallback (public page extraction)\n\n"
_NO_CONTENT_NOTE = (
    "_(no content extracted — page may require authentication or JavaScript rendering)_"
)


def _build_read_error_response(path: Path, exc: OSError) -> tuple[str, str, str]:
    """Build standardized extraction response for file read errors."""
    return (
        f"## File Facts\n\n- file_name: {path.name}\n\nFile read error: {exc}",
        "link-extractor",
        "error",
    )


def _read_urls_from_file(path: Path) -> tuple[list[str] | None, OSError | None]:
    """Read URL list file and return parsed non-empty lines."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, exc
    return [line.strip() for line in raw.splitlines() if line.strip()], None


def _build_extraction_content(path: Path, file_facts_fn, sections: list[str]) -> str:
    """Build final extraction markdown document for URL list content."""
    body = "\n\n---\n\n".join(sections) if sections else "_(no URLs found)_"
    return f"## File Facts\n\n{file_facts_fn(path)}\n\n## Linked Content\n\n{body}"


def _process_url(
    url: str,
    *,
    klaxoon_board_re: re.Pattern[str],
    fetch_klaxoon_api_fn,
    fetch_url_via_markitdown_fn,
    max_url_content: int,
) -> tuple[str, bool]:
    """Fetch a single URL and return (section_text, any_ok)."""
    klaxoon_match = klaxoon_board_re.match(url)
    if klaxoon_match:
        board_id = klaxoon_match.group(1)
        klaxoon_content, klaxoon_status = fetch_klaxoon_api_fn(board_id)
        section = f"### Klaxoon Board\n\n**URL**: {url}  \n**Status**: {klaxoon_status}\n\n{klaxoon_content}"
        ok = klaxoon_status == "ok"
        if not ok:
            fallback = fetch_url_via_markitdown_fn(url)
            if fallback:
                section += f"\n\n{_KLAXOON_FALLBACK_HEADER}{fallback[:max_url_content]}"
                ok = True
        return section, ok

    fetched = fetch_url_via_markitdown_fn(url)
    if fetched:
        return f"### {url}\n\n{fetched[:max_url_content]}", True
    return f"### {url}\n\n{_NO_CONTENT_NOTE}", False


def extract_url_list(
    path: Path,
    *,
    klaxoon_board_re: re.Pattern[str],
    fetch_klaxoon_api_fn,
    fetch_url_via_markitdown_fn,
    file_facts_fn,
    max_url_content: int,
) -> tuple[str, str, str]:
    """Extract content for a URL-list text file.

    Returns tuple: (content, extraction_engine, extraction_status).
    """
    urls, read_error = _read_urls_from_file(path)
    if read_error is not None:
        return _build_read_error_response(path, read_error)

    assert urls is not None
    sections: list[str] = []
    any_ok = False

    for url in urls:
        section, ok = _process_url(
            url,
            klaxoon_board_re=klaxoon_board_re,
            fetch_klaxoon_api_fn=fetch_klaxoon_api_fn,
            fetch_url_via_markitdown_fn=fetch_url_via_markitdown_fn,
            max_url_content=max_url_content,
        )
        sections.append(section)
        any_ok = any_ok or ok

    content = _build_extraction_content(path, file_facts_fn, sections)
    return content, "link-extractor", "ok" if any_ok else "partial"
