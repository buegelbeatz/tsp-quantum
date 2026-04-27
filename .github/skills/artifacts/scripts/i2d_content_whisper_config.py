"""Configuration helpers for whisper extraction."""

from __future__ import annotations

import os


def _split_models(raw_value: str) -> list[str]:
    """Split comma-separated model names and discard empty items."""
    return [name.strip() for name in raw_value.split(",") if name.strip()]


def _read_models_env() -> list[str]:
    """Read prioritized model list from I2D_WHISPER_MODELS."""
    return _split_models(os.getenv("I2D_WHISPER_MODELS", "").strip())


def _read_primary_env() -> str:
    """Read fallback primary model string from I2D_WHISPER_MODEL."""
    return os.getenv("I2D_WHISPER_MODEL", "base,small").strip() or "base,small"


def get_model_names() -> list[str]:
    """Return configured whisper model list from environment."""
    if model_names := _read_models_env():
        return model_names

    primary = _read_primary_env()
    primary_models = _split_models(primary)
    if primary_models:
        return primary_models
    return [primary]
