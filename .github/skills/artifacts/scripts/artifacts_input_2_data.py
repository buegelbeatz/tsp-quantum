"""CLI entry point for the artifacts-input-2-data pipeline.

Purpose:
    Provide command-line interface for converting input sources into data bundles.
    Routes pipeline subcommands (ingest, link, vision, audit, content) to appropriate handlers.
    Treat English as the canonical language for all normalized output written to
    .digital-artifacts/10-data/.

Security:
    Validates all input paths before processing. Runs subprocesses with restricted scopes.
    Audit records track all conversions and state changes.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from i2d_discover import discover_input_files
from i2d_audit import write_audit
from artifacts_input_2_data_processor import process_input_files


def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser for the ingest pipeline CLI."""
    parser = argparse.ArgumentParser(
        description="artifacts-input-2-data ingest pipeline"
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--date", default="", help="Date key YYYY-MM-DD (defaults to today)"
    )
    return parser


def _setup_paths(repo_root: Path) -> tuple[Path, Path, Path, Path, Path | None]:
    """Setup and return artifact pipeline paths."""
    input_root = repo_root / ".digital-artifacts" / "00-input"
    data_root = repo_root / ".digital-artifacts" / "10-data"
    audit_root = repo_root / ".digital-artifacts" / "70-audits"
    inventory_path = data_root / "INVENTORY.md"
    template_path = (
        repo_root
        / ".github"
        / "skills"
        / "artifacts"
        / "templates"
        / "digital-artifacts"
        / "10-data"
        / "INVENTORY.template.md"
    )
    return (
        input_root,
        data_root,
        audit_root,
        inventory_path,
        template_path if template_path.exists() else None,
    )


def _handle_no_input(audit_root: Path, date_key: str) -> int:
    """Handle no-input case and emit deterministic no-op audit."""
    print("[artifacts-input-2-data] no input files found — nothing to process")
    if os.getenv("DIGITAL_ARTIFACTS_EMIT_PIPELINE_AUDIT", "1") == "0":
        print(
            "[artifacts-input-2-data] done — processed=0 skipped=0 audit=disabled(parent-prompt)"
        )
        return 0
    audit_file = write_audit(audit_root, [], date_key)
    print(f"[artifacts-input-2-data] done — processed=0 skipped=0 audit={audit_file}")
    return 0


def _summarize_results(results, audit_root: Path, date_key: str) -> int:
    """Write audit and print processing summary for ingest results."""
    if os.getenv("DIGITAL_ARTIFACTS_EMIT_PIPELINE_AUDIT", "1") == "0":
        processed = sum(1 for r in results if not r.skipped and not r.error)
        skipped = sum(1 for r in results if r.skipped)
        print(
            "[artifacts-input-2-data] "
            f"done — processed={processed} skipped={skipped} audit=disabled(parent-prompt)"
        )
        return 0
    audit_file = write_audit(audit_root, results, date_key)
    processed = sum(1 for r in results if not r.skipped and not r.error)
    skipped = sum(1 for r in results if r.skipped)
    print(
        f"[artifacts-input-2-data] done — processed={processed} skipped={skipped} audit={audit_file}"
    )
    return 0


def main(argv: list[str] | None = None, *, process_fn=None) -> int:
    """Run the full ingest pipeline and return exit code."""
    if process_fn is None:
        process_fn = process_input_files

    args = _build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    date_key = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    input_root, data_root, audit_root, inventory_path, template_path = _setup_paths(
        repo_root
    )

    input_files = discover_input_files(input_root)
    if not input_files:
        return _handle_no_input(audit_root, date_key)

    print(f"[artifacts-input-2-data] discovered {len(input_files)} input file(s)")
    print("[artifacts-input-2-data] normalized-output-language=english")
    results = process_fn(
        input_files,
        data_root,
        date_key,
        inventory_path,
        template_path,
    )
    return _summarize_results(results, audit_root, date_key)


if __name__ == "__main__":
    sys.exit(main())
