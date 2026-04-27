"""OpenAI-compatible vision API call helpers."""

from __future__ import annotations

import json
import urllib.request


def call_openai_compatible(
    endpoint: str,
    api_key: str,
    model: str,
    image_b64: str,
    media_type: str,
    *,
    image_prompt: str,
) -> str:
    """Call OpenAI-compatible vision endpoint and return response content."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": image_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 400,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
        raw = json.loads(response.read().decode("utf-8"))
    return str(raw["choices"][0]["message"]["content"]).strip()
