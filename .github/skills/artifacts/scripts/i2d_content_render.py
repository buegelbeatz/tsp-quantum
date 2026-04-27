"""Markdown rendering helper for 10-data bundle content."""

from __future__ import annotations

from pathlib import Path

DEFAULT_TEMPLATE = """# Data Bundle {{ITEM_CODE}}

## Source

- source_done_file: {{SOURCE_DONE_FILE}}
- source_input_file: {{SOURCE_INPUT_FILE}}
- source_fingerprint_sha256: {{SOURCE_FINGERPRINT_SHA256}}
- classification: {{CLASSIFICATION}}
- file_format: {{FILE_FORMAT}}
- processed_at: {{PROCESSED_AT}}

## Extraction

- extraction_engine: {{EXTRACTION_ENGINE}}
- extraction_status: {{EXTRACTION_STATUS}}

## Content

{{CONTENT_BODY}}
"""


def render_bundle_markdown(
    template_path: Path | None,
    fields: dict[str, str],
    *,
    default_template: str = DEFAULT_TEMPLATE,
) -> str:
    """Render data bundle markdown from template and fields."""
    template = default_template
    if template_path and template_path.exists():
        template = template_path.read_text(encoding="utf-8")

    rendered = template
    for key, value in fields.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered
