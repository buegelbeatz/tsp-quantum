"""Vision provider API helpers for image classification."""

from __future__ import annotations

import i2d_vision_claude_api as _claude_api
import i2d_vision_config as _vision_config
import i2d_vision_openai_api as _openai_api


def image_prompt() -> str:
    """Return instruction prompt for image classification providers."""
    return _vision_config.image_prompt()


def vision_provider_order() -> list[str]:
    """Return provider order from environment with deterministic default."""
    return _vision_config.vision_provider_order()


def call_openai_compatible(
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    *,
    image_prompt_fn=None,
) -> str:
    """Call OpenAI-compatible vision endpoint and return response content."""
    if image_prompt_fn is None:
        image_prompt_fn = image_prompt
    return _openai_api.call_openai_compatible(
        endpoint,
        api_key,
        model,
        image_b64,
        media_type,
        image_prompt=image_prompt_fn(),
    )


def call_claude(
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    *,
    image_prompt_fn=None,
) -> str:
    """Call Claude Messages API for vision classification."""
    if image_prompt_fn is None:
        image_prompt_fn = image_prompt
    return _claude_api.call_claude(
        endpoint,
        api_key,
        model,
        image_b64,
        media_type,
        image_prompt=image_prompt_fn(),
    )
