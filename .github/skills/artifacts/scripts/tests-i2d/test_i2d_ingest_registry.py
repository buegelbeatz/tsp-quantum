"""Unit tests for i2d_ingest_registry delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_ingest_registry as registry  # noqa: E402


def test_write_metadata_delegates_to_metadata_helpers(tmp_path: Path) -> None:
    """write_metadata should delegate payload and rendering to metadata helpers."""
    metadata_path = tmp_path / "metadata.yml"
    bundle_info = {"metadata_path": str(metadata_path)}
    meta = SimpleNamespace(item_code="00001")

    with patch(
        "i2d_ingest_registry._metadata_doc.build_metadata_payload",
        return_value={"item_code": "00001"},
    ) as payload_mock:
        with patch(
            "i2d_ingest_registry._metadata_doc.render_metadata_content",
            return_value='item_code: "00001"\n',
        ) as render_mock:
            registry.write_metadata(
                bundle_info,
                meta,
                yaml_available=False,
                yaml_module=None,
            )

    payload_mock.assert_called_once_with(meta)
    render_mock.assert_called_once_with(
        {"item_code": "00001"},
        yaml_available=False,
        yaml_module=None,
    )
    assert metadata_path.read_text(encoding="utf-8") == 'item_code: "00001"\n'


def test_register_inventory_delegates_to_inventory_cli(tmp_path: Path) -> None:
    """Ensure register_inventory delegates inventory command construction."""
    meta = SimpleNamespace(
        source_file="done/file.txt",
        classification="document",
        file_format="txt",
        review_note="review",
        processed_at="2026-04-08T12:00:00Z",
    )

    with patch(
        "i2d_ingest_registry._inventory_cli.run_inventory_upsert",
    ) as cli_mock:
        registry.register_inventory(
            {"item_code": "00001"},
            meta,
            tmp_path / "INVENTORY.md",
            tmp_path / "INVENTORY.template.md",
            artifacts_tool=tmp_path / "artifacts_tool.py",
        )

    args, _kwargs = cli_mock.call_args
    assert args[0] == tmp_path / "artifacts_tool.py"
    assert args[1] == tmp_path / "INVENTORY.md"
    assert args[2] == tmp_path / "INVENTORY.template.md"
    assert args[3] == "00001"
    assert args[4] == meta.processed_at
    assert args[5]["status"] == "ingested"
    assert args[5]["review_note"] == "review"


def test_register_done_inventory_delegates_to_inventory_cli(tmp_path: Path) -> None:
    """Ensure register_done_inventory delegates inventory CLI helper."""
    template = tmp_path / "DONE.template.md"
    template.write_text("x", encoding="utf-8")
    meta = SimpleNamespace(
        source_input_file="input/file.txt",
        source_file="done/file.txt",
        classification="document",
        source_fingerprint_sha256="abc",
        item_code="00001",
        processed_at="2026-04-08T12:00:00Z",
    )

    with patch(
        "i2d_ingest_registry._inventory_cli.run_inventory_upsert",
    ) as cli_mock:
        registry.register_done_inventory(
            tmp_path / "DONE_INVENTORY.md",
            meta,
            artifacts_tool=tmp_path / "artifacts_tool.py",
            done_inventory_template=template,
        )

    args, _kwargs = cli_mock.call_args
    assert args[0] == tmp_path / "artifacts_tool.py"
    assert args[1] == tmp_path / "DONE_INVENTORY.md"
    assert args[2] == template
    assert args[3] == "00001"
    assert args[4] == meta.processed_at
    assert args[5]["status"] == "archived"
    assert args[5]["source_fingerprint_sha256"] == "abc"
