"""Klaxoon REST API fetch helpers for link extraction."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_CREDENTIALS_MISSING_TEMPLATE = (
    "Klaxoon board `{code}` requires OAuth 2.0 credentials.\n\n"
    "Configure the following variables in your `.env` file to enable import:\n\n"
    "```\nKLAXOON_CLIENT_ID=<your-client-id>\n"
    "KLAXOON_CLIENT_SECRET=<your-client-secret>\n"
    "KLAXOON_API_URL=https://api.klaxoon.com/v1\n```"
)


def _get_access_token(client_id: str, client_secret: str, token_url: str) -> str:
    """Exchange client credentials for an OAuth 2.0 access token."""
    payload = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "board:read",
        }
    ).encode()
    req = urllib.request.Request(
        token_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return json.loads(resp.read()).get("access_token", "")


def _fetch_board_markdown(
    board_share_code: str, api_url: str, auth_headers: dict[str, str]
) -> str:
    """Fetch board metadata and ideas; return markdown summary."""
    board_req = urllib.request.Request(
        f"{api_url}/boards/{board_share_code}", headers=auth_headers
    )
    with urllib.request.urlopen(board_req, timeout=15) as resp:  # noqa: S310
        board_data = json.loads(resp.read())

    ideas_req = urllib.request.Request(
        f"{api_url}/boards/{board_share_code}/ideas", headers=auth_headers
    )
    with urllib.request.urlopen(ideas_req, timeout=15) as resp:  # noqa: S310
        ideas_raw = json.loads(resp.read())

    ideas = (
        ideas_raw.get("items", ideas_raw) if isinstance(ideas_raw, dict) else ideas_raw
    )
    title = board_data.get("title", board_share_code)
    description = board_data.get("description", "")

    md_lines: list[str] = [f"# Klaxoon Board: {title}"]
    if description:
        md_lines.append(f"\n{description}")
    md_lines.append(f"\n## Ideas ({len(ideas)} items)\n")
    for idea in ideas:
        content = idea.get("content", "")
        cat = idea.get("category") or {}
        label = cat.get("label", "") if isinstance(cat, dict) else ""
        prefix = f"[{label}] " if label else ""
        md_lines.append(f"- {prefix}{content}")

    return "\n".join(md_lines)


def fetch_klaxoon_api(board_share_code: str) -> tuple[str, str]:
    """Fetch Klaxoon board content via REST API."""
    client_id = os.getenv("KLAXOON_CLIENT_ID", "")
    client_secret = os.getenv("KLAXOON_CLIENT_SECRET", "")
    api_url = os.getenv("KLAXOON_API_URL", "https://api.klaxoon.com/v1").rstrip("/")
    token_url = os.getenv("KLAXOON_TOKEN_URL", f"{api_url}/oauth/token")

    if not client_id or not client_secret:
        return _CREDENTIALS_MISSING_TEMPLATE.format(
            code=board_share_code
        ), "credentials-missing"

    try:
        access_token = _get_access_token(client_id, client_secret, token_url)
        if not access_token:
            return (
                f"Klaxoon board `{board_share_code}` — token exchange failed: no `access_token` in response.",
                "auth-error",
            )
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        return _fetch_board_markdown(board_share_code, api_url, auth_headers), "ok"
    except urllib.error.HTTPError as exc:
        return (
            f"Klaxoon board `{board_share_code}` — HTTP {exc.code}: {exc.reason}",
            "error",
        )
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        return f"Klaxoon board `{board_share_code}` — API call failed: {exc}", "error"
