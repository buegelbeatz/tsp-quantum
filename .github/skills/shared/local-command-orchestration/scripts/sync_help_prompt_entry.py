#!/usr/bin/env python3
"""Synchronize one prompt entry into prompts/help.prompt.md.

Purpose:
    Insert a deterministic one-line entry for a prompt command into the help
    index file before the "Output style" section if missing.

Security:
    Reads and writes a repository-local markdown file only; no network access.
"""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    """Apply prompt line insertion if not already present."""
    help_path = Path(sys.argv[1])
    prompt_name = sys.argv[2]
    prompt_purpose = sys.argv[3].strip().rstrip(".")
    new_line = f"- `/{prompt_name}` -- {prompt_purpose}."

    lines = help_path.read_text(encoding="utf-8").splitlines()
    insert_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == "## Output style":
            insert_idx = idx
            break

    if insert_idx is None:
        lines.append(new_line)
    else:
        if insert_idx > 0 and lines[insert_idx - 1].strip() != "":
            lines.insert(insert_idx, "")
            insert_idx += 1
        lines.insert(insert_idx, new_line)

    help_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
