"""Unit tests for selected i2d_ingest helpers."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_ingest  # noqa: E402
import i2d_ingest_flow  # noqa: E402
from i2d_ingest import _move_source_to_done  # noqa: E402


@dataclass
class _FlowMeta:
    item_code: str
    date_key: str
    source_file: str
    source_input_file: str
    source_fingerprint_sha256: str
    classification: str
    file_format: str
    processed_at: str
    extraction_engine: str = ""
    extraction_status: str = ""
    txt_translation: str = ""
    txt_inferred_type: str = ""
    txt_research_hints: list[str] | None = None
    language_gate_status: str = ""
    language_gate_note: str = ""
    review_note: str = ""


@dataclass(frozen=True)
class _FlowResult:
    input_file: object
    item_code: str
    bundle_root: Path
    skipped: bool = False
    error: str = ""


def test_move_source_to_done_moves_file_and_returns_destination(tmp_path: Path) -> None:
    """TODO: add docstring for test_move_source_to_done_moves_file_and_returns_destination."""
    source = tmp_path / "00-input" / "documents" / "sample.txt"
    source.parent.mkdir(parents=True)
    source.write_text("content", encoding="utf-8")

    done_root = tmp_path / "20-done"
    destination = _move_source_to_done(
        source, done_root, "document", "2026-03-31", "00000"
    )

    assert destination.exists()
    assert destination.name == "00000__sample.txt"
    assert not source.exists()


def test_move_source_to_done_strips_stacked_bundle_prefixes(tmp_path: Path) -> None:
    """Stacked bundle prefixes should be normalized during archival moves."""
    source = (
        tmp_path
        / "00-input"
        / "documents"
        / "00000__00000__00000__01-problem-statement.md"
    )
    source.parent.mkdir(parents=True)
    source.write_text("content", encoding="utf-8")

    done_root = tmp_path / "20-done"
    destination = _move_source_to_done(
        source, done_root, "document", "2026-03-31", "00000"
    )

    assert destination.exists()
    assert destination.name == "00000__01-problem-statement.md"
    assert not source.exists()


def test_ingest_flow_normalizes_markdown_content_to_english(tmp_path: Path) -> None:
    """Markdown bundles should keep canonical English content and preserve source context."""
    input_file = SimpleNamespace(
        path=tmp_path / "00-input" / "documents" / "source.md",
        classification="document",
    )
    input_file.path.parent.mkdir(parents=True)
    input_file.path.write_text("# Problem\n\nDeutscher Inhalt", encoding="utf-8")

    captured: dict[str, object] = {}

    def allocate_bundle_fn(_data_root: Path, _date_key: str) -> dict[str, str]:
        """TODO: add docstring for allocate_bundle_fn."""
        item_root = tmp_path / "10-data" / "2026-04-09" / "00000"
        item_root.mkdir(parents=True, exist_ok=True)
        return {
            "item_code": "00000",
            "item_root": str(item_root),
            "metadata_path": str(item_root / "00000.yaml"),
        }

    def extract_content_fn(_path: Path) -> tuple[str, str, str]:
        """TODO: add docstring for extract_content_fn."""
        return "# Problem\n\nDeutscher Inhalt", "markitdown", "ok"

    def move_source_to_done_fn(
        source_path: Path,
        _done_root: Path,
        _classification: str,
        _date_key: str,
        item_code: str,
    ) -> Path:
        """TODO: add docstring for move_source_to_done_fn."""
        destination = (
            tmp_path
            / "20-done"
            / "document"
            / "2026-04-09"
            / f"{item_code}__{source_path.name}"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            source_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return destination

    def process_txt_file_fn(content: str) -> dict[str, object]:
        """TODO: add docstring for process_txt_file_fn."""
        assert "Deutscher Inhalt" in content
        return {
            "translation": "# Problem\n\nEnglish content",
            "inferred_type": "project",
            "research_hints": ["hint-a"],
            "review_note": "Needs scoping.",
        }

    def write_bundle_markdown_fn(_bundle_info, meta, extracted_content: str) -> None:
        """TODO: add docstring for write_bundle_markdown_fn."""
        captured["meta"] = meta
        captured["content"] = extracted_content

    deps = i2d_ingest_flow.IngestDeps(
        compute_sha256_fn=lambda _p: "sha256",
        already_ingested_fn=lambda *_a, **_kw: False,
        allocate_bundle_fn=allocate_bundle_fn,
        extract_content_fn=extract_content_fn,
        move_source_to_done_fn=move_source_to_done_fn,
        process_txt_file_fn=process_txt_file_fn,
        write_bundle_markdown_fn=write_bundle_markdown_fn,
        write_metadata_fn=lambda *_a, **_kw: None,
        register_inventory_fn=lambda *_a, **_kw: None,
        register_done_inventory_fn=lambda *_a, **_kw: None,
        bundle_metadata_cls=_FlowMeta,
        ingest_result_cls=_FlowResult,
    )

    result = i2d_ingest_flow.ingest_file(
        input_file,
        tmp_path / "10-data",
        "2026-04-09",
        tmp_path / "10-data" / "INVENTORY.md",
        None,
        deps,
    )

    assert result.item_code == "00000"
    content = captured["content"]
    assert "### Canonical English Content" in content
    assert "# Problem\n\nEnglish content" in content
    assert "### Source-Preserved Extract" in content
    assert "Deutscher Inhalt" in content
    assert "### Ingest Hints" in content
    assert "research_hint: hint-a" in content
    assert "review_note: Needs scoping." in content
    meta = captured["meta"]
    assert meta.txt_translation == "# Problem\n\nEnglish content"  # type: ignore[attr-defined]
    assert meta.txt_inferred_type == "project"  # type: ignore[attr-defined]
    assert meta.language_gate_status == "passed"  # type: ignore[attr-defined]
    assert meta.language_gate_note == "Canonical downstream content passed the English-only gate."  # type: ignore[attr-defined]
    assert meta.review_note == "Needs scoping."  # type: ignore[attr-defined]


def test_ingest_flow_records_failed_language_gate_for_non_text_localized_content(
    tmp_path: Path,
) -> None:
    """Localized canonical bundle text outside text enrichment should be flagged explicitly."""
    input_file = SimpleNamespace(
        path=tmp_path / "00-input" / "documents" / "source.pdf",
        classification="document",
    )
    input_file.path.parent.mkdir(parents=True)
    input_file.path.write_text("localized content", encoding="utf-8")

    captured: dict[str, object] = {}

    def allocate_bundle_fn(_data_root: Path, _date_key: str) -> dict[str, str]:
        item_root = tmp_path / "10-data" / "2026-04-21" / "00001"
        item_root.mkdir(parents=True, exist_ok=True)
        return {
            "item_code": "00001",
            "item_root": str(item_root),
            "metadata_path": str(item_root / "00001.yaml"),
        }

    def extract_content_fn(_path: Path) -> tuple[str, str, str]:
        return "## 1. Ausgangslage\n\nHeute passiert die Bewertung oft.", "markitdown", "ok"

    def move_source_to_done_fn(
        source_path: Path,
        _done_root: Path,
        _classification: str,
        _date_key: str,
        item_code: str,
    ) -> Path:
        destination = tmp_path / "20-done" / "document" / "2026-04-21" / f"{item_code}__{source_path.name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        return destination

    def write_bundle_markdown_fn(_bundle_info, meta, extracted_content: str) -> None:
        captured["meta"] = meta
        captured["content"] = extracted_content

    deps = i2d_ingest_flow.IngestDeps(
        compute_sha256_fn=lambda _p: "sha256",
        already_ingested_fn=lambda *_a, **_kw: False,
        allocate_bundle_fn=allocate_bundle_fn,
        extract_content_fn=extract_content_fn,
        move_source_to_done_fn=move_source_to_done_fn,
        process_txt_file_fn=lambda *_a, **_kw: {"error": "skip"},
        write_bundle_markdown_fn=write_bundle_markdown_fn,
        write_metadata_fn=lambda *_a, **_kw: None,
        register_inventory_fn=lambda *_a, **_kw: None,
        register_done_inventory_fn=lambda *_a, **_kw: None,
        bundle_metadata_cls=_FlowMeta,
        ingest_result_cls=_FlowResult,
    )

    i2d_ingest_flow.ingest_file(
        input_file,
        tmp_path / "10-data",
        "2026-04-21",
        tmp_path / "10-data" / "INVENTORY.md",
        None,
        deps,
    )

    meta = captured["meta"]
    assert captured["content"] == "## 1. Ausgangslage\n\nHeute passiert die Bewertung oft."
    assert meta.language_gate_status == "failed"  # type: ignore[attr-defined]
    assert "localized fragments" in meta.language_gate_note  # type: ignore[attr-defined]
    assert "localized fragments" in meta.review_note  # type: ignore[attr-defined]


def test_ingest_flow_archives_already_ingested_source(tmp_path: Path) -> None:
    """Already-ingested sources should be archived out of 00-input and marked skipped."""
    input_file = SimpleNamespace(
        path=tmp_path / "00-input" / "bugs" / "bug.txt",
        classification="bug",
    )
    input_file.path.parent.mkdir(parents=True)
    input_file.path.write_text("duplicate bug", encoding="utf-8")

    def move_source_to_done_fn(
        source_path: Path,
        done_root: Path,
        classification: str,
        date_key: str,
        item_code: str,
    ) -> Path:
        destination = done_root / classification / date_key / f"{item_code}__{source_path.name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(destination)
        return destination

    deps = i2d_ingest_flow.IngestDeps(
        compute_sha256_fn=lambda _p: "a1b2c3d4",
        already_ingested_fn=lambda *_a, **_kw: True,
        allocate_bundle_fn=lambda *_a, **_kw: {},
        extract_content_fn=lambda *_a, **_kw: ("", "", ""),
        move_source_to_done_fn=move_source_to_done_fn,
        process_txt_file_fn=lambda *_a, **_kw: {},
        write_bundle_markdown_fn=lambda *_a, **_kw: None,
        write_metadata_fn=lambda *_a, **_kw: None,
        register_inventory_fn=lambda *_a, **_kw: None,
        register_done_inventory_fn=lambda *_a, **_kw: None,
        bundle_metadata_cls=_FlowMeta,
        ingest_result_cls=_FlowResult,
    )

    result = i2d_ingest_flow.ingest_file(
        input_file,
        tmp_path / "10-data",
        "2026-04-17",
        tmp_path / "10-data" / "INVENTORY.md",
        None,
        deps,
    )

    assert result.skipped is True
    assert not input_file.path.exists()
    archived = (
        tmp_path
        / "20-done"
        / "bug"
        / "2026-04-17"
        / "SKIPa1b2c3__bug.txt"
    )
    assert archived.exists()


def test_ingest_flow_adds_bug_context_review_note(tmp_path: Path) -> None:
    """Bug bundles should carry a note when sibling files may provide context."""
    input_file = SimpleNamespace(
        path=tmp_path / "00-input" / "bugs" / "bug.txt",
        classification="bug",
        context_candidates=("screenshot.png",),
    )
    input_file.path.parent.mkdir(parents=True)
    input_file.path.write_text("bug description", encoding="utf-8")

    captured: dict[str, object] = {}

    def allocate_bundle_fn(_data_root: Path, _date_key: str) -> dict[str, str]:
        item_root = tmp_path / "10-data" / "2026-04-17" / "00011"
        item_root.mkdir(parents=True, exist_ok=True)
        return {
            "item_code": "00011",
            "item_root": str(item_root),
            "metadata_path": str(item_root / "00011.yaml"),
        }

    def extract_content_fn(_path: Path) -> tuple[str, str, str]:
        return "bug description", "plain-text", "ok"

    def move_source_to_done_fn(
        source_path: Path,
        _done_root: Path,
        _classification: str,
        _date_key: str,
        item_code: str,
    ) -> Path:
        destination = tmp_path / "20-done" / "bug" / "2026-04-17" / f"{item_code}__{source_path.name}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        return destination

    def process_txt_file_fn(_content: str) -> dict[str, object]:
        return {"translation": "bug description", "review_note": "Needs reproduction."}

    def write_bundle_markdown_fn(_bundle_info, meta, extracted_content: str) -> None:
        captured["meta"] = meta
        captured["content"] = extracted_content

    deps = i2d_ingest_flow.IngestDeps(
        compute_sha256_fn=lambda _p: "sha256",
        already_ingested_fn=lambda *_a, **_kw: False,
        allocate_bundle_fn=allocate_bundle_fn,
        extract_content_fn=extract_content_fn,
        move_source_to_done_fn=move_source_to_done_fn,
        process_txt_file_fn=process_txt_file_fn,
        write_bundle_markdown_fn=write_bundle_markdown_fn,
        write_metadata_fn=lambda *_a, **_kw: None,
        register_inventory_fn=lambda *_a, **_kw: None,
        register_done_inventory_fn=lambda *_a, **_kw: None,
        bundle_metadata_cls=_FlowMeta,
        ingest_result_cls=_FlowResult,
    )

    result = i2d_ingest_flow.ingest_file(
        input_file,
        tmp_path / "10-data",
        "2026-04-17",
        tmp_path / "10-data" / "INVENTORY.md",
        None,
        deps,
    )

    assert result.item_code == "00011"
    meta = captured["meta"]
    assert "Needs reproduction." in meta.review_note  # type: ignore[attr-defined]
    assert "screenshot.png" in meta.review_note  # type: ignore[attr-defined]


def test_format_text_bundle_content_avoids_duplicate_source_block() -> None:
    """No source appendix is needed when translation matches the extracted content."""
    meta = _FlowMeta(
        item_code="00001",
        date_key="2026-04-09",
        source_file="done.md",
        source_input_file="input.md",
        source_fingerprint_sha256="sha256",
        classification="document",
        file_format="md",
        processed_at="2026-04-09T00:00:00Z",
        txt_translation="# Problem\n\nEnglish content",
    )

    format_bundle_content = getattr(i2d_ingest_flow, "_format_text_bundle_content")
    content = format_bundle_content(
        meta,
        "# Problem\n\nEnglish content",
    )

    assert content == "# Problem\n\nEnglish content"


def test_ingest_file_delegates_to_flow_helper(tmp_path: Path) -> None:
    """TODO: add docstring for test_ingest_file_delegates_to_flow_helper."""
    input_file = SimpleNamespace(path=tmp_path / "input.txt", classification="document")
    data_root = tmp_path / "10-data"
    inventory_path = tmp_path / "10-data" / "INVENTORY.md"
    template_path = tmp_path / "10-data" / "INVENTORY.template.md"
    expected = SimpleNamespace(item_code="00001")

    with patch(
        "i2d_ingest._ingest_flow.ingest_file",
        return_value=expected,
    ) as flow_mock:
        result = i2d_ingest.ingest_file(
            input_file,  # type: ignore[arg-type]
            data_root,
            "2026-04-08",
            inventory_path,
            template_path,
        )

    assert result is expected
    assert flow_mock.call_count == 1
    args, _kwargs = flow_mock.call_args
    assert len(args) == 6
    assert args[:5] == (
        input_file,
        data_root,
        "2026-04-08",
        inventory_path,
        template_path,
    )
    deps = args[5]
    assert deps.compute_sha256_fn is i2d_ingest.compute_sha256
    assert deps.already_ingested_fn is i2d_ingest.already_ingested
    assert deps.allocate_bundle_fn is i2d_ingest._allocate_bundle
    assert deps.extract_content_fn is i2d_ingest.extract_content
    assert deps.move_source_to_done_fn is i2d_ingest._move_source_to_done
    assert deps.process_txt_file_fn is i2d_ingest.process_txt_file
    assert deps.write_bundle_markdown_fn is i2d_ingest._write_bundle_markdown
    assert deps.write_metadata_fn is i2d_ingest._write_metadata
    assert deps.register_inventory_fn is i2d_ingest._register_inventory
    assert deps.register_done_inventory_fn is i2d_ingest._register_done_inventory
    assert deps.bundle_metadata_cls is i2d_ingest.BundleMetadata
    assert deps.ingest_result_cls is i2d_ingest.IngestResult


def test_write_metadata_delegates_to_registry_helper() -> None:
    """_write_metadata should write a metadata document for the allocated bundle."""
    tmp_dir = Path("/tmp")
    metadata_path = tmp_dir / "ingest-test-meta.yml"
    metadata_path.unlink(missing_ok=True)

    bundle_info = {"metadata_path": str(metadata_path)}
    meta = SimpleNamespace(
        item_code="00001",
        date_key="2026-04-09",
        source_file="sample.txt",
        source_input_file="documents/sample.txt",
        source_fingerprint_sha256="abc123",
        classification="document",
        file_format="txt",
        processed_at="2026-04-09T10:00:00Z",
        extraction_engine="plain-text",
        extraction_status="ok",
        txt_translation=None,
        txt_inferred_type=None,
        txt_research_hints=[],
        language_gate_status="failed",
        language_gate_note="Canonical downstream content still contains localized fragments; translate or normalize before planning promotion.",
        review_note="Needs review.",
    )

    i2d_ingest._write_metadata(bundle_info, meta)

    assert metadata_path.exists()
    content = metadata_path.read_text(encoding="utf-8")
    assert "item_code" in content
    assert "00001" in content
    assert "language_gate_status" in content
    assert "failed" in content
    assert "language_gate_note" in content
    metadata_path.unlink(missing_ok=True)


def test_allocate_bundle_delegates_to_bundle_helper(tmp_path: Path) -> None:
    """_allocate_bundle should return bundle info with an allocated item code."""
    result = i2d_ingest._allocate_bundle(tmp_path / "10-data", "2026-04-08")

    assert result["date_key"] == "2026-04-08"
    assert result["item_code"].isdigit()  # type: ignore[attr-defined]
    assert len(result["item_code"]) == 5  # type: ignore[arg-type]
    assert Path(result["item_root"]).exists()  # type: ignore[arg-type]


def test_move_source_to_done_delegates_to_archive_helper(tmp_path: Path) -> None:
    """Ensure _move_source_to_done delegates to i2d_ingest_archive helper."""
    expected = tmp_path / "20-done" / "document" / "2026-04-08" / "00001__sample.txt"

    with patch(
        "i2d_ingest._archive.move_source_to_done",
        return_value=expected,
    ) as archive_mock:
        result = i2d_ingest._move_source_to_done(
            tmp_path / "sample.txt",
            tmp_path / "20-done",
            "document",
            "2026-04-08",
            "00001",
        )

    assert result == expected
    archive_mock.assert_called_once_with(
        tmp_path / "sample.txt",
        tmp_path / "20-done",
        "document",
        "2026-04-08",
        "00001",
    )
