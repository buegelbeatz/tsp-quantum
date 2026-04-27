#!/usr/bin/env python3
"""Shared terminal rendering helpers for test and coverage reports.

Purpose:
    Provide unified ANSI color codes, formatting utilities, and path normalization
    for consistent human-readable terminal output across all render_*.py modules.

Security:
    No file I/O or external execution. Pure utility functions for string formatting.
"""

from __future__ import annotations

# ANSI color escape codes for terminal output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color escape codes.

    Args:
        text: The text to colorize.
        color: An ANSI color code constant (GREEN, RED, YELLOW, CYAN).

    Returns:
        The colorized text, or original text if color is invalid.
    """
    return f"{color}{text}{RESET}"


def get_coverage_color(value: float) -> str:
    """Return the appropriate ANSI color code for a coverage percentage.

    Args:
        value: Coverage percentage (0-100).

    Returns:
        Color code (GREEN for >=90%, YELLOW for >=80%, RED for <80%).
    """
    if value >= 90:
        return GREEN
    if value >= 80:
        return YELLOW
    return RED


def shorten_path(path: str, repo_root: str) -> str:
    """Shorten an absolute file path to a display-friendly relative form.

    Args:
        path: Absolute path to shorten.
        repo_root: Repository root directory (for base trimming).

    Returns:
        Relative path with repo root and /skills/ prefix stripped.
    """
    normalized = path.replace("\\", "/")
    repo_root = repo_root.replace("\\", "/")
    if normalized.startswith(repo_root + "/"):
        normalized = normalized[len(repo_root) + 1 :]
    marker = "/skills/"
    if marker in normalized:
        normalized = normalized.split(marker, 1)[1]
    return normalized
