#!/usr/bin/env python3
# layer: digital-generic-team
"""
Purpose:
    Count and report code lines, documentation lines, test lines, and config lines
    across the repository. Emits a Markdown table with file counts, line counts,
    and percentages per category.
Security:
    Reads only local repository files. No network access, no eval, no subprocess.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------

CODE_EXTENSIONS = {".py", ".sh", ".ts", ".js", ".java", ".rs", ".go", ".cpp", ".c"}
DOC_EXTENSIONS = {".md", ".rst", ".txt"}
CONFIG_EXTENSIONS = {".yaml", ".yml", ".toml", ".ini", ".json", ".env"}

TEST_PATH_PATTERNS = ["tests/", "test_", "_test.", "/tests/", "tests-"]


def is_test_file(path: Path) -> bool:
    """TODO: add docstring for is_test_file."""
    s = str(path)
    return any(p in s for p in TEST_PATH_PATTERNS)


def is_config_file(path: Path) -> bool:
    """TODO: add docstring for is_config_file."""
    return path.suffix in CONFIG_EXTENSIONS


def is_doc_file(path: Path) -> bool:
    """TODO: add docstring for is_doc_file."""
    return path.suffix in DOC_EXTENSIONS


def is_code_file(path: Path) -> bool:
    """TODO: add docstring for is_code_file."""
    return path.suffix in CODE_EXTENSIONS


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Category:
    name: str
    files: int = 0
    lines: int = 0


@dataclass
class Stats:
    code: Category = field(default_factory=lambda: Category("Scripts / Source"))
    tests: Category = field(default_factory=lambda: Category("Tests"))
    docs: Category = field(default_factory=lambda: Category("Documentation"))
    config: Category = field(default_factory=lambda: Category("Configuration"))

    def total_lines(self) -> int:
        """TODO: add docstring for total_lines."""
        return self.code.lines + self.tests.lines + self.docs.lines + self.config.lines

    def total_files(self) -> int:
        """TODO: add docstring for total_files."""
        return self.code.files + self.tests.files + self.docs.files + self.config.files

    def categories(self) -> list[Category]:
        """TODO: add docstring for categories."""
        return [self.code, self.tests, self.docs, self.config]


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git",
    ".digital-runtime",
    ".digital-artifacts",
    ".claude",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".tests",
    ".mypy_cache",
    ".ruff_cache",
}


def count_lines(path: Path) -> int:
    """TODO: add docstring for count_lines."""
    try:
        text = path.read_bytes()
        return text.count(b"\n") + (1 if text and not text.endswith(b"\n") else 0)
    except (OSError, PermissionError):
        return 0


def scan(repo_root: Path) -> Stats:
    """TODO: add docstring for scan."""
    stats = Stats()

    for dirpath, dirnames, filenames in os.walk(repo_root):
        # Prune skipped directories
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".digital-runtime")
        ]

        for fname in filenames:
            fpath = Path(dirpath) / fname

            if is_test_file(fpath):
                if is_code_file(fpath) or fpath.suffix in {".py", ".sh"}:
                    lines = count_lines(fpath)
                    stats.tests.files += 1
                    stats.tests.lines += lines
                continue

            if is_code_file(fpath):
                lines = count_lines(fpath)
                stats.code.files += 1
                stats.code.lines += lines
            elif is_doc_file(fpath):
                lines = count_lines(fpath)
                stats.docs.files += 1
                stats.docs.lines += lines
            elif is_config_file(fpath):
                lines = count_lines(fpath)
                stats.config.files += 1
                stats.config.lines += lines

    return stats


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def pct(part: int, total: int) -> str:
    """TODO: add docstring for pct."""
    if total == 0:
        return "—"
    return f"{part / total * 100:.1f}%"


def render_table(stats: Stats, repo_name: str) -> str:
    """TODO: add docstring for render_table."""
    total_lines = stats.total_lines()
    total_files = stats.total_files()

    rows = []
    for cat in stats.categories():
        rows.append(
            f"| {cat.name:<26} | {cat.files:>6} | {cat.lines:>8,} | {pct(cat.lines, total_lines):>7} |"
        )

    sep = "|" + "-" * 28 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 9 + "|"
    total_row = (
        f"| {'**TOTAL**':<26} | {total_files:>6} | {total_lines:>8,} | {'100.0%':>7} |"
    )

    return "\n".join(
        [
            f"## Code Distribution — `{repo_name}`",
            "",
            "| Category                   | Files  |    Lines | Share   |",
            "|:---------------------------|-------:|---------:|--------:|",
            *rows,
            sep,
            total_row,
            "",
        ]
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """TODO: add docstring for main."""
    repo_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

    # Try to derive repo name from git config
    git_config = repo_root / ".git" / "config"
    repo_name = repo_root.name
    if git_config.exists():
        for line in git_config.read_text().splitlines():
            if "url" in line and "=" in line:
                url = line.split("=", 1)[1].strip().rstrip(".git")
                repo_name = url.split("/")[-1]
                break

    stats = scan(repo_root)
    print(render_table(stats, repo_name))


if __name__ == "__main__":
    main()
