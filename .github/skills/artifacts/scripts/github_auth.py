"""GitHub authentication token resolution and environment setup.

Purpose:
    Centralize GitHub token discovery from environment variables and .env files.
    Provide consistent environment setup for gh CLI and subprocess execution.

Security:
    Reads tokens only from standard GitHub env vars and local .env file.
    Never logs or returns tokens directly in error messages.
"""

from __future__ import annotations

import os
from pathlib import Path


def read_env_file_token(env_file: Path) -> tuple[str | None, str | None]:
    """Read GH token from .env-style file without loading unrelated variables.

    Args:
        env_file: Path to .env file.

    Returns:
        Tuple of (token_value, source_var_name) or (None, None) if not found.
    """
    if not env_file.exists():
        return None, None
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in {"GITHUB_TOKEN", "GH_TOKEN"}:
            continue
        token = value.strip().strip('"').strip("'")
        if token:
            return token, key
    return None, None


def resolve_github_token(
    repo_root: Path | None = None,
) -> tuple[str | None, str | None]:
    """Return available GitHub token and its source env var name.

    Priority:
        1. GITHUB_TOKEN env var
        2. GH_TOKEN env var
        3. Token in repo_root/.env file

    Args:
        repo_root: Optional repo root. If None, derived from this module's location.

    Returns:
        Tuple of (token_value, source_var_name) or (None, None) if not found.
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        return github_token, "GITHUB_TOKEN"

    gh_token = os.getenv("GH_TOKEN")
    if gh_token:
        return gh_token, "GH_TOKEN"

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[4]

    file_token, file_source = read_env_file_token(repo_root / ".env")
    if file_token and file_source:
        return file_token, file_source

    return None, None


def build_github_env(token: str) -> dict[str, str]:
    """Build environment dict for gh CLI and GitHub subprocess calls.

    Args:
        token: GitHub authentication token.

    Returns:
        Environment dict with GITHUB_TOKEN and GH_TOKEN set.
    """
    env = os.environ.copy()
    env["GITHUB_TOKEN"] = token
    env["GH_TOKEN"] = token
    return env
