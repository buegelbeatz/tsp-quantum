"""Unit tests for i2d_content_commands registry-backed execution."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_commands as commands  # noqa: E402


def test_run_command_status_uses_registry_for_registered_missing_tool(
    tmp_path: Path,
) -> None:
    """Registered tools should use the shared/shell runner when local binary is missing."""
    repo_root = tmp_path / "repo"
    shared_shell = repo_root / ".github" / "skills" / "shared/shell" / "scripts"
    shared_shell.mkdir(parents=True)
    run_tool = shared_shell / "run-tool.sh"
    run_tool.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    tools_csv = shared_shell / "metadata" / "tools.csv"
    tools_csv.parent.mkdir(parents=True)
    tools_csv.write_text(
        "tool_name,min_version,public_container,install_help_mac,install_help_windows\n"
        "ffprobe,6.0,jrottenberg/ffmpeg:6.1-alpine,brew install ffmpeg,winget install Gyan.FFmpeg\n",
        encoding="utf-8",
    )
    media = repo_root / "10-data" / "sample.mp3"

    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        """TODO: add docstring for fake_run."""
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

    with patch.object(commands, "_REPO_ROOT", repo_root):
        with patch.object(commands, "_RUN_TOOL", run_tool):
            with patch.object(commands, "_TOOLS_CSV", tools_csv):
                with patch("i2d_content_commands.shutil.which", return_value=None):
                    with patch(
                        "i2d_content_commands.subprocess.run", side_effect=fake_run
                    ):
                        stdout, stderr, returncode = commands.run_command_status(
                            ["ffprobe", "-i", str(media)]
                        )

    assert stdout == "ok"
    assert stderr == ""
    assert returncode == 0
    assert captured["cwd"] == repo_root
    assert captured["command"] == [
        "bash",
        str(run_tool),
        "ffprobe",
        "-i",
        "/workspace/10-data/sample.mp3",
    ]


def test_run_command_status_uses_local_subprocess_for_unregistered_tool() -> None:
    """Unregistered tools should keep local subprocess behavior."""
    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        """TODO: add docstring for fake_run."""
        captured["command"] = command
        captured["timeout"] = kwargs.get("timeout")
        return SimpleNamespace(stdout="x\n", stderr="", returncode=0)

    with patch.object(commands, "_is_registered_tool", return_value=False):
        with patch("i2d_content_commands.subprocess.run", side_effect=fake_run):
            stdout, stderr, returncode = commands.run_command_status(["echo", "x"])

    assert stdout == "x"
    assert stderr == ""
    assert returncode == 0
    assert captured["command"] == ["echo", "x"]
    assert captured["timeout"] is None
