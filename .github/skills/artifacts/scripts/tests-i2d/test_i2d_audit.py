"""Unit tests for i2d_audit — audit record writing."""

from __future__ import annotations

from importlib import import_module
import sys
from pathlib import Path
from unittest.mock import patch
from typing import Any

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

i2d_models = import_module("i2d_models")
i2d_audit = import_module("i2d_audit")
InputFile = i2d_models.InputFile
IngestResult = i2d_models.IngestResult
write_audit = i2d_audit.write_audit


def _make_input_file(
    tmp_path: Path, subfolder: str, name: str, classification: str
) -> Any:
    folder = tmp_path / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / name
    f.write_text("content")
    return InputFile(path=f, classification=classification)


def test_write_audit_creates_file_with_correct_name(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_creates_file_with_correct_name."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "features", "feat.txt", "feature")
    bundle_root = tmp_path / "10-data" / "00000-feat"
    bundle_root.mkdir(parents=True)
    result = IngestResult(input_file=inp, item_code="00000", bundle_root=bundle_root)

    audit_file = write_audit(audit_root, [result], "2025-07-01")

    assert audit_file.name == "00000-artifacts-input-2-data.md"
    assert audit_file.parent.name == "2025-07-01"


def test_write_audit_increments_sequence_for_second_run(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_increments_sequence_for_second_run."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "features", "feat.txt", "feature")
    bundle_root = tmp_path / "10-data" / "00000-feat"
    bundle_root.mkdir(parents=True)
    result = IngestResult(input_file=inp, item_code="00000", bundle_root=bundle_root)

    write_audit(audit_root, [result], "2025-07-01")
    second = write_audit(audit_root, [result], "2025-07-01")

    assert second.name == "00001-artifacts-input-2-data.md"


def test_write_audit_contains_skill_metadata(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_contains_skill_metadata."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "documents", "doc.txt", "document")
    bundle_root = tmp_path / "10-data" / "00000-doc"
    bundle_root.mkdir(parents=True)
    result = IngestResult(input_file=inp, item_code="00000", bundle_root=bundle_root)

    audit_file = write_audit(audit_root, [result], "2025-07-01")
    content = audit_file.read_text(encoding="utf-8")

    assert "skill: artifacts-input-2-data" in content
    assert "triggered_by: agile-coach" in content
    assert "date_key: 2025-07-01" in content


def test_write_audit_processed_section_lists_item_code(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_processed_section_lists_item_code."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "bugs", "crash.txt", "bug")
    bundle_root = tmp_path / "10-data" / "00003-crash"
    bundle_root.mkdir(parents=True)
    result = IngestResult(input_file=inp, item_code="00003", bundle_root=bundle_root)

    audit_file = write_audit(audit_root, [result], "2025-07-01")
    content = audit_file.read_text(encoding="utf-8")

    assert "[00003]" in content
    assert "crash.txt" in content


def test_write_audit_skipped_section_shown_when_present(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_skipped_section_shown_when_present."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "features", "feat.txt", "feature")
    bundle_root = tmp_path / "10-data" / "00000-feat"
    bundle_root.mkdir(parents=True)
    skipped = IngestResult(
        input_file=inp, item_code="", bundle_root=bundle_root, skipped=True
    )

    audit_file = write_audit(audit_root, [skipped], "2025-07-01")
    content = audit_file.read_text(encoding="utf-8")

    assert "## Skipped" in content
    assert "feat.txt" in content


def test_write_audit_failed_section_shown_when_present(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_failed_section_shown_when_present."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "bugs", "bad.txt", "bug")
    bundle_root = tmp_path / "10-data" / "00000-bad"
    bundle_root.mkdir(parents=True)
    failed = IngestResult(
        input_file=inp, item_code="", bundle_root=bundle_root, error="LLM timeout"
    )

    audit_file = write_audit(audit_root, [failed], "2025-07-01")
    content = audit_file.read_text(encoding="utf-8")

    assert "## Failed" in content
    assert "LLM timeout" in content


def test_write_audit_counts_are_correct(tmp_path: Path) -> None:
    """TODO: add docstring for test_write_audit_counts_are_correct."""
    audit_root = tmp_path / "70-audits"
    bundle_root = tmp_path / "10-data" / "00000"
    bundle_root.mkdir(parents=True)

    ok = IngestResult(
        input_file=_make_input_file(tmp_path, "features", "f.txt", "feature"),
        item_code="00000",
        bundle_root=bundle_root,
    )
    skipped = IngestResult(
        input_file=_make_input_file(tmp_path, "documents", "d.txt", "document"),
        item_code="",
        bundle_root=bundle_root,
        skipped=True,
    )
    failed = IngestResult(
        input_file=_make_input_file(tmp_path, "bugs", "b.txt", "bug"),
        item_code="",
        bundle_root=bundle_root,
        error="timeout",
    )

    audit_file = write_audit(audit_root, [ok, skipped, failed], "2025-07-01")
    content = audit_file.read_text(encoding="utf-8")

    assert "- processed: 1" in content
    assert "- skipped: 1" in content
    assert "- failed: 1" in content


def test_write_audit_delegates_to_markdown_builder(tmp_path: Path) -> None:
    """Verify write_audit delegates markdown building to i2d_audit_markdown."""
    audit_root = tmp_path / "70-audits"
    inp = _make_input_file(tmp_path, "features", "feat.txt", "feature")
    bundle_root = tmp_path / "10-data" / "00000-feat"
    bundle_root.mkdir(parents=True)
    result = IngestResult(input_file=inp, item_code="00000", bundle_root=bundle_root)

    with patch(
        "i2d_audit.build_audit_markdown", return_value=["line1", "line2"]
    ) as mock:
        write_audit(audit_root, [result], "2025-07-01")

    assert mock.called
    assert mock.call_args.args == ([result], "2025-07-01")


def test_write_audit_with_empty_results_records_no_op_outcome(tmp_path: Path) -> None:
    """Empty ingest runs should still produce an audit document."""
    audit_root = tmp_path / "70-audits"

    audit_file = write_audit(audit_root, [], "2025-07-01")

    content = audit_file.read_text(encoding="utf-8")
    assert "No input files were discovered" in content
    assert "## Processed" in content
    assert "- none" in content
