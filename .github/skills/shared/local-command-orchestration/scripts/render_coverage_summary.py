#!/usr/bin/env python3
"""Render a human-readable coverage summary from a coverage JSON report.

Purpose:
    Convert machine-readable coverage JSON into terminal-friendly summary tables.
    Highlights coverage gaps and compliance against specified thresholds.

Security:
    Reads coverage reports from local paths only. No remote uploads or sensitive data exposure.

Usage:
    python render_coverage_summary.py <coverage_json_path> <threshold> <repo_root>

Arguments:
    coverage_json_path  Path to the JSON report produced by ``coverage json``.
    threshold           Minimum acceptable coverage percentage (e.g. 80).
    repo_root           Absolute path to the repository root for path shortening.

Exit codes:
    0  Total coverage is at or above the threshold.
    1  Total coverage is below the threshold or the report is missing.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure this script's directory is in sys.path for relative imports
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from render_helpers import (  # noqa: F401, E402
    colorize,
    get_coverage_color,
    shorten_path,
    GREEN,
    RED,
    YELLOW,
    CYAN,
    RESET,
)

# Public API aliases (used by tests and external callers)
cover_color = get_coverage_color
shorten = shorten_path


def _load_coverage_data(json_path: str) -> dict:
    """Load coverage JSON; exit 1 if the report file is missing."""
    if not os.path.exists(json_path):
        print(f"  {colorize('FAILED', RED):<16}coverage JSON report was not generated")
        sys.exit(1)
    with open(json_path, encoding="utf-8") as fh:
        return json.load(fh)


def _build_rows(files: dict, repo_root: str) -> list:
    """Build sorted row tuples from per-file coverage entries."""
    rows = []
    for path, details in files.items():
        file_summary = details.get("summary", {})
        percent = float(file_summary.get("percent_covered", 0.0))
        rows.append(
            (
                shorten_path(path, repo_root),
                int(file_summary.get("num_statements", 0)),
                int(file_summary.get("missing_lines", 0)),
                percent,
                ", ".join(str(item) for item in details.get("missing_lines", []))
                or "-",
            )
        )
    rows.sort(key=lambda item: (item[3], item[0]))
    return rows


def _print_file_table(rows: list) -> int:
    """Print the per-file coverage table; return the header character length."""
    name_width = max([len("File"), *(len(row[0]) for row in rows)] or [4])
    header = (
        f"  {'File':<{name_width}}  {'Stmts':>5}  {'Miss':>4}  {'Cover':>6}  Missing"
    )
    print(f"  {colorize('INFO', CYAN)} excluding tests and test helpers")
    print(header)
    print(f"  {'-' * (len(header) - 2)}")
    for file_name, stmts, miss, percent, missing in rows:
        cover_text = colorize(f"{percent:5.0f}%", get_coverage_color(percent))
        print(
            f"  {file_name:<{name_width}}  {stmts:>5}  {miss:>4}  {cover_text:>15}  {missing}"
        )
    return len(header)


def _print_totals(payload: dict, threshold: float, header_len: int) -> None:
    """Print coverage totals and exit with an appropriate status code."""
    totals = payload.get("totals", {})
    total_stmts = int(totals.get("num_statements", 0))
    total_miss = int(totals.get("missing_lines", 0))
    total_cover = float(totals.get("percent_covered", 0.0))
    name_width = header_len - 30
    status_label = (
        colorize("PASSED", GREEN)
        if total_cover >= threshold
        else colorize("FAILED", RED)
    )
    print(f"  {'-' * (header_len - 2)}")
    print(
        f"  {'TOTAL':<{name_width}}  {total_stmts:>5}  {total_miss:>4}  "
        f"{colorize(f'{total_cover:5.0f}%', get_coverage_color(total_cover)):>15}"
    )
    print(f"  {status_label} threshold={threshold:.0f}%")
    sys.exit(0 if total_cover >= threshold else 1)


def main() -> None:
    """Parse a coverage JSON report and print a compact, colored coverage table."""
    json_path, threshold_text, repo_root = sys.argv[1:4]
    threshold = float(threshold_text)
    print("\nCoverage Summary")
    payload = _load_coverage_data(json_path)
    rows = _build_rows(payload.get("files", {}), repo_root)
    header_len = _print_file_table(rows)
    _print_totals(payload, threshold, header_len)


if __name__ == "__main__":
    main()
