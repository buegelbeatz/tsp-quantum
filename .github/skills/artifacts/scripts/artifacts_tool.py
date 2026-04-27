"""Artifacts skill utility commands for managing data bundles, inventory entries, and snapshots.

This module provides a command-line interface for the artifacts skill operations including:
- Creating numbered data bundles
- Managing inventory entries
- Updating LATEST.md snapshots
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_runtime import (
    InventoryEntry,
    append_inventory_entry,
    create_data_bundle,
    write_latest_snapshot,
)
from artifacts_tool_cli import main as cli_main


def _handle_bundle(args: argparse.Namespace) -> int:
    """Handle bundle command and print created bundle metadata."""
    bundle = create_data_bundle(Path(args.data_root), args.date)
    print(
        json.dumps(
            {
                "status": "ok",
                "date_key": bundle.date_key,
                "item_code": bundle.item_code,
                "item_root": str(bundle.item_root),
                "markdown_path": str(bundle.markdown_path),
                "metadata_path": str(bundle.metadata_path),
                "reviews_dir": str(bundle.reviews_dir),
            },
            indent=2,
        )
    )
    return 0


def _handle_inventory(args: argparse.Namespace) -> int:
    """Handle inventory command and upsert one inventory entry."""
    fields = json.loads(args.fields_json)
    append_inventory_entry(
        Path(args.inventory_path),
        InventoryEntry(item_id=args.item_id, created_at=args.created_at, fields=fields),
        Path(args.template_path) if args.template_path else None,
    )
    print(json.dumps({"status": "ok", "inventory_path": args.inventory_path}, indent=2))
    return 0


def _handle_latest(args: argparse.Namespace) -> int:
    """Handle latest command and write managed snapshot file."""
    write_latest_snapshot(Path(args.latest_path), Path(args.source_path))
    print(json.dumps({"status": "ok", "latest_path": args.latest_path}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute artifacts CLI by dispatching to command handlers."""
    return cli_main(
        argv,
        handle_bundle_fn=_handle_bundle,
        handle_inventory_fn=_handle_inventory,
        handle_latest_fn=_handle_latest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
