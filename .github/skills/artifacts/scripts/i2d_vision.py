"""Image classification helpers with provider fallback routing.

Purpose:
    Classify images using external vision APIs with automatic provider fallback.
    Tries GitHub Models → DIGITAL_TEAM_VISION_API_URL → Claude Messages API in sequence.

Security:
    Requires environment credentials (GH_TOKEN, CLAUDE_TOKEN) for API access.
    Sends images only to configured endpoints. Validates provider availability before use.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import i2d_vision_api as _vision_api
import i2d_vision_flow as _vision_flow

_DEFAULT_GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
_DEFAULT_GITHUB_MODELS_MODEL = "gpt-4o-mini"
_DEFAULT_CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
_DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-latest"


def _guess_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix in {".heic", ".heif"}:
        return "image/heic"
    if suffix in {".tif", ".tiff"}:
        return "image/tiff"
    if suffix == ".bmp":
        return "image/bmp"
    return "application/octet-stream"


def _prepare_image_payload(path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) with compatibility conversion for vision APIs."""
    media_type = _guess_media_type(path)
    raw_bytes = path.read_bytes()

    # Many vision APIs reject HEIC/TIFF/BMP inputs. Convert to PNG when possible.
    if media_type in {
        "image/heic",
        "image/tiff",
        "image/bmp",
        "application/octet-stream",
    }:
        try:
            from PIL import Image  # type: ignore[import-untyped]
        except ImportError:
            return base64.b64encode(raw_bytes).decode("utf-8"), media_type

        try:
            try:
                from pillow_heif import register_heif_opener  # type: ignore[import-untyped]

                register_heif_opener()
            except ImportError:
                pass

            with Image.open(io.BytesIO(raw_bytes)) as img:
                converted = io.BytesIO()
                img.convert("RGB").save(converted, format="PNG")
            return base64.b64encode(converted.getvalue()).decode("utf-8"), "image/png"
        except (OSError, ValueError, RuntimeError):
            return base64.b64encode(raw_bytes).decode("utf-8"), media_type

    return base64.b64encode(raw_bytes).decode("utf-8"), media_type


def _image_prompt() -> str:
    return _vision_api.image_prompt()


def _vision_provider_order() -> list[str]:
    return _vision_api.vision_provider_order()


def _call_openai_compatible(
    endpoint: str, api_key: str, model: str, image_b64: str, media_type: str
) -> str:
    return _vision_api.call_openai_compatible(
        endpoint,
        api_key,
        model,
        image_b64,
        media_type,
        image_prompt_fn=_image_prompt,
    )


def _call_claude(
    endpoint: str, api_key: str, model: str, image_b64: str, media_type: str
) -> str:
    return _vision_api.call_claude(
        endpoint,
        api_key,
        model,
        image_b64,
        media_type,
        image_prompt_fn=_image_prompt,
    )


def classify_image(path: Path) -> tuple[str, str, str]:
    """Classify image with provider fallback chain.

    Returns tuple ``(content, engine, status)``:
    - status ``ok`` when one provider returned content
    - status ``unavailable`` when no provider has valid credentials
    - status ``error`` when providers are configured but all calls failed
    """
    return _vision_flow.classify_image(
        path,
        prepare_image_payload_fn=_prepare_image_payload,
        vision_provider_order_fn=_vision_provider_order,
        call_openai_compatible_fn=_call_openai_compatible,
        call_claude_fn=_call_claude,
        default_github_models_url=_DEFAULT_GITHUB_MODELS_URL,
        default_github_models_model=_DEFAULT_GITHUB_MODELS_MODEL,
        default_claude_api_url=_DEFAULT_CLAUDE_API_URL,
        default_claude_model=_DEFAULT_CLAUDE_MODEL,
    )
