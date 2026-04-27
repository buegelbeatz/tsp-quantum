"""Unit tests for i2d_vision_api helper delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_vision_api as vision_api  # noqa: E402


def test_image_prompt_delegates_to_config_helper() -> None:
    """image_prompt wrapper should delegate to vision config helper."""
    with patch(
        "i2d_vision_api._vision_config.image_prompt",
        return_value="prompt",
    ) as helper_mock:
        result = vision_api.image_prompt()

    assert result == "prompt"
    helper_mock.assert_called_once_with()


def test_vision_provider_order_delegates_to_config_helper() -> None:
    """vision_provider_order wrapper should delegate to vision config helper."""
    with patch(
        "i2d_vision_api._vision_config.vision_provider_order",
        return_value=["copilot"],
    ) as helper_mock:
        result = vision_api.vision_provider_order()

    assert result == ["copilot"]
    helper_mock.assert_called_once_with()


def test_call_openai_compatible_delegates_to_transport_helper() -> None:
    """OpenAI-compatible wrapper should delegate HTTP transport to helper module."""
    with patch(
        "i2d_vision_api._openai_api.call_openai_compatible",
        return_value="ok-openai",
    ) as helper_mock:
        result = vision_api.call_openai_compatible(
            "https://example.com/chat",
            "key",
            "model",
            "abc",
            "image/png",
            image_prompt_fn=lambda: "prompt",
        )

    assert result == "ok-openai"
    helper_mock.assert_called_once_with(
        "https://example.com/chat",
        "key",
        "model",
        "abc",
        "image/png",
        image_prompt="prompt",
    )


def test_call_claude_delegates_to_transport_helper() -> None:
    """Claude wrapper should delegate HTTP transport to helper module."""
    with patch(
        "i2d_vision_api._claude_api.call_claude",
        return_value="ok-claude",
    ) as helper_mock:
        result = vision_api.call_claude(
            "https://api.anthropic.com/v1/messages",
            "key",
            "model",
            "abc",
            "image/png",
            image_prompt_fn=lambda: "prompt",
        )

    assert result == "ok-claude"
    helper_mock.assert_called_once_with(
        "https://api.anthropic.com/v1/messages",
        "key",
        "model",
        "abc",
        "image/png",
        image_prompt="prompt",
    )
