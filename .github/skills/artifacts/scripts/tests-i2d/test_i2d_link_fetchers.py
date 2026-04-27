"""Unit tests for i2d_link_fetchers helper delegations."""

from __future__ import annotations

import sys
from unittest.mock import patch
from pathlib import Path

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_link_fetchers as fetchers  # noqa: E402


def test_fetch_klaxoon_api_delegates_to_klaxoon_helper() -> None:
    """Klaxoon API wrapper should delegate to dedicated helper module."""
    with patch(
        "i2d_link_fetchers._klaxoon_api.fetch_klaxoon_api",
        return_value=("content", "ok"),
    ) as helper_mock:
        result = fetchers.fetch_klaxoon_api("kmntyg4")

    assert result == ("content", "ok")
    helper_mock.assert_called_once_with("kmntyg4")
