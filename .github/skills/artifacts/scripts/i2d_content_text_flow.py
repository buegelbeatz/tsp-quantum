"""Text-file extraction branch for content flow."""

from __future__ import annotations

from pathlib import Path


def extract_text_content(
    path: Path,
    *,
    file_facts_fn,
    build_form_markdown_from_text_description_fn,
    is_url_list_file_fn,
    extract_url_list_fn,
) -> tuple[str, str, str]:
    """Handle text file extraction including URL-list detection."""
    if is_url_list_file_fn(path):
        return extract_url_list_fn(path)

    text = path.read_text(encoding="utf-8", errors="replace").strip()
    body = text or "(empty text file)"
    form_markdown = build_form_markdown_from_text_description_fn(body)
    if form_markdown:
        body = f"{body}\n\n{form_markdown}"

    return (
        f"## File Facts\n\n{file_facts_fn(path)}\n\n## Text\n\n{body}",
        "plain-text",
        "ok",
    )
