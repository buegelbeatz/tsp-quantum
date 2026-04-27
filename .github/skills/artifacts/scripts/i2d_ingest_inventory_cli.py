"""CLI helper for ingest inventory upsert commands."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_inventory_upsert(
    artifacts_tool: Path,
    inventory_path: Path,
    template_path: Path | None,
    item_id: str,
    created_at: str,
    fields: dict[str, object],
) -> None:
    """Call artifacts_tool inventory command with serialized fields."""
    subprocess.run(
        [
            sys.executable,
            str(artifacts_tool),
            "inventory",
            "--inventory-path",
            str(inventory_path),
            "--template-path",
            str(template_path) if template_path else "",
            "--item-id",
            item_id,
            "--created-at",
            created_at,
            "--fields-json",
            json.dumps(fields),
        ],
        check=True,
        capture_output=True,
    )
