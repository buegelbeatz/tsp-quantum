"""Unit tests for i2d_content helpers."""

from __future__ import annotations

import sys
import textwrap
from types import ModuleType, SimpleNamespace
from importlib import import_module
from pathlib import Path
from email.message import EmailMessage
from unittest.mock import patch

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

i2d_content = import_module("i2d_content")
_extract_eml = getattr(i2d_content, "_extract_eml")
_extract_image_ocr = getattr(i2d_content, "_extract_image_ocr")
compute_sha256 = i2d_content.compute_sha256
extract_content = i2d_content.extract_content
render_bundle_markdown = i2d_content.render_bundle_markdown


def test_compute_sha256_returns_expected_digest(tmp_path: Path) -> None:
    """TODO: add docstring for test_compute_sha256_returns_expected_digest."""
    file_path = tmp_path / "demo.txt"
    file_path.write_text("abc", encoding="utf-8")
    assert (
        compute_sha256(file_path)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_extract_content_plain_text_returns_text(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_content_plain_text_returns_text."""
    file_path = tmp_path / "input.txt"
    file_path.write_text("hello world", encoding="utf-8")
    content, engine, status = extract_content(file_path)
    assert "hello world" in content
    assert "## File Facts" in content
    assert engine == "plain-text"
    assert status == "ok"


def test_extract_content_plain_text_builds_form_markdown_when_described(
    tmp_path: Path,
) -> None:
    """Textual form descriptions should produce a normalized markdown form."""
    file_path = tmp_path / "form-notes.txt"
    file_path.write_text(
        "Login form\nUsername: \nPassword: \nEnter button",
        encoding="utf-8",
    )

    content, engine, status = extract_content(file_path)

    assert engine == "plain-text"
    assert status == "ok"
    assert "Detected Form (from text)" in content
    assert "| Username |" in content
    assert "| Password |" in content


def test_render_bundle_markdown_replaces_placeholders() -> None:
    """TODO: add docstring for test_render_bundle_markdown_replaces_placeholders."""
    fields = {
        "ITEM_CODE": "00042",
        "SOURCE_DONE_FILE": "/done/path/file.txt",
        "SOURCE_INPUT_FILE": "/input/path/file.txt",
        "SOURCE_FINGERPRINT_SHA256": "hash",
        "CLASSIFICATION": "document",
        "FILE_FORMAT": "txt",
        "PROCESSED_AT": "2026-03-31T00:00:00Z",
        "EXTRACTION_ENGINE": "plain-text",
        "EXTRACTION_STATUS": "ok",
        "CONTENT_BODY": "normalized body",
    }
    rendered = render_bundle_markdown(None, fields)
    assert "00042" in rendered
    assert "normalized body" in rendered
    assert "source_done_file" in rendered


def test_render_bundle_markdown_delegates_to_render_helper(tmp_path: Path) -> None:
    """Ensure render wrapper delegates to i2d_content_render helper."""
    fields = {"ITEM_CODE": "00001", "CONTENT_BODY": "x"}

    with patch(
        "i2d_content._render.render_bundle_markdown",
        return_value="delegated",
    ) as render_mock:
        result = i2d_content.render_bundle_markdown(tmp_path / "tpl.md", fields)

    assert result == "delegated"
    args, kwargs = render_mock.call_args
    assert args == (tmp_path / "tpl.md", fields)
    assert kwargs["default_template"] == i2d_content._DEFAULT_TEMPLATE


# ---------------------------------------------------------------------------
# EML extraction
# ---------------------------------------------------------------------------


def _make_eml(
    tmp_path: Path, subject: str, body: str, content_type: str = "text/plain"
) -> Path:
    """Write a minimal single-part EML file and return its path."""
    p = tmp_path / "sample.eml"
    p.write_bytes(
        textwrap.dedent(f"""\
            From: sender@example.com
            To: recipient@example.com
            Subject: {subject}
            MIME-Version: 1.0
            Content-Type: {content_type}; charset=utf-8

            {body}
        """).encode("utf-8")
    )
    return p


def test_extract_eml_plain_text_body(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_eml_plain_text_body."""
    p = _make_eml(tmp_path, "Hello EML", "This is the email body.")
    content, engine, status = _extract_eml(p)
    assert engine == "eml-parser"
    assert status == "ok"
    assert "Hello EML" in content
    assert "This is the email body." in content
    assert "## Email Headers" in content
    assert "## Email Body" in content


def test_extract_eml_via_extract_content(tmp_path: Path) -> None:
    """extract_content must route .eml to the EML parser (not markitdown)."""
    p = _make_eml(tmp_path, "Invoice Ready", "Please review the attached invoice.")
    content, engine, status = extract_content(p)
    assert engine == "eml-parser"
    assert status == "ok"
    assert "Invoice Ready" in content


def test_extract_eml_html_body_is_converted_to_text(tmp_path: Path) -> None:
    """HTML-only EML bodies should be converted to readable plain text."""
    p = _make_eml(
        tmp_path,
        "HTML EML",
        "<html><body><p>Hello <b>World</b></p></body></html>",
        content_type="text/html",
    )

    content, engine, status = _extract_eml(p)

    assert engine == "eml-parser"
    assert status == "ok"
    assert "HTML EML" in content
    assert "Hello World" in content


# ---------------------------------------------------------------------------
# markitdown/error fallthrough for images and video
# ---------------------------------------------------------------------------


def test_extract_content_image_falls_through_on_markitdown_error(
    tmp_path: Path,
) -> None:
    """When markitdown returns error for an image, OCR must be attempted."""
    p = tmp_path / "test.heic"
    p.write_bytes(b"\x00\x00\x00\x18ftyp")  # minimal fake HEIC header

    # Simulate markitdown returning error (as with real HEIC)
    with patch(
        "i2d_content._extract_with_markitdown",
        return_value=("md error text", "markitdown", "error"),
    ):
        with patch(
            "i2d_content._extract_image_ocr", return_value=("ocr text", "ocr", "ok")
        ) as mock_ocr:
            content, engine, status = extract_content(p)

    mock_ocr.assert_called_once_with(p)
    assert engine == "ocr+form-local"
    assert status == "ok"
    assert "Local Form Analysis" in content


def test_extract_content_video_falls_through_on_markitdown_error(
    tmp_path: Path,
) -> None:
    """When markitdown returns error for a video, Whisper must be attempted."""
    p = tmp_path / "test.mp4"
    p.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    with patch(
        "i2d_content._extract_with_markitdown",
        return_value=("md error text", "markitdown", "error"),
    ):
        with patch(
            "i2d_content._extract_whisper", return_value=("transcript", "whisper", "ok")
        ) as mock_whisper:
            _content, engine, status = extract_content(p)

    mock_whisper.assert_called_once_with(p)
    assert engine == "whisper"
    assert status == "ok"


def test_extract_content_audio_falls_through_on_markitdown_transcript_error(
    tmp_path: Path,
) -> None:
    """Audio placeholder transcript errors from markitdown must trigger Whisper."""
    p = tmp_path / "test.mp3"
    p.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    with patch(
        "i2d_content._extract_with_markitdown",
        return_value=(
            "## Extracted Text\n\n### Audio Transcript:\nError. Could not transcribe this audio.",
            "markitdown",
            "ok",
        ),
    ):
        with patch(
            "i2d_content._extract_whisper",
            return_value=("whisper transcript", "whisper", "ok"),
        ) as mock_whisper:
            _content, engine, status = extract_content(p)

    mock_whisper.assert_called_once_with(p)
    assert engine == "whisper"
    assert status == "ok"


# ---------------------------------------------------------------------------
# URL list .txt file routing
# ---------------------------------------------------------------------------


def test_extract_content_url_list_txt_routes_to_link_extractor(tmp_path: Path) -> None:
    """A .txt file containing only URLs must be handled by the link extractor."""
    p = tmp_path / "links.txt"
    p.write_text("https://example.com\n", encoding="utf-8")

    with patch("i2d_link.is_url_list_file", return_value=True):
        with patch(
            "i2d_link.extract_url_list",
            return_value=("link content", "link-extractor", "ok"),
        ) as mock_link:
            _content, engine, status = extract_content(p)

    mock_link.assert_called_once_with(p)
    assert engine == "link-extractor"
    assert status == "ok"


def test_extract_content_plain_txt_not_urls_uses_plain_text(tmp_path: Path) -> None:
    """A .txt file with non-URL content must still be handled as plain text."""
    p = tmp_path / "notes.txt"
    p.write_text("These are plain notes, not URLs.", encoding="utf-8")

    with patch("i2d_link.is_url_list_file", return_value=False):
        content, engine, status = extract_content(p)

    assert engine == "plain-text"
    assert status == "ok"
    assert "plain notes" in content


def test_extract_content_image_combines_ocr_and_vision_when_available(
    tmp_path: Path,
) -> None:
    """Image extraction should combine OCR and vision when both are available."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    with patch(
        "i2d_content._extract_with_markitdown", return_value=("", "markitdown", "error")
    ):
        with patch(
            "i2d_vision.classify_image",
            return_value=('{"labels":["cat"]}', "vision-copilot", "ok"),
        ):
            with patch(
                "i2d_content._extract_image_ocr",
                return_value=("## OCR Text\n\nhello", "ocr", "ok"),
            ) as ocr_mock:
                content, engine, status = extract_content(p)

    ocr_mock.assert_called_once_with(p)
    assert engine == "ocr+vision-copilot"
    assert status == "ok"
    assert "Vision Analysis" in content
    assert "OCR Text" in content


def test_extract_content_image_prefers_vision_for_clear_form_and_noisy_ocr(
    tmp_path: Path,
) -> None:
    """Noisy OCR should be omitted when vision form detection is high confidence."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    noisy_ocr = "## OCR Text\n\na\nbe\nrt\nxy\nzz\nq\n"
    vision_json = (
        '{"contains_form": true, "contains_text": true, '
        '"detected_fields": [{"label": "User", "value": "", "confidence": "high"}], '
        '"detected_text_lines": ["User", "Password", "Enter"]}'
    )

    with patch(
        "i2d_content._extract_with_markitdown", return_value=("", "markitdown", "error")
    ):
        with patch(
            "i2d_content._extract_image_ocr", return_value=(noisy_ocr, "ocr", "ok")
        ):
            with patch(
                "i2d_vision.classify_image",
                return_value=(vision_json, "vision-copilot", "ok"),
            ):
                content, engine, status = extract_content(p)

    assert engine == "vision-copilot"
    assert status == "ok"
    assert "Detected Form (normalized)" in content
    assert "OCR output omitted" in content
    assert "## OCR Text" not in content


def test_extract_content_image_falls_back_to_ocr_when_vision_unavailable(
    tmp_path: Path,
) -> None:
    """TODO: add docstring for test_extract_content_image_falls_back_to_ocr_when_vision_unavailable."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    with patch(
        "i2d_content._extract_with_markitdown", return_value=("", "markitdown", "error")
    ):
        with patch(
            "i2d_vision.classify_image",
            return_value=("no creds", "vision", "unavailable"),
        ):
            with patch(
                "i2d_content._extract_image_ocr", return_value=("ocr text", "ocr", "ok")
            ) as ocr_mock:
                content, engine, status = extract_content(p)

    ocr_mock.assert_called_once_with(p)
    assert engine == "ocr+form-local"
    assert status == "ok"
    assert "Local Form Analysis" in content


def test_extract_content_image_uses_vision_when_ocr_is_empty(tmp_path: Path) -> None:
    """Vision should be used when OCR yields no text."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    with patch(
        "i2d_content._extract_with_markitdown", return_value=("", "markitdown", "error")
    ):
        with patch(
            "i2d_content._extract_image_ocr",
            return_value=("## OCR Text\n\n(no text detected)", "ocr", "empty"),
        ):
            with patch(
                "i2d_vision.classify_image",
                return_value=('{"summary":"form sketch"}', "vision-digital", "ok"),
            ):
                content, engine, status = extract_content(p)

    assert engine == "vision-digital"
    assert status == "ok"
    assert "OCR Status" in content
    assert "Vision Analysis" in content


def test_extract_whisper_empty_mentions_model(tmp_path: Path) -> None:
    """Whisper empty output should include the model name for troubleshooting."""
    p = tmp_path / "sample.mp3"
    p.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x00")

    class _Info:
        language = "en"

    class _WhisperModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, *args, **kwargs):
            """TODO: add docstring for transcribe."""
            return iter(()), _Info()

    fake_fw = ModuleType("faster_whisper")
    fake_fw.WhisperModel = _WhisperModel  # type: ignore[attr-defined]

    with patch.dict(sys.modules, {"faster_whisper": fake_fw}):
        with patch.dict("os.environ", {"I2D_WHISPER_MODEL": "tiny"}, clear=False):
            content, engine, status = i2d_content._extract_whisper(p)

    assert engine == "whisper"
    assert status == "empty"
    assert "models=tiny" in content


def test_extract_image_ocr_cli_timeout_returns_unavailable(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_image_ocr_cli_timeout_returns_unavailable."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    builtin_import = __import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name in {"PIL", "pytesseract"}:
            raise ImportError("missing")
        return builtin_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch("builtins.__import__", side_effect=_fake_import):
        with patch(
            "i2d_content._run_command_with_timeout",
            return_value=("", "command timed out after 20s"),
        ):
            content, engine, status = _extract_image_ocr(p)

    assert engine == "ocr"
    assert status == "unavailable"
    assert "timed out" in content


def test_extract_image_ocr_pytesseract_uses_configured_timeout(tmp_path: Path) -> None:
    """TODO: add docstring for test_extract_image_ocr_pytesseract_uses_configured_timeout."""
    p = tmp_path / "img.png"
    p.write_bytes(b"fakepng")

    captured: dict[str, int] = {}

    class _ImageCtx:
        def __enter__(self) -> "_ImageCtx":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return

        def convert(self, mode: str) -> "_ImageCtx":
            """TODO: add docstring for convert."""
            assert mode == "RGB"
            return self

    class _ImageModule:
        @staticmethod
        def open(path: Path) -> _ImageCtx:
            """TODO: add docstring for open."""
            assert path.exists()
            return _ImageCtx()

    fake_pil = ModuleType("PIL")
    fake_pil.Image = _ImageModule  # type: ignore[attr-defined]

    fake_pytesseract = ModuleType("pytesseract")

    def _image_to_string(_img: object, timeout: int) -> str:
        captured["timeout"] = timeout
        return "detected text"

    fake_pytesseract.image_to_string = _image_to_string  # type: ignore[attr-defined]

    with patch.dict(sys.modules, {"PIL": fake_pil, "pytesseract": fake_pytesseract}):
        with patch.dict("os.environ", {"I2D_OCR_TIMEOUT_SECONDS": "7"}, clear=False):
            content, engine, status = _extract_image_ocr(p)

    assert captured["timeout"] == 7
    assert engine == "ocr"
    assert status == "ok"
    assert "detected text" in content


def test_extract_eml_binary_attachment_metadata_included(tmp_path: Path) -> None:
    """Binary EML attachments should be listed with metadata and digest."""
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Attachment test"
    msg.set_content("Body text")
    msg.add_attachment(
        b"%PDF-1.4\n%demo",
        maintype="application",
        subtype="pdf",
        filename="invoice.pdf",
    )
    p = tmp_path / "attachment.eml"
    p.write_bytes(msg.as_bytes())

    content, engine, status = _extract_eml(p)

    assert engine == "eml-parser"
    assert status == "ok"
    assert "## Email Attachments" in content
    assert "name: invoice.pdf" in content
    assert "content_type: application/pdf" in content
    assert "sha256:" in content


def test_extract_content_epub_filters_css_zip_noise(tmp_path: Path) -> None:
    """EPUB markitdown output should prefer chapter content over CSS blobs."""
    p = tmp_path / "book.epub"
    p.write_bytes(b"PK\x03\x04")

    markitdown_output = (
        "Content from the zip file `book.epub`:\n\n"
        "## File: EPUB/styles/stylesheet1.css\n"
        "body { color: black; }\n\n"
        "## File: EPUB/text/chapter1.xhtml\n"
        "<h1>Chapter 1</h1>\n<p>Hello world</p>\n"
    )

    with patch(
        "i2d_content._extract_with_markitdown",
        return_value=(
            f"## File Facts\n\n- file_name: book.epub\n\n## Extracted Text\n\n{markitdown_output}",
            "markitdown",
            "ok",
        ),
    ):
        content, engine, status = extract_content(p)

    assert engine == "markitdown"
    assert status == "ok"
    assert "chapter1.xhtml" in content
    assert "stylesheet1.css" not in content


def test_extract_image_ocr_empty_includes_raw_form_template(tmp_path: Path) -> None:
    """When OCR returns empty text, emit a raw form template for manual fill-in."""
    p = tmp_path / "form.png"
    p.write_bytes(b"fakepng")

    class _ImageCtx:
        def __enter__(self) -> "_ImageCtx":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return

        def convert(self, mode: str) -> "_ImageCtx":
            """TODO: add docstring for convert."""
            assert mode == "RGB"
            return self

    class _ImageModule:
        @staticmethod
        def open(path: Path) -> _ImageCtx:
            """TODO: add docstring for open."""
            assert path.exists()
            return _ImageCtx()

    fake_pil = ModuleType("PIL")
    fake_pil.Image = _ImageModule  # type: ignore[attr-defined]

    fake_pytesseract = ModuleType("pytesseract")
    fake_pytesseract.image_to_string = lambda _img, timeout: ""  # type: ignore[attr-defined]

    with patch.dict(sys.modules, {"PIL": fake_pil, "pytesseract": fake_pytesseract}):
        content, engine, status = _extract_image_ocr(p)

    assert engine == "ocr"
    assert status == "empty"
    assert "Raw Form Template" in content


def test_build_form_markdown_from_text_description_delegates_to_helper() -> None:
    """TODO: add docstring for test_build_form_markdown_from_text_description_delegates_to_helper."""
    expected = SimpleNamespace(value=True)

    with patch(
        "i2d_content._form_text.build_form_markdown_from_text_description",
        return_value=expected,
    ) as helper_mock:
        result = i2d_content._build_form_markdown_from_text_description("login form")

    assert result is expected
    assert helper_mock.call_count == 1
    args, kwargs = helper_mock.call_args
    assert args == ("login form",)
    assert (
        kwargs["extract_form_fields_fn"] is i2d_content._extract_form_fields_from_text
    )
