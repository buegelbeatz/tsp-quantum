"""Shared test helpers for GitHub shell wrapper regression tests."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def repo_root() -> Path:
    """Locate repository root by searching for the layer marker directory."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = repo_root()


def write_executable(path: Path, content: str) -> Path:
    """Write executable shell content to path and return the same path."""
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def build_env(
    *, path_prefix: Path | None = None, gh_token: str | None = None
) -> dict[str, str]:
    """Build deterministic environment for GitHub shell test execution."""
    env = os.environ.copy()
    env["DIGITAL_TEAM_SKIP_DOTENV"] = "1"
    if gh_token is None:
        env.pop("GH_TOKEN", None)
    else:
        env["GH_TOKEN"] = gh_token
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}:/usr/local/bin:/usr/bin:/bin"
    return env
