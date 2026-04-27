"""Tests for MCP registry launch and config generation scripts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mcp_test_support import GEN_SCRIPT, LAUNCH_SCRIPT, ROOT, create_fake_server


def test_mcp_launch_executes_registered_server(tmp_path: Path) -> None:
    """Verify registry-backed launch executes a local fake MCP server."""

    server = create_fake_server(tmp_path)
    registry = tmp_path / "mcp-servers.csv"
    registry.write_text(
        "server_id;image_or_command;transport;domain;description\n"
        f"local-test;{server};stdio;testing;Local test server\n",
        encoding="utf-8",
    )
    args_file = tmp_path / "args.yaml"
    args_file.write_text("x: 1\n", encoding="utf-8")
    output_file = tmp_path / "result.json"

    env = os.environ.copy()
    env["MCP_REGISTRY_CSV"] = str(registry)
    result = subprocess.run(
        [
            "bash",
            str(LAUNCH_SCRIPT),
            "--server-id",
            "local-test",
            "--tool",
            "echo-tool",
            "--args-file",
            str(args_file),
            "--output-file",
            str(output_file),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'kind: "mcp_tool_call"' in result.stdout
    assert json.loads(output_file.read_text(encoding="utf-8"))["ok"] is True


def test_mcp_generate_vscode_config_from_registry(tmp_path: Path) -> None:
    """Verify MCP registry entries render into VS Code MCP config."""

    registry = tmp_path / "mcp-servers.csv"
    registry.write_text(
        "server_id;image_or_command;transport;domain;description\n"
        "alpha;python -m alpha.server;stdio;general;Alpha\n",
        encoding="utf-8",
    )
    output = tmp_path / "mcp.json"

    env = os.environ.copy()
    env["MCP_REGISTRY_CSV"] = str(registry)
    env["MCP_VSCODE_CONFIG"] = str(output)
    env["MCP_VSCODE_MODE"] = "all"
    result = subprocess.run(
        ["bash", str(GEN_SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config = json.loads(output.read_text(encoding="utf-8"))
    assert config["servers"]["alpha"]["command"] == "python"


def test_mcp_generate_vscode_config_disabled_mode(tmp_path: Path) -> None:
    """Disabled mode must generate an empty servers map."""

    registry = tmp_path / "mcp-servers.csv"
    registry.write_text(
        "server_id;image_or_command;transport;domain;description\n"
        "alpha;python -m alpha.server;stdio;general;Alpha\n",
        encoding="utf-8",
    )
    output = tmp_path / "mcp.json"

    env = os.environ.copy()
    env["MCP_REGISTRY_CSV"] = str(registry)
    env["MCP_VSCODE_CONFIG"] = str(output)
    env["MCP_VSCODE_MODE"] = "disabled"
    result = subprocess.run(
        ["bash", str(GEN_SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config = json.loads(output.read_text(encoding="utf-8"))
    assert config["servers"] == {}


def test_mcp_generate_vscode_config_allowlist_mode(tmp_path: Path) -> None:
    """Allowlist mode must include only selected server ids."""

    registry = tmp_path / "mcp-servers.csv"
    registry.write_text(
        "server_id;image_or_command;transport;domain;description\n"
        "alpha;python -m alpha.server;stdio;general;Alpha\n"
        "beta;python -m beta.server;stdio;general;Beta\n",
        encoding="utf-8",
    )
    output = tmp_path / "mcp.json"

    env = os.environ.copy()
    env["MCP_REGISTRY_CSV"] = str(registry)
    env["MCP_VSCODE_CONFIG"] = str(output)
    env["MCP_VSCODE_MODE"] = "allowlist"
    env["MCP_VSCODE_SERVERS"] = "beta"
    result = subprocess.run(
        ["bash", str(GEN_SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config = json.loads(output.read_text(encoding="utf-8"))
    assert sorted(config["servers"].keys()) == ["beta"]
