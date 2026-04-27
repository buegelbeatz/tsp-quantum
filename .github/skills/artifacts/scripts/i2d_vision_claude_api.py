"""Claude vision API call helpers."""

from __future__ import annotations

import json
import urllib.request

_ANTHROPIC_VERSION = "2023-06-01"


def _build_claude_payload(
    model: str, image_b64: str, media_type: str, image_prompt: str
) -> dict:
    """Build the request payload for the Claude Messages API."""
    return {
        "model": model,
        "max_tokens": 400,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": image_prompt},
                ],
            }
        ],
    }


def _extract_claude_text(raw: dict) -> str:
    """Extract the first text block from a Claude Messages API response."""
    content = raw.get("content", [])
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("text", "")).strip()
    return ""


def call_claude(
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    *,
    image_prompt: str,
) -> str:
    """Call Claude Messages API for vision classification."""
    payload = _build_claude_payload(model, image_b64, media_type, image_prompt)
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
        raw = json.loads(response.read().decode("utf-8"))
    return _extract_claude_text(raw)
