"""Utility helpers for markitdown post-processing."""

from __future__ import annotations


def markitdown_contains_transcript_error(
    content: str, snippets: tuple[str, ...]
) -> bool:
    """Detect synthetic transcript error placeholders in markitdown output."""
    normalized = content.lower()
    return any(snippet in normalized for snippet in snippets)


def _is_file_skip_extension(file_name: str) -> bool:
    """Check if file should be skipped based on extension."""
    lower_name = file_name.lower()
    return lower_name.endswith((".css", ".opf", ".ncx", "container.xml", "mimetype"))


def _is_file_keep_extension(file_name: str) -> bool:
    """Check if file should be kept based on extension."""
    return file_name.lower().endswith((".xhtml", ".html", ".htm", ".txt", ".md"))


def _parse_file_block(raw_section: str) -> tuple[str, str]:
    """Parse section into file name and content."""
    section = raw_section.strip()
    first_line, _, remainder = section.partition("\n")
    return first_line.strip(), remainder.strip()


def _should_keep_file_block(file_name: str) -> bool:
    """Determine if file block should be kept."""
    if not file_name:
        return False
    if _is_file_skip_extension(file_name):
        return False
    return _is_file_keep_extension(file_name)


def _collect_kept_epub_sections(sections: list[str]) -> list[str]:
    """Collect normalized EPUB file sections that should be retained."""
    kept_sections: list[str] = []
    for raw_section in sections:
        section = raw_section.strip()
        if not section:
            continue
        file_name, content_part = _parse_file_block(raw_section)
        if not _should_keep_file_block(file_name):
            continue
        kept_sections.append(f"## File: {file_name}\n{content_part}")
    return kept_sections


def _render_cleaned_epub_content(header: str, kept_sections: list[str]) -> str:
    """Render cleaned EPUB content preserving original formatting conventions."""
    return (
        "\n".join(part.rstrip() for part in [header.strip(), *kept_sections] if part)
        + "\n"
    )


def cleanup_epub_markitdown_content(content: str) -> str:
    """Remove EPUB archive noise (for example CSS blobs) from markitdown output."""
    if "Content from the zip file" not in content or "## File:" not in content:
        return content

    header, *sections = content.split("## File:")
    kept_sections = _collect_kept_epub_sections(sections)

    if not kept_sections:
        return content

    return _render_cleaned_epub_content(header, kept_sections)
