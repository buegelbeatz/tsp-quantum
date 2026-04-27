"""Bundle allocation helper for ingest pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def allocate_bundle(
    artifacts_tool: Path, data_root: Path, date_key: str
) -> dict[str, object]:
    """Call artifacts_tool bundle command and parse JSON output."""
    result = subprocess.run(
        [
            sys.executable,
            str(artifacts_tool),
            "bundle",
            "--data-root",
            str(data_root),
            "--date",
            date_key,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)
