"""Unit tests for i2d_discover — file discovery and idempotency check."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

from i2d_models import CLASSIFICATION_MAP  # noqa: E402
from i2d_discover import discover_input_files, already_ingested  # noqa: E402


# ── discover_input_files ──────────────────────────────────────────────────────


def test_discover_returns_empty_for_missing_input_root(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_returns_empty_for_missing_input_root."""
    result = discover_input_files(tmp_path / "00-input")
    assert result == []


def test_discover_skips_gitkeep_and_ds_store(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_skips_gitkeep_and_ds_store."""
    folder = tmp_path / "features"
    folder.mkdir(parents=True)
    (folder / ".gitkeep").write_text("")
    (folder / ".DS_Store").write_text("")
    result = discover_input_files(tmp_path)
    assert result == []


def test_discover_finds_txt_file_under_features(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_finds_txt_file_under_features."""
    folder = tmp_path / "features"
    folder.mkdir(parents=True)
    (folder / "user_login.txt").write_text("User login feature")
    result = discover_input_files(tmp_path)
    assert len(result) == 1
    assert result[0].classification == "feature"
    assert result[0].path.name == "user_login.txt"


def test_discover_classification_for_all_subfolders(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_classification_for_all_subfolders."""
    for subfolder in CLASSIFICATION_MAP:
        folder = tmp_path / subfolder
        folder.mkdir(parents=True)
        (folder / f"test_{subfolder}.txt").write_text("content")
    result = discover_input_files(tmp_path)
    assert len(result) == 3
    classifications = {r.classification for r in result}
    assert classifications == {"document", "feature", "bug"}


def test_discover_order_is_stable_alphabetical_within_subfolder(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_order_is_stable_alphabetical_within_subfolder."""
    folder = tmp_path / "documents"
    folder.mkdir(parents=True)
    for name in ("z_last.txt", "a_first.txt", "m_middle.txt"):
        (folder / name).write_text("content")
    result = discover_input_files(tmp_path)
    names = [r.path.name for r in result]
    assert names == ["a_first.txt", "m_middle.txt", "z_last.txt"]


def test_discover_skips_subdirectories(tmp_path: Path) -> None:
    """TODO: add docstring for test_discover_skips_subdirectories."""
    folder = tmp_path / "bugs"
    folder.mkdir(parents=True)
    (folder / "actual_bug.txt").write_text("content")
    (folder / "subdir").mkdir()
    result = discover_input_files(tmp_path)
    assert len(result) == 1


def test_discover_skips_empty_files(tmp_path: Path, capsys) -> None:
    """Empty (0-byte) files must be skipped with a WARNING to prevent noise bundles.

    Regression test for BUG-THM-02: the empty exploration.txt file produced
    a synthetic bundle with 'This is an empty text file.' content that
    polluted the downstream specification and planning pipeline.
    """
    folder = tmp_path / "bugs"
    folder.mkdir(parents=True)
    (folder / "empty_audit.txt").write_bytes(b"")
    result = discover_input_files(tmp_path)
    assert result == []
    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert "empty_audit.txt" in captured.out


def test_discover_includes_nonempty_file_alongside_empty(tmp_path: Path) -> None:
    """Non-empty files are included even when an empty file is present in the same folder.

    Regression guard: the empty-file skip must not suppress adjacent valid files.
    """
    folder = tmp_path / "bugs"
    folder.mkdir(parents=True)
    (folder / "empty_audit.txt").write_bytes(b"")
    (folder / "real_bug.md").write_text("Actual bug content")
    result = discover_input_files(tmp_path)
    assert len(result) == 1
    assert result[0].path.name == "real_bug.md"


def test_discover_skips_empty_file_across_all_subfolders(tmp_path: Path) -> None:
    """Empty files in documents/, features/, and bugs/ are all skipped."""
    for subfolder in ("documents", "features", "bugs"):
        folder = tmp_path / subfolder
        folder.mkdir(parents=True)
        (folder / "zero.txt").write_bytes(b"")
    result = discover_input_files(tmp_path)
    assert result == []


def test_discover_marks_multiple_bug_files_as_possible_context(tmp_path: Path) -> None:
    """Multiple bug files in one run should be marked as possible context partners."""
    folder = tmp_path / "bugs"
    folder.mkdir(parents=True)
    (folder / "bug.txt").write_text("bug description")
    (folder / "screenshot.png").write_bytes(b"png")

    result = discover_input_files(tmp_path)

    assert len(result) == 2
    by_name = {entry.path.name: entry for entry in result}
    assert by_name["bug.txt"].context_candidates == ("screenshot.png",)
    assert by_name["screenshot.png"].context_candidates == ("bug.txt",)


# ── already_ingested ──────────────────────────────────────────────────────────


def test_already_ingested_returns_false_for_empty_data_root(tmp_path: Path) -> None:
    """TODO: add docstring for test_already_ingested_returns_false_for_empty_data_root."""
    source = tmp_path / "00-input" / "features" / "my_feature.txt"
    data_root = tmp_path / "10-data"
    data_root.mkdir(parents=True)
    assert already_ingested(source, data_root) is False


def test_already_ingested_returns_true_when_referenced_in_yaml(tmp_path: Path) -> None:
    """TODO: add docstring for test_already_ingested_returns_true_when_referenced_in_yaml."""
    source = tmp_path / "00-input" / "features" / "my_feature.txt"
    data_root = tmp_path / "10-data" / "00001-test"
    data_root.mkdir(parents=True)
    yaml_file = data_root / "00001.yaml"
    yaml_file.write_text(f"source_file: {source}\n")
    assert already_ingested(source, tmp_path / "10-data") is True


def test_already_ingested_returns_false_for_different_source(tmp_path: Path) -> None:
    """TODO: add docstring for test_already_ingested_returns_false_for_different_source."""
    source_a = tmp_path / "00-input" / "features" / "feature_a.txt"
    source_b = tmp_path / "00-input" / "features" / "feature_b.txt"
    data_root = tmp_path / "10-data" / "00001-test"
    data_root.mkdir(parents=True)
    (data_root / "00001.yaml").write_text(f"source_file: {source_a}\n")
    assert already_ingested(source_b, tmp_path / "10-data") is False


def test_already_ingested_returns_true_for_matching_fingerprint(tmp_path: Path) -> None:
    """TODO: add docstring for test_already_ingested_returns_true_for_matching_fingerprint."""
    source = tmp_path / "00-input" / "features" / "feature_a.txt"
    data_root = tmp_path / "10-data" / "00001-test"
    data_root.mkdir(parents=True)
    (data_root / "00001.yaml").write_text('source_fingerprint_sha256: "abc123"\n')
    assert already_ingested(source, tmp_path / "10-data", "abc123") is True


def test_already_ingested_is_robust_to_unreadable_yaml(tmp_path: Path) -> None:
    """Should silently skip files that cannot be read and return False."""
    source = tmp_path / "00-input" / "features" / "my_feature.txt"
    data_root = tmp_path / "10-data" / "00001-test"
    data_root.mkdir(parents=True)
    broken = data_root / "00001.yaml"
    broken.write_bytes(b"\xff\xfe invalid utf-8")
    # When content has no match (or read fails) → not ingested
    assert already_ingested(source, tmp_path / "10-data") is False
