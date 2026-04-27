"""Unit tests for i2d_content_extract_flow delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_extract_flow as extract_flow  # noqa: E402


def test_extract_content_txt_delegates_to_text_flow(tmp_path: Path) -> None:
    """Ensure txt branch delegates to text-flow helper with injected functions."""
    p = tmp_path / "notes.txt"
    p.write_text("hello", encoding="utf-8")

    with patch(
        "i2d_content_extract_flow._text_flow.extract_text_content",
        return_value=("body", "plain-text", "ok"),
    ) as text_mock:
        result = extract_flow.extract_content(
            p,
            file_facts_fn=lambda _path: "facts",
            extract_eml_fn=lambda _path: ("", "", ""),
            extract_with_markitdown_fn=lambda _path: ("", "", ""),
            cleanup_epub_markitdown_content_fn=lambda t: t,
            markitdown_contains_transcript_error_fn=lambda _c: False,
            extract_image_ocr_fn=lambda _path: ("", "", ""),
            extract_json_payload_fn=lambda _text: None,
            build_form_markdown_from_vision_fn=lambda _payload: None,
            should_prefer_vision_form_fn=lambda _payload, _ocr: False,
            build_local_form_analysis_fn=lambda _ocr, _status, _path: "",
            extract_whisper_fn=lambda _path: ("", "", ""),
            build_form_markdown_from_text_description_fn=lambda _text: None,
            image_suffixes={".png"},
            audio_suffixes={".mp3"},
            video_suffixes={".mp4"},
            eml_suffixes={".eml"},
        )

    assert result == ("body", "plain-text", "ok")
    args, kwargs = text_mock.call_args
    assert args == (p,)
    assert kwargs["is_url_list_file_fn"].__name__ == "is_url_list_file"
    assert kwargs["extract_url_list_fn"].__name__ == "extract_url_list"


def test_extract_content_image_delegates_to_image_flow(tmp_path: Path) -> None:
    """Ensure image branch delegates to image-flow helper with injected functions."""
    p = tmp_path / "photo.png"
    p.write_bytes(b"fake")

    with patch(
        "i2d_content_extract_flow._image_flow.extract_image_content",
        return_value=("body", "vision", "ok"),
    ) as image_mock:
        result = extract_flow.extract_content(
            p,
            file_facts_fn=lambda _path: "facts",
            extract_eml_fn=lambda _path: ("", "", ""),
            extract_with_markitdown_fn=lambda _path: ("", "", "error"),
            cleanup_epub_markitdown_content_fn=lambda t: t,
            markitdown_contains_transcript_error_fn=lambda _c: False,
            extract_image_ocr_fn=lambda _path: ("", "", ""),
            extract_json_payload_fn=lambda _text: None,
            build_form_markdown_from_vision_fn=lambda _payload: None,
            should_prefer_vision_form_fn=lambda _payload, _ocr: False,
            build_local_form_analysis_fn=lambda _ocr, _status, _path: "",
            extract_whisper_fn=lambda _path: ("", "", ""),
            build_form_markdown_from_text_description_fn=lambda _text: None,
            image_suffixes={".png"},
            audio_suffixes={".mp3"},
            video_suffixes={".mp4"},
            eml_suffixes={".eml"},
        )

    assert result == ("body", "vision", "ok")
    kwargs = image_mock.call_args.kwargs
    assert image_mock.call_args.args == (p,)
    assert kwargs["file_facts_fn"](p) == "facts"
