"""Command execution helpers for i2d content extraction."""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUN_TOOL = (
    _REPO_ROOT / ".github" / "skills" / "shared/shell" / "scripts" / "run-tool.sh"
)
_TOOLS_CSV = (
    _REPO_ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "metadata"
    / "tools.csv"
)


def _is_registered_tool(tool_name: str) -> bool:
    """Return True when a tool is present in the shared/shell registry."""
    try:
        with _TOOLS_CSV.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return any(row.get("tool_name") == tool_name for row in reader)
    except OSError:
        return False


def _translate_arg_for_workspace(arg: str) -> str:
    """Translate repo-local absolute paths to the shared container mount path."""
    candidate = Path(arg)
    if not candidate.is_absolute():
        return arg

    try:
        relative = candidate.resolve(strict=False).relative_to(
            _REPO_ROOT.resolve(strict=False)
        )
    except ValueError:
        return arg

    if str(relative) == ".":
        return "/workspace"
    return f"/workspace/{relative.as_posix()}"


def _run_via_tool_registry(
    command: list[str],
    *,
    timeout_seconds: int | None = None,
) -> tuple[str, str, int]:
    """Run a registered tool through shared/shell to enable container fallback."""
    translated_args = [_translate_arg_for_workspace(arg) for arg in command[1:]]
    env = os.environ.copy()
    env.setdefault("RUN_TOOL_PREFER_CONTAINER", "1")

    result = subprocess.run(
        ["bash", str(_RUN_TOOL), command[0], *translated_args],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _should_use_registry(tool_name: str) -> bool:
    """Determine whether command should run via shared/shell registry."""
    return _is_registered_tool(tool_name) and (
        os.getenv("RUN_TOOL_PREFER_CONTAINER") == "1" or shutil.which(tool_name) is None
    )


def _run_direct_command(
    command: list[str],
    timeout_seconds: int | None = None,
) -> tuple[str, str, int]:
    """Run command directly on host and return normalized output tuple."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_command_status(
    command: list[str],
    timeout_seconds: int | None = None,
) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and exit status."""
    if not command:
        return "", "empty command", 127

    tool_name = command[0]

    try:
        if _should_use_registry(tool_name):
            return _run_via_tool_registry(command, timeout_seconds=timeout_seconds)

        return _run_direct_command(command, timeout_seconds=timeout_seconds)
    except subprocess.TimeoutExpired:
        timeout_label = timeout_seconds if timeout_seconds is not None else "unknown"
        return "", f"command timed out after {timeout_label}s", 124
    except OSError as exc:
        return "", str(exc), 127


def run_command(command: list[str]) -> tuple[str, str]:
    """Run a command and return (stdout, stderr) as text."""
    stdout, stderr, _returncode = run_command_status(command)
    return stdout, stderr


def run_command_with_timeout(
    command: list[str],
    timeout_seconds: int,
) -> tuple[str, str]:
    """Run a command with timeout and return (stdout, stderr) as text."""
    stdout, stderr, _returncode = run_command_status(
        command,
        timeout_seconds=timeout_seconds,
    )
    return stdout, stderr
