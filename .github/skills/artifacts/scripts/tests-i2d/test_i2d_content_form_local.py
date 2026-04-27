"""Unit tests for i2d_content_form_local helper delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_form_local as form_local  # noqa: E402


def test_extract_form_fields_from_text_delegates_to_field_helper() -> None:
    """Field extraction wrapper should delegate to dedicated helper module."""
    with patch(
        "i2d_content_form_local._form_fields.extract_form_fields_from_text",
        return_value=[("Name", "Alice")],
    ) as fields_mock:
        result = form_local.extract_form_fields_from_text("Name: Alice")

    assert result == [("Name", "Alice")]
    fields_mock.assert_called_once_with("Name: Alice")


def test_local_visual_signals_delegates_to_visual_helper(tmp_path: Path) -> None:
    """Ensure local visual signal wrapper delegates to visual helper module."""
    image = tmp_path / "img.png"
    image.write_bytes(b"fake")

    with patch(
        "i2d_content_form_local._form_visual.local_visual_signals",
        return_value=(3, 1),
    ) as visual_mock:
        result = form_local.local_visual_signals(image)

    assert result == (3, 1)
    visual_mock.assert_called_once_with(image)


def test_build_local_form_analysis_uses_injected_helpers(tmp_path: Path) -> None:
    """Build analysis should call injected extraction and visual helper functions."""
    source = tmp_path / "form.png"
    source.write_bytes(b"fake")

    def fields_mock(_text: str) -> list[tuple[str, str]]:
        """TODO: add docstring for fields_mock."""
        return [("Name", "")]

    def visual_mock(_path: Path) -> tuple[int, int]:
        """TODO: add docstring for visual_mock."""
        return (2, 1)

    report = form_local.build_local_form_analysis(
        "Name:\n",
        "ok",
        source,
        extract_form_fields_fn=fields_mock,
        local_visual_signals_fn=visual_mock,
    )

    assert "contains_form: true" in report
    assert "detected_fields: 1" in report
    assert "detected_input_boxes: 2" in report
    assert "| Name |  |" in report
