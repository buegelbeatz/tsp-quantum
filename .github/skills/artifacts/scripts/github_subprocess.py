"""GitHub CLI subprocess execution helpers.

Purpose:
    Centralize gh command execution and error handling.
    Provide consistent subprocess interface for GitHub operations.

Security:
    Executes only subprocess.run with safe argument passing.
    Returns both stdout and stderr combined for debugging.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_command(
    args: list[str], env: dict[str, str], cwd: Path | None = None
) -> tuple[bool, str]:
    """Execute a subprocess command and return (success, output).

    Args:
        args: Command and arguments as list.
        env: Environment dict for subprocess execution.
        cwd: Optional working directory.

    Returns:
        Tuple of (success: bool, combined_output: str).
        Returns (False, error_msg) if subprocess raises OSError.
    """
    try:
        completed = subprocess.run(
            args,
            check=False,
            text=True,
            capture_output=True,
            env=env,
            cwd=cwd,
        )
    except OSError as exc:
        return False, str(exc)

    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, output.strip()


def run_gh_command(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
    """Execute a gh CLI command in the current directory.

    Args:
        args: gh command arguments (starting with ["gh", ...]).
        env: Environment dict with GITHUB_TOKEN set.

    Returns:
        Tuple of (success: bool, output: str).
    """
    return run_command(args, env)
