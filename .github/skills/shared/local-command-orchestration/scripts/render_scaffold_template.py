#!/usr/bin/env python3
"""Render scaffold templates with deterministic placeholder replacement.

Purpose:
    Fill prompt scaffold templates using explicit key/value placeholders and
    write rendered files with UTF-8 encoding.

Security:
    Reads template and writes output on local filesystem only; no dynamic code
    execution or network access.
"""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    """Render template file with placeholders like __KEY__."""
    template_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    content = template_path.read_text(encoding="utf-8")

    for pair in sys.argv[3:]:
        key, value = pair.split("=", 1)
        content = content.replace(f"__{key}__", value)

    output_path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
