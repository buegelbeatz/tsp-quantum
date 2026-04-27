"""Merge requirement files deterministically for layer runtime setup."""

from __future__ import annotations

import argparse
from pathlib import Path


def merge_requirements(input_paths: list[Path], output_path: Path) -> None:
    """Merge requirement files, remove duplicates and write sorted output."""
    lines: list[str] = []
    for path in input_paths:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)

    unique_sorted = sorted(set(lines), key=lambda item: item.lower())
    output_path.write_text(
        "\n".join(unique_sorted) + ("\n" if unique_sorted else ""), encoding="utf-8"
    )


def main() -> None:
    """Parse CLI arguments and run requirements merge."""
    parser = argparse.ArgumentParser(
        description="Merge, deduplicate and sort requirement files."
    )
    parser.add_argument("--output", required=True, help="Output requirements file")
    parser.add_argument("inputs", nargs="*", help="Input requirement files")
    args = parser.parse_args()

    output_path = Path(args.output)
    input_paths = [Path(item) for item in args.inputs]
    merge_requirements(input_paths, output_path)


if __name__ == "__main__":
    main()
