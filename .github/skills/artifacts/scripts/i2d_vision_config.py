"""Configuration helpers for vision API providers."""

from __future__ import annotations

import os


def image_prompt() -> str:
    """Return instruction prompt for image classification providers."""
    return (
        "Analyze this image for artifact ingestion with strict uncertainty handling. "
        "Do not guess missing or unreadable text. "
        "Return concise JSON with keys: "
        "contains_form (true|false), "
        "contains_text (true|false), "
        "detected_text_lines (array of short strings, empty if unreadable), "
        "detected_fields (array of objects {label, value, confidence} where confidence is high|medium|low), "
        "labels (array of 3-8 short tags), "
        "suggested_type (feature|bug|document), "
        "summary (1-2 sentences)."
    )


def vision_provider_order() -> list[str]:
    """Return provider order from environment with deterministic default."""
    raw = os.getenv("VISION_PROVIDER_ORDER", "copilot,digital,claude")
    providers = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return providers or ["copilot", "digital", "claude"]
