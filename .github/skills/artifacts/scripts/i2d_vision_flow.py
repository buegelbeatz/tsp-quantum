"""Provider fallback flow helper for i2d_vision."""

from __future__ import annotations

import os
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_OPENAI_ERRORS = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    OSError,
    ValueError,
    KeyError,
)
_UNCONFIGURED = object()  # sentinel for missing config


@dataclass
class ClassifyImageDeps:
    """Bundled dependency-injection bag for classify_image."""

    prepare_image_payload_fn: Any
    vision_provider_order_fn: Any
    call_openai_compatible_fn: Any
    call_claude_fn: Any
    default_github_models_url: str
    default_github_models_model: str
    default_claude_api_url: str
    default_claude_model: str


def _try_openai_provider(
    name: str,
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    call_openai_compatible_fn,
) -> tuple[str, str, str] | None:
    """Try a single OpenAI-compatible provider. Returns result tuple or None."""
    try:
        text = call_openai_compatible_fn(
            endpoint, api_key, model, image_b64, media_type
        )
        if text:
            return text, f"vision-{name}", "ok"
        return None
    except _OPENAI_ERRORS:
        return None


def _try_claude_provider(
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    call_claude_fn,
) -> tuple[str, str, str] | None:
    """Try the Claude provider. Returns result tuple or None."""
    try:
        text = call_claude_fn(endpoint, api_key, model, image_b64, media_type)
        if text:
            return text, "vision-claude", "ok"
        return None
    except _OPENAI_ERRORS:
        return None


def _try_provider_block(
    provider_name: str,
    env_url_var: str,
    env_key_var: str,
    env_model_var: str,
    default_url: str,
    default_model: str,
    image_b64: str,
    media_type: str,
    is_claude: bool,
    call_openai_fn,
    call_claude_fn,
) -> tuple[bool, str, tuple[str, str, str] | None]:
    """Try a single provider block. Returns (configured, engine_name, result_or_none)."""
    endpoint = os.getenv(env_url_var, default_url if not is_claude else default_url)
    api_key = os.getenv(env_key_var, "")
    # Special case: copilot can fall back to GH_TOKEN
    if provider_name == "copilot" and not api_key:
        api_key = os.getenv("GH_TOKEN", "")
    model = os.getenv(env_model_var, default_model)

    if not endpoint or not api_key:
        return False, "", None

    if is_claude:
        result = _try_claude_provider(
            endpoint, api_key, model, image_b64, media_type, call_claude_fn
        )
        return True, provider_name, result
    else:
        result = _try_openai_provider(
            provider_name,
            endpoint,
            api_key,
            model,
            image_b64,
            media_type,
            call_openai_fn,
        )
        return True, provider_name, result


def _handle_provider(
    provider_name: str,
    env_url_var: str,
    env_key_var: str,
    env_model_var: str,
    default_url: str,
    default_model: str,
    image_b64: str,
    media_type: str,
    is_claude: bool,
    deps: ClassifyImageDeps,
) -> tuple[bool, str, tuple[str, str, str] | None]:
    """Handle a single provider. Returns (configured, error_msg, result_or_none)."""
    configured, _, result = _try_provider_block(
        provider_name,
        env_url_var,
        env_key_var,
        env_model_var,
        default_url,
        default_model,
        image_b64,
        media_type,
        is_claude,
        deps.call_openai_compatible_fn,
        deps.call_claude_fn,
    )
    if not configured:
        return False, "", None
    if result:
        return True, "", result
    return True, f"{provider_name}: empty response or error", None


def _process_provider_chain(
    deps: ClassifyImageDeps,
    image_b64: str,
    media_type: str,
) -> tuple[int, list[str], tuple[str, str, str] | None]:
    """Process all configured vision providers. Returns (configured_count, errors, result_or_none)."""
    providers_config = [
        (
            "copilot",
            "GITHUB_MODELS_VISION_API_URL",
            "GITHUB_MODELS_VISION_API_KEY",
            "GITHUB_MODELS_VISION_MODEL",
            deps.default_github_models_url,
            deps.default_github_models_model,
            False,
        ),
        (
            "digital",
            "DIGITAL_TEAM_VISION_API_URL",
            "DIGITAL_TEAM_VISION_API_KEY",
            "DIGITAL_TEAM_VISION_MODEL",
            deps.default_github_models_url,
            deps.default_github_models_model,
            False,
        ),
        (
            "claude",
            "CLAUDE_VISION_API_URL",
            "CLAUDE_TOKEN",
            "CLAUDE_VISION_MODEL",
            deps.default_claude_api_url,
            deps.default_claude_model,
            True,
        ),
    ]
    errors: list[str] = []
    configured_count = 0

    for provider in deps.vision_provider_order_fn():
        for (
            name,
            url_var,
            key_var,
            model_var,
            default_url,
            default_model,
            is_claude,
        ) in providers_config:
            if name == provider:
                configured, error, result = _handle_provider(
                    name,
                    url_var,
                    key_var,
                    model_var,
                    default_url,
                    default_model,
                    image_b64,
                    media_type,
                    is_claude,
                    deps,
                )
                if configured:
                    configured_count += 1
                    if result:
                        return configured_count, errors, result
                    if error:
                        errors.append(error)

    return configured_count, errors, None


def classify_image_impl(path: Path, deps: ClassifyImageDeps) -> tuple[str, str, str]:
    """Implementation of classify_image using deps."""
    image_b64, media_type = deps.prepare_image_payload_fn(path)
    configured_count, errors, result = _process_provider_chain(
        deps, image_b64, media_type
    )

    if result:
        return result

    if configured_count == 0:
        return (
            "Vision classification unavailable (no provider credentials configured).",
            "vision",
            "unavailable",
        )

    return "Vision classification failed: " + " | ".join(errors), "vision", "error"


def classify_image(
    path: Path,
    *,
    prepare_image_payload_fn,
    vision_provider_order_fn,
    call_openai_compatible_fn,
    call_claude_fn,
    default_github_models_url: str,
    default_github_models_model: str,
    default_claude_api_url: str,
    default_claude_model: str,
) -> tuple[str, str, str]:
    """Classify image with provider fallback chain."""
    deps = ClassifyImageDeps(
        prepare_image_payload_fn=prepare_image_payload_fn,
        vision_provider_order_fn=vision_provider_order_fn,
        call_openai_compatible_fn=call_openai_compatible_fn,
        call_claude_fn=call_claude_fn,
        default_github_models_url=default_github_models_url,
        default_github_models_model=default_github_models_model,
        default_claude_api_url=default_claude_api_url,
        default_claude_model=default_claude_model,
    )
    return classify_image_impl(path, deps)
