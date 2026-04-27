"""Bundle allocation and registry wiring for ingest flow."""

from __future__ import annotations

from functools import partial
from pathlib import Path

import i2d_ingest_archive as _archive
import i2d_ingest_bundle as _bundle
import i2d_ingest_flow as _ingest_flow
import i2d_ingest_paths as _paths
import i2d_ingest_registry as _registry

try:
    import yaml as _yaml  # type: ignore[import-untyped]

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _yaml = None  # type: ignore[assignment]
    _YAML_AVAILABLE = False

from i2d_models import BundleMetadata, InputFile, IngestResult  # noqa: E402
from i2d_discover import already_ingested  # noqa: E402
from i2d_content import compute_sha256, extract_content, render_bundle_markdown  # noqa: E402
from i2d_txt_processor import process_txt_file  # noqa: E402

_ARTIFACTS_TOOL = _paths.ARTIFACTS_TOOL
_CONTENT_TEMPLATE = _paths.CONTENT_TEMPLATE
_DONE_INVENTORY_TEMPLATE = _paths.DONE_INVENTORY_TEMPLATE


_allocate_bundle = partial(_bundle.allocate_bundle, _ARTIFACTS_TOOL)
_write_metadata = partial(
    _registry.write_metadata,
    yaml_available=_YAML_AVAILABLE,
    yaml_module=_yaml,
)
_write_bundle_markdown = partial(
    _registry.write_bundle_markdown,
    content_template=_CONTENT_TEMPLATE,
    render_bundle_markdown_fn=render_bundle_markdown,
)
_register_inventory = partial(
    _registry.register_inventory,
    artifacts_tool=_ARTIFACTS_TOOL,
)
_register_done_inventory = partial(
    _registry.register_done_inventory,
    artifacts_tool=_ARTIFACTS_TOOL,
    done_inventory_template=_DONE_INVENTORY_TEMPLATE,
)


def _move_source_to_done(
    source_path: Path,
    done_root: Path,
    classification: str,
    date_key: str,
    item_code: str,
) -> Path:
    """Move one processed source file from input to 20-done and return destination path."""
    return _archive.move_source_to_done(
        source_path,
        done_root,
        classification,
        date_key,
        item_code,
    )


def ingest_file(
    input_file: InputFile,
    data_root: Path,
    date_key: str,
    inventory_path: Path,
    template_path: Path | None,
) -> IngestResult:
    """Process one input file: allocate bundle, write metadata, register inventory."""
    return _ingest_flow.ingest_file(
        input_file,
        data_root,
        date_key,
        inventory_path,
        template_path,
        _ingest_flow.IngestDeps(
            compute_sha256_fn=compute_sha256,
            already_ingested_fn=already_ingested,
            allocate_bundle_fn=_allocate_bundle,
            extract_content_fn=extract_content,
            move_source_to_done_fn=_move_source_to_done,
            process_txt_file_fn=process_txt_file,
            write_bundle_markdown_fn=_write_bundle_markdown,
            write_metadata_fn=_write_metadata,
            register_inventory_fn=_register_inventory,
            register_done_inventory_fn=_register_done_inventory,
            bundle_metadata_cls=BundleMetadata,
            ingest_result_cls=IngestResult,
        ),
    )
