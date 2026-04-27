"""Vision/LLM API integration for text processing."""

from __future__ import annotations

import json
import os
import urllib.request


_SYSTEM_PROMPT = """\
You are an Agile Coach assistant. Given colloquial text (any language), respond
with a JSON object containing exactly these keys:
- "translation": the text translated to clear English
- "inferred_type": one of "feature", "bug", or "project"
- "research_hints": a list of 2-4 concise search terms or URLs to investigate
- "review_note": one sentence for the downstream planning agent summarizing what
  needs further specification

Respond ONLY with valid JSON, no markdown fences."""


def vision_api_call(prompt: str, content: str) -> str:
    """Call the configured Vision/LLM API and return the response text."""
    api_url = os.environ.get("DIGITAL_TEAM_VISION_API_URL", "")
    api_key = os.environ.get("DIGITAL_TEAM_VISION_API_KEY", "")
    model = os.environ.get("DIGITAL_TEAM_VISION_MODEL", "gpt-4o-mini")

    if not api_url or not api_key:
        raise RuntimeError(
            "DIGITAL_TEAM_VISION_API_URL or DIGITAL_TEAM_VISION_API_KEY not set"
        )

    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
            "max_tokens": 800,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/json", "api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def system_prompt() -> str:
    """Return the system prompt for text classification."""
    return _SYSTEM_PROMPT
