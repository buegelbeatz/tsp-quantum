"""Bundle identifier allocation for artifact runtime."""

from __future__ import annotations

import re
from pathlib import Path

BUNDLE_DIR_RE = re.compile(r"^(?P<code>\d{5})$")


def next_bundle_code(day_root: Path) -> str:
    """Return the next five-digit bundle code for a date folder."""
    highest = (
        max(
            (
                int(match.group("code"))
                for child in day_root.iterdir()
                if child.is_dir() and (match := BUNDLE_DIR_RE.match(child.name))
            ),
            default=-1,
        )
        if day_root.exists()
        else -1
    )
    next_value = highest + 1
    if next_value > 99999:
        raise ValueError("bundle id space exhausted for date folder")
    return f"{next_value:05d}"
