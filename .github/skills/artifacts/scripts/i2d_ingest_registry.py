"""Metadata and inventory registration helpers for i2d_ingest."""

from __future__ import annotations
from pathlib import Path
import i2d_ingest_inventory_cli as _inventory_cli
import i2d_ingest_metadata_doc as _metadata_doc


def write_metadata(
    bundle_info: dict,
    meta,
    *,
    yaml_available: bool,
    yaml_module,
) -> None:
    """Write YAML metadata file into the allocated bundle."""
    metadata_path = Path(bundle_info["metadata_path"])
    data = _metadata_doc.build_metadata_payload(meta)
    content = _metadata_doc.render_metadata_content(
        data,
        yaml_available=yaml_available,
        yaml_module=yaml_module,
    )
    metadata_path.write_text(content, encoding="utf-8")


def write_bundle_markdown(
    bundle_info: dict,
    meta,
    content_body: str,
    *,
    content_template: Path,
    render_bundle_markdown_fn,
) -> None:
    """Write normalized markdown content file into allocated data bundle."""
    markdown_path = Path(bundle_info["markdown_path"])
    fields = {
        "ITEM_CODE": meta.item_code,
        "SOURCE_DONE_FILE": meta.source_file,
        "SOURCE_INPUT_FILE": meta.source_input_file,
        "SOURCE_FINGERPRINT_SHA256": meta.source_fingerprint_sha256,
        "CLASSIFICATION": meta.classification,
        "FILE_FORMAT": meta.file_format,
        "PROCESSED_AT": meta.processed_at,
        "EXTRACTION_ENGINE": meta.extraction_engine or "unknown",
        "EXTRACTION_STATUS": meta.extraction_status or "unknown",
        "CONTENT_BODY": content_body or "(no extractable content)",
    }
    rendered = render_bundle_markdown_fn(
        content_template if content_template.exists() else None, fields
    )
    markdown_path.write_text(rendered, encoding="utf-8")


def register_inventory(
    bundle_info: dict,
    meta,
    inventory_path: Path,
    template_path: Path | None,
    *,
    artifacts_tool: Path,
) -> None:
    """Register the bundle in 10-data/INVENTORY.md via artifacts_tool.py."""
    fields = {
        "source": meta.source_file,
        "classification": meta.classification,
        "format": meta.file_format,
        "status": "ingested",
    }
    if meta.review_note:
        fields["review_note"] = meta.review_note
    _inventory_cli.run_inventory_upsert(
        artifacts_tool,
        inventory_path,
        template_path,
        bundle_info["item_code"],
        meta.processed_at,
        fields,
    )


def register_done_inventory(
    done_inventory_path: Path,
    meta,
    *,
    artifacts_tool: Path,
    done_inventory_template: Path,
) -> None:
    """Register moved source file in 20-done inventory."""
    fields = {
        "source_input_file": meta.source_input_file,
        "source_done_file": meta.source_file,
        "classification": meta.classification,
        "status": "archived",
        "source_fingerprint_sha256": meta.source_fingerprint_sha256,
    }
    _inventory_cli.run_inventory_upsert(
        artifacts_tool,
        done_inventory_path,
        done_inventory_template if done_inventory_template.exists() else None,
        meta.item_code,
        meta.processed_at,
        fields,
    )
