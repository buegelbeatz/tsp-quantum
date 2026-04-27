"""Unit tests for i2d_content_helpers delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_helpers as helpers  # noqa: E402


def test_run_command_delegates_to_commands_module() -> None:
    """Ensure _run_command delegates to i2d_content_commands module."""
    with patch(
        "i2d_content_helpers._commands.run_command",
        return_value=("out", "err"),
    ) as cmd_mock:
        result = helpers._run_command(["echo", "x"])

    assert result == ("out", "err")
    cmd_mock.assert_called_once_with(["echo", "x"])


def test_run_command_with_timeout_delegates_to_commands_module() -> None:
    """Ensure timeout wrapper delegates to i2d_content_commands module."""
    with patch(
        "i2d_content_helpers._commands.run_command_with_timeout",
        return_value=("out", ""),
    ) as timeout_mock:
        result = helpers._run_command_with_timeout(["echo", "x"], 7)

    assert result == ("out", "")
    timeout_mock.assert_called_once_with(["echo", "x"], 7)


def test_extract_ocr_plain_text_delegates_to_ocr_quality_module() -> None:
    """Ensure OCR plain text extraction delegates to quality helper module."""
    with patch(
        "i2d_content_helpers._ocr_quality.extract_ocr_plain_text",
        return_value="plain",
    ) as ocr_mock:
        result = helpers._extract_ocr_plain_text("md")

    assert result == "plain"
    ocr_mock.assert_called_once_with("md")


def test_is_low_quality_ocr_text_delegates_to_ocr_quality_module() -> None:
    """Ensure OCR quality check delegates with extractor injection."""
    with patch(
        "i2d_content_helpers._ocr_quality.is_low_quality_ocr_text",
        return_value=True,
    ) as quality_mock:
        result = helpers._is_low_quality_ocr_text("md")

    assert result is True
    args, kwargs = quality_mock.call_args
    assert args == ("md",)
    assert kwargs["extract_plain_text_fn"] is helpers._extract_ocr_plain_text


def test_extract_json_payload_delegates_to_vision_form_module() -> None:
    """Ensure JSON payload parser delegates to vision/form helper module."""
    with patch(
        "i2d_content_helpers._vision_form.extract_json_payload",
        return_value={"k": "v"},
    ) as json_mock:
        result = helpers._extract_json_payload("raw")

    assert result == {"k": "v"}
    json_mock.assert_called_once_with("raw")


def test_build_form_markdown_from_vision_delegates_to_vision_form_module() -> None:
    """Ensure vision-form markdown builder delegates to helper module."""
    payload: dict[str, object] = {"contains_form": True}
    with patch(
        "i2d_content_helpers._vision_form.build_form_markdown_from_vision",
        return_value="md",
    ) as form_mock:
        result = helpers._build_form_markdown_from_vision(payload)

    assert result == "md"
    form_mock.assert_called_once_with(payload)


def test_should_prefer_vision_form_delegates_to_vision_form_module() -> None:
    """Ensure vision preference check delegates with OCR-quality injection."""
    payload: dict[str, object] = {"contains_form": True}
    with patch(
        "i2d_content_helpers._vision_form.should_prefer_vision_form",
        return_value=True,
    ) as prefer_mock:
        result = helpers._should_prefer_vision_form(payload, "ocr")

    assert result is True
    args, kwargs = prefer_mock.call_args
    assert args == (payload, "ocr")
    assert kwargs["is_low_quality_ocr_text_fn"] is helpers._is_low_quality_ocr_text
