"""Mail part helpers for EML content extraction."""

from __future__ import annotations

from html.parser import HTMLParser


class _TagStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        """TODO: add docstring for handle_data."""
        self._parts.append(data)

    def get_text(self) -> str:
        """TODO: add docstring for get_text."""
        return " ".join(self._parts).strip()


def decode_message_part(part: object) -> str:
    """Decode a text email part using its declared charset when available."""
    raw = part.get_payload(decode=True)  # type: ignore[attr-defined]
    if not raw:
        return ""
    charset = part.get_content_charset() or "utf-8"  # type: ignore[attr-defined]
    return raw.decode(charset, errors="replace")


def html_to_text(html: str) -> str:
    """Convert a small HTML body fragment to plain text."""
    stripper = _TagStripper()
    stripper.feed(html)
    return " ".join(stripper.get_text().split())
