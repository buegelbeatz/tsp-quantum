"""Metadata document helpers for ingest registry."""

from __future__ import annotations

from typing import Any


def _str_representer(dumper, data: str) -> Any:
    """Represent multiline strings as literal block scalars (|-)."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def build_metadata_payload(meta: Any) -> dict[str, object]:
    """Build the metadata payload written into bundle metadata files."""
    data: dict[str, object] = {
        "item_code": meta.item_code,
        "date_key": meta.date_key,
        "source_file": meta.source_file,
        "source_input_file": meta.source_input_file,
        "source_fingerprint_sha256": meta.source_fingerprint_sha256,
        "classification": meta.classification,
        "file_format": meta.file_format,
        "processed_at": meta.processed_at,
        "extraction_engine": meta.extraction_engine,
        "extraction_status": meta.extraction_status,
    }
    if meta.txt_translation:
        data["txt_translation"] = meta.txt_translation
        data["txt_inferred_type"] = meta.txt_inferred_type
        data["txt_research_hints"] = meta.txt_research_hints
    if meta.language_gate_status:
        data["language_gate_status"] = meta.language_gate_status
        data["language_gate_note"] = meta.language_gate_note
    if meta.review_note:
        data["review_note"] = meta.review_note
    return data


def render_metadata_content(
    data: dict[str, object],
    *,
    yaml_available: bool,
    yaml_module,
) -> str:
    """Render metadata payload as YAML or a deterministic fallback text format.
    
    Multiline strings are rendered as YAML block scalars (|-) for readability.
    """
    if yaml_available and yaml_module is not None:
        # Register custom representer for multiline strings (uses |-)
        yaml_module.add_representer(str, _str_representer)
        return yaml_module.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
            continue
        safe = str(value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}: "{safe}"')
    return "\n".join(lines) + "\n"
