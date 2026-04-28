"""Ingestion flow helper for i2d_ingest.

All normalized bundle content written to `.digital-artifacts/10-data/` is
expected to be English. Any non-English source content must be translated
before it becomes the canonical downstream bundle payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from i2d_language_gate import evaluate_english_language_gate


@dataclass
class IngestDeps:
    """Bundled dependency-injection bag for ingest_file."""

    compute_sha256_fn: Any
    already_ingested_fn: Any
    allocate_bundle_fn: Any
    extract_content_fn: Any
    move_source_to_done_fn: Any
    process_txt_file_fn: Any
    write_bundle_markdown_fn: Any
    write_metadata_fn: Any
    register_inventory_fn: Any
    register_done_inventory_fn: Any
    bundle_metadata_cls: Any
    ingest_result_cls: Any


def _build_bundle_metadata(
    meta_cls,
    *,
    item_code: str,
    date_key: str,
    source_done_path: Path,
    source_input_path: Path,
    source_hash: str,
    classification: str,
    now: str,
    extraction_engine: str,
    extraction_status: str,
):
    """Build initial bundle metadata from extraction results."""
    return meta_cls(
        item_code=item_code,
        date_key=date_key,
        source_file=str(source_done_path),
        source_input_file=str(source_input_path),
        source_fingerprint_sha256=source_hash,
        classification=classification,
        file_format=source_done_path.suffix.lstrip(".").lower() or "unknown",
        processed_at=now,
        extraction_engine=extraction_engine,
        extraction_status=extraction_status,
    )


def _apply_text_enrichment(
    meta,
    source_done_path: Path,
    extracted_content: str,
    *,
    process_txt_file_fn,
    bundle_metadata_cls,
):
    """Optionally enrich metadata with canonical-English text normalization.

    The downstream 10-data bundle content must be English for stage workflows.
    Reuse the existing text processor for plain text and markdown-like sources.
    """
    if source_done_path.suffix.lower() not in {
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".adoc",
    }:
        return meta
    if not extracted_content.strip():
        return meta
    txt_result = process_txt_file_fn(extracted_content)
    if "error" in txt_result:
        return meta
    return bundle_metadata_cls(
        **{
            **meta.__dict__,
            "txt_translation": str(txt_result.get("translation", "")),
            "txt_inferred_type": str(txt_result.get("inferred_type", "")),
            "txt_research_hints": list(txt_result.get("research_hints", [])),
            "review_note": str(txt_result.get("review_note", "")),
        },
    )


def _apply_context_enrichment(meta, input_file, *, bundle_metadata_cls):
    """Add a review note when multiple bug files may belong to the same context."""
    context_candidates = getattr(input_file, "context_candidates", ())
    if not context_candidates:
        return meta

    context_note = (
        "Potential related bug context files in same ingest run: "
        + ", ".join(context_candidates)
        + ". Verify whether screenshots and textual descriptions belong together before downstream planning."
    )
    existing_note = getattr(meta, "review_note", "")
    merged_note = f"{existing_note} {context_note}".strip() if existing_note else context_note
    return bundle_metadata_cls(
        **{
            **meta.__dict__,
            "review_note": merged_note,
        },
    )


def _apply_language_gate(meta, extracted_content: str, *, bundle_metadata_cls):
    """Record English-only gate status for canonical downstream bundle content."""
    gate_result = evaluate_english_language_gate(extracted_content)
    existing_note = getattr(meta, "review_note", "")
    merged_note = existing_note
    if gate_result.status == "failed":
        merged_note = (
            f"{existing_note} {gate_result.note}".strip() if existing_note else gate_result.note
        )
    return bundle_metadata_cls(
        **{
            **meta.__dict__,
            "language_gate_status": gate_result.status,
            "language_gate_note": gate_result.note,
            "review_note": merged_note,
        },
    )


def _format_text_bundle_content(meta, original_content: str) -> str:
    """Preserve source extract and ingest hints while keeping English content primary."""
    canonical_content = meta.txt_translation.strip()
    source_content = original_content.strip()
    if not canonical_content:
        return original_content
    if canonical_content == source_content:
        return canonical_content

    hint_lines: list[str] = []
    if getattr(meta, "txt_inferred_type", ""):
        hint_lines.append(f"- inferred_type: {meta.txt_inferred_type}")
    for hint in getattr(meta, "txt_research_hints", []) or []:
        hint_lines.append(f"- research_hint: {hint}")
    if getattr(meta, "review_note", ""):
        hint_lines.append(f"- review_note: {meta.review_note}")
    hints_block = "\n".join(hint_lines) if hint_lines else "- none"

    return (
        "### Canonical English Content\n\n"
        f"{canonical_content}\n\n"
        "### Source-Preserved Extract\n\n"
        "```markdown\n"
        f"{source_content}\n"
        "```\n\n"
        "### Ingest Hints\n\n"
        f"{hints_block}"
    )


def _allocate_extract_move(
    input_file,
    data_root: Path,
    date_key: str,
    *,
    allocate_bundle_fn,
    extract_content_fn,
    move_source_to_done_fn,
):
    """Allocate bundle slot, extract content, move source to done folder."""
    bundle_info = allocate_bundle_fn(data_root, date_key)
    item_code = bundle_info["item_code"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    extracted_content, extraction_engine, extraction_status = extract_content_fn(
        input_file.path
    )
    done_root = data_root.parent / "20-done"
    source_done_path = move_source_to_done_fn(
        input_file.path, done_root, input_file.classification, date_key, item_code
    )
    return (
        bundle_info,
        item_code,
        now,
        extracted_content,
        extraction_engine,
        extraction_status,
        done_root,
        source_done_path,
    )


def _write_bundle_outputs(
    bundle_info,
    meta,
    extracted_content: str,
    done_root: Path,
    inventory_path: Path,
    template_path,
    *,
    write_bundle_markdown_fn,
    write_metadata_fn,
    register_inventory_fn,
    register_done_inventory_fn,
) -> None:
    """Persist bundle artefacts and register in both inventory files."""
    write_bundle_markdown_fn(bundle_info, meta, extracted_content)
    write_metadata_fn(bundle_info, meta)
    register_inventory_fn(bundle_info, meta, inventory_path, template_path)
    register_done_inventory_fn(done_root / "INVENTORY.md", meta)


def ingest_file(
    input_file,
    data_root: Path,
    date_key: str,
    inventory_path: Path,
    template_path: Path | None,
    deps: IngestDeps,
):
    """Allocate bundle, extract content, write outputs, register inventory (English output expected)."""
    source_input_path = input_file.path
    source_hash = deps.compute_sha256_fn(source_input_path)
    if deps.already_ingested_fn(source_input_path, data_root, source_hash):
        # Keep 00-input clean by archiving duplicate sources that were already ingested
        # in an earlier run. This preserves traceability in 20-done without creating
        # a new 10-data bundle.
        skip_item_code = f"SKIP{source_hash[:6]}"
        deps.move_source_to_done_fn(
            source_input_path,
            data_root.parent / "20-done",
            input_file.classification,
            date_key,
            skip_item_code,
        )
        return deps.ingest_result_cls(
            input_file=input_file, item_code="", bundle_root=data_root, skipped=True
        )
    (
        bundle_info,
        item_code,
        now,
        extracted_content,
        extraction_engine,
        extraction_status,
        done_root,
        source_done_path,
    ) = _allocate_extract_move(
        input_file,
        data_root,
        date_key,
        allocate_bundle_fn=deps.allocate_bundle_fn,
        extract_content_fn=deps.extract_content_fn,
        move_source_to_done_fn=deps.move_source_to_done_fn,
    )
    meta = _build_bundle_metadata(
        deps.bundle_metadata_cls,
        item_code=item_code,
        date_key=date_key,
        source_done_path=source_done_path,
        source_input_path=source_input_path,
        source_hash=source_hash,
        classification=input_file.classification,
        now=now,
        extraction_engine=extraction_engine,
        extraction_status=extraction_status,
    )
    meta = _apply_text_enrichment(
        meta,
        source_done_path,
        extracted_content,
        process_txt_file_fn=deps.process_txt_file_fn,
        bundle_metadata_cls=deps.bundle_metadata_cls,
    )
    meta = _apply_context_enrichment(
        meta,
        input_file,
        bundle_metadata_cls=deps.bundle_metadata_cls,
    )
    canonical_content = extracted_content
    if meta.txt_translation:
        canonical_content = meta.txt_translation
        extracted_content = _format_text_bundle_content(meta, extracted_content)
    meta = _apply_language_gate(
        meta,
        canonical_content,
        bundle_metadata_cls=deps.bundle_metadata_cls,
    )
    _write_bundle_outputs(
        bundle_info,
        meta,
        extracted_content,
        done_root,
        inventory_path,
        template_path,
        write_bundle_markdown_fn=deps.write_bundle_markdown_fn,
        write_metadata_fn=deps.write_metadata_fn,
        register_inventory_fn=deps.register_inventory_fn,
        register_done_inventory_fn=deps.register_done_inventory_fn,
    )
    return deps.ingest_result_cls(
        input_file=input_file,
        item_code=item_code,
        bundle_root=Path(bundle_info["item_root"]),
    )
